"""Entidades persistidas (docs/contexto-produto.md §8.1).

Nomes e valores de enum seguem o esquema Oracle da Fase 5 para que a migração
futura seja mecânica. Toda entidade vinda da Belvo guarda o ``id_externo``
original, para reconciliar por upsert.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.types import DecimalTexto


def agora() -> datetime:
    return datetime.now(timezone.utc)


def _dinheiro(**kw: Any) -> Any:
    return Field(sa_type=DecimalTexto, **kw)


# --- enums -------------------------------------------------------------------


class NivelFamiliaridade(StrEnum):
    INICIANTE = "INICIANTE"
    INTERMEDIARIO = "INTERMEDIARIO"
    AVANCADO = "AVANCADO"


class TipoInstituicao(StrEnum):
    BANCO = "BANCO"
    FINTECH = "FINTECH"
    CARTAO = "CARTAO"
    CREDIARIO = "CREDIARIO"
    OUTRO = "OUTRO"


class StatusConsentimento(StrEnum):
    PENDENTE = "PENDENTE"
    ATIVO = "ATIVO"
    EXPIRADO = "EXPIRADO"
    REVOGADO = "REVOGADO"
    ERRO = "ERRO"


class Recurso(StrEnum):
    OWNERS = "OWNERS"
    ACCOUNTS = "ACCOUNTS"
    TRANSACTIONS = "TRANSACTIONS"
    BILLS = "BILLS"
    INCOMES = "INCOMES"
    RECURRING_EXPENSES = "RECURRING_EXPENSES"


RECURSOS_ESSENCIAIS = (Recurso.ACCOUNTS, Recurso.BILLS, Recurso.TRANSACTIONS)
RECURSOS_OPCIONAIS = (Recurso.OWNERS, Recurso.INCOMES, Recurso.RECURRING_EXPENSES)


class StatusColeta(StrEnum):
    AGUARDANDO = "AGUARDANDO"
    RECEBIDO = "RECEBIDO"
    INDISPONIVEL = "INDISPONIVEL"  # add-on não habilitado / sem dado — degrada sem erro
    ERRO = "ERRO"


class TipoConta(StrEnum):
    CORRENTE = "CORRENTE"
    POUPANCA = "POUPANCA"
    PAGAMENTO = "PAGAMENTO"
    CARTAO_CREDITO = "CARTAO_CREDITO"
    EMPRESTIMO = "EMPRESTIMO"
    FINANCIAMENTO = "FINANCIAMENTO"
    ADIANTAMENTO = "ADIANTAMENTO"  # adiantamento a depositante (cheque especial)
    OUTRO = "OUTRO"


TIPOS_CONTA_DEPOSITO = (TipoConta.CORRENTE, TipoConta.POUPANCA, TipoConta.PAGAMENTO)


class Direcao(StrEnum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"


class Modalidade(StrEnum):
    CARTAO_FATURA = "CARTAO_FATURA"
    CARTAO_ROTATIVO = "CARTAO_ROTATIVO"
    CARTAO_PARCELADO = "CARTAO_PARCELADO"
    CHEQUE_ESPECIAL = "CHEQUE_ESPECIAL"
    CREDITO_PESSOAL = "CREDITO_PESSOAL"
    CONSIGNADO = "CONSIGNADO"
    FIN_VEICULO = "FIN_VEICULO"
    FIN_IMOVEL = "FIN_IMOVEL"
    CREDIARIO = "CREDIARIO"
    OUTRO = "OUTRO"


class Origem(StrEnum):
    OPEN_FINANCE = "OPEN_FINANCE"
    MANUAL = "MANUAL"


class TaxaOrigem(StrEnum):
    INFORMADA = "INFORMADA"
    ESTIMADA = "ESTIMADA"


class MetodoPlano(StrEnum):
    AVALANCHE = "AVALANCHE"
    SNOWBALL = "SNOWBALL"
    EQUILIBRADO = "EQUILIBRADO"


class CapacidadeOrigem(StrEnum):
    INCOMES = "INCOMES"
    TRANSACOES = "TRANSACOES"
    USUARIO = "USUARIO"  # sobrescrita pelo slider (§5.1)


class StatusPlano(StrEnum):
    SIMULADO = "SIMULADO"
    ATIVO = "ATIVO"
    PAUSADO = "PAUSADO"
    CONCLUIDO = "CONCLUIDO"


class TipoEvento(StrEnum):
    ENTRADA_ROTATIVO = "ENTRADA_ROTATIVO"
    ATRASO_IMINENTE = "ATRASO_IMINENTE"
    ATRASO_CONFIRMADO = "ATRASO_CONFIRMADO"
    PICO_CATEGORIA = "PICO_CATEGORIA"
    DESVIO_PLANO = "DESVIO_PLANO"
    DIVIDA_QUITADA = "DIVIDA_QUITADA"
    CHEQUE_ESPECIAL = "CHEQUE_ESPECIAL"
    OPORTUNIDADE_PORTABILIDADE = "OPORTUNIDADE_PORTABILIDADE"


# --- tabelas -----------------------------------------------------------------


class Usuario(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    uuid_externo: str = Field(index=True, unique=True, max_length=64)  # external_id da Belvo, sem PII
    # Login. Nulos só por compatibilidade com bancos criados antes da autenticação.
    email: str | None = Field(default=None, index=True, unique=True, max_length=254)
    senha_hash: str | None = Field(default=None, max_length=200)  # argon2id, nunca a senha
    # Conta de demonstração (Juliana): usa o FixtureProvider em vez da Belvo.
    demo: bool = False
    apelido: str = Field(max_length=60)
    # Necessários só para o token do widget (§7.2). Nunca logados, nunca devolvidos inteiros.
    nome_completo: str | None = Field(default=None, max_length=120)
    cpf: str | None = Field(default=None, max_length=11)
    faixa_renda: str | None = Field(default=None, max_length=30)
    vinculo_renda: str | None = Field(default=None, max_length=30)
    nivel_familiaridade: NivelFamiliaridade | None = None
    ja_desistiu_de_plano: bool | None = None  # alimenta a pré-seleção da §5.4
    # Relógio de demonstração (só na conta demo): meses simulados à frente.
    meses_simulados: int = 0
    criado_em: datetime = Field(default_factory=agora)
    excluido_em: datetime | None = None


class Sessao(SQLModel, table=True):
    """Sessão de login. Guarda só o SHA-256 do token — o token em si vive
    apenas no cookie HttpOnly do navegador."""

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True, ondelete="CASCADE")
    token_hash: str = Field(index=True, unique=True, max_length=64)
    criado_em: datetime = Field(default_factory=agora)
    expira_em: datetime


class Instituicao(SQLModel, table=True):
    """Instituição. Para bancos, a fonte da verdade é o catálogo da Belvo
    (``GET /api/institutions/``): ``codigo_externo`` = ``name`` (ex.:
    ``ofnubank_br_retail``), ``nome`` = ``display_name`` (ex.: "Nubank")."""

    id: int | None = Field(default=None, primary_key=True)
    codigo_externo: str = Field(index=True, unique=True, max_length=120)
    nome: str = Field(max_length=120)
    tipo: TipoInstituicao = TipoInstituicao.BANCO
    logo_url: str | None = Field(default=None, max_length=500)  # ``logo`` (marca com texto)
    icone_url: str | None = Field(default=None, max_length=500)  # ``icon_logo`` (quadrado)
    catalogo_em: datetime | None = None  # última vez que veio do catálogo da Belvo


class Consentimento(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    instituicao_id: int | None = Field(default=None, foreign_key="instituicao.id")
    link_externo: str | None = Field(default=None, index=True, unique=True, max_length=64)
    escopo: str = Field(default="REGISTER,ACCOUNTS,CREDIT_CARDS,CREDIT_OPERATIONS", max_length=200)
    status: StatusConsentimento = StatusConsentimento.PENDENTE
    criado_em: datetime = Field(default_factory=agora)
    concedido_em: datetime | None = None
    expira_em: datetime | None = None
    revogado_em: datetime | None = None
    ultima_sync_em: datetime | None = None
    erro_codigo: str | None = Field(default=None, max_length=80)


class ColetaRecurso(SQLModel, table=True):
    __tablename__ = "coleta_recurso"  # type: ignore[assignment]
    __table_args__ = (UniqueConstraint("consentimento_id", "recurso"),)

    id: int | None = Field(default=None, primary_key=True)
    consentimento_id: int = Field(foreign_key="consentimento.id", index=True, ondelete="CASCADE")
    recurso: Recurso
    status: StatusColeta = StatusColeta.AGUARDANDO
    atualizado_em: datetime = Field(default_factory=agora)


class Conta(SQLModel, table=True):
    """Todo produto que veio do banco: conta, cartão, empréstimo (PFM).

    ``saldo`` por tipo: conta/poupança = saldo atual; cartão = valor usado do
    limite; empréstimo/financiamento/adiantamento = saldo devedor.
    """

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    instituicao_id: int = Field(foreign_key="instituicao.id")
    consentimento_id: int | None = Field(default=None, foreign_key="consentimento.id", ondelete="CASCADE")
    id_externo: str = Field(index=True, unique=True, max_length=64)
    tipo: TipoConta
    nome: str = Field(default="", max_length=120)
    numero_final: str | None = Field(default=None, max_length=8)  # só os últimos dígitos
    tipo_externo: str | None = Field(default=None, max_length=80)  # ``type`` da Belvo
    # Agência e número só de conta de depósito. Cartão nunca guarda número (PCI DSS).
    agencia: str | None = Field(default=None, max_length=10)
    numero_conta: str | None = Field(default=None, max_length=30)
    saldo: Decimal = _dinheiro(default=Decimal("0.00"))
    disponivel: Decimal | None = _dinheiro(default=None, nullable=True)
    limite_credito: Decimal | None = _dinheiro(default=None, nullable=True)
    limite_cheque_especial: Decimal = _dinheiro(default=Decimal("0.00"))
    usado_cheque_especial: Decimal = _dinheiro(default=Decimal("0.00"))
    atualizado_em: datetime = Field(default_factory=agora)


class Fatura(SQLModel, table=True):
    """Fatura de cartão (``/api/bills/`` da Belvo)."""

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    consentimento_id: int | None = Field(default=None, foreign_key="consentimento.id", ondelete="CASCADE")
    conta_id: int = Field(foreign_key="conta.id", index=True, ondelete="CASCADE")
    id_externo: str = Field(index=True, unique=True, max_length=64)
    nome: str = Field(default="", max_length=60)
    vencimento: date | None = Field(default=None, index=True)
    total: Decimal = _dinheiro(default=Decimal("0.00"))
    minimo: Decimal | None = _dinheiro(default=None, nullable=True)
    pago: Decimal = _dinheiro(default=Decimal("0.00"))
    encargos: Decimal = _dinheiro(default=Decimal("0.00"))
    parcelada: bool = False
    # payments[] da Belvo: [{"data": "2026-09-10", "valor": "208.00"}], por data.
    # Valor como texto para manter o Decimal exato dentro do JSON.
    pagamentos: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    atualizado_em: datetime = Field(default_factory=agora)


class Divida(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    instituicao_id: int = Field(foreign_key="instituicao.id")
    consentimento_id: int | None = Field(default=None, foreign_key="consentimento.id", ondelete="CASCADE")
    id_externo: str | None = Field(default=None, index=True, unique=True, max_length=64)
    modalidade: Modalidade
    descricao: str = Field(max_length=120)
    saldo_devedor: Decimal = _dinheiro()
    saldo_inicial: Decimal = _dinheiro()  # primeiro saldo visto — base da barra de progresso
    taxa_juros_mes: Decimal = _dinheiro()
    parcela_minima: Decimal = _dinheiro()
    # No Brasil a Belvo não entrega a parcela de empréstimo (monthly_payment
    # vem null): quando derivada, a interface pede para o usuário conferir.
    parcela_estimada: bool = False
    parcelas_restantes: int | None = None
    dia_vencimento: int | None = Field(default=None, ge=1, le=31)
    em_atraso_dias: int = 0
    negativada: bool = False
    origem: Origem
    taxa_origem: TaxaOrigem = TaxaOrigem.INFORMADA
    quitada_em: date | None = None
    # Conta de origem na Belvo (account.id) e dados do contrato — só o que a
    # instituição entrega em loan_data; cartão e manual ficam sem.
    conta_id_externo: str | None = Field(default=None, max_length=64)
    valor_contratado: Decimal | None = _dinheiro(default=None, nullable=True)
    parcelas_total: int | None = None
    parcelas_pagas: int | None = None
    contrato_inicio: date | None = None
    contrato_fim: date | None = None
    atualizado_em: datetime = Field(default_factory=agora)


class Transacao(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    conta_id: int | None = Field(default=None, foreign_key="conta.id", index=True, ondelete="CASCADE")
    # ``account.id`` da Belvo: a transação fica amarrada à conta de origem mesmo
    # antes de a conta existir aqui (ordem dos webhooks) — e filtra direto.
    conta_id_externo: str | None = Field(default=None, index=True, max_length=64)
    divida_id: int | None = Field(default=None, foreign_key="divida.id", ondelete="SET NULL")
    consentimento_id: int | None = Field(default=None, foreign_key="consentimento.id", ondelete="CASCADE")
    id_externo: str | None = Field(default=None, index=True, unique=True, max_length=64)
    data_mov: date = Field(index=True)  # data em horário de Brasília
    transacionado_em: datetime | None = None  # UTC, como a Belvo manda (transacted_at)
    tipo_operacao: str | None = Field(default=None, max_length=60)  # operation_type, cru
    final_cartao: str | None = Field(default=None, max_length=4)  # credit_card_data.card_number, só o final
    fatura_nome: str | None = Field(default=None, max_length=60)  # credit_card_data.bill_name
    valor: Decimal = _dinheiro()  # negativo = saída
    # Direção explícita: o valor é guardado como texto (Decimal exato), então
    # filtrar entrada/saída pelo sinal em SQL não seria confiável.
    direcao: Direcao = Field(default=Direcao.SAIDA, index=True)
    descricao: str = Field(default="", max_length=200)
    estabelecimento: str | None = Field(default=None, max_length=120)
    estabelecimento_site: str | None = Field(default=None, max_length=200)
    subcategoria: str | None = Field(default=None, max_length=80)
    categoria: str | None = Field(default=None, max_length=80)
    essencial: bool = False
    recorrente: bool = False
    pagamento_divida: bool = False
    entrada_renda: bool = False  # entrada que conta como renda (exclui crédito tomado)
    origem: Origem = Origem.OPEN_FINANCE


class RendaDetectada(SQLModel, table=True):
    """Resumo do add-on INCOMES / RECURRING_EXPENSES (§7.8), por consentimento."""

    __tablename__ = "renda_detectada"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    consentimento_id: int = Field(foreign_key="consentimento.id", unique=True, ondelete="CASCADE")
    entradas_mediana: Decimal | None = _dinheiro(default=None, nullable=True)
    essenciais_recorrentes: Decimal | None = _dinheiro(default=None, nullable=True)
    atualizado_em: datetime = Field(default_factory=agora)


class Plano(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    metodo: MetodoPlano
    capacidade_mensal: Decimal = _dinheiro()
    capacidade_origem: CapacidadeOrigem
    meses_projetados: int
    data_quitacao: date | None = None
    juros_totais: Decimal = _dinheiro()
    economia_vs_minimo: Decimal | None = _dinheiro(default=None, nullable=True)
    divida_inicial: Decimal = _dinheiro()
    status: StatusPlano = StatusPlano.ATIVO
    criado_em: datetime = Field(default_factory=agora)
    mes_referencia: date  # 1º dia do mês em que o plano começou a valer


class PlanoItem(SQLModel, table=True):
    __tablename__ = "plano_item"  # type: ignore[assignment]
    id: int | None = Field(default=None, primary_key=True)
    plano_id: int = Field(foreign_key="plano.id", index=True, ondelete="CASCADE")
    divida_id: int = Field(foreign_key="divida.id", ondelete="CASCADE")
    ordem: int
    valor_mensal: Decimal = _dinheiro()
    mes_quitacao: int | None = None
    juros_pagos: Decimal = _dinheiro()


class Acompanhamento(SQLModel, table=True):
    """Previsto × realizado de cada mês fechado (F4)."""

    id: int | None = Field(default=None, primary_key=True)
    plano_id: int = Field(foreign_key="plano.id", index=True, ondelete="CASCADE")
    mes_referencia: date
    previsto: Decimal = _dinheiro()
    realizado: Decimal = _dinheiro()
    data_quitacao_anterior: date | None = None
    data_quitacao_nova: date | None = None
    criado_em: datetime = Field(default_factory=agora)


class Evento(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("usuario_id", "chave"),)

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    divida_id: int | None = Field(default=None, foreign_key="divida.id", ondelete="SET NULL")
    tipo: TipoEvento
    # Os números que a mensagem vai usar (§8.3). A mensagem nunca é genérica.
    contexto: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    severidade: int = Field(default=1, ge=1, le=3)
    chave: str = Field(max_length=160)  # deduplicação entre sincronizações
    detectado_em: datetime = Field(default_factory=agora)
    notificado_em: datetime | None = None


class Licao(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True, max_length=80)
    titulo: str = Field(max_length=120)
    corpo: str
    tipo_evento: TipoEvento | None = None
    modalidade: Modalidade | None = None
    nivel: NivelFamiliaridade = NivelFamiliaridade.INICIANTE
    ativo: bool = True


class WebhookLog(SQLModel, table=True):
    __tablename__ = "webhook_log"  # type: ignore[assignment]
    id: int | None = Field(default=None, primary_key=True)
    webhook_id: str = Field(index=True, unique=True, max_length=80)  # chave de deduplicação
    webhook_type: str = Field(max_length=40)
    webhook_code: str = Field(max_length=60)
    process_type: str | None = Field(default=None, max_length=40)
    link_id: str | None = Field(default=None, index=True, max_length=64)
    request_id: str | None = Field(default=None, max_length=80)
    external_id: str | None = Field(default=None, max_length=64)
    recebido_em: datetime = Field(default_factory=agora)
    processado_em: datetime | None = None
    erro: str | None = Field(default=None, max_length=500)
