"""N2 (Fase 7): para onde foi o dinheiro — F-3, F-4."""

from datetime import date
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.domain.gastos import Gasto, GastoDetalhado, candidata_a_corte, historico_categoria, por_categoria
from app.main import app
from tests.test_api import H


@pytest.fixture(scope="module")
def api():
    with TestClient(app) as c:
        yield c


OUT, SET, AGO, JUL = date(2026, 10, 1), date(2026, 9, 1), date(2026, 8, 1), date(2026, 7, 1)
MESES = {OUT, SET, AGO, JUL}


def g(mes, cat, valor, essencial=False):
    return Gasto(mes.replace(day=10), cat, D(valor), essencial)


def test_media_dos_3_meses_anteriores_e_variacao():
    gastos = [g(OUT, "Delivery", "470"), g(SET, "Delivery", "250"), g(AGO, "Delivery", "250"), g(JUL, "Delivery", "250")]
    [c] = por_categoria(gastos, OUT, MESES)
    assert (c.total, c.media_3m, c.variacao) == (D("470.00"), D("250.00"), D("0.88"))


def test_mes_sem_dado_nao_entra_na_media():
    """Agosto sem nenhuma transação: média sobre setembro e julho, não sobre 3."""
    gastos = [g(OUT, "Mercado", "300", True), g(SET, "Mercado", "200", True), g(JUL, "Mercado", "400", True)]
    [c] = por_categoria(gastos, OUT, {OUT, SET, JUL})
    assert c.media_3m == D("300.00")


def test_transferencias_ficam_de_fora_e_selo_essencial_so_quando_tudo_e_essencial():
    """Teste com conta real: "bebidas" e "loja de conveniência" levavam o selo de
    essencial. Agora a categoria só leva o selo quando todo o gasto nela é essencial."""
    gastos = [
        g(OUT, "Transfers", "1000"),
        g(OUT, "Bills & Utilities", "150", True),
        g(OUT, "Food & Groceries", "1200", True),  # mercado
        g(OUT, "Food & Groceries", "100", False),  # bebida
    ]
    cats = {c.categoria: c for c in por_categoria(gastos, OUT, MESES)}
    assert set(cats) == {"Bills & Utilities", "Food & Groceries"}
    assert cats["Bills & Utilities"].essencial and not cats["Food & Groceries"].essencial
    assert cats["Food & Groceries"].nao_essencial == D("100.00")


def test_candidata_e_a_nao_essencial_com_maior_excesso():
    gastos = [
        g(OUT, "Mercado", "900", True), g(SET, "Mercado", "500", True),  # essencial: nunca é sugerida
        g(OUT, "Delivery", "400"), g(SET, "Delivery", "200"),
        g(OUT, "Roupas", "500"), g(SET, "Roupas", "450"),
    ]
    c = candidata_a_corte(por_categoria(gastos, OUT, {OUT, SET}))
    assert c is not None and c.categoria == "Delivery"
    assert candidata_a_corte(por_categoria([g(OUT, "Delivery", "100"), g(SET, "Delivery", "200")], OUT, {OUT, SET})) is None


def test_candidata_olha_so_a_parte_nao_essencial_e_nunca_investimento():
    gastos = [
        # Alimentação: o mercado caiu, o delivery subiu 220 — é o delivery que conta.
        g(OUT, "Food & Groceries", "1300", True), g(SET, "Food & Groceries", "1400", True),
        g(OUT, "Food & Groceries", "430"), g(SET, "Food & Groceries", "210"),
        # Investimento muito acima da média: dinheiro guardado não é corte.
        g(OUT, "Investments & Savings", "10000"), g(SET, "Investments & Savings", "5000"),
    ]
    c = candidata_a_corte(por_categoria(gastos, OUT, {OUT, SET}))
    assert c is not None and c.categoria == "Food & Groceries"
    assert (c.nao_essencial, c.media_nao_essencial) == (D("430.00"), D("210.00"))
    so_invest = [g(OUT, "Investments & Savings", "10000"), g(SET, "Investments & Savings", "5000")]
    assert candidata_a_corte(por_categoria(so_invest, OUT, {OUT, SET})) is None


