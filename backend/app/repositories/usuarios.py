from datetime import datetime, timezone

from sqlmodel import Session, col, delete, select

from app.models import (
    Acompanhamento,
    ColetaRecurso,
    Consentimento,
    Conta,
    Divida,
    Evento,
    Fatura,
    Plano,
    PlanoItem,
    RendaDetectada,
    Sessao,
    Transacao,
    Usuario,
)


def por_id(session: Session, usuario_id: int) -> Usuario | None:
    u = session.get(Usuario, usuario_id)
    return u if u and u.excluido_em is None else None


def por_email(session: Session, email: str) -> Usuario | None:
    return session.exec(
        select(Usuario).where(Usuario.email == email.strip().lower(), col(Usuario.excluido_em).is_(None))
    ).first()


def por_cpf(session: Session, cpf: str) -> Usuario | None:
    return session.exec(select(Usuario).where(Usuario.cpf == cpf, col(Usuario.excluido_em).is_(None))).first()


def criar(session: Session, usuario: Usuario) -> Usuario:
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


def salvar(session: Session, usuario: Usuario) -> Usuario:
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


# --- sessões ----------------------------------------------------------------------


def criar_sessao(session: Session, usuario_id: int, token_hash: str, expira_em: datetime) -> None:
    session.add(Sessao(usuario_id=usuario_id, token_hash=token_hash, expira_em=expira_em))
    session.commit()


def usuario_da_sessao(session: Session, token_hash: str) -> Usuario | None:
    sessao = session.exec(select(Sessao).where(Sessao.token_hash == token_hash)).first()
    if sessao is None:
        return None
    expira = sessao.expira_em if sessao.expira_em.tzinfo else sessao.expira_em.replace(tzinfo=timezone.utc)
    if expira <= datetime.now(timezone.utc):
        session.delete(sessao)
        session.commit()
        return None
    return por_id(session, sessao.usuario_id)


def apagar_sessao(session: Session, token_hash: str) -> None:
    session.exec(delete(Sessao).where(col(Sessao.token_hash) == token_hash))  # type: ignore[call-overload]
    session.commit()


# --- exclusão real (§12.8) -----------------------------------------------------------


def apagar_dados_financeiros(session: Session, usuario_id: int) -> None:
    """Apaga tudo que veio dos bancos ou do plano — mantém só o cadastro e o login."""
    consent_ids = list(
        session.exec(select(Consentimento.id).where(Consentimento.usuario_id == usuario_id))
    )
    plano_ids = list(session.exec(select(Plano.id).where(Plano.usuario_id == usuario_id)))
    for stmt in (
        delete(PlanoItem).where(col(PlanoItem.plano_id).in_(plano_ids)),
        delete(Acompanhamento).where(col(Acompanhamento.plano_id).in_(plano_ids)),
        delete(Plano).where(col(Plano.usuario_id) == usuario_id),
        delete(Evento).where(col(Evento.usuario_id) == usuario_id),
        delete(Transacao).where(col(Transacao.usuario_id) == usuario_id),
        delete(Divida).where(col(Divida.usuario_id) == usuario_id),
        delete(Fatura).where(col(Fatura.usuario_id) == usuario_id),
        delete(Conta).where(col(Conta.usuario_id) == usuario_id),
        delete(ColetaRecurso).where(col(ColetaRecurso.consentimento_id).in_(consent_ids)),
        delete(RendaDetectada).where(col(RendaDetectada.consentimento_id).in_(consent_ids)),
        delete(Consentimento).where(col(Consentimento.usuario_id) == usuario_id),
    ):
        session.exec(stmt)  # type: ignore[call-overload]
    session.commit()


def apagar_tudo(session: Session, usuario_id: int) -> None:
    """Exclusão de conta: dados, sessões e o próprio cadastro (linhas apagadas, não marcadas)."""
    apagar_dados_financeiros(session, usuario_id)
    session.exec(delete(Sessao).where(col(Sessao.usuario_id) == usuario_id))  # type: ignore[call-overload]
    session.exec(delete(Usuario).where(col(Usuario.id) == usuario_id))  # type: ignore[call-overload]
    session.commit()
