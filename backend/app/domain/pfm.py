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


def fatura_aberta_estimada(usado: Decimal, parcelas_futuras: Decimal, restante_fechada: Decimal) -> Decimal:
    """A fatura que ainda está aberta (o banco só manda as fechadas).

    Teste com conta Nubank real: o app mostrava só o que sobrou da última fatura
    fechada (R$ 61), e a pessoa sabia que a próxima já passava de R$ 1.000. O
    limite usado (dado do banco) é a soma de três coisas: o que falta da fatura
    fechada, a fatura aberta e as parcelas que ainda vão cair. Tirando as duas
    que conhecemos, sobra a aberta. Estimativa: nunca abaixo de zero.
    """
    return max(usado - parcelas_futuras - restante_fechada, Decimal("0.00"))
