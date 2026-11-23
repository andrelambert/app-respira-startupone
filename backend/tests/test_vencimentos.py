"""N3 (Fase 7): próximos vencimentos — F-5."""

from datetime import date
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.domain.vencimentos import DividaVenc, FaturaVenc, montar, proxima_data
from app.main import app
from tests.test_api import H


@pytest.fixture(scope="module")
def api():
    with TestClient(app) as c:
        yield c


HOJE = date(2026, 11, 23)


def _div(**kw):
    base = {"id": 1, "credor": "Banco", "descricao": "Empréstimo", "modalidade": "CREDITO_PESSOAL",
            "dia_vencimento": 5, "parcela": D("300.00"), "em_atraso_dias": 0, "saldo": D("4000.00")}
    return DividaVenc(**{**base, **kw})


def _fat(**kw):
    base = {"id": 1, "conta_id": 10, "credor": "Nubank", "descricao": "Cartão", "vencimento": date(2026, 12, 12),
            "total": D("2080.00"), "minimo": D("208.00"), "pago": D("0.00"), "divida_id": 7}
    return FaturaVenc(**{**base, **kw})


def test_proxima_data_vira_o_mes_e_respeita_meses_curtos():
    assert proxima_data(HOJE, 25) == date(2026, 11, 25)
    assert proxima_data(HOJE, 5) == date(2026, 12, 5)
    assert proxima_data(date(2027, 1, 31), 31) == date(2027, 1, 31)
    assert proxima_data(date(2027, 2, 1), 31) == date(2027, 2, 28)


def test_janela_de_dias_e_atrasados_sempre():
    dividas = [_div(id=1, dia_vencimento=25), _div(id=2, dia_vencimento=5), _div(id=3, dia_vencimento=10, em_atraso_dias=12)]
    em_7 = montar(hoje=HOJE, dias=7, faturas=[], dividas=dividas)
    assert [(v.divida_id, v.status.value) for v in em_7] == [(3, "ATRASADO"), (1, "PENDENTE")]
    em_15 = montar(hoje=HOJE, dias=15, faturas=[], dividas=dividas)
    assert [v.divida_id for v in em_15] == [3, 1, 2]
    assert em_7[0].dias == -12


def test_cartao_sai_pela_fatura_e_so_a_mais_recente():
    cartao = _div(id=7, modalidade="CARTAO_ROTATIVO", dia_vencimento=12)
    antiga = _fat(id=1, vencimento=date(2026, 11, 12), pago=D("208.00"))
    atual = _fat(id=2, vencimento=date(2026, 12, 12))
    vs = montar(hoje=HOJE, dias=30, faturas=[antiga, atual], dividas=[cartao])
    assert [(v.tipo, v.data) for v in vs] == [("FATURA", date(2026, 12, 12))]
    assert (vs[0].valor, vs[0].valor_total, vs[0].divida_id) == (D("208.00"), D("2080.00"), 7)


def test_status_da_fatura():
    paga = montar(hoje=HOJE, dias=30, faturas=[_fat(pago=D("2080.00"))], dividas=[])
    assert paga[0].status.value == "PAGO"
    atrasada = montar(hoje=HOJE, dias=7, faturas=[_fat(vencimento=date(2026, 11, 12))], dividas=[])
    assert atrasada[0].status.value == "ATRASADO"  # fora da janela, mas atrasada aparece
    parcial = montar(hoje=HOJE, dias=30, faturas=[_fat(pago=D("100.00"))], dividas=[])
    assert (parcial[0].status.value, parcial[0].valor) == ("PENDENTE", D("108.00"))  # falta do mínimo


def test_quitada_ou_sem_dia_nao_aparece():
    assert montar(hoje=HOJE, dias=30, faturas=[], dividas=[_div(saldo=D(0)), _div(id=2, dia_vencimento=None)]) == []


def test_api_vencimentos_da_juliana(demo_limpa):
    api = demo_limpa
    r = api.get("/vencimentos", params={"dias": 30})
    assert r.status_code == 200
    v = r.json()
    itens = v["itens"]
    assert itens and all(i["status"] in ("PAGO", "PENDENTE", "ATRASADO") for i in itens)
    # atrasados primeiro; o resto por data, dentro da janela
    status = [i["status"] for i in itens]
    assert status == sorted(status, key=lambda s: s != "ATRASADO")
    futuros = [i for i in itens if i["status"] != "ATRASADO"]
    assert [i["data"] for i in futuros] == sorted(i["data"] for i in futuros)
    assert all(0 <= i["dias"] <= 30 for i in futuros)
    # cartão não aparece duas vezes (fatura + dívida)
    assert not any(i["tipo"] == "PARCELA" and "Rotativo" in i["descricao"] for i in itens)
    assert all(i["valor_plano"] is None for i in itens)  # sem plano ativo

    assert api.post("/plano", json={"metodo": "AVALANCHE", "capacidade": "1755.00"}, headers=H).status_code == 201
    com_plano = api.get("/vencimentos").json()["itens"]
    assert any(i["valor_plano"] for i in com_plano)

    for invalido in ("0", "61", "abc"):
        assert api.get("/vencimentos", params={"dias": invalido}).status_code == 422


def test_vencimentos_exigem_login(api):
    api.cookies.clear()
    assert api.get("/vencimentos").status_code == 401
