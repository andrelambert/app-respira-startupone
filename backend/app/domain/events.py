"""Detecção determinística de eventos (docs/contexto-produto.md §8.3). Sem IA, sem I/O.

Cada evento carrega em ``contexto`` os números que a mensagem vai usar — a
mensagem é montada a partir deles no frontend, nunca genérica. Regra de
parcimônia (§2): só existe evento com uma ação concreta e um valor em reais.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Sequence

from app.domain.planner import adicionar_meses, arredondar
from app.domain.xray import taxa_anual

# Picos abaixo deste valor não merecem alerta: não há ação relevante em jogo.
PICO_VALOR_MINIMO = Decimal("50.00")
PICO_FATOR = Decimal("1.5")
DIAS_ATRASO_IMINENTE = 3
DESVIO_LIMIAR = Decimal("0.80")


@dataclass(frozen=True)
class DividaEstado:
    id: int
    descricao: str
    instituicao: str
    modalidade: str
    saldo: Decimal
    taxa_mes: Decimal
    minima: Decimal
    dia_vencimento: int | None
    em_atraso_dias: int


@dataclass(frozen=True)
class GastoCategoria:
    data: date
    categoria: str
    valor: Decimal  # positivo


@dataclass(frozen=True)
class EventoDetectado:
    tipo: str
    chave: str
    severidade: int
    divida_id: int | None = None
    contexto: dict[str, Any] = field(default_factory=dict)


def _s(v: Decimal) -> str:
    return str(arredondar(v))


def _proximo_vencimento(hoje: date, dia: int) -> date:
    for delta in (0, 1):
        base = adicionar_meses(hoje.replace(day=1), delta)
        ultimo = (adicionar_meses(base, 1) - timedelta(days=1)).day
        venc = base.replace(day=min(dia, ultimo))
        if venc >= hoje:
            return venc
    raise AssertionError("inalcançável")


def detectar(
    *,
    hoje: date,
    dividas: Sequence[DividaEstado],
    anteriores: dict[int, DividaEstado],
    saldo_em_conta: Decimal | None,  # None = sem conta conectada: não há como avaliar
    usado_cheque_especial: Decimal,
    gastos: Sequence[GastoCategoria],
) -> list[EventoDetectado]:
    eventos: list[EventoDetectado] = []
    mes = hoje.strftime("%Y-%m")

    for d in dividas:
        antes = anteriores.get(d.id)

        # "Surgiu ou cresceu": inclui a fatura que só agora foi reclassificada
        # como rotativo (as faturas chegam depois das contas na coleta).
        if d.modalidade == "CARTAO_ROTATIVO" and d.saldo > 0 and (
            antes is None or antes.modalidade != "CARTAO_ROTATIVO" or d.saldo > antes.saldo
        ):
            eventos.append(
                EventoDetectado(
                    "ENTRADA_ROTATIVO",
                    f"ROT:{d.id}:{mes}",
                    3,
                    d.id,
                    {
                        "instituicao": d.instituicao,
                        "saldo": _s(d.saldo),
                        "taxa_anual": str(taxa_anual(d.taxa_mes)),
                        "juros_mes": _s(d.saldo * d.taxa_mes),
                    },
                )
            )

        if d.dia_vencimento and d.saldo > 0 and d.minima > 0:
            venc = _proximo_vencimento(hoje, d.dia_vencimento)
            dias = (venc - hoje).days
            if (
                saldo_em_conta is not None
                and dias <= DIAS_ATRASO_IMINENTE
                and saldo_em_conta < d.minima
            ):
                eventos.append(
                    EventoDetectado(
                        "ATRASO_IMINENTE",
                        f"AI:{d.id}:{venc.isoformat()}",
                        3,
                        d.id,
                        {
                            "descricao": d.descricao,
                            "instituicao": d.instituicao,
                            "parcela": _s(d.minima),
                            "saldo_conta": _s(max(saldo_em_conta, Decimal(0))),
                            "falta": _s(d.minima - max(saldo_em_conta, Decimal(0))),
                            "vencimento": venc.isoformat(),
                            "dias": dias,
                        },
                    )
                )

        if d.em_atraso_dias > 0 and (antes is None or antes.em_atraso_dias == 0):
            eventos.append(
                EventoDetectado(
                    "ATRASO_CONFIRMADO",
                    f"AC:{d.id}:{mes}",
                    3,
                    d.id,
                    {
                        "descricao": d.descricao,
                        "instituicao": d.instituicao,
                        "dias": d.em_atraso_dias,
                        "parcela": _s(d.minima),
                        "saldo": _s(d.saldo),
                    },
                )
            )

        if antes is not None and antes.saldo > 0 and d.saldo <= 0:
            eventos.append(
                EventoDetectado(
                    "DIVIDA_QUITADA",
                    f"DQ:{d.id}",
                    1,
                    d.id,
                    {
                        "descricao": d.descricao,
                        "instituicao": d.instituicao,
                        "parcela_liberada": _s(d.minima),
                        "data": hoje.isoformat(),
                    },
                )
            )

    # Parcimônia: avisa quando o uso do cheque especial aparece ou cresce, não
    # todo mês enquanto ele existir.
    usado_antes = sum(
        (a.saldo for a in anteriores.values() if a.modalidade == "CHEQUE_ESPECIAL" and a.saldo > 0),
        Decimal(0),
    )
    if usado_cheque_especial > 0 and usado_cheque_especial > usado_antes:
        cheque = next((d for d in dividas if d.modalidade == "CHEQUE_ESPECIAL"), None)
        taxa = cheque.taxa_mes if cheque else None
        eventos.append(
            EventoDetectado(
                "CHEQUE_ESPECIAL",
                f"CE:{mes}",
                2,
                cheque.id if cheque else None,
                {
                    "usado": _s(usado_cheque_especial),
                    "taxa_anual": str(taxa_anual(taxa)) if taxa is not None else None,
                    "juros_mes": _s(usado_cheque_especial * taxa) if taxa is not None else None,
                },
            )
        )

    eventos.extend(_picos(hoje, gastos))
    return eventos


def _picos(hoje: date, gastos: Sequence[GastoCategoria]) -> list[EventoDetectado]:
    """PICO_CATEGORIA: último mês completo > 1,5 × mediana dos 6 meses anteriores."""
    alvo = adicionar_meses(hoje.replace(day=1), -1)
    anteriores = [adicionar_meses(alvo, -i) for i in range(1, 7)]
    por_mes: dict[str, dict[date, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for g in gastos:
        por_mes[g.categoria][g.data.replace(day=1)] += g.valor

    eventos = []
    for categoria, meses in por_mes.items():
        atual = meses.get(alvo, Decimal(0))
        historico = sorted(meses.get(m, Decimal(0)) for m in anteriores if m in meses)
        if len(historico) < 3:
            continue  # pouco histórico para dizer o que é "normal"
        meio = len(historico) // 2
        mediana = (
            historico[meio]
            if len(historico) % 2
            else (historico[meio - 1] + historico[meio]) / 2
        )
        excesso = atual - mediana
        if mediana > 0 and atual > mediana * PICO_FATOR and excesso >= PICO_VALOR_MINIMO:
            eventos.append(
                EventoDetectado(
                    "PICO_CATEGORIA",
                    f"PC:{categoria}:{alvo:%Y-%m}",
                    1,
                    None,
                    {
                        "categoria": categoria,
                        "mes": alvo.isoformat(),
                        "gasto": _s(atual),
                        "normal": _s(mediana),
                        "excesso": _s(excesso),
                    },
                )
            )
    return eventos


def desvio_plano(previsto: Decimal, realizado: Decimal) -> bool:
    """DESVIO_PLANO: pago no mês < 80% do previsto."""
    return previsto > 0 and realizado < previsto * DESVIO_LIMIAR
