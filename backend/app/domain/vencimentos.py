"""Próximos vencimentos (N3, Fase 7 — F-5 "não sei quando vence cada coisa").

Python puro, sem I/O. Organiza o que já existe; não gera alerta novo (a regra
de parcimônia dos alertas, §2, continua valendo).

Fontes:
- fatura de cartão: o vencimento e a situação vêm da própria fatura;
- demais dívidas (empréstimo, financiamento, cheque especial, carnê): o
  ``dia_vencimento`` do contrato gera a próxima data.
A dívida de cartão sai pela fatura — nunca as duas, para não contar em dobro.

Status:
- ``ATRASADO``: fatura vencida sem o mínimo pago, ou dívida com ``em_atraso_dias``;
- ``PAGO``: fatura paga (para as demais dívidas, o Open Finance não diz se a
  parcela do mês foi paga — elas ficam ``PENDENTE`` até vencer);
- ``PENDENTE``: o resto.
Atrasados aparecem sempre, mesmo fora da janela de dias: são o que mais importa.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Sequence

from app.domain.pfm import SituacaoFatura, em_aberto, situacao_fatura
from app.domain.planner import adicionar_meses

MODALIDADES_CARTAO = {"CARTAO_FATURA", "CARTAO_ROTATIVO", "CARTAO_PARCELADO"}


class StatusVencimento(StrEnum):
    PAGO = "PAGO"
    PENDENTE = "PENDENTE"
    ATRASADO = "ATRASADO"


@dataclass(frozen=True)
class FaturaVenc:
    id: int
    conta_id: int
    credor: str
    descricao: str
    vencimento: date
    total: Decimal
    minimo: Decimal | None
    pago: Decimal
    divida_id: int | None  # dívida de cartão ligada à mesma conta, se houver


@dataclass(frozen=True)
class DividaVenc:
    id: int
    credor: str
    descricao: str
    modalidade: str
    dia_vencimento: int | None
    parcela: Decimal
    em_atraso_dias: int
    saldo: Decimal


@dataclass(frozen=True)
class Vencimento:
    data: date
    tipo: str  # "FATURA" | "PARCELA"
    credor: str
    descricao: str
    valor: Decimal  # mínimo da fatura ou parcela do contrato
    valor_total: Decimal | None  # fatura: quanto falta pagar dela inteira
    status: StatusVencimento
    dias: int  # negativo = já venceu
    divida_id: int | None
    conta_id: int | None


def _data_no_mes(base: date, dia: int) -> date:
    ultimo = (adicionar_meses(base.replace(day=1), 1) - timedelta(days=1)).day
    return base.replace(day=min(dia, ultimo))


def proxima_data(hoje: date, dia: int) -> date:
    """Próxima ocorrência do dia do mês, a partir de hoje (inclusive)."""
    este = _data_no_mes(hoje, dia)
    return este if este >= hoje else _data_no_mes(adicionar_meses(hoje.replace(day=1), 1), dia)


def montar(
    *, hoje: date, dias: int, faturas: Sequence[FaturaVenc], dividas: Sequence[DividaVenc]
) -> list[Vencimento]:
    limite = hoje + timedelta(days=dias)
    out: list[Vencimento] = []

    # Cartão: só a fatura mais recente de cada cartão (as antigas são histórico).
    ultima: dict[int, FaturaVenc] = {}
    for f in faturas:
        if f.conta_id not in ultima or f.vencimento > ultima[f.conta_id].vencimento:
            ultima[f.conta_id] = f
    for f in ultima.values():
        sit = situacao_fatura(f.total, f.minimo, f.pago, f.vencimento, hoje)
        status = {
            SituacaoFatura.PAGA: StatusVencimento.PAGO,
            SituacaoFatura.ATRASADA: StatusVencimento.ATRASADO,
        }.get(sit, StatusVencimento.PENDENTE)
        if status is not StatusVencimento.ATRASADO and not (hoje <= f.vencimento <= limite):
            continue
        falta = em_aberto(f.total, f.pago)
        minimo = f.minimo if f.minimo is not None else f.total
        out.append(
            Vencimento(
                data=f.vencimento,
                tipo="FATURA",
                credor=f.credor,
                descricao=f.descricao,
                valor=min(max(minimo - f.pago, Decimal("0.00")), falta),
                valor_total=falta,
                status=status,
                dias=(f.vencimento - hoje).days,
                divida_id=f.divida_id,
                conta_id=f.conta_id,
            )
        )

    for d in dividas:
        if d.modalidade in MODALIDADES_CARTAO or d.saldo <= 0 or not d.dia_vencimento:
            continue
        if d.em_atraso_dias > 0:
            data = hoje - timedelta(days=d.em_atraso_dias)
            status = StatusVencimento.ATRASADO
        else:
            data = proxima_data(hoje, d.dia_vencimento)
            if data > limite:
                continue
            status = StatusVencimento.PENDENTE
        out.append(
            Vencimento(
                data=data,
                tipo="PARCELA",
                credor=d.credor,
                descricao=d.descricao,
                valor=min(d.parcela, d.saldo),
                valor_total=None,
                status=status,
                dias=(data - hoje).days,
                divida_id=d.id,
                conta_id=None,
            )
        )

    # Atrasados primeiro (o mais antigo no topo), depois por data.
    return sorted(out, key=lambda v: (v.status is not StatusVencimento.ATRASADO, v.data, v.credor))
