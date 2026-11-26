"""Teste com conta real (Estela, Nubank, Fase 7): fatura aberta, resultado do mês,
sobra real e o mês que vem. Números do caso real, sem dado pessoal."""

from datetime import date
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.domain.gastos import Movimento, fluxo_mensal, sobra_real
from app.domain.pfm import fatura_aberta_estimada
from app.main import app


@pytest.fixture(scope="module")
def api():
    with TestClient(app) as c:
        yield c

OUT = date(2026, 10, 1)


def test_fatura_aberta_e_o_usado_menos_parcelas_futuras_menos_o_resto_da_fechada():
    """O app mostrava R$ 61 (o resto da fatura de novembro); a aberta já passava de R$ 1.000."""
    assert fatura_aberta_estimada(D("3389.18"), D("2293.24"), D("61.14")) == D("1034.80")
    assert fatura_aberta_estimada(D("100.00"), D("150.00"), D("0")) == D("0.00")  # nunca negativa


def _mv(valor, **kw):
    base = {"essencial": False, "pagamento_divida": False, "entrada_renda": False, "categoria": None}
    return Movimento(date(2026, 10, 5), D(valor), **{**base, **kw})


def test_resultado_do_mes_nao_conta_a_fatura_duas_vezes():
    movs = [
        _mv("2500", entrada_renda=True),
        _mv("-1000", essencial=True),
        _mv("-1800"),  # compras (inclusive no cartão)
        _mv("-1700", pagamento_divida=True, fatura_cartao=True),  # paga as compras do cartão: já contadas
        _mv("-300", pagamento_divida=True),  # parcela de empréstimo: conta
        _mv("600", categoria="Investments & Savings", reserva=True),  # resgatou para cobrir
    ]
    [f] = fluxo_mensal(movs, [OUT])
    assert f.resultado == D("-600.00")  # fechou negativo
    assert f.pagamentos_divida == D("2000.00") and f.reserva == D("-600.00")


def test_sobra_real_e_a_mediana_depois_de_todos_os_gastos():
    def mes(m, e, ess, o):
        return [
            Movimento(date(2026, m, 5), D(e), False, False, True, None),
            Movimento(date(2026, m, 6), -D(ess), True, False, False, None),
            Movimento(date(2026, m, 7), -D(o), False, False, False, None),
        ]

    movs = mes(8, "2765", "1629", "2563") + mes(9, "577", "1451", "2029") + mes(10, "4397", "1577", "3343")
    fl = fluxo_mensal(movs, [date(2026, 8, 1), date(2026, 9, 1), OUT, date(2026, 11, 1)])
    assert sobra_real(fl) == D("-1427.00")  # mês sem dado (novembro) não entra
    assert sobra_real([]) is None


def test_api_mes_que_vem_fatura_aberta_e_sobra_real(demo_limpa):
    api = demo_limpa
    pm = api.get("/pfm/proximo-mes").json()
    previsto = D(pm["faturas_cartao"]) + D(pm["parcelas_dividas"]) + D(pm["essenciais_conta"] or 0)
    assert D(pm["previsto"]) == previsto
    assert D(pm["sobra"]) == D(pm["entradas"]) - previsto
    cap = api.get("/plano/simulacoes").json()["capacidade_calculada"]
    assert cap["sobra_real"] is not None and D(cap["sobra_real"]) < D(cap["valor"]) / D("0.9")
    cartoes = [c for b in api.get("/pfm/visao-geral").json()["bancos"] for c in b["contas"] if c["tipo"] == "CARTAO_CREDITO"]
    assert cartoes and all(c["fatura_aberta"] is not None and D(c["fatura_aberta"]) >= 0 for c in cartoes)
    meses = api.get("/pfm/fluxo-mensal").json()["meses"]
    assert all("resultado" in m for m in meses)
    g = api.get("/pfm/categorias").json()
    mes = next(m for m in meses if m["mes"] == g["mes"])
    assert D(g["entradas"]) == D(mes["entradas"])  # o mesmo "entrou no mês" das duas telas
