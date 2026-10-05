"""Rotas exclusivas da conta de demonstração (Juliana).

Toda rota aqui exige estar logado numa conta ``demo``: uma conta real nunca
vê widget simulado, relógio adiantado ou reinício de dados.
"""

from fastapi import APIRouter, HTTPException, status

from app.providers.base import ErroProvedor
from app.routers.analise import _plano_ativo_out
from app.routers.comum import SessionDep, UsuarioDemoDep
from app.schemas import (
    AutorizarFixtureEntrada,
    AutorizarFixtureOut,
    DemoAvancarEntrada,
    PlanoAtivoOut,
)
from app.services import analise, demo
from app.services.contexto import fixture

router = APIRouter(tags=["demonstração"])


@router.post("/fixture/widget/autorizar", response_model=AutorizarFixtureOut)
def autorizar(dados: AutorizarFixtureEntrada, u: UsuarioDemoDep) -> AutorizarFixtureOut:
    """O widget simulado chama isto quando a Juliana "autoriza no banco"."""
    try:
        link = fixture().autorizar(dados.access_token, dados.instituicao, u.uuid_externo)
    except ErroProvedor as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=e.codigo) from e
    return AutorizarFixtureOut(link=link, institution=dados.instituicao)


@router.post("/demo/avancar-mes", response_model=PlanoAtivoOut)
def avancar_mes(dados: DemoAvancarEntrada, u: UsuarioDemoDep, s: SessionDep) -> PlanoAtivoOut:
    try:
        analise.avancar_mes_demo(s, u, dados.mes_dificil)
    except analise.PlanoInviavel as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="sem_plano") from e
    r = analise.plano_ativo(s, u)
    assert r is not None
    return _plano_ativo_out(s, r)


@router.post("/demo/reiniciar", status_code=status.HTTP_204_NO_CONTENT)
async def reiniciar(u: UsuarioDemoDep, s: SessionDep) -> None:
    """Volta a Juliana ao começo: dívidas da §2, sem plano, relógio em hoje."""
    await demo.reiniciar(s, u)