def test_historico_da_categoria_por_mes_e_subcategoria():
    meses = [AGO, SET, OUT]
    gastos = [
        GastoDetalhado(date(2026, 10, 3), "Delivery", D("30")),
        GastoDetalhado(date(2026, 10, 9), "Groceries", D("200")),
        GastoDetalhado(date(2026, 9, 9), "Groceries", D("150")),
        GastoDetalhado(date(2026, 9, 10), None, D("5")),  # sem subcategoria: só no total
        GastoDetalhado(date(2026, 7, 9), "Groceries", D("999")),  # fora da janela
    ]
    serie, subs = historico_categoria(gastos, meses)
    assert serie == [(AGO, D("0.00")), (SET, D("155.00")), (OUT, D("230.00"))]
    assert subs == [("Groceries", D("350.00")), ("Delivery", D("30.00"))]


def test_api_gastos_e_impacto_no_plano(demo_limpa):
    api = demo_limpa
    r = api.get("/pfm/categorias")  # padrão: último mês completo, onde a demo tem o pico
    assert r.status_code == 200
    v = r.json()
    nomes = [c["categoria"] for c in v["categorias"]]
    assert "Credits & Loans" not in nomes and "Transfers" not in nomes  # dívida e transferência fora
    assert D(v["total"]) == sum(D(c["total"]) for c in v["categorias"])
    imp = v["impacto_plano"]
    # Categoria principal; o valor é só o excesso do delivery (não essencial), não do mercado.
    assert imp["categoria"] == "Food & Groceries" and imp["meses_antecipados"] >= 1
    assert D(imp["valor_mensal"]) == D("220.00")
    alim = next(c for c in v["categorias"] if c["categoria"] == "Food & Groceries")
    assert not alim["essencial"]  # mercado + delivery: não leva o selo
    assert imp["data_nova"] < imp["data_atual"]
    assert v["meses_disponiveis"] == sorted(v["meses_disponiveis"]) and len(v["meses_disponiveis"]) <= 12

    # Com plano ativo, o impacto usa a capacidade e o método do plano.
    assert api.post("/plano", json={"metodo": "SNOWBALL", "capacidade": "2000.00"}, headers=H).status_code == 201
    com_plano = api.get("/pfm/categorias").json()["impacto_plano"]
    assert com_plano is None or com_plano["data_atual"] != imp["data_atual"]

    for invalido in ("2026-13", "26-10", "2026-1", "x"):
        assert api.get("/pfm/categorias", params={"mes": invalido}).status_code == 422


def test_api_historico_da_categoria(demo_limpa):
    api = demo_limpa
    r = api.get("/pfm/categorias/historico", params={"categoria": "Food & Groceries"})
    assert r.status_code == 200
    v = r.json()
    assert len(v["meses"]) == 12 and [m["mes"] for m in v["meses"]] == sorted(m["mes"] for m in v["meses"])
    subs = [s["subcategoria"] for s in v["subcategorias"]]
    assert {"Groceries", "Delivery"} <= set(subs)
    # Com um tipo de gasto escolhido, o gráfico segue o filtro; a lista de tipos não muda.
    so = api.get("/pfm/categorias/historico", params={"categoria": "Food & Groceries", "subcategoria": "Delivery"}).json()
    assert [s["subcategoria"] for s in so["subcategorias"]] == subs
    assert all(D(a["total"]) <= D(b["total"]) for a, b in zip(so["meses"], v["meses"]))
    assert any(D(a["total"]) < D(b["total"]) for a, b in zip(so["meses"], v["meses"]))
    assert api.get("/pfm/categorias/historico", params={"categoria": "Food & Groceries", "meses": "13"}).status_code == 422
    assert api.get("/pfm/categorias/historico").status_code == 422


