"""Belvo → domínio (docs/contexto-produto.md §7.7), incluindo a taxa de juros."""

from datetime import date
from decimal import Decimal as D

import pytest

from app.domain.planner import Movimento, capacidade_de_pagamento, medianas_mensais
from app.providers import fixture
from app.providers.mapping import (
    mapear_contas,
    mapear_transacoes,
    numero_parcela,
    modalidade_de_cartao,
    modalidade_de_emprestimo,
    normalizar_taxa,
    parcela_price,
)

HOJE = date(2026, 10, 3)
NU, IT, CX = fixture.NUBANK, fixture.ITAU, fixture.CAIXA


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
        # CET (total_effective_cost): fração anual mesmo acima de 1 — dados reais, out/2026
        ("0.2720", "CET", D("0.020252")),  # financiamento de veículo, 27,2% a.a.
        ("2.20", "CET", D("0.101782")),  # crédito pessoal caro, 220% a.a.
    ],
)
def test_normalizar_taxa(bruto, periodo, esperado):
    assert normalizar_taxa(bruto, periodo) == esperado


@pytest.mark.parametrize("bruto", [None, "", "abc", 0, "-1", "0.0005", "25", "0.35", "0.95"])
def test_taxa_fora_do_intervalo_ou_invalida_vira_none(bruto):
    # 0,05% a.m. e 25%/35%/95% a.m. estão fora do sanity check de 0,1%–20% a.m.
    assert normalizar_taxa(bruto, "MONTHLY") is None


def test_cet_absurdo_e_recusado():
    assert normalizar_taxa("9", "CET") is None  # 900% a.a. não é crédito de varejo


@pytest.mark.parametrize("bruto", ["4.362", "1.5", "7.99"])
def test_taxa_anual_ambigua_e_recusada(bruto):
    # 4.362 pode ser 436,2% a.a. (fração) ou 4,362% a.a. (percentual): não adivinhar.
    assert normalizar_taxa(bruto, "YEARLY") is None


# --- contas → dívidas --------------------------------------------------------


def _dividas(codigo):
    r = mapear_contas(fixture.contas("L", codigo, HOJE), fixture.faturas("L", codigo, HOJE), HOJE, codigo)
    return {d.descricao: d for d in r.dividas}, r


def _emprestimo_nubank():
    return next(c for c in fixture.contas("L", NU, HOJE) if c["category"] == "LOAN_ACCOUNT")


def test_fixture_nubank_rotativo_e_emprestimo():
    dividas, r = _dividas(NU)
    rot = dividas["Rotativo do cartão Nubank"]
    assert (rot.modalidade, rot.saldo_devedor, rot.parcela_minima, rot.dia_vencimento) == (
        "CARTAO_ROTATIVO", D("2080.00"), D("208.00"), 12,
    )
    # credit_data.interest_rate é sempre null no Brasil → estimada, com badge
    assert (rot.taxa_juros_mes, rot.taxa_origem) == (D("0.1502"), "ESTIMADA")

    emp = dividas["Empréstimo pessoal Nubank"]
    assert (emp.saldo_devedor, emp.taxa_juros_mes, emp.taxa_origem) == (D("4200.00"), D("0.0644"), "INFORMADA")
    # monthly_payment é null no Brasil: parcela pela tabela Price, marcada como estimada
    assert (emp.parcela_minima, emp.parcela_estimada) == (parcela_price(D("4200.00"), D("0.0644"), 28), True)
    assert (emp.dia_vencimento, emp.parcelas_restantes, emp.parcelas_pagas, emp.parcelas_total) == (5, 28, 8, 36)
    assert (emp.valor_contratado, emp.conta_id_externo) == (D("4630.00"), _emprestimo_nubank()["id"])

    # PFM: todo produto do banco vira conta, não só a corrente
    assert [c.tipo for c in r.contas] == ["CORRENTE", "CARTAO_CREDITO", "EMPRESTIMO"]
    corrente, cartao = r.contas[0], r.contas[1]
    assert (corrente.saldo, corrente.disponivel, corrente.numero_conta) == (D("63.40"), D("63.40"), "48213907-3")
    assert (cartao.limite_credito, cartao.saldo, cartao.disponivel) == (D("2500.00"), D("2080.00"), D("420.00"))
    assert sorted(f.total for f in r.faturas) == [D("1720.00"), D("1840.00"), D("1950.00"), D("2080.00")]
    anterior = max((f for f in r.faturas if f.total != D("2080.00")), key=lambda f: f.vencimento)
    assert (anterior.pago, anterior.parcelada) == (D("208.00"), False)


