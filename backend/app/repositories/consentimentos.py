from collections.abc import Iterable
from datetime import datetime, timedelta

from sqlmodel import Session, col, delete, select

from app.models import (
    ColetaRecurso,
    Consentimento,
    Conta,
    Divida,
    Fatura,
    Instituicao,
    Recurso,
    RendaDetectada,
    StatusColeta,
    StatusConsentimento,
    TipoInstituicao,
    Transacao,
    agora,
)
from app.providers.mapping import InstituicaoCatalogo


def instituicao(session: Session, codigo: str, nome: str, tipo: TipoInstituicao) -> Instituicao:
    """Busca ou cria. Nunca sobrescreve o nome de uma instituição que já existe:
    para bancos, o nome vem do catálogo da Belvo (fonte da verdade)."""
    inst = session.exec(select(Instituicao).where(Instituicao.codigo_externo == codigo)).first()
    if inst is None:
        inst = Instituicao(codigo_externo=codigo, nome=nome, tipo=tipo)
        session.add(inst)
        session.flush()
    return inst


def instituicao_por_codigo(session: Session, codigo: str) -> Instituicao | None:
    return session.exec(select(Instituicao).where(Instituicao.codigo_externo == codigo)).first()


def ultima_atualizacao_catalogo(session: Session) -> datetime | None:
    return session.exec(
        select(Instituicao.catalogo_em)
        .where(col(Instituicao.catalogo_em).is_not(None))
        .order_by(col(Instituicao.catalogo_em).desc())
    ).first()


def aplicar_catalogo(session: Session, itens: Iterable[InstituicaoCatalogo]) -> int:
    """Upsert do catálogo da Belvo. Se o nome de um banco já conectado mudar
    (ex.: "ofnubank_br_retail" → "Nubank"), as descrições das dívidas dele, que
    levam o nome do banco, acompanham."""
    momento = agora()
    total = 0
    for item in itens:
        inst = instituicao_por_codigo(session, item.codigo)
        if inst is None:
            inst = Instituicao(codigo_externo=item.codigo, nome=item.nome, tipo=TipoInstituicao.BANCO)
        elif inst.nome != item.nome and inst.id is not None:
            antigo = inst.nome
            for d in session.exec(select(Divida).where(Divida.instituicao_id == inst.id)):
                if antigo in d.descricao:
                    d.descricao = d.descricao.replace(antigo, item.nome)[:120]
                    session.add(d)
        inst.nome = item.nome
        inst.logo_url = item.logo_url
        inst.icone_url = item.icone_url
        inst.catalogo_em = momento
        session.add(inst)
        total += 1
    session.commit()
    return total


def obter_instituicao(session: Session, instituicao_id: int | None) -> Instituicao | None:
    return session.get(Instituicao, instituicao_id) if instituicao_id else None


def criar_pendente(session: Session, usuario_id: int) -> Consentimento:
    c = Consentimento(usuario_id=usuario_id)
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


def ultimo_pendente(session: Session, usuario_id: int, janela: timedelta) -> Consentimento | None:
    limite = agora() - janela
    return session.exec(
        select(Consentimento)
        .where(
            Consentimento.usuario_id == usuario_id,
            Consentimento.status == StatusConsentimento.PENDENTE,
            col(Consentimento.criado_em) >= limite,
        )
        .order_by(col(Consentimento.criado_em).desc())
    ).first()


def por_link(session: Session, link: str) -> Consentimento | None:
    return session.exec(select(Consentimento).where(Consentimento.link_externo == link)).first()


def por_id(session: Session, usuario_id: int, consentimento_id: int) -> Consentimento | None:
    c = session.get(Consentimento, consentimento_id)
    return c if c and c.usuario_id == usuario_id else None


def listar(session: Session, usuario_id: int) -> list[Consentimento]:
    return list(
        session.exec(
            select(Consentimento)
            .where(
                Consentimento.usuario_id == usuario_id,
                Consentimento.status != StatusConsentimento.PENDENTE,
            )
            .order_by(col(Consentimento.criado_em))
        )
    )


def ativos(session: Session) -> list[Consentimento]:
    return list(
        session.exec(
            select(Consentimento).where(
                Consentimento.status == StatusConsentimento.ATIVO,
                col(Consentimento.link_externo).is_not(None),
            )
        )
    )


def salvar(session: Session, c: Consentimento) -> Consentimento:
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


def descartar_pendentes_antigos(session: Session, usuario_id: int, janela: timedelta) -> None:
    limite = agora() - janela
    session.exec(  # type: ignore[call-overload]
        delete(Consentimento).where(
            col(Consentimento.usuario_id) == usuario_id,
            col(Consentimento.status) == StatusConsentimento.PENDENTE,
            col(Consentimento.criado_em) < limite,
        )
    )
    session.commit()


# --- coleta por recurso (tela de espera, §7.5) ----------------------------------


def iniciar_coleta(session: Session, consentimento_id: int, estados: dict[Recurso, StatusColeta]) -> None:
    for recurso, status in estados.items():
        existente = session.exec(
            select(ColetaRecurso).where(
                ColetaRecurso.consentimento_id == consentimento_id, ColetaRecurso.recurso == recurso
            )
        ).first()
        if existente is None:
            session.add(ColetaRecurso(consentimento_id=consentimento_id, recurso=recurso, status=status))
    session.commit()


def marcar_recurso(session: Session, consentimento_id: int, recurso: Recurso, status: StatusColeta) -> None:
    item = session.exec(
        select(ColetaRecurso).where(
            ColetaRecurso.consentimento_id == consentimento_id, ColetaRecurso.recurso == recurso
        )
    ).first()
    if item is None:
        item = ColetaRecurso(consentimento_id=consentimento_id, recurso=recurso)
    item.status = status
    item.atualizado_em = agora()
    session.add(item)
    session.commit()


def coleta(session: Session, consentimento_id: int) -> list[ColetaRecurso]:
    return list(
        session.exec(select(ColetaRecurso).where(ColetaRecurso.consentimento_id == consentimento_id))
    )


def apagar_dados_do_link(session: Session, c: Consentimento) -> None:
    """Revogação (§7.10, §12.8): apaga os dados locais daquele link de verdade.
    Fica só o registro mínimo do consentimento (instituição + data da revogação),
    sem nenhum dado financeiro."""
    assert c.id is not None
    for stmt in (
        delete(Transacao).where(col(Transacao.consentimento_id) == c.id),
        delete(Divida).where(col(Divida.consentimento_id) == c.id),
        delete(Fatura).where(col(Fatura.consentimento_id) == c.id),
        delete(Conta).where(col(Conta.consentimento_id) == c.id),
        delete(ColetaRecurso).where(col(ColetaRecurso.consentimento_id) == c.id),
        delete(RendaDetectada).where(col(RendaDetectada.consentimento_id) == c.id),
    ):
        session.exec(stmt)  # type: ignore[call-overload]
    c.status = StatusConsentimento.REVOGADO
    c.revogado_em = agora()
    c.link_externo = None
    c.ultima_sync_em = None
    session.add(c)
    session.commit()


def marcar_sync(session: Session, c: Consentimento, quando: datetime | None = None) -> None:
    c.ultima_sync_em = quando or agora()
    session.add(c)
    session.commit()
