"""Motor de plano de quitação (docs/contexto-produto.md §5).

Porte do pacote PL/SQL ``PKG_PLANO`` da Fase 5. Python puro, sem I/O e sem
dependência de framework: recebe dívidas e capacidade, devolve a simulação.

Dinheiro é sempre ``Decimal`` com arredondamento a cada incidência de juros
(``ROUND_HALF_UP``, o mesmo comportamento do ``ROUND`` do Oracle para valores
positivos). Nunca ``float``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from statistics import median
from typing import Iterable, Sequence

CENTAVO = Decimal("0.01")
MAX_MESES = 600
# Reserva de 10% para imprevistos (§5.1). Obrigatória: um plano que consome
# tudo quebra no primeiro mês atípico.
FATOR_RESERVA = Decimal("0.90")
# §5.3: "restantes = contagem de dívidas com saldo > 0.01"
SALDO_RESIDUAL = Decimal("0.01")
# Trava contra divergência: com capacidade abaixo dos juros, o saldo cresce
# exponencialmente e estoura a precisão do Decimal antes dos 600 meses. Se o
# saldo total passar deste múltiplo do inicial, o plano não converge.
FATOR_DIVERGENCIA = 1000


class Metodo(StrEnum):
    AVALANCHE = "AVALANCHE"
    SNOWBALL = "SNOWBALL"
    EQUILIBRADO = "EQUILIBRADO"


# Pré-seleção da estratégia — §5.4. Decisão PROVISÓRIA, tomada sobre n=10
# respostas de um público que não é o alvo. Este é o único lugar do código que
# define a regra; mude aqui se a validação futura apontar outro padrão.
METODO_PADRAO = Metodo.AVALANCHE
METODO_PARA_QUEM_JA_DESISTIU = Metodo.EQUILIBRADO


def metodo_pre_selecionado(ja_desistiu_de_plano: bool | None) -> Metodo:
    return METODO_PARA_QUEM_JA_DESISTIU if ja_desistiu_de_plano else METODO_PADRAO


def arredondar(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class DividaEntrada:
    id: str
    saldo: Decimal
    taxa_mes: Decimal  # fração: 0.1502 = 15,02% a.m.
    minima: Decimal


@dataclass
class ItemPlano:
    divida_id: str
    ordem: int
    valor_mensal: Decimal  # quanto vai para esta dívida no 1º mês do plano
    mes_quitacao: int | None
    juros_pagos: Decimal


@dataclass
class Simulacao:
    metodo: Metodo
    capacidade: Decimal
    converge: bool
    meses: int
    juros_totais: Decimal
    data_quitacao: date | None
    primeira_quitacao_mes: int | None
    itens: list[ItemPlano] = field(default_factory=list)
    # saldo total ao fim de cada mês (índice 0 = saldo inicial)
    trajetoria: list[Decimal] = field(default_factory=list)


def ordenar(dividas: Sequence[DividaEntrada], metodo: Metodo) -> list[DividaEntrada]:
    """Ordenação por estratégia (§5.2). O ``id`` fecha o desempate para que a
    ordem seja determinística mesmo com taxa e saldo iguais."""
    avalanche = sorted(dividas, key=lambda d: (-d.taxa_mes, d.saldo, d.id))
    if metodo is Metodo.AVALANCHE:
        return avalanche
    if metodo is Metodo.SNOWBALL:
        return sorted(dividas, key=lambda d: (d.saldo, -d.taxa_mes, d.id))
    # EQUILIBRADO: a menor dívida vai para a posição 0; as demais seguem o avalanche.
    menor = min(dividas, key=lambda d: (d.saldo, -d.taxa_mes, d.id))
    return [menor, *(d for d in avalanche if d is not menor)]


def adicionar_meses(base: date, meses: int) -> date:
    total = base.month - 1 + meses
    return date(base.year + total // 12, total % 12 + 1, 1)


def simular(
    dividas: Sequence[DividaEntrada],
    capacidade: Decimal,
    metodo: Metodo,
    hoje: date,
) -> Simulacao:
    """Simulação mês a mês — pseudocódigo normativo do §5.3."""
    capacidade = arredondar(Decimal(capacidade))
    abertas = [d for d in dividas if d.saldo > 0]
    if not abertas or capacidade <= 0:
        return Simulacao(
            metodo=metodo,
            capacidade=capacidade,
            converge=not abertas,
            meses=0,
            juros_totais=Decimal("0.00"),
            data_quitacao=None,
            primeira_quitacao_mes=None,
            trajetoria=[arredondar(sum((d.saldo for d in abertas), Decimal(0)))],
        )

    ordem = ordenar(abertas, metodo)
    saldo = {d.id: arredondar(d.saldo) for d in ordem}
    juros_por = {d.id: Decimal("0.00") for d in ordem}
    pago_mes1 = {d.id: Decimal("0.00") for d in ordem}
    mes_quitacao: dict[str, int | None] = {d.id: None for d in ordem}
    trajetoria = [sum(saldo.values(), Decimal("0.00"))]

    juros_totais = Decimal("0.00")
    primeira_quitacao_mes: int | None = None
    mes = 0

    while True:
        mes += 1
        sobra = capacidade

        # 1) Juros do mês + mínimo de cada dívida aberta, na ordem da estratégia.
        for d in ordem:
            if saldo[d.id] > 0:
                juros = arredondar(saldo[d.id] * d.taxa_mes)
                saldo[d.id] += juros
                juros_totais += juros
                juros_por[d.id] += juros

                pgto = min(d.minima, saldo[d.id], sobra)
                saldo[d.id] -= pgto
                sobra -= pgto
                if mes == 1:
                    pago_mes1[d.id] += pgto

        # 2) A sobra vai integralmente para a dívida da vez.
        for d in ordem:
            if sobra <= 0:
                break
            if saldo[d.id] > 0:
                pgto = min(sobra, saldo[d.id])
                saldo[d.id] -= pgto
                sobra -= pgto
                if mes == 1:
                    pago_mes1[d.id] += pgto
                # Só a quitação pela sobra marca a primeira vitória (fiel à referência).
                if saldo[d.id] <= 0 and primeira_quitacao_mes is None:
                    primeira_quitacao_mes = mes

        for d in ordem:
            if mes_quitacao[d.id] is None and saldo[d.id] <= SALDO_RESIDUAL:
                mes_quitacao[d.id] = mes

        total = sum((s for s in saldo.values() if s > 0), Decimal("0.00"))
        trajetoria.append(total)

        # 3) Encerrou?
        restantes = sum(1 for s in saldo.values() if s > SALDO_RESIDUAL)
        if restantes == 0 or mes >= MAX_MESES:
            break
        if total > trajetoria[0] * FATOR_DIVERGENCIA:
            break

    converge = restantes == 0
    itens = [
        ItemPlano(
            divida_id=d.id,
            ordem=i,
            valor_mensal=pago_mes1[d.id],
            mes_quitacao=mes_quitacao[d.id],
            juros_pagos=juros_por[d.id],
        )
        for i, d in enumerate(ordem)
    ]
    return Simulacao(
        metodo=metodo,
        capacidade=capacidade,
        converge=converge,
        meses=mes,
        juros_totais=juros_totais,
        data_quitacao=adicionar_meses(hoje.replace(day=1), mes) if converge else None,
        primeira_quitacao_mes=primeira_quitacao_mes,
        itens=itens,
        trajetoria=trajetoria,
    )


def simular_todas(
    dividas: Sequence[DividaEntrada], capacidade: Decimal, hoje: date
) -> dict[Metodo, Simulacao]:
    return {m: simular(dividas, capacidade, m, hoje) for m in Metodo}


@dataclass
class CenarioMinimo:
    """Pagar só o mínimo de cada dívida, sem redirecionar o que sobra."""

    converge: bool
    meses: int
    juros_no_horizonte: Decimal
    saldo_no_horizonte: Decimal


def simular_so_minimo(dividas: Sequence[DividaEntrada], horizonte: int) -> CenarioMinimo:
    saldo = {d.id: arredondar(d.saldo) for d in dividas if d.saldo > 0}
    taxas = {d.id: d for d in dividas}
    juros = Decimal("0.00")
    mes = 0
    inicial = sum(saldo.values(), Decimal("0.00"))
    while mes < max(horizonte, 1):
        mes += 1
        if sum(saldo.values(), Decimal(0)) > inicial * FATOR_DIVERGENCIA:
            break
        for did in saldo:
            if saldo[did] > 0:
                j = arredondar(saldo[did] * taxas[did].taxa_mes)
                saldo[did] += j
                juros += j
                saldo[did] -= min(taxas[did].minima, saldo[did])
        if all(s <= SALDO_RESIDUAL for s in saldo.values()):
            break
    restante = sum((s for s in saldo.values() if s > 0), Decimal("0.00"))
    return CenarioMinimo(
        converge=restante <= SALDO_RESIDUAL,
        meses=mes,
        juros_no_horizonte=juros,
        saldo_no_horizonte=restante,
    )


def capacidade_minima(dividas: Sequence[DividaEntrada], hoje: date) -> Decimal | None:
    """Menor capacidade, em reais inteiros, com que o plano converge em até
    ``MAX_MESES``. Alimenta a mensagem do §14.2 ("são necessários pelo menos R$ X")."""
    abertas = [d for d in dividas if d.saldo > 0]
    if not abertas:
        return None
    total = sum((d.saldo for d in abertas), Decimal(0))
    baixo, alto = Decimal(0), arredondar(total).to_integral_value() + 1
    while alto - baixo > 1:
        meio = (baixo + alto) // 2
        if simular(abertas, meio, Metodo.AVALANCHE, hoje).converge:
            alto = meio
        else:
            baixo = meio
    return alto


# ---------------------------------------------------------------------------
# Capacidade de pagamento a partir do histórico (§5.1 / §7.8)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Movimento:
    data: date
    valor: Decimal  # negativo = saída
    essencial: bool


def _meses_anteriores(hoje: date, n: int) -> list[tuple[int, int]]:
    inicio = adicionar_meses(hoje.replace(day=1), -n)
    return [(d.year, d.month) for d in (adicionar_meses(inicio, i) for i in range(n))]


def _mediana(valores: Iterable[Decimal]) -> Decimal:
    lista = list(valores)
    return Decimal(median(lista)) if lista else Decimal(0)


def medianas_mensais(
    movimentos: Iterable[Movimento], hoje: date, meses: int = 6
) -> tuple[Decimal, Decimal, int]:
    """(mediana de entradas, mediana de essenciais, meses com dado).

    Janela: os ``meses`` meses completos anteriores ao mês corrente. Só entram
    na mediana os meses que têm alguma transação — mês sem dado não é mês de
    renda zero, é ausência de histórico.
    """
    janela = set(_meses_anteriores(hoje, meses))
    entradas: dict[tuple[int, int], Decimal] = {}
    essenciais: dict[tuple[int, int], Decimal] = {}
    for m in movimentos:
        chave = (m.data.year, m.data.month)
        if chave not in janela:
            continue
        entradas.setdefault(chave, Decimal(0))
        essenciais.setdefault(chave, Decimal(0))
        if m.valor > 0:
            entradas[chave] += m.valor
        elif m.essencial:
            essenciais[chave] += -m.valor
    return (
        arredondar(_mediana(entradas.values())),
        arredondar(_mediana(essenciais.values())),
        len(entradas),
    )


def capacidade_de_pagamento(entradas: Decimal, essenciais: Decimal) -> Decimal:
    return max(arredondar((entradas - essenciais) * FATOR_RESERVA), Decimal("0.00"))
