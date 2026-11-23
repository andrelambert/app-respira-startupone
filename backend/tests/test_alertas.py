"""A1 (Fase 7): alertas não se acumulam nem repetem com o passar dos meses."""

from collections import Counter
from datetime import date
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.domain.events import DividaEstado, EventoPendente, detectar, grupo, resolvidos
from app.main import app
from tests.test_api import H


@pytest.fixture(scope="module")
def api():
    with TestClient(app) as c:
        yield c


def _pendentes(api):
    return [e for e in api.get("/eventos").json() if not e["notificado_em"] and e["tipo"] != "DIVIDA_QUITADA"]


def test_tres_meses_simulados_sem_alerta_repetido(demo_limpa):
    api = demo_limpa
    atraso_inicial = [e for e in _pendentes(api) if e["tipo"] == "ATRASO_CONFIRMADO"]
    assert len(atraso_inicial) == 2  # carnê (12 dias) e crédito pessoal da Caixa

    assert api.post("/plano", json={"metodo": "AVALANCHE", "capacidade": "1755.00"}, headers=H).status_code == 201
    for mes_dificil in (False, True, False):
        r = api.post("/demo/avancar-mes", json={"mes_dificil": mes_dificil}, headers=H)
        assert r.status_code == 200
        grupos = Counter(
            (e["tipo"], e["divida_id"], e["contexto"].get("categoria")) for e in _pendentes(api)
        )
        repetidos = {g: n for g, n in grupos.items() if n > 1}
        assert not repetidos, repetidos

    # A parcela em atraso foi paga pelo plano: o atraso não fica pendurado.
    assert not [e for e in _pendentes(api) if e["tipo"] == "ATRASO_CONFIRMADO"]
    # Nenhum "vence em breve" com o vencimento já passado.
    hoje = api.get("/usuarios/me").json().get("hoje")
    for e in _pendentes(api):
        if e["tipo"] == "ATRASO_IMINENTE" and hoje:
            assert e["contexto"]["vencimento"] >= hoje


# --- regra de domínio, sem banco -------------------------------------------------------


def _divida(**kw):
    base = {
        "id": 1, "descricao": "Rotativo", "instituicao": "Nubank", "modalidade": "CARTAO_ROTATIVO",
        "saldo": D("2080.00"), "taxa_mes": D("0.1502"), "minima": D("208.00"),
        "dia_vencimento": 12, "em_atraso_dias": 0,
    }
    return DividaEstado(**{**base, **kw})


def _resolve(hoje, pendente, dividas, saldo_em_conta=D("50.00"), usado=D(0)):
    detectados = detectar(
        hoje=hoje, dividas=dividas, anteriores={d.id: d for d in dividas},
        saldo_em_conta=saldo_em_conta, usado_cheque_especial=usado, gastos=[],
    )
    return resolvidos(
        hoje=hoje, pendentes=[pendente], dividas=dividas, detectados=detectados, usado_cheque_especial=usado
    )


AI = EventoPendente(10, "ATRASO_IMINENTE", 1, {"vencimento": "2026-11-12"})


def test_atraso_iminente_continua_enquanto_vale():
    assert _resolve(date(2026, 11, 10), AI, [_divida()]) == []


def test_atraso_iminente_sai_depois_do_vencimento():
    assert _resolve(date(2026, 11, 13), AI, [_divida()]) == [10]


def test_atraso_iminente_sai_quando_a_conta_cobre_a_parcela():
    assert _resolve(date(2026, 11, 10), AI, [_divida()], saldo_em_conta=D("500.00")) == [10]


def test_atraso_iminente_sai_quando_a_divida_e_quitada():
    assert _resolve(date(2026, 11, 10), AI, [_divida(saldo=D(0))]) == [10]


def test_atraso_confirmado_sai_quando_o_atraso_zera():
    ac = EventoPendente(11, "ATRASO_CONFIRMADO", 1, {})
    assert _resolve(date(2026, 11, 20), ac, [_divida(em_atraso_dias=12)]) == []
    assert _resolve(date(2026, 11, 20), ac, [_divida(em_atraso_dias=0)]) == [11]


def test_pico_sai_quando_fecha_outro_mes_e_cheque_quando_zera():
    pico = EventoPendente(12, "PICO_CATEGORIA", None, {"categoria": "Delivery", "mes": "2026-10-01"})
    assert _resolve(date(2026, 11, 20), pico, []) == []
    assert _resolve(date(2026, 12, 2), pico, []) == [12]
    ce = EventoPendente(13, "CHEQUE_ESPECIAL", 3, {})
    assert _resolve(date(2026, 11, 20), ce, [], usado=D("500.00")) == []
    assert _resolve(date(2026, 11, 20), ce, [], usado=D(0)) == [13]


def test_marco_de_quitacao_nunca_sai():
    dq = EventoPendente(14, "DIVIDA_QUITADA", 1, {})
    assert _resolve(date(2027, 5, 1), dq, [_divida(saldo=D(0))]) == []


def test_grupo_separa_picos_por_categoria():
    assert grupo("PICO_CATEGORIA", None, {"categoria": "A"}) != grupo("PICO_CATEGORIA", None, {"categoria": "B"})
    assert grupo("ATRASO_IMINENTE", 1, {}) != grupo("ATRASO_IMINENTE", 2, {})



def test_atraso_iminente_usa_a_conta_do_mesmo_banco_e_diz_o_nome():
    """A5: com R$ 563 somando todas as contas, mas só R$ 63,40 no Nubank, a fatura
    do Nubank está em risco — e o alerta diz de qual conta está falando."""
    eventos = detectar(
        hoje=date(2026, 11, 10), dividas=[_divida()], anteriores={},
        saldo_em_conta=D("563.40"), usado_cheque_especial=D(0), gastos=[],
        saldo_por_banco={"Nubank": D("63.40"), "Caixa": D("500.00")},
    )
    ai = next(e for e in eventos if e.tipo == "ATRASO_IMINENTE")
    assert (ai.contexto["conta"], ai.contexto["saldo_conta"], ai.contexto["falta"]) == ("Nubank", "63.40", "144.60")

    # Sem conta no banco da dívida: compara com a soma e não inventa um nome.
    sem_conta = detectar(
        hoje=date(2026, 11, 10), dividas=[_divida(instituicao="Loja D")], anteriores={},
        saldo_em_conta=D("100.00"), usado_cheque_especial=D(0), gastos=[],
        saldo_por_banco={"Nubank": D("100.00")},
    )
    assert next(e for e in sem_conta if e.tipo == "ATRASO_IMINENTE").contexto["conta"] is None
