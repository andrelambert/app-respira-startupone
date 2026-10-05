"""Belvo → domínio (docs/contexto-produto.md §7.7), incluindo a taxa de juros."""

from datetime import date
from decimal import Decimal as D

import pytest

from app.domain.planner import Movimento, capacidade_de_pagamento, medianas_mensais
from app.providers import fixture
from app.providers.mapping import (
    mapear_contas,
    mapear_transacoes,
    modalidade_de_cartao,
    modalidade_de_emprestimo,
    normalizar_taxa,
    parcela_price,
)

HOJE = date(2026, 10, 3)
A, B = "fixture_banco_a_br_retail", "fixture_banco_b_br_retail"


# --- normalizar_taxa ---------------------------------------------------------


@pytest.mark.parametrize(
    ("bruto", "periodo", "esperado"),
    [
        ("0.0644", "MONTHLY", D("0.0644")),  # fração mensal
        ("6.44", "MONTHLY", D("0.0644")),  # percentual mensal
        (6.44, None, D("0.0644")),  # sem periodicidade → mensal
        ("436.2", "YEARLY", D("0.150210")),  # percentual anual → mensal composto
        ("0.268242", "YEARLY", D("0.020000")),  # fração anual: 26,82% a.a. ≈ 2% a.m.
        ("26.8242", "YEARLY", D("0.020000")),  # percentual anual
    ],
)
def test_normalizar_taxa(bruto, periodo, esperado):
    assert normalizar_taxa(bruto, periodo) == esperado


@pytest.mark.parametrize("bruto", [None, "", "abc", 0, "-1", "0.0005", "25", "0.35", "0.95"])
def test_taxa_fora_do_intervalo_ou_invalida_vira_none(bruto):
    # 0,05% a.m. e 25%/35%/95% a.m. estão fora do sanity check de 0,1%–20% a.m.
    assert normalizar_taxa(bruto, "MONTHLY") is None


@pytest.mark.parametrize("bruto", ["4.362", "1.5", "7.99"])
def test_taxa_anual_ambigua_e_recusada(bruto):
    # 4.362 pode ser 436,2% a.a. (fração) ou 4,362% a.a. (percentual): não adivinhar.
    assert normalizar_taxa(bruto, "YEARLY") is None


# --- contas → dívidas --------------------------------------------------------


def _dividas(codigo):
    r = mapear_contas(fixture.contas("L", codigo, HOJE), fixture.faturas("L", codigo, HOJE), HOJE, codigo)
    return {d.modalidade: d for d in r.dividas}, r


def test_fixture_banco_a_reproduz_a_juliana():
    dividas, r = _dividas(A)
    rot = dividas["CARTAO_ROTATIVO"]
    assert (rot.saldo_devedor, rot.parcela_minima, rot.dia_vencimento) == (D("2080.00"), D("208.00"), 12)
    # credit_data.interest_rate é sempre null no Brasil → estimada, com badge
    assert (rot.taxa_juros_mes, rot.taxa_origem) == (D("0.1502"), "ESTIMADA")

    emp = dividas["CREDITO_PESSOAL"]
    assert (emp.saldo_devedor, emp.taxa_juros_mes, emp.taxa_origem) == (D("4200.00"), D("0.0644"), "INFORMADA")
    assert (emp.parcela_minima, emp.dia_vencimento, emp.parcelas_restantes) == (D("260.00"), 5, 28)

    chq = dividas["CHEQUE_ESPECIAL"]
    assert (chq.saldo_devedor, chq.taxa_juros_mes, chq.parcela_minima, chq.dia_vencimento) == (
        D("500.00"), D("0.0749"), D("50.00"), 1,
    )
    # PFM: todo produto do banco vira conta, não só a corrente
    assert [c.tipo for c in r.contas] == ["CORRENTE", "CARTAO_CREDITO", "EMPRESTIMO", "ADIANTAMENTO"]
    corrente, cartao = r.contas[0], r.contas[1]
    assert (corrente.saldo, corrente.disponivel) == (D("180.00"), D("180.00"))
    assert corrente.numero_final and len(corrente.numero_final) == 4
    assert (cartao.limite_credito, cartao.saldo, cartao.disponivel) == (D("2500.00"), D("2080.00"), D("420.00"))
    assert sorted(f.total for f in r.faturas) == [D("1950.00"), D("2080.00")]
    anterior = min(r.faturas, key=lambda f: f.vencimento)
    assert (anterior.pago, anterior.parcelada) == (D("208.00"), False)


