"""N1 (Fase 7): todas as transações, com filtros — F-1, F-2."""

from datetime import date, timedelta
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_api import H


@pytest.fixture(scope="module")
def api():
    with TestClient(app) as c:
        yield c


def _todas(api, **params):
    r = api.get("/transacoes", params={"por_pagina": 100, **params})
    assert r.status_code == 200, r.text
    return r.json()


def _tudo(api, **params):
    """Percorre as páginas e devolve todos os itens do filtro."""
    primeira = _todas(api, **params)
    itens = list(primeira["itens"])
    for p in range(2, primeira["paginas"] + 1):
        itens += _todas(api, pagina=p, **params)["itens"]
    assert len(itens) == primeira["total"]
    return primeira, itens


def test_extrato_unificado_junta_contas_e_cartoes(demo_limpa):
    api = demo_limpa
    resumo, itens = _tudo(api)
    bancos = {t["banco"] for t in itens if t["banco"]}
    assert bancos == {"Nubank", "Itaú", "Caixa"}
    assert any(t["final_cartao"] for t in itens) and any(not t["final_cartao"] for t in itens)
    datas = [t["data"] for t in itens]
    assert datas == sorted(datas, reverse=True)
    entradas = sum(D(t["valor"]) for t in itens if D(t["valor"]) > 0)
    saidas = sum(-D(t["valor"]) for t in itens if D(t["valor"]) < 0)
    assert (D(resumo["total_entradas"]), D(resumo["total_saidas"])) == (entradas, saidas)
    assert D(resumo["resultado"]) == entradas - saidas


def test_cada_filtro_restringe_o_que_promete(demo_limpa):
    api = demo_limpa
    _, todos = _tudo(api)
    conta = next(t["conta_id"] for t in todos if t["conta_id"])
    _, por_conta = _tudo(api, contas=str(conta))
    assert por_conta and {t["conta_id"] for t in por_conta} == {conta}

    _, saidas = _tudo(api, direcao="SAIDA")
    assert saidas and all(D(t["valor"]) < 0 for t in saidas)

    cats = api.get("/transacoes/categorias").json()
    assert "Food & Groceries" in cats and cats == sorted(cats)
    _, mercado = _tudo(api, categorias="Food & Groceries,Bills & Utilities")
    assert mercado and {t["categoria"] for t in mercado} <= {"Food & Groceries", "Bills & Utilities"}

    termo = next(t["descricao"] for t in todos if len(t["descricao"]) > 5)[:5]
    _, achados = _tudo(api, busca=termo.lower())
    assert achados and all(
        termo.lower() in (t["descricao"] + (t["estabelecimento"] or "")).lower() for t in achados
    )

    _, faixa = _tudo(api, valor_min="100", valor_max="500")
    assert faixa and all(D(100) <= abs(D(t["valor"])) <= D(500) for t in faixa)

    hoje = date.fromisoformat(api.get("/usuarios/me").json()["hoje"])
    desde = (hoje - timedelta(days=30)).isoformat()
    _, recentes = _tudo(api, desde=desde, ate=hoje.isoformat())
    assert recentes and all(desde <= t["data"] <= hoje.isoformat() for t in recentes)


def test_so_pagamentos_de_divida_e_ordem_por_valor(demo_limpa):
    api = demo_limpa
    assert api.post("/plano", json={"metodo": "AVALANCHE", "capacidade": "1755.00"}, headers=H).status_code == 201
    assert api.post("/demo/avancar-mes", json={"mes_dificil": False}, headers=H).status_code == 200
    _, dividas = _tudo(api, so_divida="true")
    assert dividas and all(t["pagamento_divida"] for t in dividas)

    _, por_valor = _tudo(api, ordem="maior_valor", direcao="SAIDA")
    valores = [abs(D(t["valor"])) for t in por_valor]
    assert valores == sorted(valores, reverse=True)


