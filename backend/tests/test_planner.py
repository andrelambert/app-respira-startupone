"""Suíte do motor de plano — fixture canônica da §14.1 e casos da §14.2.

Os números esperados são os publicados no documento da Fase 5 (PKG_PLANO,
Oracle). O porte em Python reproduz os mesmos meses e mês da primeira
quitação, e os juros totais batem ao centavo com os valores arredondados
publicados (R$ 7.924 / R$ 8.240 / R$ 10.492).
"""

from datetime import date
from decimal import Decimal as D

import pytest

from app.domain.planner import (
    MAX_MESES,
    DividaEntrada,
    Metodo,
    Movimento,
    capacidade_de_pagamento,
    capacidade_minima,
    medianas_mensais,
    metodo_pre_selecionado,
    ordenar,
    simular,
    simular_so_minimo,
    simular_todas,
)

HOJE = date(2026, 10, 3)

JULIANA = [
    DividaEntrada("rotativo_a", D("2080.00"), D("0.1502"), D("208.00")),
    DividaEntrada("parcelado_b", D("1100.00"), D("0.0905"), D("110.00")),
    DividaEntrada("pessoal", D("4200.00"), D("0.0644"), D("260.00")),
    DividaEntrada("cheque", D("500.00"), D("0.0749"), D("50.00")),
    DividaEntrada("crediario_d", D("380.00"), D("0.0350"), D("95.00")),
]


# --- §14.1 -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("metodo", "meses", "juros", "juros_publicado", "primeira"),
    [
        (Metodo.AVALANCHE, 18, D("7923.69"), 7924, 10),
        (Metodo.EQUILIBRADO, 19, D("8239.99"), 8240, 2),
        (Metodo.SNOWBALL, 21, D("10491.56"), 10492, 2),
    ],
)
def test_fixture_canonica_juliana(metodo, meses, juros, juros_publicado, primeira):
    s = simular(JULIANA, D("900"), metodo, HOJE)
    assert s.converge
    assert s.meses == meses
    assert s.juros_totais == juros
    assert round(s.juros_totais) == juros_publicado
    assert s.primeira_quitacao_mes == primeira


def test_diferencas_publicadas():
    r = simular_todas(JULIANA, D("900"), HOJE)
    av, eq, sb = r[Metodo.AVALANCHE], r[Metodo.EQUILIBRADO], r[Metodo.SNOWBALL]
    assert round(eq.juros_totais - av.juros_totais) == 316
    assert eq.meses - av.meses == 1
    assert round(sb.juros_totais - av.juros_totais) == 2568


def test_data_quitacao_e_primeiro_dia_do_mes_corrente_mais_meses():
    s = simular(JULIANA, D("900"), Metodo.AVALANCHE, HOJE)
    assert s.data_quitacao == date(2028, 4, 1)


def test_cronograma_primeiro_mes_soma_a_capacidade():
    for s in simular_todas(JULIANA, D("900"), HOJE).values():
        assert sum(i.valor_mensal for i in s.itens) == D("900.00")
        assert [i.ordem for i in s.itens] == list(range(5))
        assert all(i.mes_quitacao is not None for i in s.itens)
        assert sum(i.juros_pagos for i in s.itens) == s.juros_totais


def test_trajetoria_cai_ate_zero():
    s = simular(JULIANA, D("900"), Metodo.AVALANCHE, HOJE)
    assert s.trajetoria[0] == D("8260.00")
    assert s.trajetoria[-1] == 0
    assert len(s.trajetoria) == s.meses + 1


def test_primeira_quitacao_so_conta_pela_sobra():
    # No avalanche, o crediário zera pelo próprio mínimo no 5º mês, mas a
    # referência só marca a primeira vitória quando a sobra quita uma dívida.
    s = simular(JULIANA, D("900"), Metodo.AVALANCHE, HOJE)
    crediario = next(i for i in s.itens if i.divida_id == "crediario_d")
    assert crediario.mes_quitacao == 5
    assert s.primeira_quitacao_mes == 10


# --- §5.2 ordenação ----------------------------------------------------------