def test_fixture_banco_b_e_parcelado():
    dividas, _ = _dividas(B)
    parc = dividas["CARTAO_PARCELADO"]
    assert (parc.saldo_devedor, parc.taxa_juros_mes, parc.parcela_minima, parc.dia_vencimento) == (
        D("1100.00"), D("0.0905"), D("110.00"), 20,
    )


def test_cheque_especial_nao_conta_duas_vezes():
    # Conta corrente negativa + ADVANCE_DEPOSIT_ACCOUNT no mesmo link → uma dívida só.
    contas = fixture.contas("L", A, HOJE)
    contas[0]["balance"] = {"current": "-500.00", "available": "0"}
    contas[0]["overdraft"] = {"arranged": "1000.00", "used": "500.00"}
    r = mapear_contas(contas, [], HOJE, A)
    assert sum(1 for d in r.dividas if d.modalidade == "CHEQUE_ESPECIAL") == 1


def test_cheque_especial_pela_conta_corrente_quando_nao_ha_adiantamento():
    corrente = fixture.contas("L", A, HOJE)[0]
    corrente["overdraft"] = {"arranged": "1000.00", "used": "320.00"}
    r = mapear_contas([corrente], [], HOJE, A)
    (d,) = r.dividas
    assert (d.modalidade, d.saldo_devedor, d.taxa_origem, d.parcela_estimada) == (
        "CHEQUE_ESPECIAL", D("320.00"), "ESTIMADA", True,
    )
    assert r.contas[0].usado_cheque_especial == D("320.00")


def test_emprestimo_sem_monthly_payment_usa_price():
    emp = next(c for c in fixture.contas("L", A, HOJE) if c["category"] == "LOAN_ACCOUNT")
    emp["loan_data"]["monthly_payment"] = None  # o que a Belvo Brasil devolve hoje
    (d,) = mapear_contas([emp], [], HOJE, A).dividas
    assert d.parcela_estimada
    assert d.parcela_minima == parcela_price(D("4200.00"), D("0.0644"), 28)


def test_taxa_absurda_cai_para_estimada():
    emp = next(c for c in fixture.contas("L", A, HOJE) if c["category"] == "LOAN_ACCOUNT")
    emp["loan_data"]["interest_rates"] = [{"type": "MONTHLY", "value": "64.4"}]  # 64% a.m.
    (d,) = mapear_contas([emp], [], HOJE, A).dividas
    assert (d.taxa_origem, d.taxa_juros_mes) == ("ESTIMADA", D("0.0644"))


def test_investimento_e_ignorado():
    conta = fixture.contas("L", A, HOJE)[0] | {"category": "INVESTMENT_ACCOUNT", "id": "inv"}
    r = mapear_contas([conta], [], HOJE, A)
    assert (r.contas, r.dividas, r.ignoradas) == ([], [], 1)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("CREDITO_PESSOAL_COM_CONSIGNACAO", "CONSIGNADO"),
        ("CREDITO_PESSOAL_SEM_CONSIGNACAO", "CREDITO_PESSOAL"),
        ("FINANCIAMENTO_AQUISICAO_BENS_VEICULOS_AUTOMOTORES", "FIN_VEICULO"),
        ("FINANCIAMENTO_HABITACIONAL_SFH", "FIN_IMOVEL"),
    ],
)
def test_modalidade_de_emprestimo(texto, esperado):
    assert modalidade_de_emprestimo({"category": "LOAN_ACCOUNT", "subtype": texto}) == esperado


def test_cartao_pago_integralmente_e_fatura():
    fs = [
        {"due_date": "2026-09-12", "total_amount": "800", "payments": [{"amount": "800"}]},
        {"due_date": "2026-10-12", "total_amount": "900", "finance_charges": []},
    ]
    assert modalidade_de_cartao(fs) == "CARTAO_FATURA"


# --- transações --------------------------------------------------------------


