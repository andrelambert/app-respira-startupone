"""Belvo → domínio Respira (docs/contexto-produto.md §7.7).

Todo o acoplamento com os nomes da Belvo mora aqui. Nenhuma outra parte do
código conhece ``category``, ``credit_data``, ``loan_data`` & cia.

Schema conferido na documentação pública da Belvo em 2026-10-03 (OpenAPI
v1.223.0, ``AccountOpenFinanceBrazil``, ``TransactionOpenFinanceBrazil``,
``Bill``). Dois fatos dessa conferência moldam as regras abaixo:

* No Brasil vêm sempre ``null``: ``credit_data.interest_rate``,
  ``credit_data.next_payment_date``, ``credit_data.monthly_payment``,
  ``loan_data.interest_rate``, ``loan_data.monthly_payment`` e
  ``loan_data.payment_day``. Por isso a taxa de cartão é sempre estimada, a de
  empréstimo vem de ``loan_data.interest_rates[]`` e a parcela/vencimento do
  empréstimo são derivados.
* ``account.institution`` é objeto ``{name, type}``; ``transaction.account`` e
  ``bill.account`` são o objeto da conta inteiro, não um id.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Iterable

from app.content.taxas_referencia import taxa_estimada
from app.domain.pfm import horario_brasil
from app.domain.planner import arredondar

log = logging.getLogger("respira.mapping")

Json = dict[str, Any]

# Sanity check da taxa mensal normalizada (§7.7): fora disto, não usar.
TAXA_MES_MIN = Decimal("0.001")
TAXA_MES_MAX = Decimal("0.20")
ANUAL_PERCENTUAL_A_PARTIR_DE = Decimal("8")
# Cheque especial não tem "mínimo" contratual. Estimativa: 10% do usado.
FRACAO_MINIMO_CHEQUE = Decimal("0.10")

# Categorias da Belvo (enum de ``TransactionOpenFinanceBrazil.category``) que
# contam como gasto essencial no §5.1. Tabela explícita: o usuário nunca
# classifica nada (princípio 1, §3).
CATEGORIAS_ESSENCIAIS = frozenset(
    {
        "Bills & Utilities",  # luz, água, telefone, internet
        "Food & Groceries",  # mercado
        "Home & Life",  # aluguel, casa, saúde
        "Transport & Travel",  # transporte
        "Insurance",
        "Taxes",
    }
)
# Saídas nesta categoria são pagamento de dívida: não são gasto essencial —
# são justamente o que a capacidade vai cobrir.
CATEGORIA_PAGAMENTO_DIVIDA = "Credits & Loans"
# Entradas que não são renda: crédito tomado e resgate de aplicação. Contar
# empréstimo recebido como renda inflaria a capacidade de pagamento.
CATEGORIAS_ENTRADA_NAO_RENDA = frozenset({"Credits & Loans", "Investments & Savings"})
CATEGORIAS_CONTA_SEM_RENDA = frozenset(
    {"CREDIT_CARD", "LOAN_ACCOUNT", "FINANCING_ACCOUNT", "ADVANCE_DEPOSIT_ACCOUNT"}
)


# --- saída do mapeamento -----------------------------------------------------


@dataclass
class InstituicaoMapeada:
    codigo: str
    nome: str


@dataclass
class ContaMapeada:
    id_externo: str
    tipo: str  # models.TipoConta
    nome: str
    saldo: Decimal  # conta: saldo · cartão: usado · crédito: saldo devedor
    limite_cheque_especial: Decimal = Decimal("0.00")
    usado_cheque_especial: Decimal = Decimal("0.00")
    numero_final: str | None = None
    disponivel: Decimal | None = None
    limite_credito: Decimal | None = None
    tipo_externo: str | None = None
    agencia: str | None = None
    numero_conta: str | None = None


@dataclass
class PagamentoFatura:
    data: date | None
    valor: Decimal


@dataclass
class FaturaMapeada:
    id_externo: str
    conta_id_externo: str
    nome: str
    vencimento: date | None
    total: Decimal
    minimo: Decimal | None
    pago: Decimal
    encargos: Decimal
    parcelada: bool
    pagamentos: list[PagamentoFatura] = field(default_factory=list)


@dataclass
class DividaMapeada:
    id_externo: str
    modalidade: str
    descricao: str
    saldo_devedor: Decimal
    taxa_juros_mes: Decimal
    taxa_origem: str  # INFORMADA | ESTIMADA
    parcela_minima: Decimal
    parcela_estimada: bool
    parcelas_restantes: int | None
    dia_vencimento: int | None
    em_atraso_dias: int


@dataclass
class TransacaoMapeada:
    id_externo: str
    conta_id_externo: str | None
    data_mov: date
    valor: Decimal  # negativo = saída
    descricao: str
    categoria: str | None
    essencial: bool
    pagamento_divida: bool
    conta_como_renda: bool
    estabelecimento: str | None = None
    estabelecimento_site: str | None = None
    subcategoria: str | None = None
    transacionado_em: datetime | None = None  # UTC
    tipo_operacao: str | None = None
    final_cartao: str | None = None  # só os 4 últimos dígitos (PCI)
    fatura_nome: str | None = None  # credit_card_data.bill_name (ex.: Sep-2026)


@dataclass
class ResultadoContas:
    contas: list[ContaMapeada] = field(default_factory=list)
    dividas: list[DividaMapeada] = field(default_factory=list)
    faturas: list[FaturaMapeada] = field(default_factory=list)
    ignoradas: int = 0


# --- utilitários -------------------------------------------------------------


def _dec(valor: Any) -> Decimal | None:
    if valor is None or valor == "":
        return None
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None


def _data(valor: Any) -> date | None:
    if not valor:
        return None
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def _datahora_utc(valor: Any) -> datetime | None:
    """ISO 8601 da Belvo (ex.: ``2026-10-03T14:05:00.000Z``) → datetime em UTC.

    A Belvo manda em GMT 0; sem offset explícito, assume-se UTC."""
    if not valor:
        return None
    try:
        dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _upper(*partes: Any) -> str:
    return " ".join(str(p) for p in partes if p).upper()


def _final(numero: Any) -> str | None:
    """Só os últimos 4 dígitos — número de conta/cartão completo não é guardado."""
    digitos = "".join(ch for ch in str(numero or "") if ch.isdigit())
    return digitos[-4:] or None


def _numero_conta(conta: Json) -> str | None:
    """Número da conta de depósito com dígito (ex.: 12345-6). Nunca usado para cartão."""
    numero = str(conta.get("number") or "").strip()
    digito = str(conta.get("check_digit") or "").strip()
    if not numero:
        return None
    return (f"{numero}-{digito}" if digito and not numero.endswith(f"-{digito}") else numero)[:30]


def _soma_pagamentos(fatura: Json) -> Decimal:
    return sum((_dec(p.get("amount")) or Decimal(0) for p in fatura.get("payments") or []), Decimal(0))


def mapear_fatura(f: Json, conta_id: str) -> FaturaMapeada:
    return FaturaMapeada(
        id_externo=f["id"],
        conta_id_externo=conta_id,
        nome=str(f.get("bill_name") or "")[:60],
        vencimento=_data(f.get("due_date")),
        total=arredondar(_dec(f.get("total_amount")) or Decimal(0)),
        minimo=arredondar(m) if (m := _dec(f.get("minimum_amount"))) is not None else None,
        pago=arredondar(_soma_pagamentos(f)),
        encargos=arredondar(
            sum((_dec(c.get("amount")) or Decimal(0) for c in f.get("finance_charges") or []), Decimal(0))
        ),
        parcelada=bool(f.get("is_installment")),
        pagamentos=sorted(
            (
                PagamentoFatura(data=_data(p.get("payment_date")), valor=arredondar(v))
                for p in f.get("payments") or []
                if (v := _dec(p.get("amount"))) is not None
            ),
            key=lambda p: p.data or date.min,
        ),
    )


def _limite_total(credit: Json) -> Json:
    limites = [x for x in credit.get("limits") or [] if isinstance(x, dict)]
    return next((x for x in limites if x.get("type") == "TOTAL_LIMIT"), limites[0] if limites else {})


@dataclass(frozen=True)
class InstituicaoCatalogo:
    codigo: str  # ``name`` da Belvo — como ela identifica o banco no link
    nome: str  # ``display_name`` — o que a pessoa vê
    logo_url: str | None  # ``logo``
    icone_url: str | None  # ``icon_logo``


def _url_https(valor: Any) -> str | None:
    """Só aceita URL https: nada de http (conteúdo misto) nem javascript:/data:."""
    url = str(valor or "").strip()
    return url[:500] if url.startswith("https://") and len(url) <= 500 else None


def mapear_instituicoes(itens: Iterable[Json]) -> list[InstituicaoCatalogo]:
    """``GET /api/institutions/`` → catálogo. Só ``name``, ``display_name``,
    ``logo`` e ``icon_logo`` interessam; o resto do objeto é descartado."""
    saida = []
    for i in itens:
        codigo = str(i.get("name") or "").strip()
        if not codigo or len(codigo) > 120:
            continue
        # A Belvo manda espaço não separável (\xa0) em alguns nomes.
        nome = " ".join(str(i.get("display_name") or codigo).replace("\xa0", " ").split())[:120]
        saida.append(
            InstituicaoCatalogo(
                codigo=codigo,
                nome=nome or codigo,
                logo_url=_url_https(i.get("logo")),
                icone_url=_url_https(i.get("icon_logo")),
            )
        )
    return saida


def instituicao_da_conta(conta: Json, codigo_link: str | None = None) -> InstituicaoMapeada:
    inst = conta.get("institution") or {}
    nome = inst.get("name") if isinstance(inst, dict) else str(inst)
    return InstituicaoMapeada(codigo=codigo_link or nome or "desconhecida", nome=nome or "Instituição")


# --- taxa de juros (§7.7 — o ponto crítico) ----------------------------------


def normalizar_taxa(valor_bruto: Any, periodicidade: str | None) -> Decimal | None:
    """Converte a taxa crua da instituição em fração ao mês, ou ``None``.

    Decisão provisória até a conferência contra um extrato real (§7.12 passo 5).
    O princípio é **recusar o ambíguo em vez de adivinhar**: ``None`` faz o
    chamador cair na taxa estimada, com badge e log.

    * Mensal (``MONTHLY`` ou sem periodicidade): valor > 1 é percentual
      (6.44 → 0,0644). Fração mensal > 1 seria 100%+ ao mês, que não existe.
      Um percentual < 1 (ex.: 0.95% a.m.) seria lido como 95% e cai no sanity
      check — vira estimada, nunca erro silencioso.
    * Anual (``YEARLY``): ≤ 1 é fração; ≥ 8 é percentual; entre 1 e 8 é
      ambíguo (4.362 pode ser 436% a.a. em fração ou 4,36% a.a. em percentual)
      e é recusado. Crédito de varejo no Brasil não tem taxa anual abaixo de 8%
      nem acima de 800%. Anual vira mensal equivalente: ``(1 + a)^(1/12) − 1``.
    * Sanity check final: mensal fora de 0,1%–20% → ``None``.
    """
    v = _dec(valor_bruto)
    if v is None or v <= 0:
        return None
    if (periodicidade or "").upper() in {"YEARLY", "ANNUAL", "AA"}:
        if v >= ANUAL_PERCENTUAL_A_PARTIR_DE:
            v = v / 100
        elif v > 1:
            return None
        v = ((1 + v).ln() / 12).exp() - 1  # Decimal do começo ao fim, sem float
    elif v > 1:
        v = v / 100
    v = v.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    if not (TAXA_MES_MIN <= v <= TAXA_MES_MAX):
        return None
    return v


def _taxa_do_emprestimo(loan: Json) -> tuple[Any, str | None]:
    """Escolhe o item mais relevante de ``interest_rates[]``: o mensal, se
    houver; senão o primeiro. ``value`` é preferido; ``pre_fixed_rate`` é
    o fallback dentro de ``interest_rate_data``."""
    taxas = [t for t in (loan.get("interest_rates") or []) if isinstance(t, dict)]
    if not taxas:
        return loan.get("interest_rate"), None
    taxas.sort(key=lambda t: 0 if (t.get("type") or "").upper() == "MONTHLY" else 1)
    t = taxas[0]
    bruto = t.get("value")
    if bruto is None:
        bruto = (t.get("interest_rate_data") or {}).get("pre_fixed_rate")
    return bruto, t.get("type")


def _resolver_taxa(
    bruto: Any, periodicidade: str | None, modalidade: str, instituicao: str, categoria: str
) -> tuple[Decimal, str]:
    # Log de diagnóstico da §7.7: instituição, modalidade e valor bruto — nada
    # que identifique a pessoa.
    log.info(
        "taxa_diagnostico instituicao=%s categoria=%s modalidade=%s bruto=%r periodicidade=%s",
        instituicao, categoria, modalidade, bruto, periodicidade,
    )
    taxa = normalizar_taxa(bruto, periodicidade)
    if taxa is None:
        if bruto is not None:
            log.warning(
                "taxa_fora_do_intervalo instituicao=%s modalidade=%s bruto=%r -> ESTIMADA",
                instituicao, modalidade, bruto,
            )
        return taxa_estimada(modalidade), "ESTIMADA"
    return taxa, "INFORMADA"


# --- modalidade --------------------------------------------------------------


def modalidade_de_emprestimo(conta: Json) -> str:
    loan = conta.get("loan_data") or {}
    texto = _upper(conta.get("type"), conta.get("subtype"), conta.get("name"), loan.get("loan_type"))
    if conta.get("category") == "ADVANCE_DEPOSIT_ACCOUNT" or "CHEQUE_ESPECIAL" in texto:
        return "CHEQUE_ESPECIAL"
    if "SEM_CONSIGNACAO" in texto:
        return "CREDITO_PESSOAL"
    if "CONSIGNA" in texto:
        return "CONSIGNADO"
    if "VEICULO" in texto or "AUTOMOTOR" in texto:
        return "FIN_VEICULO"
    if "IMOBILIARI" in texto or "HABITACIONAL" in texto or "IMOVE" in texto:
        return "FIN_IMOVEL"
    if conta.get("category") == "FINANCING_ACCOUNT":
        return "OUTRO"
    return "CREDITO_PESSOAL"


def modalidade_de_cartao(faturas: list[Json]) -> str:
    """CREDIT_CARD → rotativo / parcelado / fatura (§7.7).

    Rotativo: a fatura anterior foi paga abaixo do total, ou a fatura atual
    tem encargo ``LATE_PAYMENT_INTEREST`` (juros remuneratórios por pagamento
    parcial — é o rotativo no Open Finance Brasil).
    """
    if not faturas:
        return "CARTAO_FATURA"
    ordenadas = sorted(faturas, key=lambda b: b.get("due_date") or "")
    atual = ordenadas[-1]
    encargos = atual.get("finance_charges") or []
    if any(
        (c.get("type") == "LATE_PAYMENT_INTEREST") and (_dec(c.get("amount")) or 0) > 0
        for c in encargos
    ):
        return "CARTAO_ROTATIVO"
    if len(ordenadas) > 1:
        anterior = ordenadas[-2]
        total = _dec(anterior.get("total_amount")) or Decimal(0)
        pago = sum((_dec(p.get("amount")) or Decimal(0) for p in anterior.get("payments") or []), Decimal(0))
        if total > 0 and pago < total:
            return "CARTAO_ROTATIVO"
    if atual.get("is_installment"):
        return "CARTAO_PARCELADO"
    return "CARTAO_FATURA"


# --- parcela -----------------------------------------------------------------


def parcela_price(saldo: Decimal, taxa_mes: Decimal, n: int) -> Decimal:
    """PMT da tabela Price: ``PV · i / (1 − (1 + i)^−n)``."""
    if n <= 0:
        return arredondar(saldo)
    if taxa_mes == 0:
        return arredondar(saldo / n)
    fator = (1 + taxa_mes) ** -n
    return arredondar(saldo * taxa_mes / (1 - fator))


def _dias_atraso_emprestimo(loan: Json, hoje: date) -> int:
    vencidas = loan.get("number_of_installments_past_due") or 0
    primeira = _data(loan.get("first_installment_due_date"))
    pagas = loan.get("number_of_installments_paid")
    if not vencidas or primeira is None or pagas is None:
        return 0
    total = primeira.month - 1 + int(pagas)
    try:
        venc = primeira.replace(year=primeira.year + total // 12, month=total % 12 + 1)
    except ValueError:
        venc = primeira.replace(year=primeira.year + total // 12, month=total % 12 + 1, day=28)
    return max((hoje - venc).days, 0)


def _dias_atraso_fatura(fatura: Json, hoje: date) -> int:
    venc = _data(fatura.get("due_date"))
    if venc is None or venc >= hoje:
        return 0
    minimo = _dec(fatura.get("minimum_amount")) or Decimal(0)
    pago = sum((_dec(p.get("amount")) or Decimal(0) for p in fatura.get("payments") or []), Decimal(0))
    return (hoje - venc).days if pago < minimo else 0


# --- contas e dívidas --------------------------------------------------------


def mapear_contas(
    contas: Iterable[Json],
    faturas: Iterable[Json],
    hoje: date,
    codigo_instituicao: str | None = None,
    nome_instituicao: str | None = None,  # display_name do catálogo, para as descrições
) -> ResultadoContas:
    contas = list(contas)
    faturas_por_conta: dict[str, list[Json]] = {}
    for f in faturas:
        conta_f = f.get("account") or {}
        cid = conta_f.get("id") if isinstance(conta_f, dict) else conta_f
        if cid:
            faturas_por_conta.setdefault(cid, []).append(f)

    # §7.7: CHECKING negativo só vira cheque especial se não vier uma
    # ADVANCE_DEPOSIT_ACCOUNT separada — senão a mesma dívida conta duas vezes.
    tem_adiantamento = any(c.get("category") == "ADVANCE_DEPOSIT_ACCOUNT" for c in contas)

    r = ResultadoContas()
    for c in contas:
        categoria = c.get("category") or "UNCATEGORIZED"
        inst = nome_instituicao or instituicao_da_conta(c, codigo_instituicao).nome
        balance = c.get("balance") or {}
        atual = _dec(balance.get("current")) or Decimal(0)

        if categoria in {"INVESTMENT_ACCOUNT", "PENSION_FUND_ACCOUNT"}:
            r.ignoradas += 1  # fora do escopo (§13)
            continue

        if categoria in {"CHECKING_ACCOUNT", "SAVINGS_ACCOUNT"}:
            overdraft = c.get("overdraft") or {}
            usado = _dec(overdraft.get("used")) or Decimal(0)
            if atual < 0 and usado == 0:
                usado = -atual
            disp = _dec(balance.get("available"))
            r.contas.append(
                ContaMapeada(
                    id_externo=c["id"],
                    tipo_externo=(str(c.get("type") or "")[:80] or None),
                    tipo="CORRENTE" if categoria == "CHECKING_ACCOUNT" else "POUPANCA",
                    nome=c.get("name") or ("Conta corrente" if categoria == "CHECKING_ACCOUNT" else "Poupança"),
                    saldo=arredondar(max(atual, Decimal(0))),
                    limite_cheque_especial=arredondar(_dec(overdraft.get("arranged")) or Decimal(0)),
                    usado_cheque_especial=arredondar(usado),
                    numero_final=_final(c.get("number")),
                    disponivel=arredondar(disp) if disp is not None else None,
                    agencia=(str(c.get("agency") or "").strip()[:10] or None),
                    numero_conta=_numero_conta(c),
                )
            )
            if categoria == "CHECKING_ACCOUNT" and usado > 0 and not tem_adiantamento:
                taxa, origem = _resolver_taxa(None, None, "CHEQUE_ESPECIAL", inst, categoria)
                r.dividas.append(
                    DividaMapeada(
                        id_externo=f"{c['id']}:overdraft",
                        modalidade="CHEQUE_ESPECIAL",
                        descricao=f"Cheque especial {inst}",
                        saldo_devedor=arredondar(usado),
                        taxa_juros_mes=taxa,
                        taxa_origem=origem,
                        parcela_minima=arredondar(usado * FRACAO_MINIMO_CHEQUE),
                        parcela_estimada=True,
                        parcelas_restantes=None,
                        dia_vencimento=None,
                        em_atraso_dias=0,
                    )
                )
            continue

        if categoria == "CREDIT_CARD":
            fs = sorted(faturas_por_conta.get(c["id"], []), key=lambda b: b.get("due_date") or "")
            credit = c.get("credit_data") or {}
            limite_total = _limite_total(credit)
            limite = _dec(credit.get("credit_limit")) or _dec(limite_total.get("credit_limit"))
            usado = _dec(limite_total.get("used_amount"))
            if usado is None:
                usado = abs(atual)
            disp = _dec(limite_total.get("available_amount"))
            if disp is None:
                disp = _dec(balance.get("available"))
            if disp is None and limite is not None:
                disp = limite - usado
            r.contas.append(
                ContaMapeada(
                    id_externo=c["id"],
                    tipo_externo=(str(c.get("type") or "")[:80] or None),
                    tipo="CARTAO_CREDITO",
                    nome=c.get("name") or "Cartão de crédito",
                    saldo=arredondar(usado),
                    numero_final=_final(c.get("number")),
                    disponivel=arredondar(disp) if disp is not None else None,
                    limite_credito=arredondar(limite) if limite is not None else None,
                )
            )
            r.faturas.extend(mapear_fatura(f, c["id"]) for f in fs if f.get("id"))

            # Dívida do cartão = o que falta pagar da fatura mais recente. Fatura
            # paga não é dívida — é o caso de quem paga o cartão em dia.
            fatura = fs[-1] if fs else None
            modalidade = modalidade_de_cartao(fs)
            if fatura is not None:
                saldo = (_dec(fatura.get("total_amount")) or Decimal(0)) - _soma_pagamentos(fatura)
            else:
                saldo = abs(atual)
            if saldo <= 0:
                continue
            minimo = (_dec(fatura.get("minimum_amount")) if fatura else None) or _dec(
                credit.get("minimum_payment")
            )
            venc = _data(fatura.get("due_date")) if fatura else None
            if modalidade == "CARTAO_FATURA":
                # Fatura sem rotativo não cobra juros se for paga INTEIRA até o
                # vencimento: taxa 0 e "mínimo" = total. Pagar só o mínimo
                # oficial jogaria o resto no rotativo — o plano não pode sugerir isso.
                taxa, origem = Decimal("0"), "INFORMADA"
                minimo = saldo
            else:
                taxa, origem = _resolver_taxa(credit.get("interest_rate"), "MONTHLY", modalidade, inst, categoria)
            nome_cartao = {
                "CARTAO_ROTATIVO": "Rotativo do cartão",
                "CARTAO_PARCELADO": "Fatura parcelada",
                "CARTAO_FATURA": "Fatura do cartão",
            }[modalidade]
            r.dividas.append(
                DividaMapeada(
                    id_externo=c["id"],
                    modalidade=modalidade,
                    descricao=f"{nome_cartao} {inst}",
                    saldo_devedor=arredondar(saldo),
                    taxa_juros_mes=taxa,
                    taxa_origem=origem,
                    parcela_minima=arredondar(min(minimo, saldo) if minimo is not None else saldo),
                    parcela_estimada=minimo is None,
                    parcelas_restantes=None,
                    dia_vencimento=venc.day if venc else None,
                    em_atraso_dias=_dias_atraso_fatura(fatura, hoje) if fatura else 0,
                )
            )
            continue

        if categoria in {"LOAN_ACCOUNT", "FINANCING_ACCOUNT", "ADVANCE_DEPOSIT_ACCOUNT"}:
            loan = c.get("loan_data") or {}
            modalidade = modalidade_de_emprestimo(c)
            saldo = _dec(loan.get("outstanding_balance"))
            if saldo is None:
                saldo = abs(atual)
            if saldo <= 0:
                continue
            bruto, periodicidade = _taxa_do_emprestimo(loan)
            taxa, origem = _resolver_taxa(bruto, periodicidade, modalidade, inst, categoria)
            restantes = loan.get("number_of_installments_outstanding")
            if restantes is None and loan.get("number_of_installments_total") is not None:
                restantes = int(loan["number_of_installments_total"]) - int(
                    loan.get("number_of_installments_paid") or 0
                )
            # Parcela: monthly_payment (null no Brasil hoje; mantido por
            # compatibilidade) → Price com taxa e prazo → saldo / prazo.
            parcela = _dec(loan.get("monthly_payment"))
            estimada = parcela is None
            if parcela is None and restantes:
                parcela = parcela_price(saldo, taxa, int(restantes))
            if parcela is None and modalidade == "CHEQUE_ESPECIAL":
                parcela = saldo * FRACAO_MINIMO_CHEQUE
            if parcela is None:
                parcela = saldo
            primeira = _data(loan.get("first_installment_due_date"))
            dia = loan.get("payment_day")
            dia = int(dia) if dia else (primeira.day if primeira else None)
            r.contas.append(
                ContaMapeada(
                    id_externo=c["id"],
                    tipo_externo=(str(c.get("type") or "")[:80] or None),
                    tipo={
                        "LOAN_ACCOUNT": "EMPRESTIMO",
                        "FINANCING_ACCOUNT": "FINANCIAMENTO",
                        "ADVANCE_DEPOSIT_ACCOUNT": "ADIANTAMENTO",
                    }[categoria],
                    nome=c.get("name") or _descricao_emprestimo(modalidade, inst),
                    saldo=arredondar(saldo),
                    numero_final=_final(c.get("number")),
                )
            )
            r.dividas.append(
                DividaMapeada(
                    id_externo=c["id"],
                    modalidade=modalidade,
                    descricao=_descricao_emprestimo(modalidade, inst),
                    saldo_devedor=arredondar(saldo),
                    taxa_juros_mes=taxa,
                    taxa_origem=origem,
                    parcela_minima=arredondar(parcela),
                    parcela_estimada=estimada,
                    parcelas_restantes=int(restantes) if restantes is not None else None,
                    dia_vencimento=dia,
                    em_atraso_dias=_dias_atraso_emprestimo(loan, hoje),
                )
            )
            continue

        # INVOICE_FINANCING_ACCOUNT · UNCATEGORIZED → OUTRO, com registro (§7.7)
        log.warning("categoria_para_revisao categoria=%s instituicao=%s", categoria, inst)
        r.contas.append(
            ContaMapeada(
                id_externo=c["id"],
                tipo_externo=(str(c.get("type") or "")[:80] or None),
                tipo="OUTRO",
                nome=c.get("name") or "Outro produto",
                saldo=arredondar(abs(atual)),
                numero_final=_final(c.get("number")),
            )
        )
        if abs(atual) > 0 and (c.get("balance_type") == "LIABILITY" or atual < 0):
            r.dividas.append(
                DividaMapeada(
                    id_externo=c["id"],
                    modalidade="OUTRO",
                    descricao=c.get("name") or f"Compromisso {inst}",
                    saldo_devedor=arredondar(abs(atual)),
                    taxa_juros_mes=taxa_estimada("OUTRO"),
                    taxa_origem="ESTIMADA",
                    parcela_minima=arredondar(abs(atual) * FRACAO_MINIMO_CHEQUE),
                    parcela_estimada=True,
                    parcelas_restantes=None,
                    dia_vencimento=None,
                    em_atraso_dias=0,
                )
            )
        else:
            r.ignoradas += 1
    return r


def _descricao_emprestimo(modalidade: str, inst: str) -> str:
    return {
        "CHEQUE_ESPECIAL": f"Cheque especial {inst}",
        "CREDITO_PESSOAL": f"Empréstimo pessoal {inst}",
        "CONSIGNADO": f"Consignado {inst}",
        "FIN_VEICULO": f"Financiamento de veículo {inst}",
        "FIN_IMOVEL": f"Financiamento imobiliário {inst}",
    }.get(modalidade, f"Financiamento {inst}")


# --- transações --------------------------------------------------------------


def mapear_transacoes(transacoes: Iterable[Json]) -> list[TransacaoMapeada]:
    saida = []
    for t in transacoes:
        tipo = t.get("type")
        valor = _dec(t.get("amount"))
        # ``transacted_at`` (UTC, com hora) é a referência; a data do movimento é
        # a do horário de Brasília — 22h em SP já é o dia seguinte em UTC.
        # ``value_date`` só como reserva quando a instituição não manda a hora.
        transacionado_em = _datahora_utc(t.get("transacted_at"))
        data_mov = horario_brasil(transacionado_em).date() if transacionado_em else _data(t.get("value_date"))
        if tipo not in {"INFLOW", "OUTFLOW"} or valor is None or data_mov is None:
            continue  # sem direção ou sem valor não dá para usar com segurança
        if t.get("status") == "PENDING":
            continue
        valor = abs(valor) if tipo == "INFLOW" else -abs(valor)
        categoria = t.get("category")
        conta = t.get("account")
        categoria_conta = conta.get("category") if isinstance(conta, dict) else None
        merchant = t.get("merchant") or {}
        cartao = t.get("credit_card_data")
        saida.append(
            TransacaoMapeada(
                id_externo=t["id"],
                conta_id_externo=conta.get("id") if isinstance(conta, dict) else conta,
                data_mov=data_mov,
                valor=arredondar(valor),
                descricao=(t.get("description") or "")[:200],
                categoria=categoria,
                essencial=valor < 0 and categoria in CATEGORIAS_ESSENCIAIS,
                pagamento_divida=valor < 0 and categoria == CATEGORIA_PAGAMENTO_DIVIDA,
                # Entrada no cartão ou no empréstimo é pagamento/estorno, não renda.
                conta_como_renda=valor > 0
                and categoria not in CATEGORIAS_ENTRADA_NAO_RENDA
                and categoria_conta not in CATEGORIAS_CONTA_SEM_RENDA,
                estabelecimento=(merchant.get("merchant_name") or None) if isinstance(merchant, dict) else None,
                estabelecimento_site=_url_https(merchant.get("website")) if isinstance(merchant, dict) else None,
                subcategoria=(t.get("subcategory") or None),
                transacionado_em=transacionado_em,
                tipo_operacao=(str(t.get("operation_type") or "").strip()[:60] or None),
                # Já vem só com o final no Brasil; _final garante que nunca passe de 4.
                final_cartao=_final(cartao.get("card_number")) if isinstance(cartao, dict) else None,
                # null quando a compra ainda não entrou numa fatura fechada
                fatura_nome=(str(cartao.get("bill_name") or "").strip()[:60] or None)
                if isinstance(cartao, dict)
                else None,
            )
        )
    return saida


# --- enriquecimento (add-ons, §7.8) -------------------------------------------


def entradas_de_incomes(incomes: Iterable[Json]) -> Decimal | None:
    """Σ ``monthly_median`` dos streams com confiança HIGH/MEDIUM."""
    total, achou = Decimal(0), False
    for inc in incomes:
        for s in inc.get("income_streams") or []:
            if (s.get("confidence") or "").upper() in {"HIGH", "MEDIUM"}:
                v = _dec(s.get("monthly_median"))
                if v is not None:
                    total += v
                    achou = True
    return arredondar(total) if achou else None


def essenciais_recorrentes(recorrentes: Iterable[Json]) -> Decimal | None:
    total, achou = Decimal(0), False
    for r in recorrentes:
        if r.get("category") in CATEGORIAS_ESSENCIAIS:
            v = _dec(r.get("median_transaction_amount"))
            if v is not None:
                total += abs(v)
                achou = True
    return arredondar(total) if achou else None
