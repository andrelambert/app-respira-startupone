"""Jornada via API: conta demo (Juliana, fixture) e conta real (Belvo)."""

import re
import time
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.main import app

H = {"X-Respira": "1"}
DEMO = {"email": "demo@teste.local", "senha": "senha-demo-de-teste"}
# CPF fictício válido (dígitos verificadores corretos), só para teste.
REAL = {
    "email": "Pessoa.Real@Exemplo.com",
    "senha": "uma-senha-forte",
    "nome_completo": "Pessoa de Teste",
    "cpf": "529.982.247-25",
}


@pytest.fixture(scope="module")
def api():
    with TestClient(app) as c:
        yield c


def _aguardar_coleta(api, limite=10.0):
    fim = time.time() + limite
    while time.time() < fim:
        cs = [c for c in api.get("/consentimentos").json() if c["status"] == "ATIVO"]
        if cs and all(c["coleta_concluida"] for c in cs):
            return cs
        time.sleep(0.05)
    raise AssertionError("coleta não concluiu")


def test_sem_sessao_nada_e_visivel(api):
    api.cookies.clear()
    assert api.get("/raiox").status_code == 401
    assert api.get("/usuarios/me").json()["detail"] == "nao_autenticado"


def test_escrita_sem_cabecalho_e_bloqueada(api):
    assert api.post("/auth/entrar", json=DEMO).status_code == 403


def test_login_errado_e_bloqueio(api):
    api.cookies.clear()
    r = api.post("/auth/entrar", json={"email": "ninguem@x.com", "senha": "x"}, headers=H)
    assert r.status_code == 401 and r.json()["detail"] == "credenciais_invalidas"
    for _ in range(5):
        api.post("/auth/entrar", json={"email": "alvo@x.com", "senha": "errada"}, headers=H)
    assert api.post("/auth/entrar", json={"email": "alvo@x.com", "senha": "errada"}, headers=H).status_code == 429


def test_config(api):
    cfg = api.get("/config").json()
    assert cfg == {"demo_disponivel": True, "belvo_configurada": False, "webhooks": False}


def test_jornada_juliana(api):
    api.cookies.clear()
    r = api.post("/auth/entrar", json=DEMO, headers=H)
    assert r.status_code == 200, r.text
    assert r.json()["demo"] is True and r.json()["apelido"] == "Juliana"
    assert "httponly" in r.headers["set-cookie"].lower()
    cs = _aguardar_coleta(api)
    assert sorted(c["instituicao"] for c in cs) == ["Banco A", "Banco B"]

    # --- F2 Raio-X: os números do §2 -----------------------------------------
    rx = api.get("/raiox").json()
    assert (rx["qtd_dividas"], rx["divida_total"]) == (5, "8260.00")
    assert rx["juros_mes_estimado"] == "733.20" and rx["compromisso_minimo_mes"] == "723.00"
    assert rx["divida_cresce"] and rx["crescimento_mensal"] == "10.20"
    assert rx["maior_fonte_juros_valor"] == "312.42"
    assert [d["modalidade"] for d in rx["dividas"]] == [
        "CARTAO_ROTATIVO", "CARTAO_PARCELADO", "CHEQUE_ESPECIAL", "CREDITO_PESSOAL", "CREDIARIO",
    ]
    assert rx["capacidade"]["valor"] == "900.00"
    assert (rx["projecao"]["metodo"], rx["projecao"]["meses"]) == ("AVALANCHE", 18)

    # --- F3: a tabela da §14.1 ---------------------------------------------------
    sim = api.get("/plano/simulacoes").json()
    por = {e["metodo"]: e for e in sim["estrategias"]}
    assert (por["AVALANCHE"]["meses"], por["AVALANCHE"]["juros_totais"], por["AVALANCHE"]["primeira_quitacao_mes"]) == (18, "7923.69", 10)
    assert (por["EQUILIBRADO"]["meses"], por["EQUILIBRADO"]["juros_totais"], por["EQUILIBRADO"]["primeira_quitacao_mes"]) == (19, "8239.99", 2)
    assert (por["SNOWBALL"]["meses"], por["SNOWBALL"]["juros_totais"], por["SNOWBALL"]["primeira_quitacao_mes"]) == (21, "10491.56", 2)
    assert sim["capacidade_minima"] == "771.00"
    assert por["EQUILIBRADO"]["so_minimo"]["meses"] == 19  # mesmo horizonte da estratégia

    # --- ativar + eventos ----------------------------------------------------------
    assert api.post("/plano", json={"metodo": "AVALANCHE", "capacidade": "723.00"}, headers=H).status_code == 422
    plano = api.post("/plano", json={"metodo": "AVALANCHE", "capacidade": "900.00"}, headers=H).json()
    assert sum(D(p["valor"]) for p in plano["este_mes"]) == D("900.00")
    tipos = {e["tipo"] for e in api.get("/eventos").json()}
    assert {"ENTRADA_ROTATIVO", "ATRASO_CONFIRMADO", "CHEQUE_ESPECIAL", "PICO_CATEGORIA"} <= tipos

    # --- F4: mês no plano mantém a data; mês difícil move, sem falha -------------
    data_original = plano["projecao_atual"]["data_quitacao"]
    ok = api.post("/demo/avancar-mes", json={"mes_dificil": False}, headers=H).json()
    assert ok["projecao_atual"]["data_quitacao"] == data_original
    ruim = api.post("/demo/avancar-mes", json={"mes_dificil": True}, headers=H).json()
    assert ruim["projecao_atual"]["data_quitacao"] > data_original
    desvio = next(e for e in api.get("/eventos").json() if e["tipo"] == "DESVIO_PLANO")
    assert desvio["contexto"]["falta"] == "240.00"

    # --- reiniciar a demo volta tudo ao começo -------------------------------------
    assert api.post("/demo/reiniciar", headers=H).status_code == 204
    assert api.get("/plano/ativo").status_code == 404
    assert api.get("/usuarios/me").json()["meses_simulados"] == 0
    assert api.get("/raiox").json()["divida_total"] == "8260.00"
    assert api.delete("/usuarios/me", headers=H).status_code == 403  # demo não se exclui