def test_transacoes_convertem_sinal_e_classificam():
    ts = mapear_transacoes(
        [
            {"id": "1", "type": "INFLOW", "amount": "100", "value_date": "2026-09-01", "category": "Transfers"},
            {"id": "2", "type": "OUTFLOW", "amount": "50", "value_date": "2026-09-01", "category": "Food & Groceries"},
            {"id": "3", "type": "OUTFLOW", "amount": "260", "value_date": "2026-09-01", "category": "Credits & Loans"},
            {"id": "4", "type": "INFLOW", "amount": "5000", "value_date": "2026-09-01", "category": "Credits & Loans"},
            {"id": "5", "type": None, "amount": "1", "value_date": "2026-09-01"},  # sem direção: descartada
            {"id": "6", "type": "OUTFLOW", "amount": "1", "value_date": "2026-09-01", "status": "PENDING"},
        ]
    )
    por_id = {t.id_externo: t for t in ts}
    assert set(por_id) == {"1", "2", "3", "4"}
    assert por_id["1"].valor == D("100.00") and por_id["1"].conta_como_renda
    assert por_id["2"].valor == D("-50.00") and por_id["2"].essencial
    assert por_id["3"].pagamento_divida and not por_id["3"].essencial
    assert not por_id["4"].conta_como_renda  # empréstimo recebido não é renda


def test_capacidade_da_fixture_e_900():
    ts = mapear_transacoes(fixture.transacoes("L", A, HOJE))
    movs = [
        Movimento(t.data_mov, t.valor, t.essencial) for t in ts if t.valor < 0 or t.conta_como_renda
    ]
    entradas, essenciais, meses = medianas_mensais(movs, HOJE)
    assert (entradas, essenciais, meses) == (D("4800.00"), D("3800.00"), 6)
    assert capacidade_de_pagamento(entradas, essenciais) == D("900.00")


# --- cartão de quem paga em dia (PFM, sem dívida) -------------------------------


def _cartao_com_faturas(*faturas):
    cartao = next(c for c in fixture.contas("L", A, HOJE) if c["category"] == "CREDIT_CARD")
    bills = [
        {"id": f"b{i}", "account": {"id": cartao["id"]}, "due_date": venc, "total_amount": total,
         "minimum_amount": "50.00", "payments": [{"amount": p} for p in pagos], "finance_charges": []}
        for i, (venc, total, pagos) in enumerate(faturas)
    ]
    return mapear_contas([cartao], bills, HOJE, A)


def test_fatura_guarda_nome_e_pagamentos_por_data():
    from app.providers.mapping import PagamentoFatura, mapear_fatura

    f = mapear_fatura(
        {"id": "b", "bill_name": "Sep-2026", "due_date": "2026-09-10", "total_amount": "500",
         "minimum_amount": "50", "finance_charges": [],
         "payments": [{"payment_date": "2026-09-09", "amount": "300"},
                      {"payment_date": "2026-09-01", "amount": "200"},
                      {"payment_date": "2026-09-02", "amount": None}]},  # sem valor: ignorado
        "conta",
    )
    assert f.nome == "Sep-2026"
    assert f.pagamentos == [PagamentoFatura(date(2026, 9, 1), D("200.00")), PagamentoFatura(date(2026, 9, 9), D("300.00"))]
    assert f.pago == D("500.00")


def test_transacao_de_cartao_guarda_a_fatura():
    fechada, aberta = mapear_transacoes(
        [
            {"id": "a", "type": "OUTFLOW", "amount": "10", "value_date": "2026-09-06",
             "credit_card_data": {"card_number": "1234", "bill_name": "Sep-2026"}},
            {"id": "b", "type": "OUTFLOW", "amount": "10", "value_date": "2026-09-06",
             "credit_card_data": {"card_number": "1234", "bill_name": None}},
        ]
    )
    assert (fechada.fatura_nome, aberta.fatura_nome) == ("Sep-2026", None)


def test_fatura_paga_nao_e_divida():
    r = _cartao_com_faturas(("2026-09-10", "1500.00", ["1500.00"]))
    assert r.dividas == []
    assert [c.tipo for c in r.contas] == ["CARTAO_CREDITO"]  # o cartão continua no PFM
    assert r.faturas[0].pago == D("1500.00")


def test_fatura_aberta_sem_rotativo_tem_juros_zero_e_paga_inteira():
    r = _cartao_com_faturas(
        ("2026-09-10", "1500.00", ["1500.00"]),
        ("2026-10-10", "1800.00", []),
    )
    (d,) = r.dividas
    assert (d.modalidade, d.taxa_juros_mes, d.taxa_origem) == ("CARTAO_FATURA", D("0"), "INFORMADA")
    assert d.parcela_minima == d.saldo_devedor == D("1800.00")  # não sugere pagar só o mínimo