@pytest.mark.parametrize(
    "params",
    [
        {"desde": "2026-10-10", "ate": "2026-10-01"},
        {"valor_min": "500", "valor_max": "100"},
        {"valor_min": "-1"},
        {"contas": ",".join(str(i) for i in range(21))},
        {"contas": "1,abc"},
        {"categorias": ",".join(f"c{i}" for i in range(21))},
        {"busca": "x" * 61},
        {"ordem": "aleatoria"},
        {"por_pagina": "1000"},
    ],
)
def test_parametros_invalidos_sao_recusados(demo_limpa, params):
    assert demo_limpa.get("/transacoes", params=params).status_code == 422


def test_isolamento_entre_usuarios(api):
    """Outra conta não vê as transações da Juliana, nem pedindo as contas dela."""
    from tests.test_api import DEMO

    api.cookies.clear()
    api.post("/auth/entrar", json=DEMO, headers=H)
    contas_da_juliana = {t["conta_id"] for t in _todas(api)["itens"] if t["conta_id"]}
    api.cookies.clear()
    r = api.post(
        "/auth/registrar",
        json={"email": "isolamento.n1@exemplo.com", "senha": "uma-senha-forte", "nome_completo": "Outra Pessoa", "cpf": "390.533.447-05"},  # CPF fictício válido, só de teste
        headers=H,
    )
    assert r.status_code == 201, r.text
    assert _todas(api)["total"] == 0
    assert _todas(api, contas=",".join(map(str, contas_da_juliana)))["total"] == 0
    assert api.get("/transacoes/categorias").json() == []
    api.cookies.clear()
    assert api.get("/transacoes").status_code == 401


def test_filtro_por_subcategoria_e_parcelas(demo_limpa):
    """Fase 7: o toque numa barra de gastos filtra pela subcategoria V2
    ("Food & Groceries::Delivery"), sem trazer o mercado da mesma categoria; e a
    compra parcelada da demo vem com uma parcela por mês."""
    api = demo_limpa
    _, delivery = _tudo(api, categorias="Food & Groceries::Delivery")
    assert delivery and {(t["categoria"], t["subcategoria"]) for t in delivery} == {("Food & Groceries", "Delivery")}
    _, alimentacao = _tudo(api, categorias="Food & Groceries")
    assert len(alimentacao) > len(delivery)  # a categoria inteira inclui o mercado

    _, geladeira = _tudo(api, busca="eletrodom")
    assert [t["parcela_numero"] for t in sorted(geladeira, key=lambda t: t["data"])] == list(range(1, 11))
    assert {t["parcelas_total"] for t in geladeira} == {10}
    meses = [t["data"][:7] for t in geladeira]
    assert len(set(meses)) == 10  # uma parcela em cada mês, não todas no mês da compra
    assert all(t["data_compra"] in (None, min(meses) + "-09") for t in geladeira)


def test_filtro_por_tipo_de_conta_e_investimentos(demo_limpa):
    """Tudo · Conta corrente · Cartão de crédito · Poupança · Investimentos (Todas as transações)."""
    api = demo_limpa
    contas = {c["id"]: c["tipo"] for b in api.get("/pfm/visao-geral").json()["bancos"] for c in b["contas"]}
    tudo = api.get("/transacoes", params={"por_pagina": 5}).json()["total"]
    somas = 0
    for filtro, tipos in (("CORRENTE", {"CORRENTE", "PAGAMENTO"}), ("CARTAO", {"CARTAO_CREDITO"}), ("POUPANCA", {"POUPANCA"})):
        r = api.get("/transacoes", params={"tipo_conta": filtro, "por_pagina": 100}).json()
        assert r["total"] > 0 and {contas[t["conta_id"]] for t in r["itens"]} <= tipos
        somas += r["total"]
    assert somas <= tudo
    inv = api.get("/transacoes", params={"tipo_conta": "INVESTIMENTOS", "por_pagina": 100}).json()
    assert inv["total"] > 0 and all(t["categoria"] == "Investments & Savings" for t in inv["itens"])
    assert api.get("/transacoes", params={"tipo_conta": "CORRETORA"}).status_code == 422
