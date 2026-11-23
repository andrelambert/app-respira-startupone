from sqlmodel import Session, col, select

from app.domain.events import EventoDetectado, EventoPendente, grupo
from app.models import Evento, Licao, TipoEvento, WebhookLog, agora


def registrar_se_novo(session: Session, usuario_id: int, e: EventoDetectado) -> Evento | None:
    """Deduplica pela ``chave``: o mesmo fato não vira dois alertas."""
    existe = session.exec(
        select(Evento).where(Evento.usuario_id == usuario_id, Evento.chave == e.chave)
    ).first()
    if existe is not None:
        return None
    ev = Evento(
        usuario_id=usuario_id,
        divida_id=e.divida_id,
        tipo=TipoEvento(e.tipo),
        contexto=e.contexto,
        severidade=e.severidade,
        chave=e.chave,
    )
    session.add(ev)
    # Substituição (A1): só o aviso mais recente de cada grupo fica pendente.
    g = grupo(e.tipo, e.divida_id, e.contexto)
    for antigo in _nao_resolvidos(session, usuario_id, TipoEvento(e.tipo), e.divida_id):
        if antigo is not ev and grupo(antigo.tipo, antigo.divida_id, antigo.contexto) == g:
            antigo.resolvido_em = agora()
            session.add(antigo)
    session.commit()
    session.refresh(ev)
    return ev


def _nao_resolvidos(
    session: Session, usuario_id: int, tipo: TipoEvento | None = None, divida_id: int | None = None
) -> list[Evento]:
    q = select(Evento).where(Evento.usuario_id == usuario_id, col(Evento.resolvido_em).is_(None))
    if tipo is not None:
        q = q.where(Evento.tipo == tipo, Evento.divida_id == divida_id)
    return list(session.exec(q))


def pendentes(session: Session, usuario_id: int) -> list[EventoPendente]:
    return [
        EventoPendente(e.id, e.tipo, e.divida_id, e.contexto)  # type: ignore[arg-type]
        for e in _nao_resolvidos(session, usuario_id)
    ]


def resolver(session: Session, usuario_id: int, ids: list[int]) -> None:
    if not ids:
        return
    for e in session.exec(select(Evento).where(Evento.usuario_id == usuario_id, col(Evento.id).in_(ids))):
        e.resolvido_em = e.resolvido_em or agora()
        session.add(e)
    session.commit()


def atualizar_contextos(session: Session, usuario_id: int, novos: dict[int, dict]) -> None:
    if not novos:
        return
    for e in session.exec(select(Evento).where(Evento.usuario_id == usuario_id, col(Evento.id).in_(list(novos)))):
        e.contexto = novos[e.id]  # type: ignore[index]
        session.add(e)
    session.commit()


def listar(
    session: Session, usuario_id: int, *, nao_notificados: bool = False, tipo: TipoEvento | None = None
) -> list[Evento]:
    q = select(Evento).where(Evento.usuario_id == usuario_id, col(Evento.resolvido_em).is_(None))
    if nao_notificados:
        q = q.where(col(Evento.notificado_em).is_(None))
    if tipo is not None:
        q = q.where(Evento.tipo == tipo)
    return list(session.exec(q.order_by(col(Evento.severidade).desc(), col(Evento.detectado_em).desc())))


def marcar_visto(session: Session, usuario_id: int, evento_id: int) -> Evento | None:
    ev = session.get(Evento, evento_id)
    if ev is None or ev.usuario_id != usuario_id:
        return None
    ev.notificado_em = ev.notificado_em or agora()
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


# --- lições (F5) -----------------------------------------------------------------


def upsert_licoes(session: Session, licoes: list[Licao]) -> None:
    for nova in licoes:
        atual = session.exec(select(Licao).where(Licao.slug == nova.slug)).first()
        if atual is None:
            session.add(nova)
        else:
            for campo in ("titulo", "corpo", "tipo_evento", "modalidade", "nivel", "ativo"):
                setattr(atual, campo, getattr(nova, campo))
            session.add(atual)
    session.commit()


def licoes(session: Session, tipo_evento: TipoEvento | None = None) -> list[Licao]:
    q = select(Licao).where(Licao.ativo == True)  # noqa: E712
    if tipo_evento is not None:
        q = q.where(Licao.tipo_evento == tipo_evento)
    return list(session.exec(q.order_by(col(Licao.id))))


def licao(session: Session, slug: str) -> Licao | None:
    return session.exec(select(Licao).where(Licao.slug == slug, Licao.ativo == True)).first()  # noqa: E712


# --- webhook_log (§7.5) ------------------------------------------------------------


def registrar_webhook(session: Session, log: WebhookLog) -> bool:
    """Grava o webhook. Devolve ``False`` se o ``webhook_id`` já foi visto."""
    if session.exec(select(WebhookLog).where(WebhookLog.webhook_id == log.webhook_id)).first():
        return False
    session.add(log)
    session.commit()
    return True


def concluir_webhook(session: Session, webhook_id: str, erro: str | None = None) -> None:
    log = session.exec(select(WebhookLog).where(WebhookLog.webhook_id == webhook_id)).first()
    if log is None:
        return
    log.processado_em = agora()
    log.erro = (erro or None) and erro[:500]
    session.add(log)
    session.commit()