def test_fixture_itau_cheque_parcelado_e_moto():
    dividas, r = _dividas(IT)
    # Cheque especial como LOAN_ACCOUNT (subtype CHEQUE_ESPECIAL) + conta negativa: uma dívida só.
    assert sum(1 for d in r.dividas if d.modalidade == "CHEQUE_ESPECIAL") == 1
    chq = dividas["Cheque especial Itaú"]
    # taxa em interest_rate_data.pre_fixed_rate (value null)
    assert (chq.saldo_devedor, chq.taxa_juros_mes, chq.taxa_origem, chq.parcela_minima) == (
        D("500.00"), D("0.0749"), "INFORMADA", D("50.00"),
    )
    parc = dividas["Fatura parcelada Itaú"]
    assert (parc.modalidade, parc.saldo_devedor, parc.taxa_juros_mes, parc.parcela_minima, parc.dia_vencimento) == (
        "CARTAO_PARCELADO", D("1100.00"), D("0.0905"), D("110.00"), 20,
    )
    moto = dividas["Financiamento de veículo Itaú"]
    # sem interest_rates[]: a taxa vem do CET (fração anual)
    assert (moto.modalidade, moto.taxa_juros_mes, moto.taxa_origem) == (
        "FIN_VEICULO", normalizar_taxa("0.2720", "CET"), "INFORMADA",
    )
    assert (moto.saldo_devedor, moto.parcela_minima, moto.parcelas_pagas, moto.parcelas_total, moto.dia_vencimento) == (
        D("7167.54"), D("321.14"), 18, 48, 10,
    )
    corrente = r.contas[0]
    assert (corrente.tipo, corrente.saldo, corrente.usado_cheque_especial) == ("CORRENTE", D("0.00"), D("500.00"))


def test_fixture_caixa_consignado_e_atraso():
    dividas, r = _dividas(CX)
    cons = dividas["Consignado Caixa"]
    # taxa anual em interest_rate_data (type YEARLY) → mensal equivalente
    assert (cons.modalidade, cons.taxa_juros_mes, cons.parcela_minima, cons.em_atraso_dias) == (
        "CONSIGNADO", normalizar_taxa("0.245", "YEARLY"), D("189.41"), 0,
    )
    cred = dividas["Empréstimo pessoal Caixa"]
    assert cred.taxa_juros_mes == normalizar_taxa("2.20", "CET")
    assert cred.em_atraso_dias > 0  # number_of_installments_past_due = 1
    assert [c.tipo for c in r.contas] == ["POUPANCA", "EMPRESTIMO", "EMPRESTIMO"]


def test_cheque_especial_como_adiantamento_nao_conta_duas_vezes():
    # Mesma situação do Itaú, com o cheque especial vindo como ADVANCE_DEPOSIT_ACCOUNT.
    contas = fixture.contas("L", IT, HOJE)
    contas[1] = contas[1] | {"category": "ADVANCE_DEPOSIT_ACCOUNT", "subtype": "ADIANTAMENTO_DEPOSITANTES"}
    r = mapear_contas(contas, [], HOJE, IT)
    assert sum(1 for d in r.dividas if d.modalidade == "CHEQUE_ESPECIAL") == 1


def test_cheque_especial_pela_conta_corrente_quando_nao_vem_como_conta_propria():
    corrente = fixture.contas("L", IT, HOJE)[0]
    corrente["overdraft"] = {"arranged": "1000.00", "used": "320.00"}
    r = mapear_contas([corrente], [], HOJE, IT)
    (d,) = r.dividas
    assert (d.modalidade, d.saldo_devedor, d.taxa_origem, d.parcela_estimada) == (
        "CHEQUE_ESPECIAL", D("320.00"), "ESTIMADA", True,
    )
    assert r.contas[0].usado_cheque_especial == D("320.00")


def test_taxa_absurda_cai_no_cet_e_sem_cet_na_estimada():
    emp = _emprestimo_nubank()
    emp["loan_data"]["interest_rates"] = [{"type": "MONTHLY", "value": "64.4"}]  # 64% a.m.
    (d,) = mapear_contas([emp], [], HOJE, NU).dividas
    assert (d.taxa_origem, d.taxa_juros_mes) == ("INFORMADA", normalizar_taxa("1.1950", "CET"))
    emp["loan_data"]["total_effective_cost"] = None
    (d,) = mapear_contas([emp], [], HOJE, NU).dividas
    assert (d.taxa_origem, d.taxa_juros_mes) == ("ESTIMADA", D("0.0644"))