def test_ordem_por_estrategia():
    ids = lambda m: [d.id for d in ordenar(JULIANA, m)]  # noqa: E731
    assert ids(Metodo.AVALANCHE) == ["rotativo_a", "parcelado_b", "cheque", "pessoal", "crediario_d"]
    assert ids(Metodo.SNOWBALL) == ["crediario_d", "cheque", "parcelado_b", "rotativo_a", "pessoal"]
    assert ids(Metodo.EQUILIBRADO) == [
        "crediario_d", "rotativo_a", "parcelado_b", "cheque", "pessoal",
    ]


def test_empates_sao_deterministicos():
    a = DividaEntrada("a", D("100"), D("0.05"), D("10"))
    b = DividaEntrada("b", D("200"), D("0.05"), D("10"))  # mesma taxa, saldo maior
    c = DividaEntrada("c", D("100"), D("0.08"), D("10"))  # mesmo saldo, taxa maior
    assert [d.id for d in ordenar([b, a, c], Metodo.AVALANCHE)] == ["c", "a", "b"]
    assert [d.id for d in ordenar([b, a, c], Metodo.SNOWBALL)] == ["c", "a", "b"]
    # Entrada em qualquer ordem → mesma saída
    assert ordenar([c, b, a], Metodo.EQUILIBRADO) == ordenar([a, b, c], Metodo.EQUILIBRADO)


# --- §14.2 -------------------------------------------------------------------


def test_sem_dividas():
    s = simular([], D("900"), Metodo.AVALANCHE, HOJE)
    assert (s.meses, s.juros_totais, s.data_quitacao) == (0, 0, None)


@pytest.mark.parametrize("capacidade", [D("0"), D("-50")])
def test_capacidade_nao_positiva(capacidade):
    s = simular(JULIANA, capacidade, Metodo.AVALANCHE, HOJE)
    assert (s.meses, s.juros_totais, s.data_quitacao) == (0, 0, None)
    assert not s.converge


def test_capacidade_igual_aos_minimos_nao_converge_nem_trava():
    s = simular(JULIANA, D("723"), Metodo.AVALANCHE, HOJE)
    assert not s.converge
    assert s.data_quitacao is None
    assert s.meses <= MAX_MESES


def test_capacidade_minima_e_o_piso_que_converge():
    piso = capacidade_minima(JULIANA, HOJE)
    assert piso is not None
    assert simular(JULIANA, piso, Metodo.AVALANCHE, HOJE).converge
    assert not simular(JULIANA, piso - 1, Metodo.AVALANCHE, HOJE).converge


def test_uma_divida_so_resultado_identico_nas_tres():
    unica = [DividaEntrada("x", D("1500"), D("0.05"), D("100"))]
    r = simular_todas(unica, D("300"), HOJE)
    assert len({(s.meses, s.juros_totais, s.primeira_quitacao_mes) for s in r.values()}) == 1


def test_juros_maiores_que_minimos_cenario_so_minimo_cresce():
    c = simular_so_minimo(JULIANA, 18)
    assert not c.converge
    assert c.saldo_no_horizonte > D("8260")


# --- §5.4 pré-seleção --------------------------------------------------------


def test_pre_selecao():
    assert metodo_pre_selecionado(False) is Metodo.AVALANCHE
    assert metodo_pre_selecionado(None) is Metodo.AVALANCHE
    assert metodo_pre_selecionado(True) is Metodo.EQUILIBRADO


# --- §5.1 capacidade ---------------------------------------------------------


def test_capacidade_com_reserva_de_10_porcento():
    assert capacidade_de_pagamento(D("4800"), D("3800")) == D("900.00")
    assert capacidade_de_pagamento(D("3000"), D("3500")) == D("0.00")


def test_medianas_mensais_usam_seis_meses_completos_anteriores():
    movs = []
    entradas = [4800, 4650, 4800, 5100, 4800, 4720]
    essenciais = [3800, 3750, 3890, 3800, 3820, 3800]
    for i, (e, s) in enumerate(zip(entradas, essenciais, strict=True)):
        d = date(2026, 4 + i, 10)
        movs += [Movimento(d, D(e), False), Movimento(d, D(-s), True), Movimento(d, D(-500), False)]
    # mês corrente (parcial) e mês fora da janela não entram
    movs += [Movimento(date(2026, 10, 1), D(99999), False), Movimento(date(2026, 3, 5), D(1), False)]
    med_e, med_s, n = medianas_mensais(movs, HOJE)
    assert (med_e, med_s, n) == (D("4800.00"), D("3800.00"), 6)
    assert capacidade_de_pagamento(med_e, med_s) == D("900.00")
