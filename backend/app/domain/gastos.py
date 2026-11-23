"""Para onde foi o dinheiro: gastos por categoria (N2, Fase 7 — F-3, F-4).

Python puro, sem I/O. Existe para **liberar capacidade para o plano**, não para
virar app de orçamento (briefing §0.9): a saída mais importante é a frase
"se X voltasse à sua média, sua data de saída chegaria N meses antes".

Regras:
- só saídas; ficam de fora pagamentos de dívida (fatura, parcela — senão a
  compra no cartão e o pagamento da fatura contariam o mesmo dinheiro duas
  vezes) e transferências (dinheiro que muda de conta, não gasto);
- média dos 3 meses anteriores ao mês escolhido; mês sem nenhuma transação
  não entra (é falta de histórico, não gasto zero);
- categoria é essencial quando a maior parte do valor é de transações
  marcadas como essenciais (§7.7).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Sequence

from app.domain.planner import adicionar_meses, arredondar

CATEGORIAS_FORA = {"Transfers"}
MESES_MEDIA = 3


@dataclass(frozen=True)
class Gasto:
    data: date
    categoria: str | None
    valor: Decimal  # positivo
    essencial: bool


@dataclass(frozen=True)
class CategoriaMes:
    categoria: str
    total: Decimal
    media_3m: Decimal | None  # None: sem histórico suficiente
    variacao: Decimal | None  # fração: 0.38 = 38% acima da média
    essencial: bool


def por_categoria(gastos: Sequence[Gasto], mes: date, meses_com_dado: set[date]) -> list[CategoriaMes]:
    """``mes``: primeiro dia do mês escolhido. ``meses_com_dado``: primeiros dias dos
    meses em que a pessoa tem alguma transação (para a média ignorar meses vazios)."""
    anteriores = [adicionar_meses(mes, -i) for i in range(1, MESES_MEDIA + 1)]
    base = [m for m in anteriores if m in meses_com_dado]
    soma: dict[str, dict[date, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    essencial_valor: dict[str, Decimal] = defaultdict(Decimal)
    total_valor: dict[str, Decimal] = defaultdict(Decimal)
    for g in gastos:
        cat = g.categoria or "Unknown"
        if cat in CATEGORIAS_FORA:
            continue
        m = g.data.replace(day=1)
        soma[cat][m] += g.valor
        total_valor[cat] += g.valor
        if g.essencial:
            essencial_valor[cat] += g.valor

    out = []
    for cat, por_mes in soma.items():
        total = arredondar(por_mes.get(mes, Decimal(0)))
        media = arredondar(sum((por_mes.get(m, Decimal(0)) for m in base), Decimal(0)) / len(base)) if base else None
        if total == 0 and not media:
            continue
        variacao = ((total - media) / media).quantize(Decimal("0.01")) if media else None
        out.append(
            CategoriaMes(
                categoria=cat,
                total=total,
                media_3m=media,
                variacao=variacao,
                essencial=essencial_valor[cat] * 2 > total_valor[cat],
            )
        )
    return sorted(out, key=lambda c: (-c.total, c.categoria))


def candidata_a_corte(categorias: Sequence[CategoriaMes]) -> CategoriaMes | None:
    """A maior categoria NÃO essencial acima da média: é onde cortar dói menos."""
    acima = [c for c in categorias if not c.essencial and c.media_3m is not None and c.total > c.media_3m]
    return max(acima, key=lambda c: (c.total - (c.media_3m or 0), c.categoria), default=None)