def test_contrato_quitado_nao_e_divida():
    emp = _emprestimo_nubank()
    emp["loan_data"]["outstanding_balance"] = "0"
    r = mapear_contas([emp], [], HOJE, NU)
    assert (r.dividas, r.contas) == ([], [])


def test_investimento_e_ignorado():
    conta = fixture.contas("L", NU, HOJE)[0] | {"category": "INVESTMENT_ACCOUNT", "id": "inv"}
    r = mapear_contas([conta], [], HOJE, NU)
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


def _sicredi(id_, tipo, valor, descricao, *, operacao="OUTROS", categoria=None, contraparte=None, conta="CHECKING_ACCOUNT"):
    """Transação no formato em que a Sicredi manda a aplicação automática (Fase 7)."""
    return {
        "id": id_, "type": tipo, "amount": valor, "value_date": "2026-08-29", "description": descricao,
        "operation_type": operacao, "category": categoria, "counterparty": contraparte,
        "account": {"id": "cc", "category": conta},
    }


def test_aplicacao_automatica_e_reserva_nem_renda_nem_gasto():
    """Casos do estudo da conta Sicredi real (aplicação automática, §6 do documento da equipe)."""
    ts = mapear_transacoes([
        _sicredi("1", "INFLOW", "446.26", "RESG.APLIC.FIN.AVISO PREV", operacao="RESGATE_APLIC_FINANCEIRA",
                 categoria="Investments & Savings"),
        _sicredi("2", "OUTFLOW", "2691.83", "APLICACAO FINANCEIRA", categoria="Investments & Savings"),
        _sicredi("3", "OUTFLOW", "100.00", "APLICACAO POUPANCA"),  # sem categoria: pela descrição
        # Salário categorizado como viagem (o empregador é uma agência): continua renda.
        _sicredi("4", "INFLOW", "3005.57", "RECEBIMENTO PIX 00000000000100 EMPRESA", categoria="Transport & Travel",
                 contraparte={"name": "EMPRESA"}),
        _sicredi("5", "INFLOW", "23.90", "DEVOLUCAO PIX 00000000000100 UBER"),
        # Loja categorizada como aposta: gasto comum (a categoria só afeta o gráfico de gastos).
        _sicredi("6", "OUTFLOW", "80.00", "COMPRA LOJA", categoria="Online Platforms & Leisure"),
        # "APLICACAO" com contraparte é outra coisa (ex.: pagamento a terceiro com esse nome).
        _sicredi("7", "OUTFLOW", "50.00", "APLICACAO DE PELICULA", contraparte={"name": "LOJA"}),
        # No cartão não existe aplicação automática.
        _sicredi("8", "OUTFLOW", "30.00", "APLIC. CURSO", conta="CREDIT_CARD"),
    ])
    t = {x.id_externo: x for x in ts}
    assert t["1"].reserva and not t["1"].conta_como_renda
    assert t["2"].reserva and not t["2"].essencial
    assert t["3"].reserva
    assert t["4"].conta_como_renda and not t["4"].reserva
    assert not t["5"].conta_como_renda and not t["5"].reserva  # estorno não é renda
    assert not t["6"].reserva and t["6"].valor == D("-80.00")
    assert not t["7"].reserva
    assert not t["8"].reserva


def test_identidade_da_conta_com_aplicacao_automatica():
    """Conta sweep: o que entra e não é reserva, menos o que sai e não é reserva,
    é o que foi para a reserva (o saldo da conta corrente começa e termina em zero)."""
    ts = mapear_transacoes([
        _sicredi("a", "INFLOW", "3005.57", "RECEBIMENTO PIX EMPRESA", contraparte={"name": "EMPRESA"}),
        _sicredi("b", "OUTFLOW", "312.74", "COMPRA DEBITO", categoria="Food & Groceries"),
        _sicredi("c", "OUTFLOW", "2692.83", "APLICACAO FINANCEIRA", categoria="Investments & Savings"),
        _sicredi("d", "OUTFLOW", "750.00", "PIX ALUGUEL", contraparte={"name": "PROPRIETARIO"}),
        _sicredi("e", "INFLOW", "750.00", "RESG.APLIC.FIN.AVISO PREV", operacao="RESGATE_APLIC_FINANCEIRA"),
    ])
    fora = sum((x.valor for x in ts if not x.reserva), D(0))
    reserva = -sum((x.valor for x in ts if x.reserva), D(0))
    assert fora == reserva == D("1942.83")


