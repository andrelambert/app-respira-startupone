"""FixtureProvider — a Juliana (docs/contexto-produto.md §2) no formato da Belvo.

Não é "mock em vez de dado real": é o que roda nos testes e na conta demo
(provedor por usuário, ``services/contexto.py``), para demonstrar sem expor dado
bancário real e para o mapeamento ser exercitado de verdade.

Três bancos conectados — Nubank, Itaú e Caixa — com os códigos reais do catálogo
da Belvo (com o catálogo sincronizado, aparecem os logos de verdade). Os
objetos seguem o schema ``AccountOpenFinanceBrazil`` / ``TransactionOpenFinanceBrazil``
/ ``Bill`` e o que se vê em dados reais (amostra anonimizada de 99 contratos de
empréstimo e financiamento, out/2026):

* ``loan_data.interest_rate``, ``monthly_payment`` e ``payment_day`` vêm ``null``;
  a parcela é derivada pela tabela Price (badge "parcela estimada" na tela).
* A taxa vem de ``interest_rates[]`` (``value`` ou ``interest_rate_data.pre_fixed_rate``)
  ou só do CET (``total_effective_cost``, fração anual) — a fixture usa os três
  caminhos, um em cada contrato.
* O cheque especial vem como ``LOAN_ACCOUNT`` com ``subtype: CHEQUE_ESPECIAL``,
  ao mesmo tempo que a conta corrente fica negativa — o mapeamento não pode
  contar duas vezes.

As cinco dívidas da Fase 5 (rotativo, parcelado, empréstimo pessoal, cheque
especial e o carnê, este cadastrado à mão em ``services/demo.py``) continuam com
os mesmos saldos e taxas, agora distribuídas entre os três bancos; somam-se um
financiamento de moto, um consignado e um crédito pessoal com parcela atrasada.
Os números da §14.1 seguem validados em ``test_planner.py``, com as dívidas do
domínio — não com esta fixture.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.domain.planner import adicionar_meses
from app.models import Recurso
from app.providers.base import (
    AggregationProvider,
    ConsentimentoInfo,
    ErroProvedor,
    IdentificacaoUsuario,
    Json,
    LinkInfo,
)

NS = uuid.UUID("6f1c1d1e-5a1b-4c1e-9a52-7265737069ff")

NUBANK = "ofnubank_br_retail"
ITAU = "ofitau_br_retail"
CAIXA = "ofcaixa_br_retail"
INSTITUICOES = {
    NUBANK: "Nubank",
    ITAU: "Itaú",
    CAIXA: "Caixa",
    # Sempre "fora do ar": exercita a tela de saída com erro traduzido.
    "fixture_banco_fora_br_retail": "Banco Fora do Ar",
}
INSTITUICAO_FORA_DO_AR = "fixture_banco_fora_br_retail"
BANCOS_DA_JULIANA = (NUBANK, ITAU, CAIXA)

# Totais mensais dos 6 meses que entram na capacidade (do mais antigo ao mais
# recente). Medianas: entradas R$ 5.300 (salário R$ 3.100 + PIX do companheiro),
# essenciais R$ 3.350 → capacidade (5.300 − 3.350) × 0,90 = R$ 1.755. Os gastos
# essenciais se espalham pela conta do Itaú e pelos dois cartões.
# Calibrado para o último mês do plano ficar quase cheio: assim um "mês difícil"
# da demonstração move a data de quitação, em vez de sumir na folga.
ENTRADAS_6M = ["5300.00", "5150.00", "5300.00", "5600.00", "5300.00", "5220.00"]
ESSENCIAIS_6M = ["3350.00", "3300.00", "3440.00", "3350.00", "3370.00", "3350.00"]
SALARIO = Decimal("3100.00")
ESSENCIAIS_FIXOS = Decimal("2050.00")  # aluguel, contas, transporte, farmácia (abaixo)
DELIVERY_NORMAL = Decimal("210.00")
DELIVERY_PICO = Decimal("430.00")  # último mês completo: dispara PICO_CATEGORIA

# Parcelas que a Juliana paga todo mês (as mesmas que o mapeamento deriva).
PARCELA_EMPRESTIMO_NUBANK = Decimal("327.54")
PARCELA_MOTO = Decimal("321.14")
PARCELA_CREDITO_CAIXA = Decimal("148.05")
PARCELA_CARNE = Decimal("95.00")

FINAL_CARTAO = {NUBANK: "5163", ITAU: "8820"}
VENCIMENTO_CARTAO = {NUBANK: 12, ITAU: 20}
DIAS_ENTRE_FECHAMENTO_E_VENCIMENTO = 7

# Estabelecimentos fictícios (só cartão traz merchant) e subcategorias.
MERCHANTS = {
    "SUPERMERCADO": {"merchant_name": "Mercado Bom Preço", "website": None, "logo": None},
    "DELIVERY APP": {"merchant_name": "Entrega Já", "website": None, "logo": None},
    "FARMACIA": {"merchant_name": "Farmácia Saúde+", "website": None, "logo": None},
    "POSTO DE COMBUSTIVEL": {"merchant_name": "Auto Posto Avenida", "website": None, "logo": None},
    "APP DE TRANSPORTE": {"merchant_name": "Vai de Carro", "website": None, "logo": None},
    "STREAMING": {"merchant_name": "TelaPlay", "website": None, "logo": None},
    "LOJA DE ROUPAS": {"merchant_name": "Moda Centro", "website": None, "logo": None},
}
SUBCATEGORIAS = {
    "SUPERMERCADO": "Groceries",
    "DELIVERY APP": "Food delivery",
    "PIX ENVIADO - ALUGUEL": "Rent",
    "CONTA DE LUZ": "Electricity",
    "CONTA DE AGUA": "Water",
    "INTERNET E CELULAR": "Telecommunications",
    "RECARGA BILHETE UNICO": "Public transport",
    "POSTO DE COMBUSTIVEL": "Fuel",
    "APP DE TRANSPORTE": "Ride sharing",
    "FARMACIA": "Pharmacy",
    "STREAMING": "Streaming",
    "LOJA DE ROUPAS": "Clothing",
    "SALARIO - FOLHA DE PAGAMENTO": "Salary",
    "PIX RECEBIDO - COMPANHEIRO": "Pix",
    "PARCELA EMPRESTIMO PESSOAL": "Loan payment",
    "FINANCIAMENTO VEICULO": "Loan payment",
    "BOLETO CAIXA CREDITO PESSOAL": "Loan payment",
    "BOLETO CARNE LOJA D": "Loan payment",
    "JUROS CHEQUE ESPECIAL": "Interest",
    "PAGAMENTO FATURA NUBANK": "Credit card payment",
    "PAGAMENTO FATURA ITAU": "Credit card payment",
    "PAGAMENTO RECEBIDO": "Credit card payment",
    "RENDIMENTO POUPANCA": "Savings",
}
# ``operation_type`` no formato do Open Finance Brasil (conferido numa resposta real).
OPERACOES = {
    "SALARIO - FOLHA DE PAGAMENTO": "FOLHA_PAGAMENTO",
    "PIX RECEBIDO - COMPANHEIRO": "PIX",
    "PIX ENVIADO - ALUGUEL": "PIX",
    "CONTA DE LUZ": "BOLETO",
    "CONTA DE AGUA": "BOLETO",
    "INTERNET E CELULAR": "BOLETO",
    "BOLETO CAIXA CREDITO PESSOAL": "BOLETO",
    "BOLETO CARNE LOJA D": "BOLETO",
    "RECARGA BILHETE UNICO": "PIX",
    "SUPERMERCADO": "CARTAO",
    "PARCELA EMPRESTIMO PESSOAL": "OPERACAO_CREDITO",
    "FINANCIAMENTO VEICULO": "OPERACAO_CREDITO",
    "JUROS CHEQUE ESPECIAL": "ENCARGOS_JUROS_CHEQUE_ESPECIAL",
    "PAGAMENTO FATURA NUBANK": "PAGAMENTO_FATURA",
    "PAGAMENTO FATURA ITAU": "PAGAMENTO_FATURA",
    "PAGAMENTO RECEBIDO": "PAGAMENTO_FATURA",
    "RENDIMENTO POUPANCA": "RENDIMENTO_APLIC_FINANCEIRA",
}


def _id(*partes: object) -> str:
    """ID determinístico. Recebe o link: como na Belvo, cada link (e portanto
    cada usuário) tem os próprios ids — o upsert por id externo não pode achar
    a conta de outra pessoa."""
    return str(uuid.uuid5(NS, ":".join(str(p) for p in partes)))


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _proxima(hoje: date, dia: int) -> date:
    alvo = hoje.replace(day=dia) if hoje.day <= dia else adicionar_meses(hoje.replace(day=1), 1).replace(day=dia)
    return alvo


def _mes(hoje: date, delta: int, dia: int) -> date:
    return adicionar_meses(hoje.replace(day=1), delta).replace(day=dia)


def _conta(link: str, codigo: str, ident: str, categoria: str, nome: str, **extra) -> Json:
    base: Json = {
        "id": _id(link, codigo, "account", ident),
        "link": link,
        "institution": {"name": INSTITUICOES[codigo], "type": "bank"},
        "collected_at": _agora(),
        "created_at": _agora(),
        "category": categoria,
        "balance_type": "ASSET" if categoria in {"CHECKING_ACCOUNT", "SAVINGS_ACCOUNT"} else "LIABILITY",
        "type": extra.pop("type", categoria),
        "subtype": extra.pop("subtype", categoria),
        "name": nome,
        "number": extra.pop("number_override", None) or f"****{int(_id(codigo, ident)[:4], 16) % 10000:04d}",
        "agency": extra.pop("agency", None),
        "check_digit": extra.pop("check_digit", None),
        "currency": "BRL",
        "balance": {"current": None, "available": None},
        "overdraft": None,
        "credit_data": None,
        "loan_data": None,
        "funds_data": None,
    }
    base.update(extra)
    return base


def _loan(**campos) -> Json:
    # Campos que a Belvo Brasil devolve sempre null estão explícitos.
    nulos = dict.fromkeys(
        ["monthly_payment", "principal", "payment_day", "outstanding_principal", "credit_limit",
         "last_period_balance", "interest_rate", "limit_day", "cutting_day", "cutting_date",
         "last_payment_date", "no_interest_payment"]
    )
    padrao = {
        "collected_at": _agora(), "fees": [], "contracted_charges": [], "collaterals": [],
        "balloon_payments": None, "interest_rates": [], "currency": "BRL",
        "installments_contract_term_frequency": "MONTH", "installment_frequency": "MONTHLY",
        "installment_frequency_info": None, "amortization_schedule": "PRICE",
        "number_of_installments_past_due": 0, "settlement_date": None,
    }
    return {**nulos, **padrao, **campos}


def _taxa(periodicidade: str, *, value: str | None = None, pre_fixed_rate: str | None = None) -> Json:
    """Item de ``interest_rates[]`` como o Open Finance Brasil manda."""
    return {
        "name": "Taxa de juros remuneratória",
        "type": periodicidade,
        "value": value,
        "interest_rate_data": {
            "tax_type": "EFFECTIVE", "rate_type": "COMPOUND", "type": periodicidade,
            "calculation_base": "30/360", "reference_index_type": "PRE_FIXED",
            "reference_index_subtype": "PRE_FIXADO", "reference_index_info": None,
            "pre_fixed_rate": pre_fixed_rate or "0.000000", "post_fixed_rate": "0.000000",
            "additional_info": None,
        },
    }


def _credit(**campos) -> Json:
    nulos = dict.fromkeys(
        ["next_payment_date", "no_interest_payment", "interest_rate", "monthly_payment",
         "last_payment_date"]
    )
    return {**nulos, **campos}


def _contrato(hoje: date, *, total: int, pagas: int, dia: int) -> Json:
    """Datas coerentes de um contrato mensal com ``pagas`` parcelas já quitadas."""
    primeira = _mes(hoje, -pagas, dia)
    return {
        "number_of_installments_total": total,
        "number_of_installments_paid": pagas,
        "number_of_installments_outstanding": total - pagas,
        "first_installment_due_date": primeira.isoformat(),
        "contract_start_date": adicionar_meses(primeira, -1).isoformat(),
        "contract_end_date": adicionar_meses(primeira, total - 1).isoformat(),
    }


def contas(link: str, codigo: str, hoje: date) -> list[Json]:
    if codigo == NUBANK:
        return [
            _conta(
                link, codigo, "conta", "CHECKING_ACCOUNT", "Conta",
                type="CONTA_PAGAMENTO_PRE_PAGA", subtype="INDIVIDUAL",
                agency="0001", number_override="48213907", check_digit="3",
                balance={"current": "63.40", "available": "63.40"},
            ),
            _conta(
                link, codigo, "cartao", "CREDIT_CARD", "Nubank Mastercard", type="GOLD", subtype="CREDITO",
                number_override=FINAL_CARTAO[NUBANK],
                balance={"current": "2080.00", "available": "420.00"},
                credit_data=_credit(
                    collected_at=_agora(), credit_limit="2500.00",
                    cutting_date=(_proxima(hoje, 12) - timedelta(days=DIAS_ENTRE_FECHAMENTO_E_VENCIMENTO)).isoformat(),
                    minimum_payment="208.00", network="MASTERCARD",
                ),
            ),
            # Taxa em interest_rates[].value (mensal, fração).
            _conta(
                link, codigo, "emprestimo", "LOAN_ACCOUNT", "Empréstimo Pessoal",
                type="EMPRESTIMOS", subtype="CREDITO_PESSOAL_SEM_CONSIGNACAO",
                balance={"current": "4200.00", "available": "0.00"},
                loan_data=_loan(
                    loan_type="CREDITO_PESSOAL_SEM_CONSIGNACAO",
                    contract_amount="4630.00", outstanding_balance="4200.00",
                    total_effective_cost="1.1950",
                    interest_rates=[_taxa("MONTHLY", value="0.0644", pre_fixed_rate="0.064400")],
                    **_contrato(hoje, total=36, pagas=8, dia=5),
                ),
            ),
        ]
    if codigo == ITAU:
        return [
            # No cheque especial: saldo negativo na conta + o LOAN_ACCOUNT abaixo.
            _conta(
                link, codigo, "corrente", "CHECKING_ACCOUNT", "Conta Corrente",
                type="CONTA_DEPOSITO_A_VISTA", subtype="INDIVIDUAL",
                agency="0742", number_override="28561", check_digit="4",
                balance={"current": "-500.00", "available": "500.00"},
                overdraft={"arranged": "1000.00", "used": "500.00", "unarranged": "0.00"},
            ),
            # Taxa só em interest_rate_data.pre_fixed_rate (value null).
            _conta(
                link, codigo, "cheque", "LOAN_ACCOUNT", "CHEQUE ESPECIAL",
                type="EMPRESTIMOS", subtype="CHEQUE_ESPECIAL",
                balance={"current": "500.00", "available": "0.00"},
                loan_data=_loan(
                    loan_type="CHEQUE_ESPECIAL", contract_amount="1000.00", outstanding_balance="500.00",
                    total_effective_cost="1.3770",
                    interest_rates=[_taxa("MONTHLY", pre_fixed_rate="0.074900")],
                    number_of_installments_total=0, number_of_installments_paid=0,
                    number_of_installments_outstanding=0,
                    installments_contract_term_frequency="NO_FIXED_TERM",
                    installment_frequency="IRREGULAR", amortization_schedule="SEM_SISTEMA_AMORTIZACAO",
                    first_installment_due_date=None,
                    contract_start_date=_mes(hoje, -26, 3).isoformat(),
                    contract_end_date=_mes(hoje, 10, 3).isoformat(),
                ),
            ),
            _conta(
                link, codigo, "cartao", "CREDIT_CARD", "Itaú Visa", type="PLATINUM", subtype="CREDITO",
                number_override=FINAL_CARTAO[ITAU],
                balance={"current": "1100.00", "available": "900.00"},
                credit_data=_credit(
                    collected_at=_agora(), credit_limit="2000.00",
                    cutting_date=(_proxima(hoje, 20) - timedelta(days=DIAS_ENTRE_FECHAMENTO_E_VENCIMENTO)).isoformat(),
                    minimum_payment="110.00", network="VISA",
                ),
            ),
            # Sem interest_rates[]: a taxa sai do CET (fração anual).
            _conta(
                link, codigo, "moto", "FINANCING_ACCOUNT", "Financiamento de Veículos",
                type="FINANCIAMENTOS", subtype="AQUISICAO_BENS_VEICULOS_AUTOMOTORES",
                balance={"current": "7167.54", "available": None},
                loan_data=_loan(
                    loan_type="AQUISICAO_BENS_VEICULOS_AUTOMOTORES",
                    contract_amount="9800.00", outstanding_balance="7167.54",
                    total_effective_cost="0.2720",
                    collaterals=[{"type": "ALIENACAO_FIDUCIARIA", "subtype": "VEICULOS",
                                  "amount": "12500.00", "currency": "BRL"}],
                    **_contrato(hoje, total=48, pagas=18, dia=10),
                ),
            ),
        ]
    if codigo == CAIXA:
        return [
            _conta(
                link, codigo, "poupanca", "SAVINGS_ACCOUNT", "Poupança",
                type="CONTA_POUPANCA", subtype="INDIVIDUAL",
                agency="1679", number_override="45821", check_digit="7",
                balance={"current": "35.20", "available": "35.20"},
            ),
            # Taxa anual em interest_rate_data (type YEARLY).
            _conta(
                link, codigo, "consignado", "LOAN_ACCOUNT", "CREDITO CONSIGNADO",
                type="EMPRESTIMOS", subtype="CREDITO_PESSOAL_COM_CONSIGNACAO",
                balance={"current": "4114.15", "available": "0.00"},
                loan_data=_loan(
                    loan_type="CREDITO_PESSOAL_COM_CONSIGNACAO",
                    contract_amount="6000.00", outstanding_balance="4114.15",
                    total_effective_cost="0.2690",
                    interest_rates=[_taxa("YEARLY", pre_fixed_rate="0.245000")],
                    **_contrato(hoje, total=48, pagas=20, dia=7),
                ),
            ),
            # Uma parcela atrasada (number_of_installments_past_due) e taxa só no CET.
            _conta(
                link, codigo, "credito", "LOAN_ACCOUNT", "Crédito Pessoal",
                type="EMPRESTIMOS", subtype="CREDITO_PESSOAL_SEM_CONSIGNACAO",
                balance={"current": "641.44", "available": "0.00"},
                loan_data=_loan(
                    loan_type="CREDITO_PESSOAL_SEM_CONSIGNACAO",
                    contract_amount="1000.00", outstanding_balance="641.44",
                    total_effective_cost="2.2000",
                    **{**_contrato(hoje, total=12, pagas=6, dia=15),
                       # 7 parcelas venceram, 6 foram pagas: a última está em atraso.
                       "first_installment_due_date": _mes(hoje, -7, 15).isoformat(),
                       "number_of_installments_past_due": 1},
                ),
            ),
        ]
    return []


def _nome_fatura(venc: date) -> str:
    """Formato real do ``bill_name`` (ex.: ``Sep-2026``), independente do locale."""
    meses = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    return f"{meses[venc.month - 1]}-{venc.year}"


def _vencimentos(hoje: date, codigo: str, n: int) -> list[date]:
    """Os ``n`` últimos vencimentos do cartão, do mais antigo à fatura atual."""
    atual = _proxima(hoje, VENCIMENTO_CARTAO[codigo])
    return [adicionar_meses(atual.replace(day=1), -k).replace(day=atual.day) for k in range(n - 1, -1, -1)]


# Histórico das faturas: (total, mínimo, pagamentos[(tipo, valor)]) da mais antiga à atual.
# Nubank: paga só parte há meses → rotativo. Itaú: parcelado, pago em dia.
HISTORICO_FATURAS = {
    NUBANK: [
        ("1720.00", "172.00", [("OTHER", "172.00")]),
        ("1840.00", "184.00", [("OTHER", "190.00")]),
        ("1950.00", "195.00", [("OTHER", "208.00")]),
        ("2080.00", "208.00", []),
    ],
    ITAU: [
        ("1180.00", "118.00", [("FULL", "1180.00")]),
        ("1210.00", "121.00", [("FULL", "1210.00")]),
        ("1100.00", "110.00", []),
    ],
}


def faturas(link: str, codigo: str, hoje: date) -> list[Json]:
    if codigo not in HISTORICO_FATURAS:
        return []
    cartao = next(c for c in contas(link, codigo, hoje) if c["category"] == "CREDIT_CARD")
    historico = HISTORICO_FATURAS[codigo]
    saida = []
    for venc, (total, minimo, pagamentos) in zip(_vencimentos(hoje, codigo, len(historico)), historico, strict=True):
        atual = venc >= hoje
        saida.append(
            {
                "id": _id(link, codigo, "bill", venc.isoformat()),
                "account": cartao,
                "bill_name": _nome_fatura(venc),
                "due_date": venc.isoformat(),
                "currency": "BRL",
                "total_amount": total,
                "minimum_amount": minimo,
                "is_installment": codigo == ITAU,
                # Juros do rotativo na fatura atual do Nubank: é o sinal que o
                # mapeamento usa para classificar como CARTAO_ROTATIVO.
                "finance_charges": (
                    [{"type": "LATE_PAYMENT_INTEREST", "additional_info": None, "currency": "BRL",
                      "amount": "292.89"}]
                    if codigo == NUBANK and atual else []
                ),
                "payments": [
                    {"type": t, "payment_date": venc.isoformat(), "payment_mode": "DIRECT_DEBIT",
                     "currency": "BRL", "amount": v}
                    for t, v in pagamentos
                ],
                "collected_at": _agora(),
            }
        )
    return saida


def _transacted_at(d: date, n: int, *, noite: bool = False) -> str:
    """Horário UTC determinístico. ``noite``: 01:30 UTC do dia seguinte, que é
    22:30 do dia ``d`` em Brasília — exercita a virada de data na conversão."""
    if noite:
        return f"{(d + timedelta(days=1)).isoformat()}T01:30:00.000Z"
    return f"{d.isoformat()}T{12 + n % 9:02d}:{(n * 7) % 60:02d}:00.000Z"


def _fatura_da_compra(codigo: str, d: date, hoje: date) -> str | None:
    """``bill_name`` da fatura em que a compra entrou; ``None`` no ciclo aberto."""
    dia = VENCIMENTO_CARTAO[codigo]
    venc = d.replace(day=dia)
    if d > venc - timedelta(days=DIAS_ENTRE_FECHAMENTO_E_VENCIMENTO):
        venc = adicionar_meses(venc.replace(day=1), 1).replace(day=dia)
    fechamento = venc - timedelta(days=DIAS_ENTRE_FECHAMENTO_E_VENCIMENTO)
    return _nome_fatura(venc) if fechamento < hoje else None


def _resumo(conta: Json) -> Json:
    return {k: conta[k] for k in ("id", "category", "type", "name", "number", "institution")}


def transacoes(link: str, codigo: str, hoje: date) -> list[Json]:
    """12 meses completos + o mês corrente até hoje, em todas as contas e cartões."""
    if codigo not in BANCOS_DA_JULIANA:
        return []
    por_ident = {ident: c for c in contas(link, codigo, hoje)
                 for ident in ("conta", "corrente", "cartao", "poupanca") if c["id"] == _id(link, codigo, "account", ident)}
    saida: list[Json] = []
    inicio = adicionar_meses(hoje.replace(day=1), -12)
    historico = HISTORICO_FATURAS.get(codigo, [])
    pagamentos_fatura = (
        {
            _nome_fatura(v): sum((Decimal(p) for _, p in pg), Decimal(0))
            for v, (_, _, pg) in zip(_vencimentos(hoje, codigo, len(historico)), historico, strict=True)
        }
        if historico else {}
    )

    for k in range(13):
        mes = adicionar_meses(inicio, k)
        idx6 = k - 6  # 0..5 = os seis meses da janela de capacidade
        entradas = Decimal(ENTRADAS_6M[idx6] if 0 <= idx6 < 6 else ENTRADAS_6M[k % 6])
        essenciais = Decimal(ESSENCIAIS_6M[idx6] if 0 <= idx6 < 6 else ESSENCIAIS_6M[k % 6])
        mercado = essenciais - ESSENCIAIS_FIXOS
        companheiro = entradas - SALARIO
        c1 = (companheiro * Decimal("0.6")).quantize(Decimal("0.01"))
        delivery = DELIVERY_PICO if k == 11 else DELIVERY_NORMAL
        ultimo_completo = k == 11
        q = lambda f: (mercado * Decimal(f)).quantize(Decimal("0.01"))  # noqa: E731

        # (conta, dia, tipo, valor, descrição, categoria[, noite])
        linhas: list[tuple] = []
        if codigo == NUBANK:
            fatura_mes = _nome_fatura(mes.replace(day=12))
            pago = pagamentos_fatura.get(fatura_mes, Decimal("180.00"))
            linhas += [
                ("conta", 10, "INFLOW", c1, "PIX RECEBIDO - COMPANHEIRO", "Transfers"),
                ("conta", 25, "INFLOW", companheiro - c1, "PIX RECEBIDO - COMPANHEIRO", "Transfers", True),
                ("conta", 5, "OUTFLOW", PARCELA_EMPRESTIMO_NUBANK, "PARCELA EMPRESTIMO PESSOAL", "Credits & Loans"),
                ("conta", 12, "OUTFLOW", pago, "PAGAMENTO FATURA NUBANK", "Credits & Loans"),
                ("cartao", 12, "INFLOW", pago, "PAGAMENTO RECEBIDO", "Credits & Loans"),
                ("cartao", 2, "OUTFLOW", Decimal("180.00"), "POSTO DE COMBUSTIVEL", "Transport & Travel"),
                ("cartao", 27, "OUTFLOW", Decimal("40.00"), "APP DE TRANSPORTE", "Transport & Travel"),
                ("cartao", 3, "OUTFLOW", q("0.20"), "SUPERMERCADO", "Food & Groceries"),
                ("cartao", 24, "OUTFLOW", q("0.20"), "SUPERMERCADO", "Food & Groceries"),
                ("cartao", 7, "OUTFLOW", (delivery / 2).quantize(Decimal("0.01")), "DELIVERY APP",
                 "Online Platforms & Leisure"),
                ("cartao", 21, "OUTFLOW", delivery - (delivery / 2).quantize(Decimal("0.01")), "DELIVERY APP",
                 "Online Platforms & Leisure"),
                ("cartao", 14, "OUTFLOW", Decimal("39.90"), "STREAMING", "Online Platforms & Leisure"),
            ]
        elif codigo == ITAU:
            fatura_mes = _nome_fatura(mes.replace(day=20))
            pago = pagamentos_fatura.get(fatura_mes, Decimal("1150.00"))
            linhas += [
                ("corrente", 5, "INFLOW", SALARIO, "SALARIO - FOLHA DE PAGAMENTO", "Income & Payments"),
                ("corrente", 6, "OUTFLOW", Decimal("1200.00"), "PIX ENVIADO - ALUGUEL", "Home & Life"),
                ("corrente", 8, "OUTFLOW", Decimal("160.00"), "CONTA DE LUZ", "Bills & Utilities"),
                ("corrente", 9, "OUTFLOW", Decimal("70.00"), "CONTA DE AGUA", "Bills & Utilities"),
                ("corrente", 15, "OUTFLOW", Decimal("150.00"), "INTERNET E CELULAR", "Bills & Utilities"),
                ("corrente", 2, "OUTFLOW", Decimal("100.00"), "RECARGA BILHETE UNICO", "Transport & Travel"),
                # Mercado: 40% no cartão Nubank, 25% no cartão Itaú, o resto no débito.
                ("corrente", 13, "OUTFLOW", mercado - q("0.20") * 2 - q("0.25"), "SUPERMERCADO",
                 "Food & Groceries"),
                ("corrente", 10, "OUTFLOW", PARCELA_MOTO, "FINANCIAMENTO VEICULO", "Credits & Loans"),
                ("corrente", 20, "OUTFLOW", pago, "PAGAMENTO FATURA ITAU", "Credits & Loans"),
                ("cartao", 20, "INFLOW", pago, "PAGAMENTO RECEBIDO", "Credits & Loans"),
                ("cartao", 4, "OUTFLOW", Decimal("150.00"), "FARMACIA", "Home & Life"),
                ("cartao", 18, "OUTFLOW", q("0.25"), "SUPERMERCADO", "Food & Groceries"),
                ("cartao", 22, "OUTFLOW", Decimal("80.00"), "LOJA DE ROUPAS", "Personal Shopping"),
            ]
            # O carnê e o crédito da Caixa são pagos por boleto, daqui. O último
            # mês não foi pago: são as dívidas em atraso da demo.
            if not ultimo_completo and k < 12:
                linhas += [
                    ("corrente", 16, "OUTFLOW", PARCELA_CARNE, "BOLETO CARNE LOJA D", "Credits & Loans"),
                    ("corrente", 15, "OUTFLOW", PARCELA_CREDITO_CAIXA, "BOLETO CAIXA CREDITO PESSOAL",
                     "Credits & Loans"),
                ]
            if k >= 10:  # o cheque especial começou há três meses
                linhas.append(("corrente", 28, "OUTFLOW", Decimal("37.45"), "JUROS CHEQUE ESPECIAL", "Credits & Loans"))
        elif codigo == CAIXA:
            linhas.append(("poupanca", 1, "INFLOW", Decimal("0.21"), "RENDIMENTO POUPANCA", "Investments & Savings"))

        for n, linha in enumerate(linhas):
            ident, dia, tipo, valor, desc, cat = linha[:6]
            noite = len(linha) > 6 and linha[6]
            d = mes.replace(day=dia)
            if d >= hoje:
                continue
            conta = por_ident[ident]
            cartao = conta["category"] == "CREDIT_CARD"
            saida.append(
                {
                    "id": _id(link, codigo, "txn", ident, mes.strftime("%Y-%m"), n),
                    "account": _resumo(conta),
                    "internal_identification": None,
                    "collected_at": _agora(),
                    "created_at": _agora(),
                    "value_date": d.isoformat(),
                    "accounting_date": None,
                    "transacted_at": _transacted_at(d, n, noite=noite),
                    "amount": str(valor),
                    "currency": "BRL",
                    "description": desc,
                    # Estabelecimento só existe em transação de cartão.
                    "merchant": MERCHANTS.get(desc) if cartao else None,
                    "category": cat,
                    "subcategory": SUBCATEGORIAS.get(desc),
                    "type": tipo,
                    "status": "PROCESSED",
                    "operation_type": ("PAGAMENTO" if cartao and tipo == "OUTFLOW"
                                       else OPERACOES.get(desc, "OUTROS")),
                    "credit_card_data": (
                        {"card_number": FINAL_CARTAO[codigo],
                         "bill_name": _fatura_da_compra(codigo, d, hoje),
                         "installment_identifier": None, "number_of_installments": None,
                         "bill_amount": None, "bill_status": None, "bill_due_date": None}
                        if cartao else None
                    ),
                    "balance": None,
                    "observations": None,
                    "reference": None,
                }
            )
    return saida


class FixtureProvider(AggregationProvider):
    """Simula a Belvo ponta a ponta: widget, link, consentimento e coleta."""

    nome = "fixture"

    def __init__(self, app_public_url: str) -> None:
        self._base = app_public_url.rstrip("/")
        self._tokens: dict[str, str] = {}  # token → external_id
        self._links: dict[str, tuple[str, str]] = {}  # link → (instituição, external_id)

    async def criar_url_widget(self, usuario: IdentificacaoUsuario, instituicao: str | None = None) -> str:
        token = secrets.token_urlsafe(24)
        self._tokens[token] = usuario.external_id
        url = f"{self._base}/conectar/simulado?access_token={token}&external_id={usuario.external_id}"
        return f"{url}&institutions={instituicao}" if instituicao else url

    def autorizar(self, token: str, instituicao: str, external_id_esperado: str | None = None) -> str:
        """Chamado pelo widget simulado quando o "usuário autoriza no banco"."""
        external_id = self._tokens.get(token)
        if external_id is None or (external_id_esperado and external_id != external_id_esperado):
            raise ErroProvedor("ACCESS_TOKEN_NOT_VALID")
        del self._tokens[token]
        if instituicao == INSTITUICAO_FORA_DO_AR:
            raise ErroProvedor("institution_down")
        if instituicao not in INSTITUICOES:
            raise ErroProvedor("institution_not_found")
        link = str(uuid.uuid4())
        self._links[link] = (instituicao, external_id)
        return link

    def _instituicao(self, link_id: str) -> str:
        if link_id in self._links:
            return self._links[link_id][0]
        raise ErroProvedor("link_nao_encontrado")

    def registrar_link(self, link_id: str, instituicao: str, external_id: str) -> None:
        """Reidrata o registro após reinício do servidor (o link está no banco)."""
        self._links.setdefault(link_id, (instituicao, external_id))

    async def obter_link(self, link_id: str) -> LinkInfo | None:
        if link_id not in self._links:
            return None
        inst, ext = self._links[link_id]
        return LinkInfo(id=link_id, instituicao_codigo=inst, external_id=ext, status="valid")

    async def obter_consentimento(self, link_id: str, usuario: IdentificacaoUsuario):
        # Consentimento de 12 meses a partir de hoje.
        return ConsentimentoInfo(
            expira_em=datetime.now(timezone.utc) + timedelta(days=366), status="AUTHORISED"
        )

    async def listar(self, recurso: Recurso, link_id: str, *, desde=None, ate=None) -> list[Json]:
        codigo = self._instituicao(link_id)
        hoje = date.today()
        if recurso is Recurso.ACCOUNTS:
            return contas(link_id, codigo, hoje)
        if recurso is Recurso.BILLS:
            return faturas(link_id, codigo, hoje)
        if recurso is Recurso.TRANSACTIONS:
            return transacoes(link_id, codigo, hoje)
        # OWNERS não é lido (minimização); add-ons não habilitados na fixture.
        return []

    async def revogar(self, link_id: str) -> None:
        self._links.pop(link_id, None)
