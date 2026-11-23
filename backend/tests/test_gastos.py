"""N2 (Fase 7): para onde foi o dinheiro — F-3, F-4."""

from datetime import date
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.domain.gastos import Gasto, candidata_a_corte, por_categoria
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


def test_transferencias_ficam_de_fora_e_essencial_pela_maior_parte_do_valor():
    gastos = [
        g(OUT, "Transfers", "1000"),
        g(OUT, "Home & Life", "1200", True),  # aluguel
        g(OUT, "Home & Life", "100", False),
    ]
    cats = por_categoria(gastos, OUT, MESES)
    assert [c.categoria for c in cats] == ["Home & Life"] and cats[0].essencial


def test_candidata_e_a_nao_essencial_com_maior_excesso():
    gastos = [
        g(OUT, "Mercado", "900", True), g(SET, "Mercado", "500", True),  # essencial: nunca é sugerida
        g(OUT, "Delivery", "400"), g(SET, "Delivery", "200"),
        g(OUT, "Roupas", "500"), g(SET, "Roupas", "450"),
    ]
    c = candidata_a_corte(por_categoria(gastos, OUT, {OUT, SET}))
    assert c is not None and c.categoria == "Delivery"
    assert candidata_a_corte(por_categoria([g(OUT, "Delivery", "100"), g(SET, "Delivery", "200")], OUT, {OUT, SET})) is None


def test_api_gastos_e_impacto_no_plano(demo_limpa):
    api = demo_limpa
    r = api.get("/pfm/categorias")  # padrão: último mês completo, onde a demo tem o pico
    assert r.status_code == 200
    v = r.json()
    nomes = [c["categoria"] for c in v["categorias"]]
    assert "Credits & Loans" not in nomes and "Transfers" not in nomes  # dívida e transferência fora
    assert D(v["total"]) == sum(D(c["total"]) for c in v["categorias"])
    imp = v["impacto_plano"]
    assert imp["categoria"] == "Online Platforms & Leisure" and imp["meses_antecipados"] >= 1
    assert imp["data_nova"] < imp["data_atual"]
    assert v["meses_disponiveis"] == sorted(v["meses_disponiveis"]) and len(v["meses_disponiveis"]) <= 12

    # Com plano ativo, o impacto usa a capacidade e o método do plano.
    assert api.post("/plano", json={"metodo": "SNOWBALL", "capacidade": "2000.00"}, headers=H).status_code == 201
    com_plano = api.get("/pfm/categorias").json()["impacto_plano"]
    assert com_plano is None or com_plano["data_atual"] != imp["data_atual"]

    for invalido in ("2026-13", "26-10", "2026-1", "x"):
        assert api.get("/pfm/categorias", params={"mes": invalido}).status_code == 422


def test_gastos_exigem_login(api):
    api.cookies.clear()
    assert api.get("/pfm/categorias").status_code == 401