def test_capacidade_da_fixture_e_1755():
    # Os três bancos juntos: renda na conta do Itaú e do Nubank, gastos essenciais
    # espalhados pela conta e pelos dois cartões.
    ts = [t for b in fixture.BANCOS_DA_JULIANA for t in mapear_transacoes(fixture.transacoes("L", b, HOJE))]
    movs = [
        Movimento(t.data_mov, t.valor, t.essencial) for t in ts if t.valor < 0 or t.conta_como_renda
    ]
    entradas, essenciais, meses = medianas_mensais(movs, HOJE)
    assert (entradas, essenciais, meses) == (D("5300.00"), D("3350.00"), 6)
    assert capacidade_de_pagamento(entradas, essenciais) == D("1755.00")
    # Compras de cartão trazem o final do cartão; estabelecimento só no cartão.
    cartao = [t for t in ts if t.final_cartao]
    assert cartao and {t.final_cartao for t in cartao} == {"5163", "8820"}
    assert all(t.estabelecimento is None for t in ts if not t.final_cartao)


# --- cartão de quem paga em dia (PFM, sem dívida) -------------------------------


def _cartao_com_faturas(*faturas):
    cartao = next(c for c in fixture.contas("L", NU, HOJE) if c["category"] == "CREDIT_CARD")
    bills = [
        {"id": f"b{i}", "account": {"id": cartao["id"]}, "due_date": venc, "total_amount": total,
         "minimum_amount": "50.00", "payments": [{"amount": p} for p in pagos], "finance_charges": []}
        for i, (venc, total, pagos) in enumerate(faturas)
    ]
    return mapear_contas([cartao], bills, HOJE, NU)


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
    assert por["of1ssbank_br_retail"].nome == "1ss Bank"  # \xa0 normalizado e sufixo PF cortado (A12)
    assert por["of1ssbank_br_retail"].icone_url is None  # http recusado
    assert por["sem_display"].nome == "sem_display" and por["sem_display"].logo_url is None


def test_fixture_tem_ids_por_link():
    # Dois usuários demo (dois links) não podem compartilhar ids da Belvo: o
    # upsert por id externo acharia a conta do outro.
    ids = lambda link: {c["id"] for b in fixture.BANCOS_DA_JULIANA for c in fixture.contas(link, b, HOJE)}  # noqa: E731
    assert ids("link-1").isdisjoint(ids("link-2"))


def test_nome_curto_do_banco_sem_pessoa_fisica():
    """A12 (Fase 7): o app é só para pessoa física — o sufixo não informa nada."""
    from app.providers.mapping import mapear_instituicoes, nome_curto

    assert nome_curto("Itaú - Pessoa Física") == "Itaú"
    assert nome_curto("Bradesco Pessoa Fisica") == "Bradesco"
    assert nome_curto("Banco RCI - Brasil - Pessoa Física") == "Banco RCI - Brasil"
    assert nome_curto("Itaú - Pessoa Jurídica") == "Itaú - Pessoa Jurídica"  # PJ continua distinto
    assert nome_curto("Nubank") == "Nubank"
    [i] = mapear_instituicoes([{"name": "itau_br_retail", "display_name": "Itaú - Pessoa Física"}])
    assert i.nome == "Itaú"


# --- Fase 7: parcelas no cartão e taxonomia V2 ----------------------------------------


def _txn_cartao(**kw):
    base = {
        "id": "t-evino-3", "type": "OUTFLOW", "amount": "30.00", "status": "PROCESSED",
        "description": "Evino", "category": "Food & Groceries", "subcategory": "Alcohol & Tobacco",
        "value_date": "2026-10-29", "accounting_date": "2026-12-29", "transacted_at": "2026-10-29T15:00:00Z",
        "account": {"id": "cartao-1", "category": "CREDIT_CARD"},
        "credit_card_data": {"card_number": "1234", "installment_identifier": 3, "number_of_installments": 12},
    }
    base.update(kw)
    return base


def test_parcela_do_cartao_entra_no_mes_em_que_cai():
    """Compra em 12x: todas com a mesma data de compra; cada parcela no seu mês."""
    from app.providers.mapping import mapear_transacoes

    [t] = mapear_transacoes([_txn_cartao()])
    assert t.data_mov == date(2026, 12, 29)  # accounting_date
    assert t.data_compra == date(2026, 10, 29)  # a compra
    assert (t.parcela_numero, t.parcelas_total) == (3, 12)


