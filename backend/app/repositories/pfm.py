"""Consultas do PFM: contas, faturas e extrato paginado."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_
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


def salvar(session: Session, *objetos: Conta | Fatura) -> None:
    for o in objetos:
        session.add(o)
    session.commit()


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


# --- N1 (Fase 7): todas as transações, com filtros -----------------------------------


@dataclass(frozen=True)
class FiltroTransacoes:
    desde: date | None = None
    ate: date | None = None
    contas: tuple[int, ...] = ()
    direcao: Direcao | None = None
    categorias: tuple[str, ...] = ()
    busca: str | None = None
    valor_min: Decimal | None = None  # sobre o valor absoluto
    valor_max: Decimal | None = None
    so_divida: bool = False
    ordem: str = "recentes"  # "recentes" | "maior_valor"


def _condicoes(usuario_id: int, f: FiltroTransacoes) -> list[Any]:
    cond: list[Any] = [Transacao.usuario_id == usuario_id]
    if f.contas:
        cond.append(col(Transacao.conta_id).in_(f.contas))
    if f.direcao is not None:
        cond.append(Transacao.direcao == f.direcao)
    if f.categorias:
        # Cada item é uma categoria ("Food & Groceries") ou uma subcategoria
        # ("Food & Groceries::Restaurants" — o toque numa barra de gastos, N2).
        simples = [c for c in f.categorias if "::" not in c]
        compostas = [c.split("::", 1) for c in f.categorias if "::" in c]
        alternativas = [col(Transacao.categoria).in_(simples)] if simples else []
        alternativas += [
            (Transacao.categoria == cat) & (Transacao.subcategoria == sub) for cat, sub in compostas
        ]
        cond.append(or_(*alternativas))
    if f.so_divida:
        cond.append(Transacao.pagamento_divida == True)
    if f.desde is not None:
        cond.append(col(Transacao.data_mov) >= f.desde)
    if f.ate is not None:
        cond.append(col(Transacao.data_mov) <= f.ate)
    if f.busca:
        termo = f.busca.lower().replace("!", "!!").replace("%", "!%").replace("_", "!_")
        padrao = f"%{termo}%"
        cond.append(
            func.lower(func.coalesce(Transacao.descricao, "")).like(padrao, escape="!")
            | func.lower(func.coalesce(Transacao.estabelecimento, "")).like(padrao, escape="!")
        )
    return cond


def transacoes_filtradas(
    session: Session, usuario_id: int, f: FiltroTransacoes, *, pagina: int, por_pagina: int
) -> tuple[list[Transacao], int, Decimal, Decimal]:
    """(itens da página, total, soma das entradas, soma das saídas) do filtro.

    Faixa de valor e ordem por valor são aplicadas em Python: no SQLite o valor é
    texto (Decimal exato), então comparar em SQL daria ordem alfabética. Os demais
    filtros rodam no banco. O resultado é o mesmo no SQLite e no Oracle.
    """
    ordem_data = (
        col(Transacao.data_mov).desc(),
        col(Transacao.transacionado_em).desc().nulls_last(),
        col(Transacao.id).desc(),
    )
    todos = list(session.exec(select(Transacao).where(*_condicoes(usuario_id, f)).order_by(*ordem_data)))
    if f.valor_min is not None:
        todos = [t for t in todos if abs(t.valor) >= f.valor_min]
    if f.valor_max is not None:
        todos = [t for t in todos if abs(t.valor) <= f.valor_max]
    if f.ordem == "maior_valor":
        todos.sort(key=lambda t: abs(t.valor), reverse=True)  # estável: empate fica por data
    entradas = sum((t.valor for t in todos if t.valor > 0), Decimal("0.00"))
    saidas = sum((-t.valor for t in todos if t.valor < 0), Decimal("0.00"))
    inicio = (pagina - 1) * por_pagina
    return todos[inicio : inicio + por_pagina], len(todos), entradas, saidas


def categorias_usadas(session: Session, usuario_id: int) -> list[str]:
    q = (
        select(Transacao.categoria)
        .where(Transacao.usuario_id == usuario_id, col(Transacao.categoria).is_not(None))
        .distinct()
    )
    return sorted(c for c in session.exec(q) if c)
