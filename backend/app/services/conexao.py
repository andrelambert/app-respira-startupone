"""Ciclo de vida da conexão: widget → callback → coleta → revogação (docs/contexto-produto.md §7.1–§7.4, §7.10)."""

from __future__ import annotations

import logging
from datetime import timedelta, timezone

from sqlmodel import Session

from app.config import get_settings
from app.models import (
    RECURSOS_ESSENCIAIS,
    Consentimento,
    Recurso,
    StatusColeta,
    StatusConsentimento,
    TipoInstituicao,
    Usuario,
    agora,
)
from app.providers.base import ErroProvedor, IdentificacaoUsuario
from app.repositories import consentimentos as repo_c
from app.services import coleta, instituicoes
from app.services.contexto import provider

log = logging.getLogger("respira.conexao")

# Um token da Belvo vale ~10 min; uma tentativa de conexão pendente vale um
# pouco mais, para cobrir o tempo do usuário dentro do app do banco.
JANELA_PENDENTE = timedelta(minutes=30)


class ErroConexao(Exception):
    def __init__(self, codigo: str) -> None:
        super().__init__(codigo)
        self.codigo = codigo


def _ident(u: Usuario) -> IdentificacaoUsuario:
    return IdentificacaoUsuario(external_id=u.uuid_externo, nome_completo=u.nome_completo, cpf=u.cpf)


async def iniciar(s: Session, u: Usuario, instituicao: str | None = None) -> tuple[Consentimento, str]:
    """Gera o token **no clique** e devolve a URL do widget (§7.2)."""
    assert u.id is not None
    repo_c.descartar_pendentes_antigos(s, u.id, JANELA_PENDENTE)
    try:
        url = await provider(u).criar_url_widget(_ident(u), instituicao)
    except ErroProvedor as e:
        raise ErroConexao(e.codigo) from e
    return repo_c.criar_pendente(s, u.id), url


async def concluir(
    s: Session, u: Usuario, link_id: str, instituicao_codigo: str, *, iniciar_coleta: bool = True
) -> Consentimento:
    """Callback de sucesso (§7.4). Valida o link na Belvo antes de aceitar: o
    ``external_id`` precisa ser o deste usuário, senão alguém poderia anexar o
    link de outra pessoa colando uma URL."""
    assert u.id is not None
    existente = repo_c.por_link(s, link_id)
    if existente is not None:
        return existente  # aba nova e polling chegaram juntos: idempotente

    try:
        info = await provider(u).obter_link(link_id)
    except ErroProvedor as e:
        raise ErroConexao(e.codigo) from e
    if info is None:
        raise ErroConexao("link_nao_encontrado")
    if info.external_id and info.external_id != u.uuid_externo:
        log.warning("callback_external_id_divergente")
        raise ErroConexao("link_de_outro_usuario")

    codigo = info.instituicao_codigo or instituicao_codigo
    inst = repo_c.instituicao(s, codigo, codigo, TipoInstituicao.BANCO)
    if not u.demo and inst.catalogo_em is None:
        # Banco fora do catálogo local: busca agora (nome e logo chegam em segundos).
        instituicoes.agendar(forcar=True)
    if codigo.startswith("fixture_"):
        from app.providers.fixture import INSTITUICOES

        inst.nome = INSTITUICOES.get(codigo, inst.nome)

    c = repo_c.ultimo_pendente(s, u.id, JANELA_PENDENTE) or Consentimento(usuario_id=u.id)
    c.link_externo = link_id
    c.instituicao_id = inst.id
    c.status = StatusConsentimento.ATIVO
    c.concedido_em = agora()
    c.erro_codigo = None
    try:
        consent = await provider(u).obter_consentimento(link_id, _ident(u))
        if consent and consent.expira_em:
            c.expira_em = consent.expira_em.astimezone(timezone.utc)
    except ErroProvedor:
        log.info("consentimento_sem_expiracao_disponivel")
    repo_c.salvar(s, c)

    # Reconexão: o link antigo da mesma instituição sai, com os dados dele —
    # os ids da Belvo mudam por link e o dado duplicaria.
    for antigo in repo_c.listar(s, u.id):
        if antigo.id != c.id and antigo.instituicao_id == inst.id and antigo.status in (
            StatusConsentimento.EXPIRADO, StatusConsentimento.ERRO, StatusConsentimento.ATIVO,
        ):
            await revogar(s, antigo)

    s.refresh(c)
    estados = {r: StatusColeta.AGUARDANDO for r in RECURSOS_ESSENCIAIS}
    if get_settings().belvo_enrichment_enabled and not u.demo:
        estados |= {Recurso.INCOMES: StatusColeta.AGUARDANDO, Recurso.RECURRING_EXPENSES: StatusColeta.AGUARDANDO}
    assert c.id is not None
    repo_c.iniciar_coleta(s, c.id, estados)
    if iniciar_coleta:
        coleta.iniciar(c.id)
    return c


async def revogar(s: Session, c: Consentimento) -> None:
    """Revogação em um toque: ``DELETE /api/links/{id}/`` **e** apaga local (§12.8)."""
    if c.link_externo:
        dono = s.get(Usuario, c.usuario_id)
        assert dono is not None
        try:
            await provider(dono).revogar(c.link_externo)
        except ErroProvedor as e:
            # Não apagamos local sem ter revogado na Belvo: link esquecido
            # continua atualizando e custando.
            raise ErroConexao(e.codigo) from e
    repo_c.apagar_dados_do_link(s, c)


def status_efetivo(c: Consentimento) -> StatusConsentimento:
    """Expiração passada vira EXPIRADO mesmo sem webhook (fonte de verdade é a data)."""
    if c.status == StatusConsentimento.ATIVO and c.expira_em:
        exp = c.expira_em if c.expira_em.tzinfo else c.expira_em.replace(tzinfo=timezone.utc)
        if exp <= agora():
            return StatusConsentimento.EXPIRADO
    return c.status
