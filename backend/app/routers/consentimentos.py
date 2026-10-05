import logging

from fastapi import APIRouter, HTTPException, status

from app.repositories import consentimentos as repo_c
from app.routers.comum import SessionDep, UsuarioDep, consentimento_out
from app.schemas import (
    CallbackEntrada,
    ConsentimentoOut,
    SaidaEntrada,
    WidgetTokenEntrada,
    WidgetTokenOut,
)
from app.services import coleta, conexao

log = logging.getLogger("respira.consentimentos")
router = APIRouter(tags=["conexão"])


@router.post("/consentimentos/widget-token", response_model=WidgetTokenOut)
async def widget_token(dados: WidgetTokenEntrada, u: UsuarioDep, s: SessionDep) -> WidgetTokenOut:
    try:
        c, url = await conexao.iniciar(s, u, dados.instituicao)
    except conexao.ErroConexao as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=e.codigo) from e
    assert c.id is not None
    return WidgetTokenOut(consentimento_id=c.id, widget_url=url)


@router.post("/consentimentos/callback", response_model=ConsentimentoOut)
async def callback(dados: CallbackEntrada, u: UsuarioDep, s: SessionDep) -> ConsentimentoOut:
    try:
        c = await conexao.concluir(s, u, dados.link, dados.institution)
    except conexao.ErroConexao as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=e.codigo) from e
    return consentimento_out(s, c)


@router.post("/consentimentos/saida", status_code=status.HTTP_204_NO_CONTENT)
def saida(dados: SaidaEntrada, u: UsuarioDep, s: SessionDep) -> None:
    """Registra o motivo da saída do widget para diagnóstico (§7.4) e encerra a
    tentativa pendente. Só códigos — nunca a mensagem livre do banco."""
    log.info("widget_saida codigo=%s etapa=%s fatal=%s", dados.codigo, dados.etapa, dados.fatal)
    assert u.id is not None
    if dados.fatal:
        pendente = repo_c.ultimo_pendente(s, u.id, conexao.JANELA_PENDENTE)
        if pendente is not None:
            from app.models import StatusConsentimento

            pendente.status = StatusConsentimento.ERRO
            pendente.erro_codigo = dados.codigo
            repo_c.salvar(s, pendente)


@router.get("/consentimentos", response_model=list[ConsentimentoOut])
def listar(u: UsuarioDep, s: SessionDep) -> list[ConsentimentoOut]:
    assert u.id is not None
    return [consentimento_out(s, c) for c in repo_c.listar(s, u.id)]


@router.get("/consentimentos/{consentimento_id}/coleta", response_model=ConsentimentoOut)
def estado_coleta(consentimento_id: int, u: UsuarioDep, s: SessionDep) -> ConsentimentoOut:
    assert u.id is not None
    c = repo_c.por_id(s, u.id, consentimento_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return consentimento_out(s, c)


@router.delete("/consentimentos/{consentimento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revogar(consentimento_id: int, u: UsuarioDep, s: SessionDep) -> None:
    assert u.id is not None
    c = repo_c.por_id(s, u.id, consentimento_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    try:
        await conexao.revogar(s, c)
    except conexao.ErroConexao as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=e.codigo) from e


@router.post("/sync")
async def sync(u: UsuarioDep) -> dict[str, int]:
    """Força recoleta — fallback quando não há webhook (§7.5)."""
    assert u.id is not None
    return {"itens": await coleta.sincronizar_tudo(u.id)}
