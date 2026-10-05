from datetime import date

from sqlmodel import Session, col, select

from app.models import Acompanhamento, Plano, PlanoItem, StatusPlano


def ativo(session: Session, usuario_id: int) -> Plano | None:
    return session.exec(
        select(Plano)
        .where(Plano.usuario_id == usuario_id, Plano.status == StatusPlano.ATIVO)
        .order_by(col(Plano.criado_em).desc())
    ).first()


def ativar(session: Session, plano: Plano, itens: list[PlanoItem]) -> Plano:
    """Um plano ativo por vez: o anterior fica PAUSADO (histórico preservado)."""
    anterior = ativo(session, plano.usuario_id)
    if anterior is not None:
        anterior.status = StatusPlano.PAUSADO
        session.add(anterior)
    session.add(plano)
    session.flush()
    for item in itens:
        item.plano_id = plano.id  # type: ignore[assignment]
        session.add(item)
    session.commit()
    session.refresh(plano)
    return plano


def itens(session: Session, plano_id: int) -> list[PlanoItem]:
    return list(
        session.exec(select(PlanoItem).where(PlanoItem.plano_id == plano_id).order_by(col(PlanoItem.ordem)))
    )


def salvar(session: Session, plano: Plano) -> None:
    session.add(plano)
    session.commit()


def acompanhamento(session: Session, plano_id: int, mes: date) -> Acompanhamento | None:
    return session.exec(
        select(Acompanhamento).where(
            Acompanhamento.plano_id == plano_id, Acompanhamento.mes_referencia == mes
        )
    ).first()


def registrar_acompanhamento(session: Session, a: Acompanhamento) -> Acompanhamento:
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def acompanhamentos(session: Session, plano_id: int) -> list[Acompanhamento]:
    return list(
        session.exec(
            select(Acompanhamento)
            .where(Acompanhamento.plano_id == plano_id)
            .order_by(col(Acompanhamento.mes_referencia))
        )
    )