def test_tocar_na_barra_de_entradas_ou_saidas_mostra_o_que_ela_soma(demo_limpa):
    """Gráfico de entradas e saídas (Contas) → Todas as transações com fluxo=renda/gasto:
    a soma da lista é exatamente o valor da barra."""
    import calendar

    api = demo_limpa
    meses = api.get("/pfm/fluxo-mensal", params={"meses": 3}).json()["meses"]
    assert len(meses) == 3
    for m in meses:
        ini = date.fromisoformat(m["mes"])
        fim = ini.replace(day=calendar.monthrange(ini.year, ini.month)[1])
        base = {"desde": ini.isoformat(), "ate": fim.isoformat(), "por_pagina": 5}
        renda = api.get("/transacoes", params={**base, "fluxo": "renda"}).json()
        gasto = api.get("/transacoes", params={**base, "fluxo": "gasto"}).json()
        assert D(renda["total_entradas"]) == D(m["entradas"]) and D(renda["total_saidas"]) == 0
        assert D(gasto["total_saidas"]) == D(m["essenciais"]) + D(m["outros_gastos"])
        assert D(gasto["total_entradas"]) == 0
    assert api.get("/transacoes", params={"fluxo": "outro"}).status_code == 422


def test_fluxo_mensal_separa_a_reserva():
    from app.domain.gastos import Movimento, fluxo_mensal

    def mv(valor, **kw):
        base = {"essencial": False, "pagamento_divida": False, "entrada_renda": False, "categoria": None}
        return Movimento(date(2026, 10, 5), D(valor), **{**base, **kw})

    movs = [
        mv("3000", entrada_renda=True),
        mv("-2500", categoria="Investments & Savings", reserva=True),  # aplicou
        mv("700", categoria="Investments & Savings", reserva=True),  # resgatou
        mv("-1200", essencial=True),
    ]
    [f] = fluxo_mensal(movs, [OUT])
    assert (f.entradas, f.essenciais, f.outros_gastos, f.reserva) == (D("3000.00"), D("1200.00"), D("0.00"), D("1800.00"))


def test_gastos_exigem_login(api):
    api.cookies.clear()
    assert api.get("/pfm/categorias").status_code == 401
    assert api.get("/pfm/categorias/historico", params={"categoria": "Food & Groceries"}).status_code == 401


def test_fluxo_mensal_usa_a_base_da_capacidade():
    from app.domain.gastos import Movimento, fluxo_mensal

    def mv(dia, valor, **kw):
        base = {"essencial": False, "pagamento_divida": False, "entrada_renda": False, "categoria": None}
        return Movimento(dia, D(valor), **{**base, **kw})

    movs = [
        mv(date(2026, 10, 5), "3100", entrada_renda=True),
        mv(date(2026, 10, 6), "500"),  # entrada que não é renda (ex.: estorno): fora
        mv(date(2026, 10, 7), "-1200", essencial=True),
        mv(date(2026, 10, 8), "-200"),
        mv(date(2026, 10, 9), "-900", categoria="Transfers"),  # transferência: fora
        mv(date(2026, 10, 12), "-208", pagamento_divida=True),
        mv(date(2026, 11, 1), "-50", essencial=True),  # fora da janela
    ]
    [f] = fluxo_mensal(movs, [OUT])
    assert (f.entradas, f.essenciais, f.outros_gastos, f.pagamentos_divida) == (
        D("3100.00"), D("1200.00"), D("200.00"), D("208.00"),
    )
    assert f.sobra == D("1900.00")  # entradas - essenciais, como a capacidade


def test_api_fluxo_mensal_bate_com_a_capacidade(demo_limpa):
    from statistics import median

    api = demo_limpa
    r = api.get("/pfm/fluxo-mensal")
    assert r.status_code == 200
    v = r.json()
    assert len(v["meses"]) == 6 and v["reserva_pct"] == 10
    entradas = median(D(m["entradas"]) for m in v["meses"])
    essenciais = median(D(m["essenciais"]) for m in v["meses"])
    assert (D(v["entradas_mediana"]), D(v["essenciais_mediana"])) == (entradas, essenciais)
    assert D(v["capacidade"]) == ((entradas - essenciais) * D("0.90")).quantize(D("0.01"))
    assert D(v["capacidade"]) == D(api.get("/plano/simulacoes").json()["capacidade_calculada"]["valor"])
    for invalido in ("2", "13", "x"):
        assert api.get("/pfm/fluxo-mensal", params={"meses": invalido}).status_code == 422
