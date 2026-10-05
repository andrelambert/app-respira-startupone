"""FixtureProvider — a situação da Juliana (docs/contexto-produto.md §2) no formato da Belvo.

Não é "mock em vez de dado real": é o que roda nos testes e na conta demo
(provedor por usuário, ``services/contexto.py``), para demonstrar sem expor dado bancário real e para o
mapeamento ser exercitado de verdade. Os objetos seguem o schema conferido
(``AccountOpenFinanceBrazil``, ``TransactionOpenFinanceBrazil``, ``Bill``),
inclusive os campos que no Brasil vêm ``null``.

Única licença, documentada: ``loan_data.monthly_payment`` é ``null`` na Belvo
Brasil hoje, mas a fixture o preenche no empréstimo e no cheque especial. O
mínimo de R$ 260 da Juliana é menor que os juros do mês (R$ 270), o que
nenhuma fórmula de parcela reproduz — e a §14.1 precisa desses números. O
caminho real (parcela pela tabela Price) é coberto em ``test_mapping.py``.
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

INSTITUICOES = {
    "fixture_banco_a_br_retail": "Banco A",
    "fixture_banco_b_br_retail": "Banco B",
    # Sempre "fora do ar": exercita a tela de saída com erro traduzido.
    "fixture_banco_c_br_retail": "Banco C",
}
INSTITUICAO_FORA_DO_AR = "fixture_banco_c_br_retail"

# Totais mensais dos 6 meses que entram na capacidade (do mais antigo ao mais
# recente). Medianas: entradas R$ 4.800, essenciais R$ 3.800 → capacidade
# (4.800 − 3.800) × 0,90 = R$ 900, a capacidade da fixture da §14.1.
ENTRADAS_6M = ["4800.00", "4650.00", "4800.00", "5100.00", "4800.00", "4720.00"]
ESSENCIAIS_6M = ["3800.00", "3750.00", "3890.00", "3800.00", "3820.00", "3800.00"]
DELIVERY_NORMAL = Decimal("210.00")
DELIVERY_PICO = Decimal("430.00")  # último mês completo: dispara PICO_CATEGORIA


# Estabelecimentos e subcategorias fictícios, só para a demo exibir o detalhe da transação.
MERCHANTS = {
    "SUPERMERCADO": {"merchant_name": "Mercado Bom Preço", "website": None, "logo": None},
    "DELIVERY APP": {"merchant_name": "Entrega Já", "website": None, "logo": None},
    "FARMACIA": {"merchant_name": "Farmácia Saúde+", "website": None, "logo": None},
}
SUBCATEGORIAS = {
    "SUPERMERCADO": "Groceries",
    "DELIVERY APP": "Food delivery",
    "ALUGUEL": "Rent",
    "CONTA DE LUZ": "Electricity",
    "CONTA DE AGUA": "Water",
    "INTERNET E CELULAR": "Telecom",
    "RECARGA BILHETE UNICO": "Public transport",
    "APP DE TRANSPORTE": "Ride sharing",
    "FARMACIA": "Pharmacy",
    "STREAMING": "Streaming",
    "SALARIO - FOLHA DE PAGAMENTO": "Salary",
    "PIX RECEBIDO - COMPANHEIRO": "Pix",
    "PARCELA EMPRESTIMO": "Loan payment",
    "PAGAMENTO FATURA CARTAO": "Credit card payment",
}


def _id(*partes: object) -> str:
    return str(uuid.uuid5(NS, ":".join(str(p) for p in partes)))


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _proxima(hoje: date, dia: int) -> date:
    alvo = hoje.replace(day=dia) if hoje.day <= dia else adicionar_meses(hoje.replace(day=1), 1).replace(day=dia)
    return alvo


def _conta(link: str, codigo: str, ident: str, categoria: str, nome: str, **extra) -> Json:
    base: Json = {
        "id": _id(codigo, "account", ident),
        "link": link,
        "institution": {"name": INSTITUICOES[codigo], "type": "bank"},
        "collected_at": _agora(),
        "created_at": _agora(),
        "category": categoria,
        "balance_type": "ASSET" if categoria == "CHECKING_ACCOUNT" else "LIABILITY",
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
    return {**nulos, "fees": [], "contracted_charges": [], "collaterals": [], **campos}


def _credit(**campos) -> Json:
    nulos = dict.fromkeys(
        ["next_payment_date", "no_interest_payment", "interest_rate", "monthly_payment",
         "last_payment_date"]
    )
    return {**nulos, **campos}


def contas(link: str, codigo: str, hoje: date) -> list[Json]:
    if codigo == "fixture_banco_a_br_retail":
        return [
            _conta(
                link, codigo, "corrente", "CHECKING_ACCOUNT", "Conta corrente",
                type="CONTA_DEPOSITO_A_VISTA", subtype="INDIVIDUAL",
                agency="0001", check_digit="7", number_override="104582",
                balance={"current": "180.00", "available": "180.00"},
                overdraft={"arranged": "1000.00", "used": "0.00", "unarranged": "0.00"},
            ),
            _conta(
                link, codigo, "cartao", "CREDIT_CARD", "Cartão Banco A", type="CARTAO", subtype="CREDITO",
                balance={"current": "2080.00", "available": "420.00"},
                credit_data=_credit(
                    collected_at=_agora(), credit_limit="2500.00",
                    cutting_date=(_proxima(hoje, 12) - timedelta(days=7)).isoformat(),
                    minimum_payment="208.00", network="MASTERCARD",
                ),
            ),
            _conta(
                link, codigo, "emprestimo", "LOAN_ACCOUNT", "Empréstimo pessoal",
                type="EMPRESTIMO", subtype="CREDITO_PESSOAL_SEM_CONSIGNACAO",
                balance={"current": "4200.00", "available": None},
                loan_data=_loan(
                    loan_type="CREDITO_PESSOAL_SEM_CONSIGNACAO",
                    contract_amount="5000.00", outstanding_balance="4200.00",
                    interest_rates=[{"name": "Pré-fixada", "type": "MONTHLY", "value": "0.0644",
                                     "interest_rate_data": None}],
                    number_of_installments_total=36, number_of_installments_paid=8,
                    number_of_installments_outstanding=28, number_of_installments_past_due=0,
                    first_installment_due_date=adicionar_meses(hoje.replace(day=1), -8)
                    .replace(day=5).isoformat(),
                    monthly_payment="260.00",  # ver docstring do módulo
                ),
            ),
            _conta(
                link, codigo, "cheque", "ADVANCE_DEPOSIT_ACCOUNT", "Cheque especial",
                balance={"current": "500.00", "available": None},
                loan_data=_loan(
                    outstanding_balance="500.00",
                    interest_rates=[{"name": "Cheque especial", "type": "MONTHLY", "value": "0.0749",
                                     "interest_rate_data": None}],
                    first_installment_due_date=adicionar_meses(hoje.replace(day=1), -2)
                    .replace(day=1).isoformat(),
                    monthly_payment="50.00",  # ver docstring do módulo
                ),
            ),
        ]
    if codigo == "fixture_banco_b_br_retail":
        return [
            _conta(
                link, codigo, "cartao", "CREDIT_CARD", "Cartão Banco B", type="CARTAO", subtype="CREDITO",
                balance={"current": "1100.00", "available": "900.00"},
                credit_data=_credit(
                    collected_at=_agora(), credit_limit="2000.00",
                    cutting_date=(_proxima(hoje, 20) - timedelta(days=7)).isoformat(),
                    minimum_payment="110.00", network="VISA",
                ),
            )
        ]
    return []


def _nome_fatura(venc: date) -> str:
    """Formato real do ``bill_name`` (ex.: ``Sep-2026``), independente do locale."""
    meses = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    return f"{meses[venc.month - 1]}-{venc.year}"


def faturas(link: str, codigo: str, hoje: date) -> list[Json]:
    def fatura(conta_ident, venc: date, total, minimo, *, parcelado=False, encargos=(), pagamentos=()):
        conta = next(c for c in contas(link, codigo, hoje) if c["id"] == _id(codigo, "account", conta_ident))
        return {
            "id": _id(codigo, "bill", conta_ident, venc.isoformat()),
            "account": conta,
            "bill_name": _nome_fatura(venc),
            "due_date": venc.isoformat(),
            "currency": "BRL",
            "total_amount": total,
            "minimum_amount": minimo,
            "is_installment": parcelado,
            "finance_charges": [
                {"type": t, "additional_info": None, "currency": "BRL", "amount": v} for t, v in encargos
            ],
            "payments": [
                {"type": t, "payment_date": d.isoformat(), "payment_mode": "PIX", "currency": "BRL",
                 "amount": v}
                for t, d, v in pagamentos
            ],
            "collected_at": _agora(),
        }

    if codigo == "fixture_banco_a_br_retail":
        venc = _proxima(hoje, 12)
        anterior = adicionar_meses(venc.replace(day=1), -1).replace(day=12)
        return [
            fatura("cartao", anterior, "1950.00", "195.00", pagamentos=[("OTHER", anterior, "208.00")]),
            fatura("cartao", venc, "2080.00", "208.00", encargos=[("LATE_PAYMENT_INTEREST", "292.89")]),
        ]
    if codigo == "fixture_banco_b_br_retail":
        venc = _proxima(hoje, 20)
        anterior = adicionar_meses(venc.replace(day=1), -1).replace(day=20)
        return [
            fatura("cartao", anterior, "1210.00", "121.00", parcelado=True,
                   pagamentos=[("FULL", anterior, "1210.00")]),
            fatura("cartao", venc, "1100.00", "110.00", parcelado=True),
        ]
    return []


# ``operation_type`` no formato do Open Finance Brasil (conferido numa resposta real).
OPERACOES = {
    "SALARIO - FOLHA DE PAGAMENTO": "FOLHA_PAGAMENTO",
    "PIX RECEBIDO - COMPANHEIRO": "PIX",
    "ALUGUEL": "PIX",
    "CONTA DE LUZ": "BOLETO",
    "CONTA DE AGUA": "BOLETO",
    "INTERNET E CELULAR": "BOLETO",
    "RECARGA BILHETE UNICO": "PIX",
    "APP DE TRANSPORTE": "CARTAO",
    "FARMACIA": "CARTAO",
    "SUPERMERCADO": "CARTAO",
    "DELIVERY APP": "CARTAO",
    "STREAMING": "CARTAO",
    "LOJA DE ROUPAS": "CARTAO",
    "PARCELA EMPRESTIMO": "OPERACAO_CREDITO",
    "PAGAMENTO FATURA CARTAO": "PAGAMENTO_FATURA",
}


def _transacted_at(d: date, n: int) -> str:
    """Horário UTC determinístico; o PIX do dia 25 (linha 2) cai às 22:30 de Brasília."""
    if n == 2:
        return f"{(d + timedelta(days=1)).isoformat()}T01:30:00.000Z"
    return f"{d.isoformat()}T{12 + n % 9:02d}:{(n * 7) % 60:02d}:00.000Z"


def transacoes(link: str, codigo: str, hoje: date) -> list[Json]:
    """12 meses completos + o mês corrente até hoje, só na conta corrente do Banco A."""
    if codigo != "fixture_banco_a_br_retail":
        return []
    conta = contas(link, codigo, hoje)[0]
    conta_resumo = {k: conta[k] for k in ("id", "category", "type", "name", "number", "institution")}
    saida: list[Json] = []
    inicio = adicionar_meses(hoje.replace(day=1), -12)

    for k in range(13):
        mes = adicionar_meses(inicio, k)
        idx6 = k - 6  # 0..5 = os seis meses da janela de capacidade
        entradas = Decimal(ENTRADAS_6M[idx6] if 0 <= idx6 < 6 else ENTRADAS_6M[k % 6])
        essenciais = Decimal(ESSENCIAIS_6M[idx6] if 0 <= idx6 < 6 else ESSENCIAIS_6M[k % 6])
        delivery = DELIVERY_PICO if k == 11 else DELIVERY_NORMAL
        mercado = essenciais - Decimal("2350.00")
        m1 = (mercado * Decimal("0.3")).quantize(Decimal("0.01"))
        m2 = (mercado * Decimal("0.25")).quantize(Decimal("0.01"))
        m3 = (mercado * Decimal("0.25")).quantize(Decimal("0.01"))
        companheiro = entradas - Decimal("3100.00")
        c1 = (companheiro * Decimal("0.6")).quantize(Decimal("0.01"))

        linhas = [
            (5, "INFLOW", Decimal("3100.00"), "SALARIO - FOLHA DE PAGAMENTO", "Income & Payments"),
            (10, "INFLOW", c1, "PIX RECEBIDO - COMPANHEIRO", "Transfers"),
            (25, "INFLOW", companheiro - c1, "PIX RECEBIDO - COMPANHEIRO", "Transfers"),
            (6, "OUTFLOW", Decimal("1200.00"), "ALUGUEL", "Home & Life"),
            (8, "OUTFLOW", Decimal("160.00"), "CONTA DE LUZ", "Bills & Utilities"),
            (9, "OUTFLOW", Decimal("70.00"), "CONTA DE AGUA", "Bills & Utilities"),
            (15, "OUTFLOW", Decimal("150.00"), "INTERNET E CELULAR", "Bills & Utilities"),
            (2, "OUTFLOW", Decimal("300.00"), "RECARGA BILHETE UNICO", "Transport & Travel"),
            (17, "OUTFLOW", Decimal("200.00"), "RECARGA BILHETE UNICO", "Transport & Travel"),
            (27, "OUTFLOW", Decimal("120.00"), "APP DE TRANSPORTE", "Transport & Travel"),
            (19, "OUTFLOW", Decimal("150.00"), "FARMACIA", "Home & Life"),
            (3, "OUTFLOW", m1, "SUPERMERCADO", "Food & Groceries"),
            (11, "OUTFLOW", m2, "SUPERMERCADO", "Food & Groceries"),
            (18, "OUTFLOW", m3, "SUPERMERCADO", "Food & Groceries"),
            (26, "OUTFLOW", mercado - m1 - m2 - m3, "SUPERMERCADO", "Food & Groceries"),
            (7, "OUTFLOW", (delivery / 2).quantize(Decimal("0.01")), "DELIVERY APP", "Online Platforms & Leisure"),
            (21, "OUTFLOW", delivery - (delivery / 2).quantize(Decimal("0.01")), "DELIVERY APP",
             "Online Platforms & Leisure"),
            (12, "OUTFLOW", Decimal("39.90"), "STREAMING", "Online Platforms & Leisure"),
            (22, "OUTFLOW", Decimal("80.00"), "LOJA DE ROUPAS", "Personal Shopping"),
            (5, "OUTFLOW", Decimal("260.00"), "PARCELA EMPRESTIMO", "Credits & Loans"),
            (12, "OUTFLOW", Decimal("208.00"), "PAGAMENTO FATURA CARTAO", "Credits & Loans"),
        ]
        for n, (dia, tipo, valor, desc, cat) in enumerate(linhas):
            d = mes.replace(day=dia)
            if d >= hoje:
                continue
            saida.append(
                {
                    "id": _id(codigo, "txn", mes.strftime("%Y-%m"), n),
                    "account": conta_resumo,
                    "internal_identification": None,
                    "collected_at": _agora(),
                    "created_at": _agora(),
                    "value_date": d.isoformat(),
                    # UTC, como a Belvo manda. 01:30Z do dia seguinte = 22:30 em
                    # Brasília: exercita a virada de data na conversão de fuso.
                    "transacted_at": _transacted_at(d, n),
                    "operation_type": OPERACOES.get(desc, "OUTROS"),
                    "accounting_date": None,
                    "amount": str(valor),
                    "currency": "BRL",
                    "description": desc,
                    "merchant": MERCHANTS.get(desc),
                    "category": cat,
                    "subcategory": SUBCATEGORIAS.get(desc),
                    "type": tipo,
                    "status": "PROCESSED",
                    "credit_card_data": None,
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