def test_conta_real_registro_isolamento_e_belvo(api):
    api.cookies.clear()
    r = api.post("/auth/registrar", json=REAL, headers=H)
    assert r.status_code == 201, r.text
    u = r.json()
    assert u["email"] == "pessoa.real@exemplo.com" and u["demo"] is False and u["apelido"] == "Pessoa"
    assert u["cpf_mascarado"] == "529.***.***-25"
    assert u["nome_completo"] == "Pessoa de Teste"
    assert api.post("/auth/registrar", json=REAL, headers=H).json()["detail"] == "email_em_uso"

    # Não enxerga nada da Juliana
    rx = api.get("/raiox").json()
    assert rx["qtd_dividas"] == 0 and rx["dividas"] == []
    assert api.get("/consentimentos").json() == []
    assert api.post("/demo/avancar-mes", json={"mes_dificil": False}, headers=H).status_code == 403

    # Conta real vai para a Belvo — sem chaves no .env, erro claro e traduzível.
    r = api.post("/consentimentos/widget-token", json={}, headers=H)
    assert (r.status_code, r.json()["detail"]) == (502, "belvo_nao_configurada")

    # Cadastro manual funciona e é só dela
    d = api.post("/dividas", json={"credor": "Tia Cida", "modalidade": "OUTRO", "saldo": "300.00", "parcela": "50.00"}, headers=H).json()
    assert d["taxa_estimada"] is True

    # Sair encerra a sessão; entrar de novo funciona
    assert api.post("/auth/sair", headers=H).status_code == 204
    assert api.get("/usuarios/me").status_code == 401
    assert api.post("/auth/entrar", json={"email": REAL["email"], "senha": REAL["senha"]}, headers=H).status_code == 200
    assert api.get("/dividas").json()[0]["id"] == d["id"]

    # Exclusão real
    assert api.delete("/usuarios/me", headers=H).status_code == 204
    assert api.post("/auth/entrar", json={"email": REAL["email"], "senha": REAL["senha"]}, headers=H).status_code == 401


def test_registro_valida_cpf_e_senha(api):
    ruim = {**REAL, "email": "outra@ex.com", "cpf": "111.111.111-11"}
    assert api.post("/auth/registrar", json=ruim, headers=H).status_code == 422
    curta = {**REAL, "email": "outra@ex.com", "senha": "1234567"}
    assert api.post("/auth/registrar", json=curta, headers=H).status_code == 422


def test_webhook_exige_autenticacao_e_e_idempotente(api):
    corpo = {"webhook_id": "w-1", "webhook_type": "ACCOUNTS", "webhook_code": "historical_update",
             "link_id": "00000000-0000-0000-0000-000000000000", "data": {}}
    assert api.post("/webhooks/belvo", json=corpo).status_code == 401
    assert api.post("/webhooks/belvo", json=corpo, headers={"Authorization": "Bearer errado"}).status_code == 401
    ok = {"Authorization": "Bearer token-de-teste"}
    assert api.post("/webhooks/belvo", json=corpo, headers=ok).status_code == 202
    assert api.post("/webhooks/belvo", json=corpo, headers=ok).status_code == 202


def test_revogacao_apaga_dados_locais(api):
    api.cookies.clear()
    api.post("/auth/entrar", json=DEMO, headers=H)
    banco_b = next(c for c in api.get("/consentimentos").json() if c["instituicao"] == "Banco B")
    assert api.delete(f"/consentimentos/{banco_b['id']}", headers=H).status_code == 204
    assert "CARTAO_PARCELADO" not in {d["modalidade"] for d in api.get("/dividas").json()}


