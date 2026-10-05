"""Microlições — conteúdo estático curado (docs/contexto-produto.md §4 F5).

Selecionadas por regra determinística: evento detectado → lição do mesmo
``tipo_evento``. Não há IA aqui. Linguagem do §11: segunda pessoa, frases
curtas, sem jargão, sem culpa, sem promessa de resultado e sem recomendar
contratar ou deixar de contratar crédito.
"""

from app.models import Licao, Modalidade, NivelFamiliaridade, TipoEvento

LICOES: list[Licao] = [
    Licao(
        slug="rotativo",
        titulo="Por que o rotativo é a dívida mais cara",
        tipo_evento=TipoEvento.ENTRADA_ROTATIVO,
        modalidade=Modalidade.CARTAO_ROTATIVO,
        corpo=(
            "Quando você paga menos que o total da fatura, o resto vira rotativo.\n\n"
            "O rotativo cobra juros sobre juros todo mês. A taxa média no Brasil passa de "
            "400% ao ano — é a mais alta entre as dívidas do dia a dia.\n\n"
            "Por isso, no caminho mais econômico, o rotativo é a primeira dívida da fila: "
            "cada real que sai dele deixa de render juros contra você.\n\n"
            "O que dá para fazer agora: pagar mais que o mínimo na próxima fatura, mesmo "
            "que seja pouco. O seu plano já mostra quanto."
        ),
    ),
    Licao(
        slug="so-o-minimo",
        titulo="Pagar só o mínimo: por que a dívida não diminui",
        tipo_evento=None,
        corpo=(
            "O valor mínimo serve para você não atrasar. Ele não foi feito para quitar.\n\n"
            "Se os juros do mês são maiores que o mínimo, a diferença vai para o saldo. "
            "Você paga todo mês e, mesmo assim, deve mais no mês seguinte.\n\n"
            "O seu Raio-X mostra se isso está acontecendo com você e em quanto. "
            "O plano mostra quanto por mês faz a dívida começar a cair."
        ),
    ),
    Licao(
        slug="cheque-especial",
        titulo="Cheque especial: um limite que custa caro",
        tipo_evento=TipoEvento.CHEQUE_ESPECIAL,
        modalidade=Modalidade.CHEQUE_ESPECIAL,
        corpo=(
            "O cheque especial aparece como saldo disponível, mas é um empréstimo. "
            "Os juros correm todo dia em que a conta fica negativa.\n\n"
            "A lei limita a taxa a 8% ao mês — mesmo assim, isso passa de 150% ao ano.\n\n"
            "O que dá para fazer: tratar o valor usado como uma dívida do plano, com data "
            "para acabar. É isso que o Respira faz quando o colocamos na fila."
        ),
    ),
    Licao(
        slug="vencimento-chegando",
        titulo="A parcela vence em poucos dias e o saldo não cobre",
        tipo_evento=TipoEvento.ATRASO_IMINENTE,
        corpo=(
            "Um atraso costuma custar multa de até 2% e juros de mora, além dos juros "
            "normais. Em cartão, pagar menos que o mínimo pode jogar a fatura no rotativo.\n\n"
            "Se a conta não cobre a parcela inteira, pagar o mínimo no dia ainda evita a "
            "multa. Se nem isso couber, falar com o credor antes do vencimento costuma "
            "abrir mais opções do que depois."
        ),
    ),
    Licao(
        slug="atrasou",
        titulo="Atrasou. E agora?",
        tipo_evento=TipoEvento.ATRASO_CONFIRMADO,
        corpo=(
            "Atrasar acontece. O que importa é o próximo passo.\n\n"
            "Enquanto a parcela fica em aberto, correm multa (até 2%, pelo Código de Defesa "
            "do Consumidor) e juros de mora. Quanto antes for paga, menor a conta.\n\n"
            "O seu plano já considera essa dívida. Se ela entrou agora, a data de saída foi "
            "recalculada — confira na tela inicial."
        ),
    ),
    Licao(
        slug="mes-fora-da-curva",
        titulo="Um mês fora da curva não estraga o plano",
        tipo_evento=TipoEvento.PICO_CATEGORIA,
        corpo=(
            "Todo mês tem um imprevisto. O plano já guarda 10% do que sobra para isso.\n\n"
            "Quando um tipo de gasto sobe muito, o Respira mostra o tamanho da diferença "
            "em reais — não para julgar, mas para você decidir se dá para trazer de volta "
            "ao normal e usar a diferença no plano."
        ),
    ),
    Licao(
        slug="plano-dobra",
        titulo="Seu plano dobra, não quebra",
        tipo_evento=TipoEvento.DESVIO_PLANO,
        corpo=(
            "Quando entra menos dinheiro no plano em um mês, o Respira recalcula a data e "
            "mostra quanto faltou.\n\n"
            "Não existe mês perdido: a nova data já considera o que aconteceu. Se der para "
            "repor um pouco nos meses seguintes, a data volta para perto de onde estava."
        ),
    ),
    Licao(
        slug="divida-quitada",
        titulo="Uma dívida a menos. O que acontece com o dinheiro dela?",
        tipo_evento=TipoEvento.DIVIDA_QUITADA,
        corpo=(
            "A parcela que ia para a dívida quitada não some: no plano, ela passa a ir para "
            "a próxima da fila.\n\n"
            "É por isso que o plano acelera com o tempo — cada dívida que acaba empurra a "
            "seguinte."
        ),
    ),
    Licao(
        slug="avalanche-ou-bola-de-neve",
        titulo="Mais econômico ou vitória rápida?",
        tipo_evento=None,
        nivel=NivelFamiliaridade.INICIANTE,
        corpo=(
            "Existem dois jeitos clássicos de organizar a fila.\n\n"
            "O mais econômico começa pela dívida com a maior taxa. Você paga menos juros "
            "no total, mas a primeira dívida pode demorar a sumir.\n\n"
            "A bola de neve começa pela menor dívida. A primeira vitória vem rápido, mas "
            "custa mais juros no total.\n\n"
            "O equilibrado mistura os dois: quita a menor primeiro e depois segue pela "
            "taxa. O Respira mostra os três com o custo de cada um em reais — a escolha é sua."
        ),
    ),
]
