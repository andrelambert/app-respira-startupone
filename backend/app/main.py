"""Respira — API do protótipo (Fase 6).

    uv run uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.config import get_settings
from app.content.licoes import LICOES
from app.db import engine
from app.models import Licao, Usuario
from app.repositories import consentimentos as repo_c
from app.repositories import eventos as repo_e
from app.routers import analise, belvo_webhook, consentimentos, demo, eventos, pfm, usuarios
from app.services import coleta, instituicoes
from app.services.contexto import fixture
from app.services.demo import garantir_juliana

settings = get_settings()
logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
# O httpx loga a URL de cada requisição em INFO — e GET /api/consents/ leva o
# CPF na query. Nunca deixar isso chegar ao log (§12.4).
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("respira")

BACKEND = Path(__file__).resolve().parent.parent


def _migrar() -> None:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    # Sem isto o fileConfig do alembic.ini silencia nossos logs INFO —
    # inclusive o diagnóstico da taxa de juros (§7.7).
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")


def _preparar() -> None:
    with Session(engine) as s:
        repo_e.upsert_licoes(s, [Licao.model_validate(li.model_dump()) for li in LICOES])
        for c in repo_c.ativos(s):
            inst = repo_c.obter_instituicao(s, c.instituicao_id)
            dono = s.get(Usuario, c.usuario_id)
            # Links da demo vivem em memória no FixtureProvider: reidrata.
            if dono and dono.demo and inst and c.link_externo:
                fixture().registrar_link(c.link_externo, inst.codigo_externo, dono.uuid_externo)
            # Coleta interrompida por reinício: retoma.
            if c.id and any(r.status == "AGUARDANDO" for r in repo_c.coleta(s, c.id)):
                coleta.iniciar(c.id)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _migrar()
    _preparar()
    await garantir_juliana()
    instituicoes.agendar()  # catálogo de bancos da Belvo, em segundo plano
    log.info("respira_pronto belvo_configurada=%s", settings.belvo_configurada())
    yield


app = FastAPI(title="Respira API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # nunca "*" (§12.5)
    allow_credentials=True,  # cookie de sessão HttpOnly
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-Respira"],
)


@app.middleware("http")
async def exigir_cabecalho_em_escrita(request: Request, call_next):
    """Defesa contra CSRF: requisição de escrita precisa do cabeçalho
    ``X-Respira``, que força preflight de CORS — um site qualquer não consegue
    disparar ``POST`` contra a API local. O webhook da Belvo é a exceção (tem
    autenticação própria)."""
    if (
        request.method in {"POST", "PATCH", "DELETE"}
        and not request.url.path.startswith("/webhooks/")
        and request.headers.get("x-respira") != "1"
    ):
        return JSONResponse({"detail": "cabecalho_ausente"}, status_code=403)
    return await call_next(request)


app.include_router(usuarios.router)
app.include_router(consentimentos.router)
app.include_router(belvo_webhook.router)
app.include_router(analise.router)
app.include_router(eventos.router)
app.include_router(pfm.router)
app.include_router(demo.router)  # cada rota exige conta demo logada


@app.get("/health", tags=["sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}

