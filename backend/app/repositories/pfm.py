"""Consultas do PFM: contas, faturas e extrato paginado."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import Consentimento, Conta, Direcao, Fatura, StatusConsentimento, Transacao


def contas(session: Session, usuario_id: int, consentimento_id: int | None = None) -> list[Conta]:
    q = (
        select(Conta)
        .join(Consentimento, col(Conta.consentimento_id) == col(Consentimento.id))
        .where(Conta.usuario_id == usuario_id, Consentimento.status != StatusConsentimento.REVOGADO)
    )
    if consentimento_id is not None:
        q = q.where(Conta.consentimento_id == consentimento_id)
    return list(session.exec(q.order_by(col(Conta.consentimento_id), col(Conta.id))))


def conta(session: Session, usuario_id: int, conta_id: int) -> Conta | None:
    c = session.get(Conta, conta_id)
    return c if c and c.usuario_id == usuario_id else None


def faturas(session: Session, conta_id: int) -> list[Fatura]:
    return list(
        session.exec(
            select(Fatura).where(Fatura.conta_id == conta_id).order_by(col(Fatura.vencimento).desc())
        )
    )


def _filtros(
    usuario_id: int,
    conta_id: int,
    direcao: Direcao | None,
    busca: str | None,
    desde: date | None,
    ate: date | None,
):
    filtros = [Transacao.usuario_id == usuario_id, Transacao.conta_id == conta_id]
    if direcao is not None:
        filtros.append(Transacao.direcao == direcao)
    if desde is not None:
        filtros.append(col(Transacao.data_mov) >= desde)
    if ate is not None:
        filtros.append(col(Transacao.data_mov) <= ate)
    if busca:
        # Busca literal: % e _ digitados pela pessoa não viram curinga.
        termo = busca.lower().replace("!", "!!").replace("%", "!%").replace("_", "!_")
        padrao = f"%{termo}%"
        filtros.append(
            func.lower(Transacao.descricao).like(padrao, escape="!")
            | func.lower(func.coalesce(Transacao.estabelecimento, "")).like(padrao, escape="!")
        )
    return filtros


def transacoes_paginadas(
    session: Session,
    usuario_id: int,
    conta_id: int,
    *,
    pagina: int,
    por_pagina: int,
    direcao: Direcao | None = None,
    busca: str | None = None,
    desde: date | None = None,
    ate: date | None = None,
) -> tuple[list[Transacao], int, Decimal, Decimal]:
    """(itens da página, total de itens, soma das entradas, soma das saídas) do filtro."""
    filtros = _filtros(usuario_id, conta_id, direcao, busca, desde, ate)
    total = session.exec(select(func.count()).select_from(Transacao).where(*filtros)).one()
    itens = list(
        session.exec(
            select(Transacao)
            .where(*filtros)
            .order_by(
                col(Transacao.data_mov).desc(),
                col(Transacao.transacionado_em).desc().nulls_last(),
                col(Transacao.id).desc(),
            )
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
        )
    )
    # Somas em Decimal no Python: o valor é texto no banco (dinheiro exato).
    valores = session.exec(select(Transacao.valor).where(*filtros)).all()
    entradas = sum((v for v in valores if v > 0), Decimal("0.00"))
    saidas = sum((-v for v in valores if v < 0), Decimal("0.00"))
    return itens, int(total), entradas, saidas
