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
- agrupa pela categoria principal da Belvo: as subcategorias erram demais
  (teste com conta real, Fase 7) e só aparecem como filtro no detalhe;
- a categoria leva o selo de essencial só quando todo o gasto nela é essencial
  (§7.7); onde cortar olha só a parte não essencial — em Alimentação, o
  delivery, não o mercado — e nunca investimento ou poupança.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Sequence

from app.domain.planner import adicionar_meses, arredondar

CATEGORIAS_FORA = {"Transfers"}
# Dinheiro guardado não é gasto a cortar: nunca vira sugestão nem alerta de pico.
CATEGORIAS_SEM_CORTE = {"Investments & Savings"}
MESES_MEDIA = 3
SEP = "::"


def chave_gasto(categoria: str | None) -> str:
    """Onde agrupar um gasto: a categoria principal da taxonomia V2."""
    return categoria or "Unknown"


def categoria_da_chave(chave: str) -> str:
    return chave.split(SEP, 1)[0]


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
    essencial: bool  # todo o gasto da categoria é essencial
    nao_essencial: Decimal  # parte não essencial no mês
    media_nao_essencial: Decimal | None


def por_categoria(gastos: Sequence[Gasto], mes: date, meses_com_dado: set[date]) -> list[CategoriaMes]:
    """``mes``: primeiro dia do mês escolhido. ``meses_com_dado``: primeiros dias dos
    meses em que a pessoa tem alguma transação (para a média ignorar meses vazios)."""
    anteriores = [adicionar_meses(mes, -i) for i in range(1, MESES_MEDIA + 1)]
    base = [m for m in anteriores if m in meses_com_dado]
    soma: dict[str, dict[date, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    livre: dict[str, dict[date, Decimal]] = defaultdict(lambda: defaultdict(Decimal))  # não essencial
    for g in gastos:
        cat = g.categoria or "Unknown"
        if categoria_da_chave(cat) in CATEGORIAS_FORA:
            continue
        m = g.data.replace(day=1)
        soma[cat][m] += g.valor
        if not g.essencial:
            livre[cat][m] += g.valor

    def media_de(por_mes: dict[date, Decimal]) -> Decimal | None:
        return arredondar(sum((por_mes.get(m, Decimal(0)) for m in base), Decimal(0)) / len(base)) if base else None

    out = []
    for cat, por_mes in soma.items():
        total = arredondar(por_mes.get(mes, Decimal(0)))
        media = media_de(por_mes)
        if total == 0 and not media:
            continue
        variacao = ((total - media) / media).quantize(Decimal("0.01")) if media else None
        out.append(
            CategoriaMes(
                categoria=cat,
                total=total,
                media_3m=media,
                variacao=variacao,
                essencial=not livre[cat],
                nao_essencial=arredondar(livre[cat].get(mes, Decimal(0))),
                media_nao_essencial=media_de(livre[cat]),
            )
        )
    return sorted(out, key=lambda c: (-c.total, c.categoria))


@dataclass(frozen=True)
class Movimento:
    data: date
    valor: Decimal  # negativo = saída
    essencial: bool
    pagamento_divida: bool
    entrada_renda: bool
    categoria: str | None


@dataclass(frozen=True)
class FluxoMes:
    mes: date
    entradas: Decimal  # renda (as mesmas entradas que a capacidade usa)
    essenciais: Decimal
    outros_gastos: Decimal
    pagamentos_divida: Decimal
    # entradas - essenciais: a mesma base da capacidade (§5.1). Outros gastos e
    # dívida não entram na conta: a compra no cartão já está nos gastos e o
    # pagamento da fatura está na dívida — somar os dois contaria o mesmo
    # dinheiro duas vezes.
    sobra: Decimal


def fluxo_mensal(movimentos: Sequence[Movimento], meses: Sequence[date]) -> list[FluxoMes]:
    """N5: entradas × gastos × pagamentos de dívida, mês a mês, nos mesmos meses e
    com o mesmo critério de entrada (renda) e de essencial da capacidade (§5.1)."""
    soma: dict[date, dict[str, Decimal]] = {m: defaultdict(Decimal) for m in meses}
    for mv in movimentos:
        m = mv.data.replace(day=1)
        if m not in soma:
            continue
        if mv.valor > 0:
            if mv.entrada_renda:
                soma[m]["entradas"] += mv.valor
        elif mv.pagamento_divida:
            soma[m]["divida"] += -mv.valor
        elif mv.essencial:
            soma[m]["essenciais"] += -mv.valor
        elif (mv.categoria or "") not in CATEGORIAS_FORA:
            soma[m]["outros"] += -mv.valor
    out = []
    for m in meses:
        s = soma[m]
        e, ess, o, d = (arredondar(s[k]) for k in ("entradas", "essenciais", "outros", "divida"))
        out.append(FluxoMes(m, e, ess, o, d, e - ess))
    return out


def excesso_nao_essencial(c: CategoriaMes) -> Decimal:
    """Quanto a parte não essencial passou da própria média (0 se não passou)."""
    if c.media_nao_essencial is None or c.categoria in CATEGORIAS_SEM_CORTE:
        return Decimal(0)
    return max(c.nao_essencial - c.media_nao_essencial, Decimal(0))


def candidata_a_corte(categorias: Sequence[CategoriaMes]) -> CategoriaMes | None:
    """A categoria cuja parte NÃO essencial mais passou da média: é onde cortar dói menos."""
    acima = [c for c in categorias if excesso_nao_essencial(c) > 0]
    return max(acima, key=lambda c: (excesso_nao_essencial(c), c.categoria), default=None)


@dataclass(frozen=True)
class GastoDetalhado:
    data: date
    subcategoria: str | None
    valor: Decimal  # positivo


def historico_categoria(
    gastos: Sequence[GastoDetalhado], meses: Sequence[date]
) -> tuple[list[tuple[date, Decimal]], list[tuple[str, Decimal]]]:
    """Detalhe de uma categoria: total por mês (para o gráfico de evolução) e
    total por subcategoria no período (para o filtro), da maior para a menor."""
    por_mes: dict[date, Decimal] = {m: Decimal(0) for m in meses}
    por_sub: dict[str, Decimal] = defaultdict(Decimal)
    for g in gastos:
        m = g.data.replace(day=1)
        if m not in por_mes:
            continue
        por_mes[m] += g.valor
        if g.subcategoria:
            por_sub[g.subcategoria] += g.valor
    serie = [(m, arredondar(por_mes[m])) for m in meses]
    subs = sorted(((s, arredondar(v)) for s, v in por_sub.items()), key=lambda x: (-x[1], x[0]))
    return serie, subs
