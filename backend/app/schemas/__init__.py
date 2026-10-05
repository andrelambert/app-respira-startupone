"""Contratos de entrada e saída da API (Pydantic v2).

Dinheiro sai sempre como string com duas casas ("2080.00") — o frontend
converte para centavos inteiros sem passar por float.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
)

Dinheiro = Annotated[Decimal, PlainSerializer(lambda v: f"{v:.2f}", return_type=str)]
Taxa = Annotated[Decimal, PlainSerializer(lambda v: f"{v:.6f}", return_type=str)]
TaxaAnual = Annotated[Decimal, PlainSerializer(lambda v: f"{v:.2f}", return_type=str)]
Metodo = Literal["AVALANCHE", "SNOWBALL", "EQUILIBRADO"]


def _cpf_valido(cpf: str) -> str:
    digitos = re.sub(r"\D", "", cpf)
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        raise ValueError("CPF inválido")
    for n in (9, 10):
        soma = sum(int(digitos[i]) * (n + 1 - i) for i in range(n))
        dv = (soma * 10) % 11 % 10
        if dv != int(digitos[n]):
            raise ValueError("CPF inválido")
    return digitos


Cpf = Annotated[str, AfterValidator(_cpf_valido)]
TextoCurto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
Nome = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=120, pattern=r"^[A-Za-zÀ-ÿ' .-]+$"),
]


class Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- sistema ------------------------------------------------------------------


class ConfigOut(BaseModel):
    demo_disponivel: bool  # existe a conta da Juliana para entrar
    belvo_configurada: bool  # há chaves da Belvo no backend/.env
    webhooks: bool


# --- autenticação e usuário ------------------------------------------------------

Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]
# Limite superior protege o argon2 de entradas gigantes.
Senha = Annotated[str, StringConstraints(min_length=8, max_length=128)]


class RegistroEntrada(Entrada):
    email: Email
    senha: Senha
    # Nome completo e CPF são exigidos pelo token da Belvo (identification_info, §7.2).
    nome_completo: Nome
    cpf: Cpf
    ja_desistiu_de_plano: bool | None = None


class LoginEntrada(Entrada):
    email: Email
    senha: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class UsuarioAtualizar(Entrada):
    apelido: TextoCurto | None = None
    ja_desistiu_de_plano: bool | None = None


class UsuarioOut(BaseModel):
    apelido: str
    email: str | None
    nome_completo: str | None
    demo: bool
    tem_identificacao: bool  # nome + CPF já informados (sem devolvê-los)
    cpf_mascarado: str | None
    ja_desistiu_de_plano: bool | None
    meses_simulados: int
    hoje: date


# --- conexão -----------------------------------------------------------------------


class WidgetTokenEntrada(Entrada):
    instituicao: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]{3,80}$")] | None = None


class WidgetTokenOut(BaseModel):
    consentimento_id: int
    widget_url: str


class CallbackEntrada(Entrada):
    link: Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F-]{36}$")]
    institution: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]{3,80}$")]


class SaidaEntrada(Entrada):
    """Parâmetros da callback de saída/evento — só para diagnóstico (§7.4)."""

    codigo: Annotated[str, StringConstraints(max_length=80, pattern=r"^[A-Za-z0-9_.-]*$")] | None = None
    etapa: Annotated[str, StringConstraints(max_length=80, pattern=r"^[A-Za-z0-9_.-]*$")] | None = None
    fatal: bool = True


class RecursoColetaOut(BaseModel):
    recurso: str
    status: str


class ConsentimentoOut(BaseModel):
    id: int
    instituicao: str | None  # display_name do catálogo da Belvo
    instituicao_codigo: str | None
    instituicao_logo: str | None
    status: str
    concedido_em: datetime | None
    expira_em: datetime | None
    dias_para_expirar: int | None
    revogado_em: datetime | None
    ultima_sync_em: datetime | None
    erro_codigo: str | None
    coleta: list[RecursoColetaOut]
    coleta_concluida: bool


class AutorizarFixtureEntrada(Entrada):
    access_token: Annotated[str, StringConstraints(min_length=10, max_length=100)]
    instituicao: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]{3,80}$")]


class AutorizarFixtureOut(BaseModel):
    link: str
    institution: str


# --- webhook (§7.5) ----------------------------------------------------------------


class WebhookEntrada(BaseModel):
    model_config = ConfigDict(extra="allow")

    webhook_id: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    webhook_type: Annotated[str, StringConstraints(max_length=40)]
    webhook_code: Annotated[str, StringConstraints(max_length=60)]
    link_id: Annotated[str, StringConstraints(max_length=64)] | None = None
    process_type: str | None = None
    request_id: str | None = None
    external_id: str | None = None
    data: dict[str, Any] | None = None


# --- dívidas ------------------------------------------------------------------------

Modalidade = Literal[
    "CARTAO_FATURA", "CARTAO_ROTATIVO", "CARTAO_PARCELADO", "CHEQUE_ESPECIAL", "CREDITO_PESSOAL",
    "CONSIGNADO", "FIN_VEICULO", "FIN_IMOVEL", "CREDIARIO", "OUTRO",
]
Valor = Annotated[Decimal, Field(gt=0, le=Decimal("10000000"), decimal_places=2)]


class DividaCriar(Entrada):
    """Cadastro manual assistido (§7.9). Obrigatórios: saldo e parcela."""

    credor: TextoCurto
    modalidade: Modalidade = "CREDIARIO"
    saldo: Valor
    parcela: Valor
    taxa_mes_percentual: Annotated[Decimal, Field(ge=Decimal("0.1"), le=Decimal("20"), decimal_places=4)] | None = None
    dia_vencimento: Annotated[int, Field(ge=1, le=31)] | None = None
    em_atraso_dias: Annotated[int, Field(ge=0, le=3650)] = 0


class DividaAtualizar(Entrada):
    saldo: Valor | None = None
    parcela: Valor | None = None
    taxa_mes_percentual: Annotated[Decimal, Field(ge=Decimal("0.1"), le=Decimal("20"), decimal_places=4)] | None = None
    dia_vencimento: Annotated[int, Field(ge=1, le=31)] | None = None


class DividaOut(BaseModel):
    id: int
    descricao: str
    instituicao: str
    modalidade: str
    origem: str
    saldo: Dinheiro
    saldo_inicial: Dinheiro
    taxa_mes: Taxa
    taxa_anual: TaxaAnual
    taxa_estimada: bool
    juros_mes: Dinheiro
    parcela_minima: Dinheiro
    parcela_estimada: bool
    parcelas_restantes: int | None
    dia_vencimento: int | None
    em_atraso_dias: int
    quitada_em: date | None
    atualizado_em: datetime


# --- Raio-X (F2) ------------------------------------------------------------------------


class ProjecaoOut(BaseModel):
    metodo: Metodo
    capacidade: Dinheiro
    converge: bool
    meses: int
    data_quitacao: date | None
    juros_totais: Dinheiro
    primeira_quitacao_mes: int | None


class CapacidadeOut(BaseModel):
    valor: Dinheiro
    origem: str
    entradas: Dinheiro | None
    essenciais: Dinheiro | None
    meses_historico: int


class RaioXOut(BaseModel):
    coleta_em_andamento: bool
    atualizado_em: datetime | None
    qtd_dividas: int
    divida_total: Dinheiro
    juros_mes_estimado: Dinheiro
    compromisso_minimo_mes: Dinheiro
    pior_taxa_anual: TaxaAnual | None
    qtd_em_atraso: int
    divida_cresce: bool
    crescimento_mensal: Dinheiro
    maior_fonte_juros: DividaOut | None
    maior_fonte_juros_valor: Dinheiro
    comprometimento_renda_pct: TaxaAnual | None
    capacidade: CapacidadeOut
    capacidade_minima: Dinheiro | None
    projecao: ProjecaoOut
    dividas: list[DividaOut]


# --- Plano (F3) --------------------------------------------------------------------------


class ItemPlanoOut(BaseModel):
    divida_id: int
    descricao: str
    ordem: int
    valor_mensal: Dinheiro
    mes_quitacao: int | None
    juros_pagos: Dinheiro


class SoMinimoOut(BaseModel):
    """Pagar só os mínimos de hoje, no mesmo horizonte da estratégia."""

    converge: bool
    meses: int
    juros_no_horizonte: Dinheiro
    saldo_no_horizonte: Dinheiro


class EstrategiaOut(ProjecaoOut):
    itens: list[ItemPlanoOut]
    trajetoria: list[Dinheiro]
    so_minimo: SoMinimoOut | None


class SimulacoesOut(BaseModel):
    capacidade: Dinheiro
    capacidade_calculada: CapacidadeOut
    capacidade_minima: Dinheiro | None
    compromisso_minimo_mes: Dinheiro
    pre_selecionado: Metodo
    motivo_pre_selecao: Literal["PADRAO", "JA_DESISTIU"]
    estrategias: list[EstrategiaOut]


class PlanoAtivar(Entrada):
    metodo: Metodo
    capacidade: Annotated[Decimal, Field(gt=0, le=Decimal("1000000"), decimal_places=2)]


class PagamentoMesOut(BaseModel):
    divida_id: int
    descricao: str
    instituicao: str
    valor: Dinheiro
    dia_vencimento: int | None
    ordem: int
    e_minimo: bool  # só o mínimo (a sobra vai para outra da fila)


class AcompanhamentoOut(BaseModel):
    mes_referencia: date
    previsto: Dinheiro
    realizado: Dinheiro
    data_quitacao_anterior: date | None
    data_quitacao_nova: date | None


class PlanoAtivoOut(BaseModel):
    id: int
    metodo: Metodo
    status: str
    capacidade_mensal: Dinheiro
    capacidade_origem: str
    criado_em: datetime
    meses_projetados: int
    data_quitacao_original: date | None
    juros_totais_original: Dinheiro
    economia_vs_minimo: Dinheiro | None
    divida_inicial: Dinheiro
    divida_atual: Dinheiro
    abatido: Dinheiro
    progresso_pct: TaxaAnual
    projecao_atual: ProjecaoOut
    este_mes: list[PagamentoMesOut]
    cronograma: list[ItemPlanoOut]
    acompanhamentos: list[AcompanhamentoOut]
    hoje: date


# --- Eventos / lições (F4, F5) ------------------------------------------------------------


class EventoOut(BaseModel):
    id: int
    tipo: str
    severidade: int
    divida_id: int | None
    contexto: dict[str, Any]
    detectado_em: datetime
    notificado_em: datetime | None
    licao: str | None


class LicaoOut(BaseModel):
    slug: str
    titulo: str
    corpo: str
    tipo_evento: str | None


class DemoAvancarEntrada(Entrada):
    mes_dificil: bool = False


# --- PFM: contas, faturas e extrato ----------------------------------------------------


class PagamentoFaturaOut(BaseModel):
    data: date | None
    valor: Dinheiro


class FaturaOut(BaseModel):
    id: int
    nome: str
    vencimento: date | None
    total: Dinheiro
    minimo: Dinheiro | None
    pago: Dinheiro
    em_aberto: Dinheiro
    encargos: Dinheiro
    parcelada: bool
    situacao: Literal["PAGA", "EM_ABERTO", "PARCIAL", "ATRASADA"]
    pagamentos: list[PagamentoFaturaOut]


class ContaOut(BaseModel):
    id: int
    consentimento_id: int | None
    instituicao: str
    instituicao_logo: str | None
    tipo: str
    nome: str
    numero_final: str | None
    tipo_externo: str | None
    agencia: str | None
    numero_conta: str | None
    saldo: Dinheiro
    disponivel: Dinheiro | None
    limite_credito: Dinheiro | None
    limite_cheque_especial: Dinheiro
    usado_cheque_especial: Dinheiro
    fatura_atual: FaturaOut | None
    atualizado_em: datetime


class BancoOut(BaseModel):
    consentimento_id: int
    instituicao: str | None
    instituicao_codigo: str | None
    instituicao_logo: str | None
    status: str
    ultima_sync_em: datetime | None
    expira_em: datetime | None
    coleta_concluida: bool
    coleta: list[RecursoColetaOut]
    contas: list[ContaOut]


class VisaoGeralOut(BaseModel):
    bancos: list[BancoOut]
    saldo_em_contas: Dinheiro  # corrente + poupança + pagamento
    faturas_em_aberto: Dinheiro  # o que falta pagar das faturas atuais
    qtd_dividas: int
    hoje: date


class ContaDetalheOut(BaseModel):
    conta: ContaOut
    faturas: list[FaturaOut]


class TransacaoOut(BaseModel):
    id: int
    data: date  # em horário de Brasília
    transacionado_em: datetime | None  # horário de Brasília, com offset -03:00
    tipo_operacao: str | None  # operation_type, como a Belvo manda
    final_cartao: str | None  # 4 últimos dígitos do cartão usado
    fatura: str | None  # credit_card_data.bill_name, como a Belvo manda
    descricao: str
    estabelecimento: str | None
    estabelecimento_site: str | None
    categoria: str | None
    subcategoria: str | None
    valor: Dinheiro  # negativo = saída
    direcao: Literal["ENTRADA", "SAIDA"]


class ExtratoOut(BaseModel):
    itens: list[TransacaoOut]
    pagina: int
    por_pagina: int
    total: int
    paginas: int
    total_entradas: Dinheiro
    total_saidas: Dinheiro