def test_compra_a_vista_no_cartao_e_conta_corrente_nao_mudam():
    from app.providers.mapping import mapear_transacoes

    [avista] = mapear_transacoes([_txn_cartao(
        accounting_date="2026-10-29", credit_card_data={"card_number": "1234", "number_of_installments": 1},
    )])
    assert (avista.data_mov, avista.data_compra, avista.parcela_numero, avista.parcelas_total) == (
        date(2026, 10, 29), None, None, None,
    )
    [corrente] = mapear_transacoes([_txn_cartao(
        id="t-cc", credit_card_data=None, accounting_date=None, account={"id": "cc", "category": "CHECKING_ACCOUNT"},
    )])
    assert corrente.data_mov == date(2026, 10, 29) and corrente.data_compra is None


def test_essencial_pela_subcategoria_v2():
    from app.providers.mapping import essencial

    assert essencial("Food & Groceries", "Groceries")
    assert not essencial("Food & Groceries", "Restaurants")
    assert not essencial("Food & Groceries", "Alcohol & Tobacco")
    assert not essencial("Food & Groceries", "Delivery")
    assert essencial("Bills & Utilities", "Rent")
    assert essencial("Home & Life", "Pharmacies") and not essencial("Home & Life", "Gyms & Fitness")
    assert essencial("Transport & Travel", "Public Transit") and not essencial("Transport & Travel", "Flights")
    assert not essencial("Online Platforms & Leisure", "Movie & Video")
    assert essencial("Food & Groceries", None)  # sem subcategoria: vale a categoria
    assert not essencial(None, None)



def _parcela(id_, descricao, ident, *, lancamento="2026-10-15", compra="2026-10-03T15:00:00Z", total=12):
    return {
        "id": id_, "type": "OUTFLOW", "amount": "49.90", "description": descricao, "status": "BOOKED",
        "transacted_at": compra, "value_date": compra[:10], "accounting_date": lancamento,
        "category": "Food & Groceries", "account": {"id": "cartao", "category": "CREDIT_CARD"},
        "credit_card_data": {"installment_identifier": ident, "number_of_installments": total, "card_number": "1234"},
    }


def test_parcelas_com_a_mesma_data_vao_cada_uma_para_o_seu_mes():
    """Teste com conta Nubank real: as 12 parcelas da Evino chegaram com a mesma
    data e entravam todas em outubro. Cada uma vai para o seu mês."""
    ts = mapear_transacoes([_parcela(f"ev{i:02d}", f"EVINO {i}/12", f"PARCELA_{900 + i}") for i in range(12, 0, -1)])
    por_parcela = {t.parcela_numero: t for t in ts}
    assert sorted(por_parcela) == list(range(1, 13))  # o número veio da descrição ("3/12")
    assert por_parcela[1].data_mov == date(2026, 10, 15) and por_parcela[3].data_mov == date(2026, 12, 15)
    assert por_parcela[12].data_mov == date(2027, 9, 15)
    assert {t.data_compra for t in ts} == {date(2026, 10, 3)}
    assert len({(t.data_mov.year, t.data_mov.month) for t in ts}) == 12  # uma por mês


def test_parcelas_sem_numero_algum_usam_a_ordem_e_somam_igual():
    ts = mapear_transacoes([_parcela(f"x{i}", "LOJA", None, total=3) for i in range(3)])
    assert sorted((t.parcela_numero, t.data_mov.month) for t in ts) == [(1, 10), (2, 11), (3, 12)]


def test_parcelas_com_datas_proprias_nao_mudam():
    ts = mapear_transacoes([
        _parcela("a", "LOJA", "1", lancamento="2026-10-15", total=2),
        _parcela("b", "LOJA", "2", lancamento="2026-11-15", total=2),
    ])
    assert sorted(t.data_mov for t in ts) == [date(2026, 10, 15), date(2026, 11, 15)]


@pytest.mark.parametrize(
    ("ident", "descricao", "total", "esperado"),
    [
        ("3", "LOJA", 12, 3),
        (3, "LOJA", 12, 3),
        ("03/12", "LOJA", 12, 3),
        ("PARCELA_3", "LOJA", 12, 3),
        ("PARCELA_896", "LOJA", 12, None),  # id da instituição, não o número da parcela
        (None, "EVINO 3/12", 12, 3),
        (None, "EVINO 3 DE 12", 12, 3),
        (None, "EVINO 3/10", 12, None),  # o total do texto não bate
        ("13", "LOJA", 12, None),
    ],
)
def test_numero_da_parcela(ident, descricao, total, esperado):
    assert numero_parcela(ident, descricao, total) == esperado