def test_pfm_contas_faturas_e_extrato(api):
    api.cookies.clear()
    api.post("/auth/entrar", json=DEMO, headers=H)
    _aguardar_coleta(api)
    v = api.get("/pfm/visao-geral").json()
    bancos = {b["instituicao"]: b for b in v["bancos"]}
    assert set(bancos) >= {"Banco A"}
    a = bancos["Banco A"]
    # conta corrente sempre primeiro, depois cartão e crédito
    assert [c["tipo"] for c in a["contas"]] == ["CORRENTE", "CARTAO_CREDITO", "ADIANTAMENTO", "EMPRESTIMO"]
    corrente0 = a["contas"][0]
    assert (corrente0["agencia"], corrente0["numero_conta"], corrente0["tipo_externo"]) == ("0001", "104582-7", "CONTA_DEPOSITO_A_VISTA")
    cartao0 = next(c for c in a["contas"] if c["tipo"] == "CARTAO_CREDITO")
    assert cartao0["numero_conta"] is None and cartao0["agencia"] is None  # cartão: nunca o número (PCI)
    assert v["saldo_em_contas"] == "180.00"

    cartao = next(c for c in a["contas"] if c["tipo"] == "CARTAO_CREDITO")
    assert cartao["fatura_atual"]["total"] == "2080.00"
    assert cartao["fatura_atual"]["situacao"] == "EM_ABERTO"
    assert (cartao["limite_credito"], cartao["disponivel"]) == ("2500.00", "420.00")
    det = api.get(f"/contas/{cartao['id']}").json()
    assert [f["situacao"] for f in det["faturas"]] == ["EM_ABERTO", "PARCIAL"]  # mais recente primeiro
    atual, anterior = det["faturas"]
    assert re.fullmatch(r"[A-Z][a-z]{2}-\d{4}", atual["nome"])  # bill_name no formato da Belvo
    assert atual["pagamentos"] == [] and atual["minimo"] == "208.00"
    assert [p["valor"] for p in anterior["pagamentos"]] == ["208.00"] and anterior["pagamentos"][0]["data"]

    corrente = next(c for c in a["contas"] if c["tipo"] == "CORRENTE")
    url = f"/contas/{corrente['id']}/transacoes"
    p1 = api.get(url, params={"por_pagina": 20}).json()
    assert p1["total"] > 200 and p1["paginas"] == -(-p1["total"] // 20) and len(p1["itens"]) == 20
    datas = [t["data"] for t in p1["itens"]]
    assert datas == sorted(datas, reverse=True)  # mais recentes primeiro
    p2 = api.get(url, params={"por_pagina": 20, "pagina": 2}).json()
    assert {t["id"] for t in p1["itens"]}.isdisjoint({t["id"] for t in p2["itens"]})

    entradas = api.get(url, params={"direcao": "ENTRADA", "por_pagina": 100}).json()
    assert entradas["total"] > 0 and all(t["direcao"] == "ENTRADA" and not t["valor"].startswith("-") for t in entradas["itens"])
    assert entradas["total_saidas"] == "0.00"
    mercado = api.get(url, params={"busca": "supermercado", "por_pagina": 5}).json()["itens"][0]
    assert (mercado["subcategoria"], mercado["estabelecimento"]) == ("Groceries", "Mercado Bom Preço")
    assert mercado["tipo_operacao"] == "CARTAO" and mercado["transacionado_em"].endswith("-03:00")
    # PIX das 01:30 UTC aparece às 22:30 do dia anterior, em horário de Brasília
    pix = api.get(url, params={"busca": "companheiro", "por_pagina": 100}).json()["itens"]
    noite = [t for t in pix if t["transacionado_em"][11:16] == "22:30"]
    assert noite and all(t["transacionado_em"][:10] == t["data"] for t in noite)
    trinta = api.get(url, params={"dias": 30, "por_pagina": 100}).json()
    assert 0 < trinta["total"] < p1["total"]
    from datetime import date, timedelta
    assert min(t["data"] for t in trinta["itens"]) >= (date.today() - timedelta(days=30)).isoformat()
    salario = api.get(url, params={"busca": "salario"}).json()
    assert salario["total"] > 0 and all("SALARIO" in t["descricao"] for t in salario["itens"])
    assert api.get(url, params={"busca": "%"}).json()["total"] == 0  # curinga não vaza

    # outra conta não enxerga
    api.cookies.clear()
    api.post("/auth/registrar", json={**REAL, "email": "outra.pessoa@exemplo.com", "cpf": "111.444.777-35"}, headers=H)
    assert api.get(f"/contas/{corrente['id']}").status_code == 404
    assert api.get(url).status_code == 404
    assert api.get("/pfm/visao-geral").json()["bancos"] == []
