"""Agregações do Raio-X da dívida (docs/contexto-produto.md §4 F2 e §8.2). Python puro, sem I/O."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence

from app.domain.planner import arredondar


@dataclass(frozen=True)
class DividaXray:
    id: int
    descricao: str
    modalidade: str
    saldo: Decimal
    taxa_mes: Decimal
    minima: Decimal
    em_atraso_dias: int = 0


def taxa_anual(taxa_mes: Decimal) -> Decimal:
    """§8.2: ``round((pow(1 + taxa_mes, 12) - 1) * 100, 4)`` — em pontos percentuais."""
    return (((1 + taxa_mes) ** 12 - 1) * 100).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def juros_do_mes(d: DividaXray) -> Decimal:
    return arredondar(d.saldo * d.taxa_mes)


@dataclass(frozen=True)
class RaioX:
    qtd_dividas: int
    divida_total: Decimal
    juros_mes_estimado: Decimal
    compromisso_minimo_mes: Decimal
    pior_taxa_anual: Decimal | None
    qtd_em_atraso: int
    divida_cresce: bool
    crescimento_mensal: Decimal  # quanto a dívida cresce pagando só o mínimo (0 se não cresce)
    maior_fonte_juros_id: int | None
    maior_fonte_juros_valor: Decimal
    dividas: list[DividaXray]  # ordenadas por custo efetivo (taxa a.a. desc, saldo asc)


def raio_x(dividas: Sequence[DividaXray]) -> RaioX:
    abertas = [d for d in dividas if d.saldo > 0]
    ordenadas = sorted(abertas, key=lambda d: (-d.taxa_mes, d.saldo, d.id))
    juros = {d.id: juros_do_mes(d) for d in abertas}
    juros_total = sum(juros.values(), Decimal("0.00"))
    minimos = sum((d.minima for d in abertas), Decimal("0.00"))
    maior = max(abertas, key=lambda d: (juros[d.id], -d.id), default=None)
    return RaioX(
        qtd_dividas=len(abertas),
        divida_total=sum((d.saldo for d in abertas), Decimal("0.00")),
        juros_mes_estimado=juros_total,
        compromisso_minimo_mes=minimos,
        pior_taxa_anual=taxa_anual(ordenadas[0].taxa_mes) if ordenadas else None,
        qtd_em_atraso=sum(1 for d in abertas if d.em_atraso_dias > 0),
        divida_cresce=juros_total > minimos,
        crescimento_mensal=max(juros_total - minimos, Decimal("0.00")),
        maior_fonte_juros_id=maior.id if maior else None,
        maior_fonte_juros_valor=juros[maior.id] if maior else Decimal("0.00"),
        dividas=ordenadas,
    )
