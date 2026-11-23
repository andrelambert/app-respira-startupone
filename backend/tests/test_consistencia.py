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


def test_demo_contas_e_faturas_avancam_com_os_meses(demo_limpa):
    """A16: o relógio da demo anda e as contas acompanham — fatura do cartão não
    aparece "atrasada", saldos de cartão/empréstimo/cheque especial seguem a
    dívida e o contrato conta as parcelas pagas."""
    api = demo_limpa
    antes = {d["id"]: d for d in api.get("/dividas").json()}
    assert api.post("/plano", json={"metodo": "AVALANCHE", "capacidade": "1755.00"}, headers=H).status_code == 201
    for mes_dificil in (False, True, False):
        assert api.post("/demo/avancar-mes", json={"mes_dificil": mes_dificil}, headers=H).status_code == 200

    hoje = api.get("/usuarios/me").json()["hoje"]
    dividas = {d["id"]: d for d in api.get("/dividas").json()}
    v = api.get("/pfm/visao-geral").json()
    contas = [c for b in v["bancos"] for c in b["contas"]]
    for c in contas:
        if c["tipo"] == "CARTAO_CREDITO":
            f = c["fatura_atual"]
            assert f["situacao"] != "ATRASADA", (c["nome"], f)
            assert f["vencimento"] >= hoje, (c["nome"], f["vencimento"], hoje)

    por_conta = {d["conta_id"]: d for d in dividas.values() if d.get("conta_id")}
    for c in contas:
        d = por_conta.get(c["id"])
        if d is None:
            continue
        if c["tipo"] in ("CARTAO_CREDITO", "EMPRESTIMO", "FINANCIAMENTO"):
            assert D(c["saldo"]) == D(d["saldo"]), (c["nome"], c["saldo"], d["saldo"])
        elif c["tipo"] == "CORRENTE":
            assert D(c["usado_cheque_especial"]) == D(d["saldo"]), (c["nome"], d["descricao"])

    moto = next(d for d in dividas.values() if d["modalidade"] == "FIN_VEICULO")
    assert moto["parcelas_pagas"] == antes[moto["id"]]["parcelas_pagas"] + 3
