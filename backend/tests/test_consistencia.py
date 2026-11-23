"""A17/A18 (Fase 7): Raio-X, Dívidas e Início leem a mesma fonte para total e data."""

from datetime import date
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.domain.planner import adicionar_meses
from app.main import app
from tests.test_api import H


@pytest.fixture(scope="module")
def api():
    with TestClient(app) as c:
        yield c


def test_datas_e_total_coincidem_entre_telas_depois_de_simular(demo_limpa):
    """Início (projeção) e Dívidas (cronograma) dão a mesma data de saída, e o
    total do Raio-X é a soma das dívidas — também depois de meses simulados."""
    api = demo_limpa
    assert api.post("/plano", json={"metodo": "AVALANCHE", "capacidade": "1755.00"}, headers=H).status_code == 201
    for mes_dificil in (None, False, True):
        if mes_dificil is not None:
            assert api.post("/demo/avancar-mes", json={"mes_dificil": mes_dificil}, headers=H).status_code == 200
        p = api.get("/plano/ativo").json()
        hoje = date.fromisoformat(p["hoje"])
        ultimo = max(i["mes_quitacao"] for i in p["cronograma"] if i["mes_quitacao"])
        assert adicionar_meses(hoje.replace(day=1), ultimo).isoformat() == p["projecao_atual"]["data_quitacao"]

        rx = api.get("/raiox").json()
        abertas = [d for d in api.get("/dividas").json() if D(d["saldo"]) > 0]
        assert D(rx["divida_total"]) == sum(D(d["saldo"]) for d in abertas) == D(p["divida_atual"])
        assert rx["qtd_dividas"] == len(abertas)
