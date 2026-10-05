"""Taxas de referência por modalidade — usadas quando a instituição não devolve a
taxa (docs/contexto-produto.md §7.7 "Ausência" e §7.9). Toda dívida que usa este arquivo fica com
``taxa_origem = ESTIMADA`` e badge visível na interface.

ARQUIVO ÚNICO de taxas estimadas. Não espalhe taxa hardcoded pelo código.

Fonte: Banco Central do Brasil — "Taxas de juros de operações de crédito",
pessoa física, médias mensais por modalidade
(https://www.bcb.gov.br/estatisticas/txjuros). Os valores de rotativo, parcelado,
cheque especial, crédito pessoal e crediário são os mesmos da fixture validada
na Fase 5 (docs/contexto-produto.md §2: rotativo a 436,2% a.a., BCB). Os demais são aproximações
da mesma série.

⚠️ Antes da entrega, conferir cada valor contra a publicação mais recente do BCB
e atualizar a data abaixo.
"""

from decimal import Decimal

FONTE = "Banco Central do Brasil — taxas médias de juros, pessoa física"
REFERENCIA = "Fase 5 (2025); conferir antes da entrega"

# taxa ao mês, em fração (0.1502 = 15,02% a.m.)
TAXA_MES_POR_MODALIDADE: dict[str, Decimal] = {
    # Fatura sem rotativo não usa esta tabela: paga inteira até o vencimento,
    # não tem juros (mapping.py). O valor fica só como salvaguarda.
    "CARTAO_FATURA": Decimal("0.1502"),
    "CARTAO_ROTATIVO": Decimal("0.1502"),  # ≈ 436% a.a.
    "CARTAO_PARCELADO": Decimal("0.0905"),  # ≈ 183% a.a.
    "CHEQUE_ESPECIAL": Decimal("0.0749"),  # teto legal de 8% a.m. (Res. CMN 4.765/2019)
    "CREDITO_PESSOAL": Decimal("0.0644"),
    "CONSIGNADO": Decimal("0.0185"),
    "FIN_VEICULO": Decimal("0.0200"),
    "FIN_IMOVEL": Decimal("0.0095"),
    "CREDIARIO": Decimal("0.0350"),
    "OUTRO": Decimal("0.0644"),
}


def taxa_estimada(modalidade: str) -> Decimal:
    return TAXA_MES_POR_MODALIDADE.get(modalidade, TAXA_MES_POR_MODALIDADE["OUTRO"])
