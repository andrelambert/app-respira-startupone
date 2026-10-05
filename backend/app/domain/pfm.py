"""Regras de exibição do PFM (contas, faturas). Python puro, sem I/O."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum


class SituacaoFatura(StrEnum):
    PAGA = "PAGA"
    EM_ABERTO = "EM_ABERTO"  # ainda não venceu, nada pago
    PARCIAL = "PARCIAL"  # pagou parte (o resto pode virar rotativo)
    ATRASADA = "ATRASADA"  # venceu sem nem o mínimo pago


def situacao_fatura(
    total: Decimal, minimo: Decimal | None, pago: Decimal, vencimento: date | None, hoje: date
) -> SituacaoFatura:
    if total <= 0 or pago >= total:
        return SituacaoFatura.PAGA
    vencida = vencimento is not None and vencimento < hoje
    if vencida and pago < (minimo if minimo is not None else total):
        return SituacaoFatura.ATRASADA
    if pago > 0:
        return SituacaoFatura.PARCIAL
    return SituacaoFatura.EM_ABERTO


def em_aberto(total: Decimal, pago: Decimal) -> Decimal:
    return max(total - pago, Decimal("0.00"))


# A Belvo manda ``transacted_at`` em UTC (GMT 0); a interface mostra o horário
# de Brasília. Offset fixo: o Brasil não tem horário de verão desde 2019.
FUSO_BRASIL = timezone(timedelta(hours=-3), "BRT")


def horario_brasil(utc: datetime) -> datetime:
    """Datetime UTC (naive é tratado como UTC) → horário de Brasília, offset -03:00."""
    if utc.tzinfo is None:
        utc = utc.replace(tzinfo=timezone.utc)
    return utc.astimezone(FUSO_BRASIL)