def test_entrada_no_cartao_nao_e_renda():
    (t,) = mapear_transacoes(
        [{"id": "x", "type": "INFLOW", "amount": "900", "value_date": "2026-09-05",
          "category": "Transfers", "account": {"id": "c1", "category": "CREDIT_CARD"},
          "merchant": {"merchant_name": "Loja X"}}]
    )
    assert not t.conta_como_renda
    assert t.estabelecimento == "Loja X"


def test_transacao_usa_transacted_at_em_horario_de_brasilia():
    from datetime import datetime, timezone

    from app.domain.pfm import horario_brasil

    noite, sem_hora = mapear_transacoes(
        [
            # 01:30 UTC do dia 6 = 22:30 do dia 5 em Brasília: a data é a de lá.
            {"id": "n", "type": "OUTFLOW", "amount": "10", "value_date": "2026-09-06",
             "transacted_at": "2026-09-06T01:30:00.000Z", "operation_type": "PIX",
             "category": "Bills & Utilities", "subcategory": "Telecommunications",
             "account": {"id": "acc-1", "category": "CREDIT_CARD"}},
            # sem transacted_at: cai no value_date, sem horário
            {"id": "s", "type": "OUTFLOW", "amount": "10", "value_date": "2026-09-06"},
        ]
    )
    assert noite.transacionado_em == datetime(2026, 9, 6, 1, 30, tzinfo=timezone.utc)
    assert noite.data_mov == date(2026, 9, 5)
    assert horario_brasil(noite.transacionado_em).isoformat() == "2026-09-05T22:30:00-03:00"
    assert (noite.tipo_operacao, noite.conta_id_externo) == ("PIX", "acc-1")
    assert (noite.categoria, noite.subcategoria) == ("Bills & Utilities", "Telecommunications")  # crus
    assert (sem_hora.transacionado_em, sem_hora.data_mov, sem_hora.tipo_operacao) == (None, date(2026, 9, 6), None)


def test_final_do_cartao_guarda_so_quatro_digitos():
    com_final, numero_longo, conta_corrente = mapear_transacoes(
        [
            {"id": "a", "type": "OUTFLOW", "amount": "10", "value_date": "2026-09-06",
             "credit_card_data": {"card_number": "1234"}},
            {"id": "b", "type": "OUTFLOW", "amount": "10", "value_date": "2026-09-06",
             "credit_card_data": {"card_number": "5555 4444 3333 2222"}},
            {"id": "c", "type": "OUTFLOW", "amount": "10", "value_date": "2026-09-06", "credit_card_data": None},
        ]
    )
    assert (com_final.final_cartao, numero_longo.final_cartao, conta_corrente.final_cartao) == ("1234", "2222", None)


# --- catálogo de instituições -------------------------------------------------------


def test_catalogo_de_instituicoes():
    from app.providers.mapping import mapear_instituicoes

    itens = mapear_instituicoes(
        [
            {"name": "ofnubank_br_retail", "display_name": "Nubank",
             "logo": "https://statics.belvo.io/x/nubank-text.svg",
             "icon_logo": "https://statics.belvo.io/x/nubank-icon.svg", "website": "ignorado"},
            {"name": "of1ssbank_br_retail", "display_name": "1ss Bank\xa0- Pessoa Física", "logo": None,
             "icon_logo": "http://inseguro.example/icon.svg"},
            {"name": "sem_display", "logo": "javascript:alert(1)"},
            {"display_name": "Sem código"},
        ]
    )
    por = {i.codigo: i for i in itens}
    assert set(por) == {"ofnubank_br_retail", "of1ssbank_br_retail", "sem_display"}
    assert por["ofnubank_br_retail"].nome == "Nubank"
    assert por["ofnubank_br_retail"].icone_url.endswith("nubank-icon.svg")
    assert por["of1ssbank_br_retail"].nome == "1ss Bank - Pessoa Física"  # \xa0 normalizado
    assert por["of1ssbank_br_retail"].icone_url is None  # http recusado
    assert por["sem_display"].nome == "sem_display" and por["sem_display"].logo_url is None
