"""M3 (Fase 7): o motor em Python e o PKG_PLANO_APP em PL/SQL coincidem ao centavo.

Só roda no Oracle (TEST_DATABASE_URL); no SQLite é pulado.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_api import H


@pytest.fixture(scope="module")
def api():
    with TestClient(app) as c:
        yield c


@pytest.mark.oracle
def test_motor_coincide_no_oracle(demo_limpa):
    api = demo_limpa
    esperado = {"AVALANCHE": (16, "7726.58"), "EQUILIBRADO": (17, "7940.64"), "SNOWBALL": (17, "9257.67")}
    for metodo, (meses, juros) in esperado.items():
        r = api.get("/plano/conferencia-oracle", params={"metodo": metodo, "capacidade": "1755.00"})
        assert r.status_code == 200, r.text
        c = r.json()
        assert c["coincide"], c
        assert (c["oracle"]["meses"], c["oracle"]["juros"]) == (meses, juros), c


@pytest.mark.oracle
def test_motor_coincide_com_capacidade_insuficiente_e_apos_meses(demo_limpa):
    """Casos de borda: plano que não converge e saldos depois de meses simulados."""
    api = demo_limpa
    for metodo in ("AVALANCHE", "EQUILIBRADO", "SNOWBALL"):
        c = api.get("/plano/conferencia-oracle", params={"metodo": metodo, "capacidade": "900.00"}).json()
        assert c["coincide"] and c["python"]["converge"] is False, c
    assert api.post("/plano", json={"metodo": "EQUILIBRADO", "capacidade": "1755.00"}, headers=H).status_code == 201
    for d in (False, True):
        assert api.post("/demo/avancar-mes", json={"mes_dificil": d}, headers=H).status_code == 200
    for metodo in ("AVALANCHE", "EQUILIBRADO", "SNOWBALL"):
        c = api.get("/plano/conferencia-oracle", params={"metodo": metodo}).json()
        assert c["coincide"], c
