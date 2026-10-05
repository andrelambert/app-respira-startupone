"""Alertas (F4) e microlições (F5)."""

from fastapi import APIRouter, HTTPException, status

from app.models import Evento, TipoEvento
from app.repositories import eventos as repo_e
from app.routers.comum import SessionDep, UsuarioDep
from app.schemas import EventoOut, LicaoOut

router = APIRouter(tags=["alertas e lições"])


def _out(s: SessionDep, e: Evento) -> EventoOut:
    licoes = repo_e.licoes(s, e.tipo)
    assert e.id is not None
    return EventoOut(
        id=e.id,
        tipo=e.tipo,
        severidade=e.severidade,
        divida_id=e.divida_id,
        contexto=e.contexto,
        detectado_em=e.detectado_em,
        notificado_em=e.notificado_em,
        licao=licoes[0].slug if licoes else None,
    )


@router.get("/eventos", response_model=list[EventoOut])
def listar(
    u: UsuarioDep, s: SessionDep, nao_notificados: bool = False, tipo: TipoEvento | None = None
) -> list[EventoOut]:
    assert u.id is not None
    return [_out(s, e) for e in repo_e.listar(s, u.id, nao_notificados=nao_notificados, tipo=tipo)]


@router.post("/eventos/{evento_id}/visto", response_model=EventoOut)
def visto(evento_id: int, u: UsuarioDep, s: SessionDep) -> EventoOut:
    assert u.id is not None
    e = repo_e.marcar_visto(s, u.id, evento_id)
    if e is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return _out(s, e)


@router.get("/licoes", response_model=list[LicaoOut])
def licoes(s: SessionDep, evento: TipoEvento | None = None) -> list[LicaoOut]:
    return [
        LicaoOut(slug=li.slug, titulo=li.titulo, corpo=li.corpo, tipo_evento=li.tipo_evento)
        for li in repo_e.licoes(s, evento)
    ]


@router.get("/licoes/{slug}", response_model=LicaoOut)
def licao(slug: str, s: SessionDep) -> LicaoOut:
    li = repo_e.licao(s, slug)
    if li is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return LicaoOut(slug=li.slug, titulo=li.titulo, corpo=li.corpo, tipo_evento=li.tipo_evento)
