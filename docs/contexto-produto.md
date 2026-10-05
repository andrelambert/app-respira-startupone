# Respira — contexto do produto (especificação para o agente)

> **O que é este arquivo.** A especificação de produto do Respira: **o que** o produto é, **por que**
> cada decisão foi tomada e **como** as regras de negócio funcionam. Foi escrita como briefing para o
> agente de IA (Claude Code) que construiu o protótipo da Fase 6 e continua sendo carregada por ele
> em toda sessão, via [`CLAUDE.md`](../CLAUDE.md). As decisões vêm da Fase 5 do Enterprise
> Challenge / Startup One (Engenharia de Software, FIAP).
>
> **Para visão geral, arquitetura, como rodar e limitações, leia o [README](../README.md).**
>
> As referências `§N` nos comentários do código apontam para as seções deste arquivo — por isso a
> numeração das seções não deve mudar.
>
> **Mudou desde que este texto foi escrito** (o código é a fonte de verdade nesses pontos):
>
> - Não existe `APP_PROVIDER`. O provedor é **por usuário**: a conta demo (Juliana) usa o
>   `FixtureProvider`; toda conta registrada usa a Belvo real (`backend/app/services/contexto.py`).
> - Há login real (e-mail + senha, cookie HttpOnly e sessão no banco), não usuário único — §16.1.
> - Sem túnel público, a coleta é por **polling** (`BELVO_WEBHOOKS_ENABLED=false`) — §16.3.
>
> A integração com a Belvo (Open Finance Brasil) está detalhada na
> [seção 7](#7-integração-belvo-open-finance-brasil--ofda). **Confira sempre o schema atual na
> documentação da Belvo antes de implementar — e não invente campo que não exista.**

---

## Índice

1. [O produto em uma frase](#1-o-produto-em-uma-frase)
2. [O problema e a persona](#2-o-problema-e-a-persona)
3. [Princípios de produto (critério de corte)](#3-princípios-de-produto-critério-de-corte)
4. [Escopo do MVP — F1 a F5](#4-escopo-do-mvp--f1-a-f5)
5. [Motor de plano de quitação — a regra de negócio central](#5-motor-de-plano-de-quitação--a-regra-de-negócio-central)
6. [Arquitetura técnica e stack](#6-arquitetura-técnica-e-stack)
7. [Integração Belvo (Open Finance Brasil / OFDA)](#7-integração-belvo-open-finance-brasil--ofda)
8. [Modelo de dados](#8-modelo-de-dados)
9. [Telas, rotas e estados](#9-telas-rotas-e-estados)
10. [Design system](#10-design-system)
11. [Regras de escrita (copy)](#11-regras-de-escrita-copy)
12. [Segurança e privacidade — requisitos não negociáveis](#12-segurança-e-privacidade--requisitos-não-negociáveis)
13. [Fora do escopo](#13-fora-do-escopo)
14. [Critérios de aceite e fixtures de teste](#14-critérios-de-aceite-e-fixtures-de-teste)
15. [Ordem de implementação sugerida](#15-ordem-de-implementação-sugerida)
16. [Decisões ainda em aberto](#16-decisões-ainda-em-aberto)

---

## 1. O produto em uma frase

> **Respira é um aplicativo que lê todas as suas dívidas via Open Finance, calcula quando você fica livre delas e te ajuda a chegar lá.**

A unidade de valor do produto é **uma data**, não um gráfico. Todo concorrente responde
"para onde foi meu dinheiro". O Respira responde **"quando isso acaba"**. Guarde esta frase:
sempre que houver dúvida sobre o que colocar em uma tela, a pergunta é "isso aproxima o
usuário de ver e sustentar a data de quitação?".

Três capacidades sustentam a promessa:

| Capacidade | O que significa na prática |
|---|---|
| **Consolidação sem esforço** | O usuário autoriza uma vez via Open Finance. Contas, cartões, faturas, limites, empréstimos e parcelamentos entram automaticamente. Zero digitação para o valor inicial. |
| **Plano de quitação inteligente** | O motor calcula quanto sobra por mês a partir do **histórico observado** (não de um orçamento declarado) e distribui esse valor entre as dívidas. A saída é uma data, uma economia em reais e ações concretas para o mês corrente. |
| **Orientação no momento certo** | O sistema observa eventos nos dados (entrada no rotativo, atraso iminente, pico de categoria) e dispara uma explicação curta ancorada no **número do próprio usuário**. |

---

## 2. O problema e a persona

### O problema central

**Endividamento crônico e ausência de um plano viável de saída.** No Brasil: 83,9 milhões de
inadimplentes (Serasa), 82,0% das famílias endividadas (PEIC/CNC), 28,85% da renda média
comprometida, 85,3% das dívidas concentradas no cartão de crédito, juros do rotativo a
436,2% ao ano (BCB).

O problema não é falta de informação — é **ausência de horizonte**. A pessoa sabe que deve.
Ela não sabe *quanto no total*, *o que pagar primeiro* e *quando isso acaba*.

### Persona principal — Juliana Ramos, 34 anos

> *"Eu sei que devo, só não sei quando isso acaba."*

Persona fictícia, ancorada em dados secundários públicos. Auxiliar administrativa em
Guarulhos (SP), R$ 3.100 líquidos CLT, mora com companheiro (autônomo) e filha de 8 anos.
Renda familiar ~R$ 4.800. Android intermediário, **plano de dados limitado**, usa Pix
diariamente, tem apps de dois bancos e do Serasa instalados.

**A situação dela é a fixture de teste do produto** — use estes números em todo o seed:

| Compromisso | Modalidade | Saldo | Taxa a.m. | Mínimo | Vencimento |
|---|---|---:|---:|---:|---:|
| Rotativo do cartão Banco A | `CARTAO_ROTATIVO` | R$ 2.080,00 | 15,02% | R$ 208,00 | dia 12 |
| Fatura parcelada Banco B | `CARTAO_PARCELADO` | R$ 1.100,00 | 9,05% | R$ 110,00 | dia 20 |
| Empréstimo pessoal (8 meses) | `CREDITO_PESSOAL` | R$ 4.200,00 | 6,44% | R$ 260,00 | dia 5 |
| Cheque especial | `CHEQUE_ESPECIAL` | R$ 500,00 | 7,49% | R$ 50,00 | dia 1 |
| Carnê da Loja D (12 dias em atraso) | `CREDIARIO` | R$ 380,00 | 3,50% | R$ 95,00 | dia 15 |
| **Total** | | **R$ 8.260,00** | | **R$ 723,00** | |

**O número que importa:** os juros do mês somam **R$ 733** e os mínimos somam **R$ 723**.
Pagando exatamente o mínimo de tudo, **a dívida da Juliana cresce**. Essa é a armadilha que
nenhum app de controle de gastos mostra, e é o que o Raio-X precisa tornar visível na
primeira tela. R$ 312 desses juros vêm só do rotativo.

### As dores, na ordem em que ela mesma as descreveria

1. "Não sei quanto eu realmente devo." — informação espalhada em cinco apps e dois carnês de papel.
2. "Não sei o que pagar primeiro." — quando sobra dinheiro, ela paga **quem está cobrando mais**, não a dívida **mais cara**.
3. **"Não sei quando isso acaba."** — a dor central. A ausência de horizonte transforma dívida em desesperança.
4. "Todo mês tem um imprevisto." — qualquer plano rígido quebra no primeiro mês.
5. "Tenho vergonha de pedir ajuda." — não vai à agência, não liga para o banco, não conta para a família.

### Jobs to be done

- *Quando eu recebo o salário*, quero saber quanto posso destinar às dívidas sem faltar o essencial.
- *Quando sobra um dinheiro extra*, quero saber em qual dívida colocar para pagar menos juros no total.
- *Quando eu olho meu plano*, quero ver uma data de término, para saber que existe um fim.
- *Quando eu erro um mês*, quero que o app recalcule **sem me punir**, para não desistir.

### Critérios de adoção / motivo de abandono

Ela adota se: a conexão levar menos de 5 minutos e explicar em português simples; a primeira
tela útil aparecer **sem digitar nada**; e o app disser, na primeira sessão, "seguindo este
plano, você sai das dívidas em X meses".

Ela abandona por: categorização manual, jargão financeiro, cobrança antes de entregar valor,
ou um plano que ela sabe que não cabe no bolso dela.

### O que a validação (n=10) ensinou e que vira regra de interface

A pesquisa primária teve **alcance limitado e não alcançou o público-alvo** (amostra de renda
média, majoritariamente adimplente). Ainda assim, cinco achados viraram decisão de produto —
**implemente todos**:

| Achado | Consequência para a interface |
|---|---|
| **9 de 10** apontaram *"o app não poder movimentar meu dinheiro"* como fator decisivo de confiança (muito à frente de saber quais dados são lidos: 4; ou poder cancelar: 3) | A frase **"Este app não movimenta o seu dinheiro"** é o **elemento mais visível** da tela de consentimento — não uma linha nos termos. |
| **Metade da amostra não sabe o que é Open Finance** | A tela **explica o mecanismo**, não invoca o nome. Nada de "conecte via Open Finance" como chamada principal. |
| **8 de 10** pedem consolidação ("quanto eu devo no total") | A tela de diagnóstico **abre pela consolidação** — total + lista de compromissos — com a data de quitação **imediatamente abaixo, na mesma tela**. A promessa não muda; muda a ordem de leitura. |
| Motivo nº 1 de abandono de apps financeiros: **"esqueci de usar"** (todos os 6 que já usaram e pararam citaram isso), mas a opção de aviso mais votada foi **"só quando eu abrir o app"** (4 de 10) | **Regra de parcimônia:** só existe notificação quando há **uma ação concreta a tomar e um valor em reais em jogo**. Sem resumo semanal, sem lembrete de engajamento, sem notificação que não caiba em uma frase com um número dentro. |
| **8 de 10** pagam a dívida que está cobrando mais, não a mais cara | O produto precisa **traduzir a escolha em reais e meses** — é isso que o usuário não consegue fazer sozinho. |
| **H5 não sustentada:** diante do custo explicitado, apenas 1 de 10 preferiu quitar a dívida menor | O padrão pré-selecionado passa a ser **Avalanche**, com exceção adaptativa (ver §5). |
| **7 de 10** pagariam no máximo R$ 10/mês ou nada; nenhum passaria de R$ 20 | Camada gratuita permanente. Nenhum paywall no protótipo. |
| **9 de 10** buscam ajuda financeira com família/amigos; **nenhum** recorre a banco ou Serasa | Indicação pessoal é o canal de aquisição mais provável — se houver tela de compartilhamento, é disso que ela trata. |

---

## 3. Princípios de produto (critério de corte)

Cinco princípios governam escopo e interface. **Uma funcionalidade que viola um princípio não
entra**, por mais desejável que pareça.

1. **Zero digitação para o valor inicial.** Tudo que puder ser lido, é lido. O usuário só digita o que o Open Finance não entrega.
2. **Uma resposta, não um painel.** Toda tela responde a uma pergunta específica. A tela inicial responde "quando isso acaba".
3. **Sempre há um próximo passo.** Nenhum diagnóstico é entregue sem uma ação recomendada ao lado.
4. **O plano dobra, não quebra.** Um mês ruim gera recálculo e ajuste, **nunca uma mensagem de falha**. A desistência é o principal inimigo do produto.
5. **Linguagem de gente.** "Você está pagando R$ 312 de juros por mês só no rotativo" em vez de "encargos rotativos incidentes sobre saldo devedor".

---

## 4. Escopo do MVP — F1 a F5

### F1 — Conexão de contas via Open Finance

Autorização de compartilhamento junto às instituições do usuário, intermediada pela Belvo.
**O "como" está todo na [seção 7](#7-integração-belvo-open-finance-brasil--ofda)** — esta seção
é o "o quê".

- **Escopo via Open Finance:** contas de depósito, cartões de crédito (faturas, limites, situação de rotativo), empréstimos e financiamentos.
- **Exceção deliberada ao princípio de zero digitação:** compromissos que **não trafegam pelo Open Finance** — carnês de loja, crediário, dívidas com pessoas conhecidas — entram por **cadastro manual assistido**. Isso se justifica porque sem eles o total fica errado, e um total errado invalida o plano inteiro. (4 de 10 respondentes têm compromissos desse tipo.)
- **Onboarding guiado** com explicação em linguagem simples do que é lido, do que não é acessado, e revogação disponível em um toque a qualquer momento.
- **Reconexão automática quando o consentimento expira**, com aviso antecipado. É ponto de falha silenciosa em produtos concorrentes — trate expiração como estado de primeira classe (ver §9).

### F2 — Raio-X da dívida

A primeira tela útil, e o momento de verdade do produto.

Abre pela **consolidação** (total + lista de compromissos), com a **data de quitação projetada
logo abaixo, na mesma tela**. Consolida em uma visão única:

- dívida total
- número de compromissos
- custo mensal em juros
- comprometimento de renda
- classificação de cada dívida **por custo efetivo** (taxa anualizada, não por saldo)

E traduz tudo em uma frase que o usuário entende:

> "Você deve **R$ 8.260** em **5 compromissos** e paga **R$ 733 por mês só em juros**;
> **R$ 312** disso vem do rotativo do cartão."

**Obrigatório:** quando os juros mensais forem maiores que a soma dos mínimos, o Raio-X
precisa dizer isso explicitamente — *"pagando só o mínimo, sua dívida cresce R$ 10 por mês"*.
É o insight mais valioso do produto e ele não pode ficar implícito num gráfico.

### F3 — Plano de quitação personalizado

O núcleo do produto. Ver a regra completa na [seção 5](#5-motor-de-plano-de-quitação--a-regra-de-negócio-central).

Três estratégias aparecem **lado a lado**, com a diferença traduzida **em reais e em meses**:

| Estratégia | Lógica | Vantagem | Custo |
|---|---|---|---|
| **Avalanche** | Maior taxa efetiva primeiro | Menor custo total em juros | Primeira vitória pode demorar meses |
| **Bola de neve** (snowball) | Menor saldo primeiro | Vitórias rápidas, sustenta a motivação | Custa mais em juros no total |
| **Equilibrado** | Quita a menor dívida primeiro para gerar tração, depois migra para ordem de custo | Aderência com perda pequena de eficiência | Ligeiramente acima do ótimo |

A comparação precisa ser lida como uma frase, não como uma tabela de specs:

> "Pelo caminho equilibrado você fica livre em **19 meses** e paga **R$ 316 a mais** de juros do
> que pelo caminho mais econômico, que leva **18 meses** — só que nele a primeira dívida
> some no **10º mês**, e no equilibrado ela some já no **2º**."

O plano gerado inclui **data de quitação**, **valor mensal sugerido por dívida** e **economia
projetada em juros**.

**Slider de capacidade:** o usuário pode ajustar o valor mensal e **ver a data se mover em
tempo real**. Isso torna tangível a relação entre esforço e resultado e é requisito, não enfeite.

### F4 — Acompanhamento e alertas de desvio

Um plano sem acompanhamento é uma planilha. A validação mostrou que esta funcionalidade
não é conveniência, é **condição de sobrevivência**.

- Mensalmente o sistema compara **previsto × realizado** a partir dos dados que continuam chegando, atualiza a data de quitação e sinaliza desvios **antes que virem atraso**.
- Exemplo de alerta no tom certo: *"A fatura do Banco A fecha em 3 dias e faltam R$ 180 no seu plano; se pagar o mínimo, entra no rotativo e sua data de saída atrasa 2 meses."*
- **Marcos de progresso são celebrados explicitamente.** Cada dívida quitada é um **evento** no produto — é o que sustenta a adesão.
- **Regra de parcimônia** (ver §2): notificação só existe com ação concreta + valor em reais.

### F5 — Microlições contextuais e copiloto financeiro · *evolução planejada*

Depende de IA generativa e **não foi implementada na Fase 5**, por decisão de custo (os
serviços de IA da OCI são muito limitados no plano gratuito).

Para a Fase 6: **implemente a estrutura, não o modelo.** Ou seja:

- A tabela/entidade de lições existe, com `tipo_evento` e `modalidade` como chaves de casamento.
- As microlições do protótipo são **conteúdo estático curado**, selecionado por regra determinística (evento detectado → lição correspondente), não por embedding.
- O copiloto em linguagem natural fica **visível porém desabilitado**, com rótulo honesto de "em breve", ou atrás de uma feature flag `VITE_FEATURE_COPILOTO=false`.
- **Não simule respostas de IA fingindo que são reais.** Se houver demo, rotule como demonstração.

---

## 5. Motor de plano de quitação — a regra de negócio central

Este algoritmo já existe, validado, como pacote PL/SQL (`PKG_PLANO`) na Fase 5. **Porte-o
fielmente.** A implementação de referência está em
`Fase 5 .../Oracle/sql/04_motor_plano.sql` — leia se tiver acesso.

### 5.1 Capacidade de pagamento mensal

Não pergunte ao usuário quanto ele pode pagar — ele superestima. Calcule do histórico:

```
mediana_entradas    = mediana, por mês, da soma das transações com valor > 0
                      (últimos 6 meses)
mediana_essenciais  = mediana, por mês, da soma do |valor| das transações com
                      valor < 0 E essencial = true (últimos 6 meses)

capacidade = max( round( (mediana_entradas - mediana_essenciais) * 0.90, 2), 0 )
```

**O fator 0,90 é uma reserva de 10% para imprevistos e é obrigatório.** Um plano que consome
tudo quebra no primeiro mês atípico, e plano quebrado é plano abandonado (dor nº 4 da
persona). O usuário pode sobrescrever a capacidade pelo slider; o valor calculado é o padrão.

### 5.2 Ordenação das dívidas por estratégia

| Método | Ordenação |
|---|---|
| `AVALANCHE` | `taxa_juros_mes DESC`, desempate por `saldo_devedor ASC` |
| `SNOWBALL` | `saldo_devedor ASC`, desempate por `taxa_juros_mes DESC` |
| `EQUILIBRADO` | a **menor dívida** vai para a posição 0; **todas as demais** seguem a ordem do avalanche (`taxa DESC`) |

### 5.3 Simulação mês a mês

Pseudocódigo normativo. Rode em laço até zerar tudo, com trava de segurança de **600 meses**.

```
juros_totais = 0
primeira_quitacao_mes = null
mes = 0

repita:
  mes += 1
  sobra = capacidade

  # 1) Juros do mês + pagamento mínimo de cada dívida ainda aberta,
  #    percorrendo NA ORDEM DA ESTRATÉGIA
  para cada divida d (na ordem) com d.saldo > 0:
      juros    = round(d.saldo * d.taxa_mes, 2)
      d.saldo += juros
      juros_totais += juros

      pgto     = min(d.minima, d.saldo, sobra)
      d.saldo -= pgto
      sobra   -= pgto

  # 2) A sobra vai INTEGRALMENTE para a dívida da vez, na ordem do método
  para cada divida d (na ordem):
      se sobra <= 0: pare
      se d.saldo > 0:
          pgto     = min(sobra, d.saldo)
          d.saldo -= pgto
          sobra   -= pgto
          se d.saldo <= 0 e primeira_quitacao_mes é null:
              primeira_quitacao_mes = mes

  # 3) Encerrou?
  restantes = contagem de dívidas com saldo > 0.01
  até restantes == 0 ou mes >= 600

data_quitacao = primeiro dia do mês atual + `mes` meses
```

Detalhes que importam e que são fáceis de errar:

- Os juros incidem **antes** do pagamento, no mesmo mês.
- `round(..., 2)` em cada incidência de juros — não acumule em float sem arredondar. **Use decimal/centavos inteiros, nunca `number` do JS para dinheiro.**
- `primeira_quitacao_mes` só é marcado no **passo 2** (quitação pela sobra), não quando o mínimo zera uma dívida. É assim na referência; mantenha.
- Se não houver dívidas ou a capacidade for ≤ 0, retorne `meses = 0`, `juros = 0`, `data = null`.

### 5.4 Saída esperada e qual estratégia vem pré-selecionada

A saída de cada simulação é: `metodo`, `meses`, `juros_totais`, `data_quitacao`,
`primeira_quitacao_mes`, e o cronograma por dívida (`ordem`, `valor_mensal`, `mes_quitacao`,
`juros_pagos`).

**Pré-seleção — regra adaptativa:**

- Padrão: **Avalanche** (a validação não sustentou a hipótese de que o usuário prefere a vitória rápida ao custo menor).
- **Exceção:** quem indicar no onboarding que **já tentou e desistiu de um plano de pagamento antes** recebe o **Equilibrado** pré-selecionado — para esse perfil, a primeira vitória rápida é o que sustenta a adesão.
- A escolha final é **sempre do usuário**, e as três permanecem visíveis com o custo de cada uma.
- Esta decisão é **provisória** (tomada sobre 10 respostas de um público que não é o alvo). Deixe-a configurável em um único lugar no código, com comentário apontando para esta seção.

---

## 6. Arquitetura técnica e stack

### 6.1 Decisão: por que existe um backend

O protótipo da Fase 6 usa **dados reais da Belvo desde o início** (não mock). Isso força duas
coisas:

1. **As credenciais da Belvo nunca podem estar no navegador.** Qualquer chave embarcada em
   bundle de frontend é uma chave vazada — ela fica legível no DevTools de qualquer usuário.
   Portanto, **toda chamada à Belvo sai de um backend**, nunca do React.
2. **Persistência local.** Os dados coletados precisam sobreviver ao refresh da página e
   alimentar o histórico de 6 meses que o motor usa. `localStorage` não serve para isso.

Logo: **FastAPI + SQLite**, local, no mesmo repositório. Oracle Autonomous Database fica para
uma implementação futura — ver §6.4.

### 6.2 Stack prescrita

**Frontend**

| Item | Escolha | Observação |
|---|---|---|
| Build | **Vite** | `npm create vite@latest -- --template react-ts` |
| Framework | **React 18 + TypeScript** (strict) | |
| Estilo | **Tailwind CSS** | tokens em `tailwind.config.ts`, ver §10 |
| Rotas | **React Router** | |
| Estado de servidor | **TanStack Query** | cache, refetch, estados de loading/erro de graça |
| Estado de UI | **Zustand** ou Context | só para o que não vem do servidor |
| Formulários | **React Hook Form + Zod** | Zod também valida as respostas da API |
| Gráficos | **Recharts** | ver §10 sobre o que cada visual precisa comunicar |
| Dinheiro | **dinero.js** ou inteiros em centavos | **nunca** float para valores monetários |
| Datas | **date-fns** com locale `pt-BR` | |
| Testes | **Vitest** + Testing Library | obrigatório para o motor de plano |

**Backend**

| Item | Escolha | Observação |
|---|---|---|
| Framework | **FastAPI** | tipos + OpenAPI automático |
| ORM | **SQLModel** (ou SQLAlchemy 2.x) | |
| Banco | **SQLite** (arquivo `respira.db`) | migrações com Alembic |
| Validação | **Pydantic v2** | |
| HTTP client | **httpx** | para a Belvo |
| Testes | **pytest** | o motor de plano tem suíte própria |
| Config | **pydantic-settings** lendo `.env` | ver §12 |

**Onde mora o motor de plano:** no **backend**, em Python puro
(`backend/app/domain/planner.py`), sem dependência de framework, com testes unitários
próprios. O frontend só consome o resultado. Motivos: é a regra de negócio, precisa ser
testável isoladamente, e é o código que amanhã será comparado com o `PKG_PLANO` do Oracle.

### 6.3 Estrutura de pastas

```
respira/
├── README.md                    ← este arquivo (ou CLAUDE.md)
├── .env.example                 ← nunca commitar o .env real
├── docker-compose.yml           ← opcional, para subir tudo com um comando
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py              ← FastAPI app, CORS, routers
│   │   ├── config.py            ← pydantic-settings
│   │   ├── db.py                ← engine + session
│   │   ├── models/              ← SQLModel: usuario, divida, conta, transacao,
│   │   │                          plano, plano_item, evento, licao, consentimento
│   │   ├── schemas/             ← Pydantic de entrada/saída da API
│   │   ├── domain/
│   │   │   ├── planner.py       ← MOTOR DE PLANO (§5) — Python puro, sem I/O
│   │   │   ├── xray.py          ← agregações do Raio-X (§4 F2)
│   │   │   └── events.py        ← detecção de eventos (§8.3)
│   │   ├── providers/
│   │   │   ├── base.py          ← AggregationProvider (interface, §7.11)
│   │   │   ├── belvo.py         ← cliente HTTP da Belvo (token, GETs, DELETE link)
│   │   │   ├── mapping.py       ← Belvo → domínio Respira (§7.7) — o arquivo
│   │   │   │                      mais importante da integração; todo o
│   │   │   │                      acoplamento com a Belvo mora aqui
│   │   │   └── fixture.py       ← respostas no formato Belvo, p/ dev e testes
│   │   ├── repositories/        ← acesso a dados — ÚNICA camada que conhece SQL
│   │   └── routers/
│   │       ├── belvo_webhook.py ← POST /webhooks/belvo (§7.5)
│   │       └── ...              ← demais endpoints HTTP (§8.4)
│   └── tests/
│       ├── test_planner.py      ← fixtures da §14
│       └── test_mapping.py      ← Belvo → domínio, incluindo a taxa de juros
└── frontend/
    ├── package.json
    ├── tailwind.config.ts
    └── src/
        ├── main.tsx
        ├── routes/              ← uma pasta por tela da §9
        │                           (inclui /conectar/sucesso, /saida, /evento — §7.4)
        ├── components/
        │   ├── ui/              ← primitivos: Button, Card, Sheet, Money, ...
        │   └── respira/         ← DebtCard, StrategyCompare, PayoffDate, ...
        ├── lib/
        │   ├── api.ts           ← cliente tipado do backend
        │   ├── money.ts         ← formatação BRL e aritmética em centavos
        │   └── copy.ts          ← strings centralizadas (pt-BR) — ver §11
        └── hooks/
```

### 6.4 Portabilidade para o Oracle (não implementar agora, só não atrapalhar)

A Fase 5 implementou e validou no **Oracle Autonomous AI Database 26ai**: o esquema
relacional, o motor em PL/SQL, a priorização por custo efetivo, JSON Relational Duality Views e
a integração Python. Isso volta numa fase futura.

Para que a troca seja barata depois, **só a camada `repositories/` pode conhecer o banco**.
Nenhum `SELECT`, nenhum `session.query()`, nenhum nome de tabela fora dela. Routers falam
com repositories; domain não fala com banco nenhum.

### 6.5 Mobile-first, de verdade

A persona usa **Android intermediário com plano de dados limitado**. Isso é requisito técnico:

- Desenhe para **360–430 px** de largura primeiro; desktop é adaptação, não o contrário.
- Alvos de toque de no mínimo **44×44 px**.
- Orçamento de bundle inicial: **< 250 KB gzipped**. Code splitting por rota.
- Sem fontes pesadas, sem bibliotecas de animação grandes, sem imagens não otimizadas.
- Toda tela precisa de estado de **carregando**, **vazio**, **erro** e **offline**.

---

## 7. Integração Belvo (Open Finance Brasil / OFDA)

> **Fonte:** [guia do produto](https://developers.belvo.com/products/aggregation_brazil/aggregation-brazil-introduction) ·
> [documentação da API](https://developers.belvo.com/apis/belvoopenapispec) ·
> [guia do widget](https://developers.belvo.com/products/aggregation_brazil/ofda-widget-introduction) ·
> [configuração do widget](https://developers.belvo.com/products/aggregation_brazil/ofda-widget-startup-configuration)
>
> **Sempre confira o schema atual na documentação antes de implementar um endpoint.** Os campos
> abaixo foram conferidos, mas a API evolui. Se um campo não existir na resposta real, **não
> invente** — registre e trate como ausente.

### 7.0 Variáveis de ambiente

```bash
# backend/.env — NUNCA commitar este arquivo
BELVO_BASE_URL=https://api.belvo.com
BELVO_SECRET_ID=
BELVO_SECRET_PASSWORD=
BELVO_WIDGET_URL=https://widget.belvo.io
BELVO_WEBHOOK_TOKEN=            # token que a Belvo envia no header, p/ validar o webhook
APP_PUBLIC_URL=http://localhost:5173
APP_TERMS_URL=https://exemplo.com/termos
```

`.env.example` entra no Git com os nomes e **valores vazios**. O `.env` real, nunca.
Autenticação na Belvo é **Basic auth** com `BELVO_SECRET_ID:BELVO_SECRET_PASSWORD` —
e por isso **nenhuma chamada à Belvo sai do navegador**. Toda ela sai do backend.

### 7.1 O fluxo, do botão ao dado

```
1. Usuário toca em "Conectar meu banco"           [frontend → nosso backend]
2. Backend chama POST {BELVO_BASE_URL}/api/token/  → recebe access (válido ~10 min)
3. Backend devolve ao frontend: access_token + external_id
4. Frontend abre a URL do widget em UMA NOVA ABA do navegador (nunca iframe — §7.3)
5. Usuário escolhe a instituição → é levado ao app/site do banco → autoriza
6. Volta ao widget → clica em "Finalizar" → a ABA NOVA cai na nossa callback de sucesso
   com ?link=<uuid>&institution=<codigo>, avisa a aba original e se fecha
7. Backend salva o link_id e espera os webhooks historical_update
8. A cada webhook recebido, backend faz o GET do recurso correspondente e persiste
9. Frontend mostra o Raio-X quando houver dado
```

### 7.2 Passo 2 — `POST /api/token/`

Pré-requisitos: **nome completo e CPF do usuário**, que já temos do cadastro (§9, etapa 2).

```json
{
  "id": "{BELVO_SECRET_ID}",
  "password": "{BELVO_SECRET_PASSWORD}",
  "scopes": "read_institutions,write_links,read_consents,write_consents,write_consent_callback,delete_consents",
  "stale_in": "300d",
  "fetch_resources": [
    "ACCOUNTS",
    "OWNERS",
    "TRANSACTIONS",
    "BILLS",
    "INCOMES",
    "RECURRING_EXPENSES",
    "RISK_INSIGHTS"
  ],
  "widget": {
    "openfinance_feature": "consent_link_creation",
    "purpose": "Organização das dívidas do usuário e geração de um plano de quitação personalizado, com acompanhamento mensal.",
    "callback_urls": {
      "success": "{APP_PUBLIC_URL}/conectar/sucesso",
      "exit":    "{APP_PUBLIC_URL}/conectar/saida",
      "event":   "{APP_PUBLIC_URL}/conectar/evento"
    },
    "consent": {
      "terms_and_conditions_url": "{APP_TERMS_URL}",
      "permissions": ["REGISTER", "ACCOUNTS", "CREDIT_CARDS", "CREDIT_OPERATIONS"],
      "identification_info": [
        { "type": "CPF", "number": "<cpf do usuário, só dígitos>", "name": "<nome completo>" }
      ]
    },
    "branding": {
      "company_name": "Respira",
      "company_logo": "{APP_PUBLIC_URL}/logo.svg",
      "company_icon": "{APP_PUBLIC_URL}/icon.svg",
      "company_terms_url": "{APP_TERMS_URL}",
      "overlay_background_color": "#F8FAFC",
      "social_proof": true
    }
  }
}
```

Notas que economizam tempo:

- A resposta traz `access` (o token, **validade ~10 minutos**) e `refresh`. Gere o token **no momento do clique**, nunca antecipadamente.
- `openfinance_feature: "consent_link_creation"` e `purpose` são específicos do Open Finance Brasil. O `purpose` é mostrado ao usuário na tela de consentimento do banco — escreva na linguagem do §11, não em juridiquês.
- `permissions`: `REGISTER` (cadastro/owners), `ACCOUNTS` (conta corrente/poupança), `CREDIT_CARDS` (cartões e faturas), `CREDIT_OPERATIONS` (empréstimos e financiamentos). **São exatamente as quatro que o MVP usa** — não peça mais (princípio de minimização, §12.7).
- `INCOMES`, `RECURRING_EXPENSES` e `RISK_INSIGHTS` são produtos de **enriquecimento** (add-on). Se a conta do André não os tiver habilitados, a chamada falha ou vem vazia — **trate como opcional e degrade com elegância** (ver §7.6).
- Nunca logar o corpo dessa requisição: ele contém o secret e o CPF.

### 7.3 Passo 4 — abrir o widget

```
https://widget.belvo.io/?access_token={access_token}
                        &locale=pt
                        &access_mode=recurrent
                        &country_codes=BR
                        &institution_types=retail
                        &external_id={external_id}
```

| Parâmetro | Valor | Observação |
|---|---|---|
| `access_token` | da resposta do passo 2 | obrigatório |
| `locale` | `pt` | obrigatório para o Brasil (o padrão é espanhol) |
| `access_mode` | `recurrent` | mantém os dados atualizados automaticamente e dispara webhooks a cada ciclo. **É o que o Respira precisa** — `single` só faz a coleta inicial |
| `country_codes` | `BR` | maiúsculas |
| `institution_types` | `retail` | pessoa física |
| `external_id` | id interno do usuário | **mínimo 3 caracteres, só letras/números/`-`/`_`, e SEM PII** — nada de e-mail, CPF ou telefone, senão a Belvo anula o campo. Gere um UUID ou nanoid por usuário e guarde no nosso banco. |

#### Como abrir o widget — decisão tomada: **nova aba**

**Nada de `<iframe>`.** A decisão está fechada e não precisa ser reavaliada. O motivo é
concreto: mesmo que `widget.belvo.io` aceitasse ser enquadrado, o **passo seguinte é o site
do banco**, e bancos praticamente sempre enviam `X-Frame-Options: DENY` ou
`frame-ancestors 'none'`. O usuário veria uma moldura em branco exatamente no ponto mais
crítico do funil (§9, etapa 3).

**O widget abre em uma nova aba do navegador:**

```ts
// Precisa ser chamado DIRETAMENTE no handler do clique, de forma síncrona.
// Se você await-ar o fetch do token antes do window.open, o navegador trata
// como popup não solicitado e bloqueia.
function onConectarClick() {
  const aba = window.open('', '_blank');          // 1. abre já, vazia
  if (!aba) { mostrarAvisoPopupBloqueado(); return; }
  aba.document.write('<p>Abrindo conexão segura…</p>');

  api.criarWidgetToken().then(({ widgetUrl }) => {  // 2. busca o token
    aba.location.href = widgetUrl;                   // 3. navega a aba nova
  }).catch(() => {
    aba.close();
    mostrarErro();
  });
}
```

Três coisas que essa escolha exige:

1. **Bloqueador de popup.** Abrir a aba de forma síncrona no clique resolve na maioria dos
   casos. Ainda assim, trate `window.open` retornando `null`: mostre um aviso com um link
   normal (`<a target="_blank">`) para o usuário clicar — um clique direto no link nunca é
   bloqueado.
2. **A aba original fica viva e precisa saber o que aconteceu.** As callbacks do §7.4 caem na
   **aba nova**, não na original. O fluxo de retorno é:
   - a aba nova recebe `/conectar/sucesso?link=…&institution=…`;
   - ela faz `POST /consentimentos/callback` no nosso backend;
   - avisa a aba original via **`BroadcastChannel('respira-belvo')`** (fallback:
     `localStorage.setItem` + evento `storage`);
   - mostra "pronto, pode fechar esta aba" e chama `window.close()`;
   - a aba original recebe a mensagem e navega para `/raiox`, que entra na tela de espera
     da coleta (§7.5).
3. **Nunca confie só na mensagem entre abas.** Se o usuário fechar a aba nova na mão, a
   original nunca recebe o aviso. Por isso a aba original **também** faz polling de
   `GET /consentimentos` a cada 5 s enquanto a conexão estiver em andamento. A fonte de
   verdade é o backend, não a mensagem do navegador.

### 7.4 Passo 6 — as callbacks

Os três `callback_urls` do passo 2 precisam existir como rotas no frontend. A documentação
da Belvo mostra deep links (`seu-app://success`) porque assume mobile; para web, use URLs
`https`/`http` da nossa aplicação.

| Callback | Parâmetros na URL | O que fazer |
|---|---|---|
| **sucesso** | `link` (UUID do link), `institution` (código da instituição, ex.: `erebor_br_retail`) | `POST` para o nosso backend com o `link`; salvar na tabela `consentimento`; redirecionar para `/raiox` |
| **saída** | `last_encountered_error_code`, `last_encountered_error_message`, `meta_data_institution_name`, `meta_data_step` | Mostrar uma tela de "não deu certo desta vez" **com o motivo em português** e o botão de tentar de novo. Registrar o código para diagnóstico. |
| **evento** | `error`, `error_message` (ex.: `ACCESS_TOKEN_NOT_VALID`); ou `warning`, `warning_message` (ex.: `institution_disabled`) | `warning` não é fatal — siga o fluxo. `error` é fatal — volte para `/conectar` com mensagem útil. |

Erros comuns no evento de saída: instituição fora do ar, credenciais inválidas no banco,
conta bloqueada, excesso de sessões. **Traduza todos.** "Erro 500" na tela de conexão é o
fim do funil.

### 7.5 Passos 7–8 — webhooks e coleta

A Belvo leva de **~30 segundos a alguns minutos** depois da conexão para disponibilizar os
dados. A regra da Belvo é explícita: **`GET` só retorna dados depois que o webhook
correspondente chegar.** Polling cego desperdiça chamada e dá resultado vazio.

#### O endpoint de webhook

`POST /webhooks/belvo` no nosso backend. Payload:

```json
{
  "webhook_id":   "...",
  "webhook_type": "ACCOUNTS",
  "webhook_code": "historical_update",
  "process_type": "historical_update",
  "link_id":      "cb65f82c-...",
  "request_id":   "...",
  "external_id":  "...",
  "data":         { }
}
```

| Momento | `webhook_code` |
|---|---|
| Coleta inicial, logo após a criação do link | `owners.historical_update`, `accounts.historical_update`, `transactions.historical_update`, `bills.historical_update` — um por recurso em `fetch_resources` |
| Atualizações recorrentes (link `recurrent`) | `new_owners_available`, `new_accounts_available`, `new_transactions_available`, `new_bills_available` |

Regras obrigatórias:

1. **Responda sempre 2xx**, e rápido. A Belvo tenta até 5 vezes com backoff linear; um 500 nosso vira reentrega.
2. **Processe de forma assíncrona.** Responda 2xx primeiro, enfileire o `GET` depois (`BackgroundTasks` do FastAPI já resolve nesta escala).
3. **Seja idempotente.** O mesmo webhook pode chegar duas vezes. Use `webhook_id` como chave de deduplicação e faça *upsert* por `id` da Belvo, nunca insert cego.
4. **Autentique o endpoint.** Configure Basic auth ou Bearer no dashboard da Belvo e valide no backend (`BELVO_WEBHOOK_TOKEN`). Um endpoint de webhook aberto é um endpoint de injeção de dados.
5. Registre todo webhook recebido numa tabela `webhook_log` (`webhook_id`, `webhook_type`, `webhook_code`, `link_id`, `recebido_em`, `processado_em`, `erro`) — é o que torna o problema depurável quando o dado não aparece.

#### Em desenvolvimento local

`localhost` não recebe webhook da internet. Use um túnel (ngrok, Cloudflare Tunnel) e
registre a URL pública no dashboard da Belvo. **Enquanto o túnel não estiver de pé, o
fallback é polling** — ver abaixo.

#### A tela de espera (requisito, não detalhe)

Quando o usuário volta da conexão e ainda não há dados, a tela `/raiox` **não pode** mostrar
"R$ 0,00" nem uma lista vazia. Estado dedicado:

> **Conectamos sua conta. Estamos buscando seus dados no banco.**
> Isso costuma levar de 30 segundos a 2 minutos.
> *[barra de progresso indeterminada]*

Implementação: polling do **nosso** backend (não da Belvo) a cada 5 s, até 3 min, mostrando
quais recursos já chegaram ("contas ✓ · transações…"). Passado o limite, uma tela honesta
com botão de recarregar e um "pode fechar o app, avisamos quando estiver pronto". O
backend sabe o estado porque registrou os webhooks.

### 7.6 Os endpoints de leitura

Consuma **apenas** estes. Todos aceitam `?link={link_id}` e paginação
(`page`, `page_size`, máx. 1000 — **sempre pagine, nunca assuma uma página só**).

| Endpoint | Para que serve no Respira |
|---|---|
| `GET /api/links/` | status do link e do consentimento; detectar expiração |
| `GET /api/owners/?link=` | nome, CPF, e-mail, telefone — confirmar titularidade |
| `GET /api/accounts/?link=` | **a fonte principal das dívidas** — cartões, empréstimos, financiamentos, cheque especial, além das contas |
| `GET /api/transactions/?link=&value_date__range=` | histórico (até 12 meses) → capacidade de pagamento e detecção de eventos |
| `GET /api/bills/?link=` | faturas do cartão: total, mínimo, vencimento |
| `GET /api/incomes/?link=` | *(add-on)* renda já calculada pela Belvo |
| `GET /api/recurring-expenses/?link=` | *(add-on)* gastos recorrentes detectados |
| `GET /api/risk-insights/?link=` | *(add-on)* métricas agregadas; **opcional no MVP** |
| `DELETE /api/links/{id}` | revogação em um toque (§9, `/privacidade`) — e **obrigatório**: link não removido continua atualizando e gerando custo |

#### Campos que realmente importam

**`/accounts`** — `id`, `link`, `institution`, `category`, `type`, `name`, `number`,
`balance.current`, `balance.available`, `currency`,
`credit_data.{credit_limit, cutting_date, next_payment_date, minimum_payment, interest_rate, monthly_payment, network}`,
`loan_data.{principal, outstanding_balance, contract_amount, interest_rate, interest_rates[], number_of_installments, monthly_payment, payment_day, contract_start_date, contract_end_date}`.

`category` assume: `ADVANCE_DEPOSIT_ACCOUNT`, `CHECKING_ACCOUNT`, `CREDIT_CARD`,
`FINANCING_ACCOUNT`, `INVESTMENT_ACCOUNT`, `INVOICE_FINANCING_ACCOUNT`, `LOAN_ACCOUNT`,
`PENSION_FUND_ACCOUNT`, `SAVINGS_ACCOUNT`, `UNCATEGORIZED`.

**`/transactions`** — `id`, `account`, `value_date`, `accounting_date`, `amount`
(**sempre positivo**), `type` (`INFLOW` | `OUTFLOW`), `description`, `merchant`, `category`,
`subcategory`, `status`, `credit_card_data`, `currency`.
⚠️ No Brasil, `balance`, `observations` e `reference` vêm `null` — não dependa deles.

**`/bills`** — `id`, `account`, `bill_name`, `due_date`, `total_amount`, **`minimum_amount`**,
`is_installment`, `finance_charges[]`, `payments[]`, `currency`, `collected_at`.

**`/incomes`** — `income_streams[]` com `income_type` (SALARY, GOVERNMENT, FREELANCE…),
`frequency`, **`monthly_median`**, `monthly_average`, `stability`, `regularity`, `confidence`;
e os agregados `monthly_average_regular` / `monthly_average_irregular`.

**`/recurring-expenses`** — `name`, `category`, `frequency`, `average_transaction_amount`,
**`median_transaction_amount`**, `payment_type` (`SUBSCRIPTION` | `REGULAR`),
`days_since_last_transaction`.

### 7.7 O mapeamento — Belvo → domínio Respira

**Este é o arquivo mais importante da integração** (`providers/mapping.py`). Todo o
acoplamento com a Belvo mora aqui; nenhuma outra parte do código conhece os nomes dela.

#### `account.category` → `divida.modalidade`

| `category` da Belvo | Vira | Regra |
|---|---|---|
| `CREDIT_CARD` | `CARTAO_FATURA` · `CARTAO_ROTATIVO` · `CARTAO_PARCELADO` | Combine conta + fatura: pagamento abaixo do total no ciclo anterior ou encargo de rotativo em `finance_charges` → `CARTAO_ROTATIVO`; `is_installment` / parcelas em `credit_card_data` → `CARTAO_PARCELADO`; caso contrário `CARTAO_FATURA` |
| `LOAN_ACCOUNT` | `CREDITO_PESSOAL` ou `CONSIGNADO` | `type`/`name` indicando consignado → `CONSIGNADO` |
| `FINANCING_ACCOUNT` | `FIN_VEICULO` ou `FIN_IMOVEL` | pelo `type`/`name`; na dúvida, `OUTRO` |
| `ADVANCE_DEPOSIT_ACCOUNT` | `CHEQUE_ESPECIAL` | é literalmente o "adiantamento a depositante" do Open Finance |
| `CHECKING_ACCOUNT` com `balance.current < 0` | `CHEQUE_ESPECIAL` | só quando não vier uma `ADVANCE_DEPOSIT_ACCOUNT` separada — **cuidado para não contar a mesma dívida duas vezes** |
| `CHECKING_ACCOUNT` · `SAVINGS_ACCOUNT` (saldo ≥ 0) | **`conta`**, não dívida | alimenta o saldo disponível e o alerta de atraso iminente |
| `INVESTMENT_ACCOUNT` · `PENSION_FUND_ACCOUNT` | **ignorar** | fora do escopo (§13) |
| `INVOICE_FINANCING_ACCOUNT` · `UNCATEGORIZED` | `OUTRO` | registre no log para revisão |

#### Campo a campo

| Campo do domínio | De onde vem |
|---|---|
| `saldo_devedor` | cartão: `total_amount` da fatura aberta (ou `|balance.current|`) · empréstimo/financiamento: `loan_data.outstanding_balance` · cheque especial: `|balance.current|` ou o usado do limite |
| **`taxa_juros_mes`** | cartão: `credit_data.interest_rate` · empréstimo: `loan_data.interest_rate` (ou o item mais relevante de `loan_data.interest_rates[]`) — **ver o alerta abaixo** |
| `parcela_minima` | cartão: `bills.minimum_amount` (preferir) ou `credit_data.minimum_payment` · empréstimo: `loan_data.monthly_payment` |
| `dia_vencimento` | cartão: `credit_data.next_payment_date` ou `bills.due_date` · empréstimo: `loan_data.payment_day` |
| `parcelas_restantes` | `loan_data.number_of_installments` menos as já pagas |
| `em_atraso_dias` | `due_date` vencida sem pagamento correspondente |
| `instituicao` | `account.institution` (código e nome) |
| `origem` | `OPEN_FINANCE` |

#### 🚨 A taxa de juros é o ponto crítico

O motor do §5 inteiro depende de `taxa_juros_mes`. Dois perigos, nesta ordem:

1. **Unidade.** `interest_rate` pode vir **mensal** ou **anual**, e pode vir como `0.15`
   (fração) ou `15.0` (percentual). Errar isso produz um plano absurdo com cara de
   certeza. Não adivinhe: na primeira integração real, **imprima o valor bruto, a
   instituição e o tipo de conta num log de diagnóstico** (sem PII), confira contra o
   extrato, e só então escreva a normalização — num único lugar
   (`mapping.normalizar_taxa()`), com a decisão comentada e um teste.
   Sanity check automático: taxa mensal normalizada fora do intervalo **0,1% a 20% a.m.**
   → não use; marque como estimada e registre.
2. **Ausência.** Se a instituição não devolver taxa, siga a regra que já está no §7.9:
   `taxa_origem = 'ESTIMADA'`, taxa de referência por modalidade vinda de um arquivo único
   com fonte documentada, e **badge visível na interface**.

#### Transações

`amount` vem sempre positivo e a direção está em `type`. Converta para a nossa convenção
(negativo = saída) **no mapeamento**:

```python
valor = txn.amount if txn.type == "INFLOW" else -txn.amount
```

`essencial` sai da classificação da Belvo (`category` / `subcategory`) via uma tabela
explícita no nosso código — Bills & Utilities, aluguel, mercado, transporte, saúde,
educação. Nunca peça ao usuário para classificar (princípio 1, §3).

### 7.8 Capacidade de pagamento com dado real (atualiza o §5.1)

Com a Belvo no circuito, a capacidade passa a ter uma fonte melhor que a mediana crua.
Ordem de preferência, com queda limpa:

```
entradas:
  1) incomes.monthly_median dos streams com confidence HIGH/MEDIUM   (se o add-on existir)
  2) mediana mensal das transações INFLOW dos últimos 6 meses        (§5.1 original)

essenciais:
  1) Σ median_transaction_amount dos recurring-expenses de categoria essencial
     + mediana dos gastos essenciais não-recorrentes
  2) mediana mensal das OUTFLOW classificadas como essencial          (§5.1 original)

capacidade = max( round((entradas - essenciais) * 0.90, 2), 0 )
```

**A reserva de 10% continua valendo**, qualquer que seja a fonte. E o campo `capacidade_origem`
(`INCOMES` | `TRANSACOES`) é persistido no plano — quando a projeção não bater com a
realidade, é a primeira coisa que se quer saber.

### 7.9 Compromissos fora do Open Finance

O cadastro manual assistido (F1) produz dívidas com `origem = 'MANUAL'`. O formulário pede:
credor, modalidade, saldo, taxa (com ajuda — *"está no carnê, geralmente ao lado de 'juros
ao mês'"*), valor da parcela e dia de vencimento. Obrigatórios: **saldo e parcela**. Taxa é
opcional e, quando ausente, cai na regra de estimativa do §7.7.

### 7.10 Ciclo de vida do consentimento

O consentimento do Open Finance **expira** (tipicamente 12 meses, definido na autorização).
A Fase 5 registrou isso como ponto de falha silenciosa dos concorrentes — então aqui é
funcionalidade, não tratamento de erro:

- `GET /api/links/` dá o status. Reflita em `consentimento.status` (`ATIVO` | `EXPIRADO` | `REVOGADO` | `ERRO`).
- **Avise com antecedência** (30 e 7 dias), com a consequência concreta: *"em 7 dias seus dados param de atualizar e seu plano congela"*. Isso **cabe na regra de parcimônia** (§2) — há ação concreta e consequência clara.
- Expirou: estado próprio na interface, com reconexão em um toque. **Nunca mostre dado velho como se fosse atual** — carimbe "atualizado em {data}" em toda tela que depende de dado da Belvo.
- Revogação pelo usuário: `DELETE /api/links/{id}` **e** apagar os dados locais daquele link. Link não removido continua atualizando e custando.
- O usuário também pode gerenciar consentimentos pelo **My Belvo Portal** e pelo app do próprio banco — a tela `/privacidade` precisa dizer isso.

### 7.11 Dois provedores, desde o dia 1

1. **`FixtureProvider`** — devolve a situação da Juliana (§2) + 6 meses de transações sintéticas, **no formato de resposta da Belvo**, para o mapeamento ser exercitado de verdade. É o que roda nos testes e em `APP_PROVIDER=fixture`.
2. **`BelvoProvider`** — a integração real, selecionada por `APP_PROVIDER=belvo`.

Isso não é "mock em vez de dado real": é o que permite testes determinísticos, demonstração
sem expor dados financeiros reais do André, e desenvolvimento de tela enquanto a conexão
não está de pé. **A entrega roda contra a Belvo.**

### 7.12 Ordem de ataque da integração

1. `POST /api/token/` pelo backend; confirmar que volta `access`.
2. Montar a URL do widget, abrir em **nova aba** (§7.3) e **testar o fluxo inteiro com um banco real**. Faça isso antes de construir qualquer tela ao redor — é o passo que revela as surpresas.
3. Callback de sucesso capturando `link` e `institution`; persistir.
4. Endpoint de webhook + túnel; registrar tudo em `webhook_log`.
5. `GET /api/accounts/` e `GET /api/bills/` → mapeamento → tabela `divida`. **Conferir a taxa contra o extrato real antes de confiar no plano.**
6. `GET /api/transactions/` → capacidade de pagamento.
7. `GET /api/incomes/` e `/recurring-expenses/` se o add-on estiver habilitado.
8. Ciclo de vida do consentimento e `DELETE /api/links/{id}`.

---

## 8. Modelo de dados

Derivado do esquema Oracle da Fase 5 (`Oracle/sql/01_schema.sql`). Mantenha os **nomes e os
valores de enum** — assim a migração futura é mecânica.

### 8.1 Entidades

```
usuario(id, uuid_externo, apelido, faixa_renda, vinculo_renda,
        nivel_familiaridade[INICIANTE|INTERMEDIARIO|AVANCADO],
        ja_desistiu_de_plano: bool,          ← alimenta a pré-seleção da §5.4
        criado_em, excluido_em)

instituicao(id, codigo_externo, nome, tipo[BANCO|FINTECH|CARTAO|CREDIARIO|OUTRO])

consentimento(id, usuario_id, instituicao_id, link_externo, escopo,
              status[PENDENTE|ATIVO|EXPIRADO|REVOGADO|ERRO],
              concedido_em, expira_em, revogado_em)

conta(id, usuario_id, instituicao_id, tipo[CORRENTE|POUPANCA|PAGAMENTO],
      saldo, limite_cheque_especial, usado_cheque_especial, atualizado_em)

divida(id, usuario_id, instituicao_id,
       modalidade[CARTAO_FATURA|CARTAO_ROTATIVO|CARTAO_PARCELADO|CHEQUE_ESPECIAL|
                  CREDITO_PESSOAL|CONSIGNADO|FIN_VEICULO|FIN_IMOVEL|CREDIARIO|OUTRO],
       descricao, saldo_devedor, taxa_juros_mes, parcela_minima,
       parcelas_restantes, dia_vencimento, em_atraso_dias, negativada,
       origem[OPEN_FINANCE|MANUAL], taxa_origem[INFORMADA|ESTIMADA], atualizado_em)

transacao(id, usuario_id, conta_id, divida_id, data_mov, valor,   ← negativo = saída
          descricao, categoria, essencial: bool, recorrente: bool,
          origem[OPEN_FINANCE|MANUAL])

plano(id, usuario_id, metodo[AVALANCHE|SNOWBALL|EQUILIBRADO], capacidade_mensal,
      capacidade_origem[INCOMES|TRANSACOES],                    ← ver §7.8
      meses_projetados, data_quitacao, juros_totais, economia_vs_minimo,
      status[SIMULADO|ATIVO|PAUSADO|CONCLUIDO], criado_em)

plano_item(id, plano_id, divida_id, ordem, valor_mensal, mes_quitacao, juros_pagos)

evento(id, usuario_id, divida_id,
       tipo[ENTRADA_ROTATIVO|ATRASO_IMINENTE|ATRASO_CONFIRMADO|PICO_CATEGORIA|
            DESVIO_PLANO|DIVIDA_QUITADA|CHEQUE_ESPECIAL|OPORTUNIDADE_PORTABILIDADE],
       contexto: json, severidade 1..3, detectado_em, notificado_em)

licao(id, titulo, corpo, tipo_evento, modalidade, nivel, ativo)

webhook_log(id, webhook_id, webhook_type, webhook_code, process_type, link_id,
            request_id, external_id, recebido_em, processado_em, erro)
            ← §7.5; webhook_id é a chave de deduplicação
```

Na tabela `consentimento`, `link_externo` guarda o **link_id da Belvo** e `escopo` guarda as
`permissions` concedidas. Toda entidade vinda da Belvo guarda também o **`id` original dela**,
para que a reconciliação seja *upsert* e não insert duplicado.

### 8.2 Campos derivados

- **`taxa_juros_ano`** = `round((pow(1 + taxa_juros_mes, 12) - 1) * 100, 4)` — é esta que aparece na interface e ordena o avalanche. Mostre a anual: 15,02% a.m. vira **436% a.a.**, e é esse número que choca e informa.
- **Raio-X** (agregação por usuário): `qtd_dividas`, `divida_total`, `juros_mes_estimado` = `Σ(saldo × taxa_mes)`, `compromisso_minimo_mes` = `Σ parcela_minima`, `pior_taxa_anual`, `qtd_em_atraso`.
- **`divida_cresce`** = `juros_mes_estimado > compromisso_minimo_mes` → o insight obrigatório do F2.

### 8.3 Detecção de eventos (determinística, sem IA)

Rode após cada sincronização:

| Evento | Regra |
|---|---|
| `ENTRADA_ROTATIVO` | surgiu ou cresceu uma dívida `CARTAO_ROTATIVO` desde a última sync |
| `ATRASO_IMINENTE` | `dia_vencimento` em ≤ 3 dias **e** saldo em conta < parcela devida |
| `ATRASO_CONFIRMADO` | `em_atraso_dias` passou de 0 para > 0 |
| `CHEQUE_ESPECIAL` | `usado_cheque_especial > 0` |
| `PICO_CATEGORIA` | gasto do mês numa categoria > 1,5 × mediana dos 6 meses anteriores |
| `DESVIO_PLANO` | pago no mês < 80% do `valor_mensal` previsto |
| `DIVIDA_QUITADA` | `saldo_devedor` chegou a 0 |

Cada evento carrega em `contexto` os números que a mensagem vai usar. **A mensagem é
montada a partir do contexto, nunca genérica.**

### 8.4 Endpoints do backend (sugestão)

```
POST   /usuarios                        cria o usuário do protótipo
GET    /usuarios/me

POST   /consentimentos/widget-token     §7.2 — gera o access token e o external_id
POST   /consentimentos/callback         §7.4 — recebe o link_id do redirect de sucesso
GET    /consentimentos                  lista + status (ATIVO/EXPIRADO/...)
DELETE /consentimentos/{id}             revogação: DELETE /api/links/{id} + apaga local
GET    /consentimentos/{id}/coleta      estado da coleta p/ a tela de espera (§7.5)
POST   /webhooks/belvo                  §7.5 — autenticado, idempotente, responde 2xx rápido
POST   /sync                            força recoleta (fallback quando não há webhook)

GET    /raiox                           F2 — agregações + frase pronta
GET    /dividas  ·  POST /dividas       lista; cadastro manual assistido
PATCH  /dividas/{id}

GET    /plano/simulacoes?capacidade=900 F3 — as três estratégias lado a lado
POST   /plano                           ativa a estratégia escolhida
GET    /plano/ativo                     plano + cronograma por dívida
POST   /plano/recalcular                F4 — recálculo mensal

GET    /eventos?nao_notificados=true    F4 — alertas pendentes
POST   /eventos/{id}/visto
GET    /licoes?evento={tipo}            F5 — conteúdo estático casado por regra
```

---

## 9. Telas, rotas e estados

A jornada tem **seis etapas**. As métricas de funil ao lado são as metas definidas na Fase 5 —
use-as para priorizar o que precisa ficar impecável.

| # | Etapa | Rota | Meta de funil |
|---|---|---|---|
| 1 | Descoberta | `/` (landing) | — |
| 2 | Cadastro | `/cadastro` | > 70% concluem |
| 3 | Conexão | `/conectar` | > 55% conectam ≥ 1 instituição; > 35% conectam ≥ 2 |
| 4 | Diagnóstico | `/raiox` | > 80% de quem conecta avança para o plano |
| 5 | Plano | `/plano` | > 60% de quem vê o diagnóstico ativa um plano |
| 6 | Execução | `/inicio` | > 40% ativos no 3º mês |

### Etapa 1 — Descoberta `/`

O gatilho **não é** o desejo de "organizar as finanças" — é um evento de dor: a fatura
impagável, a recusa de crédito, o nome negativado. A chamada é
**"Descubra quando você sai das dívidas"**, não "controle seus gastos".

### Etapa 2 — Cadastro `/cadastro`

Cadastro mínimo. **Nenhum dado financeiro é pedido na entrada** — perguntar "quanto você
deve?" antes de conectar é exatamente o pedido que o usuário não sabe responder, e a razão
pela qual ele desiste.

Uma única pergunta de produto, opcional, com resposta que alimenta a pré-seleção da
estratégia (§5.4): *"Você já tentou um plano para sair das dívidas antes?"* →
`ja_desistiu_de_plano`.

### Etapa 3 — Conexão `/conectar`

Ponto de maior atrito da jornada e etapa mais crítica do funil.

- **"Este app não movimenta o seu dinheiro"** é o elemento mais visível da tela — tipograficamente destacado, acima de qualquer outro texto.
- **Explique o mecanismo, não o nome.** Metade das pessoas não sabe o que é Open Finance. "Seu banco te mostra uma tela para autorizar a leitura — e só a leitura — das suas contas" funciona; "conecte via Open Finance" não.
- Uma instituição por vez, com explicação antes de cada consentimento.
- **Feedback de progresso durante a coleta** — a Belvo leva de 30 s a alguns minutos (§7.5). Nada de spinner mudo, e nunca "R$ 0,00" no lugar de "ainda buscando".
- Revogação disponível **em um toque**, sempre visível em `/privacidade`.
- Link discreto e sempre presente para **"tenho um carnê ou dívida que não aparece aqui"** → cadastro manual assistido.

- O widget abre **em uma nova aba** (§7.3). A aba original fica na tela "aguardando você
  concluir no banco", com um botão de "já concluí" e um de "cancelar" — ela não pode ficar
  congelada esperando uma mensagem que talvez nunca chegue.

**Rotas desta etapa** (§7.4): `/conectar` · `/conectar/sucesso` (recebe `?link=&institution=`,
roda **na aba nova**) · `/conectar/saida` · `/conectar/evento`.

**Estados obrigatórios:** pendente de autorização · **coletando** (com progresso por recurso:
"contas ✓ · transações…") · sucesso parcial (2 de 3 instituições) · erro recuperável, com o
motivo **traduzido para português** · **consentimento expirado** (com CTA de reconexão e aviso
antecipado aos 30 e 7 dias).

### Etapa 4 — Diagnóstico `/raiox`

O momento de verdade. Ordem de leitura **obrigatória**, de cima para baixo:

1. **Total consolidado** — "Você deve R$ 8.260" (o número grande).
2. **Lista dos compromissos**, ordenada **por custo efetivo** (taxa a.a. decrescente), cada um com saldo, taxa anual, mínimo e vencimento.
3. **Data de quitação projetada** — imediatamente abaixo, **na mesma tela**, sem scroll obrigatório num celular de 360 px.
4. **A frase do custo** — "paga R$ 733 por mês só em juros; R$ 312 disso vem do rotativo".
5. **O alerta do mínimo**, quando aplicável — "pagando só o mínimo, sua dívida cresce".
6. **CTA único:** "Ver meu plano de saída".

O sentimento aqui é ambivalente — é um choque, mas também um alívio. **A tela nunca entrega
o diagnóstico sozinho** (princípio 3): a projeção do plano vem junto.

### Etapa 5 — Plano `/plano`

- As **três estratégias lado a lado** (em mobile: cards empilháveis ou carrossel), cada uma com meses, juros totais e mês da primeira vitória.
- A **frase de comparação** (§4 F3) em destaque — é ela que faz o trabalho, não a tabela.
- **Slider de capacidade mensal** com recálculo em tempo real da data. Debounce de ~200 ms; se o cálculo for no backend, mantenha a resposta abaixo de 300 ms ou calcule no cliente para o preview e confirme no servidor ao ativar.
- A estratégia pré-selecionada segue §5.4, e **o motivo da pré-seleção é dito em uma linha**.
- Ao ativar: **cronograma por dívida** — quanto vai para cada uma neste mês e em que mês cada uma morre.

### Etapa 6 — Execução `/inicio` (tela inicial após ter plano)

Responde "quando isso acaba" logo no topo. Contém:

- **Data de quitação** e meses restantes, com barra de progresso sobre o total já abatido.
- **O que fazer este mês** — a lista de pagamentos sugeridos, na ordem, com valor.
- **Alertas pendentes**, sob a regra de parcimônia.
- **Marcos** — cada dívida quitada vira um evento celebrado, com data.
- Acesso a `/raiox`, `/plano`, `/privacidade`.

**Quando o mês foi ruim:** recálculo e nova data, **sem linguagem de falha**. Nunca "você
falhou", "você está atrasado com seu plano", nenhum vermelho de reprovação. O texto certo é
*"este mês entrou R$ 180 a menos no plano; sua data nova é março de 2028 — dá para
recuperar colocando R$ 60 a mais nos próximos três meses"*.

### Telas de apoio

- `/privacidade` — o que é lido, o que não é acessado, revogação em um toque, exclusão de conta e dados.
- `/dividas/nova` — cadastro manual assistido.
- `/licoes/{id}` — microlição (conteúdo estático, F5).

---

## 10. Design system

Reaproveite a identidade dos diagramas e slides da Fase 5 — o protótipo precisa parecer a
mesma coisa que foi apresentada.

### Cores

| Token | Hex | Uso |
|---|---|---|
| `navy` | `#12314F` | texto de títulos, fundo de telas escuras |
| `ink` | `#1E293B` | texto corrido |
| `slate` | `#64748B` | texto secundário, legendas |
| `line` | `#E2E8F0` | bordas, divisores |
| `light` | `#F8FAFC` | fundo de seções |
| `blue` | `#2563EB` | ação primária, destaque |
| `purple` | `#7C3AED` | estratégia / plano |
| `green` | `#059669` | progresso, dívida quitada, economia |
| `amber` | `#D97706` | atenção, estimativas, prazos próximos |
| `rose` | `#E11D48` | custo alto, rotativo, atraso confirmado |

Fundos suaves correspondentes: `#FAF8FF` (roxo), `#F5F9FF` (azul), `#F4FDF8` (verde),
`#FFFCF3` (âmbar), `#FFF7F8` (rosa).

**Uso do vermelho/rosa:** só para **fatos** (esta dívida custa 436% a.a.; esta fatura está em
atraso), **nunca para julgar o usuário**. Um mês fora do plano é âmbar, não rosa.

### Tipografia

- Família: **Inter** (fallback: `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`).
- Números monetários com **tabular-nums**.
- O "número grande" do total e da data de quitação é o maior elemento da tela — hierarquia clara, não mais de três níveis por tela.

### Componentes-chave a criar

`Money` (BRL, centavos, tabular) · `PayoffDate` (data + meses restantes) · `DebtCard` (saldo,
taxa a.a., mínimo, vencimento, badge de estimativa) · `StrategyCard` e `StrategyCompare` ·
`CapacitySlider` · `AlertBanner` (com valor em reais obrigatório) · `MilestoneBadge` ·
`ConsentExplainer` · `EmptyState` / `ErrorState` / `OfflineState`.

### Visualizações

Mantenha poucas e com função clara. Cada gráfico responde a uma pergunta:

- **Composição da dívida** — qual parte do total cada compromisso ocupa, ordenado por custo.
- **Trajetória do saldo** — linha do saldo total caindo até zero na data de quitação; com as três estratégias sobrepostas na tela de comparação.
- **Juros evitados** — quanto o plano economiza contra "pagar só o mínimo".

Sem gráfico de pizza de categorias de gasto. É exatamente o que a persona já abandonou duas
vezes e não é a pergunta do produto.

### Acessibilidade

Contraste mínimo **4,5:1** para texto. Nunca comunique estado só por cor — sempre ícone ou
rótulo junto. Navegação por teclado funcional. `aria-live` nos recálculos do slider. Suporte a
`prefers-reduced-motion`.

---

## 11. Regras de escrita (copy)

A escrita **é** o produto aqui. Centralize todas as strings em `src/lib/copy.ts` — isso força
consistência e facilita revisão.

**Faça:**

- Português do Brasil, segunda pessoa, direto: "você paga", "sua data".
- **Sempre com o número do próprio usuário.** "Você está pagando R$ 312 de juros por mês só no rotativo."
- Frases curtas. Se não cabe numa linha de celular, corte.
- Taxa em **% ao ano** na interface (a mensal engana a percepção).
- Toda má notícia vem acompanhada do próximo passo.

**Não faça:**

- Jargão: "encargos rotativos", "saldo devedor atualizado", "comprometimento de renda" sem tradução, "CET", "amortização".
- Invocar "Open Finance" como se todos soubessem o que é.
- Linguagem de culpa, gamificação infantil, emoji como substituto de informação.
- Promessa de resultado garantido. O plano é uma projeção — diga "projeção" quando for.
- Qualquer sugestão que pareça aconselhamento financeiro personalizado regulado. O produto **organiza e projeta**; não recomenda contratar nem deixar de contratar crédito.

**Exemplos canônicos** (reutilize o tom):

> "Você deve R$ 8.260 em 5 compromissos e paga R$ 733 por mês só em juros; R$ 312 disso vem do rotativo do cartão."

> "Pagando só o mínimo, sua dívida não diminui — ela cresce R$ 10 por mês."

> "A fatura do Banco A fecha em 3 dias e faltam R$ 180 no seu plano; se pagar o mínimo, entra no rotativo e sua data de saída atrasa 2 meses."

> "Pelo caminho equilibrado você fica livre em 19 meses e paga R$ 316 a mais de juros do que pelo mais econômico, que leva 18 — só que nele a primeira dívida some no 10º mês, e no equilibrado ela some já no 2º."

> "Este app não movimenta o seu dinheiro."

---

## 12. Segurança e privacidade — requisitos não negociáveis

Este é um protótipo acadêmico, mas trata **dados financeiros reais** do André e de quem ele
conectar. Trate como produção.

> **Antes de tudo: rotacione as credenciais da Belvo.** O par `secretId`/`secretPassword`
> usado neste projeto já circulou fora de um cofre. Gere um novo no dashboard da Belvo e
> **nunca mais transmita esse par por chat, e-mail ou commit.**

1. **Nenhum segredo no frontend, nunca.** A Belvo usa **Basic auth** com o par secreto — ele vive apenas no backend, lido de variável de ambiente. Nenhuma chamada à Belvo sai do navegador; o frontend só fala com o nosso backend.
2. **`.env` nunca entra no Git.** Commite `.env.example` com os nomes das variáveis e valores vazios. `.gitignore` com `.env`, `*.db`, `wallet/`, `__pycache__/`, `node_modules/`, `dist/`.
3. **Nada de credencial hardcoded**, nem "temporariamente", nem em comentário, nem em teste.
4. **Nunca logar dados sensíveis.** Em log, mascare: nunca número de cartão completo, nunca CPF completo, nunca token nem secret. **O corpo do `POST /api/token/` contém secret e CPF — nunca o imprima.** Saldos e transações não vão para log em nível `info`. O log de diagnóstico da taxa de juros (§7.7) registra instituição, modalidade e o valor bruto da taxa — nada que identifique a pessoa.
5. **CORS restrito** à origem do frontend local. Nada de `allow_origins=["*"]`.
6. **Valide toda entrada** com Pydantic no backend e Zod no frontend — inclusive o que vem do provedor externo.
7. **Minimize a coleta.** Peça só as quatro `permissions` do §7.2. Escopo a mais é risco a mais e atrito a mais na tela de consentimento.
8. **Exclusão real.** `/privacidade` precisa de um botão que faça `DELETE /api/links/{id}` na Belvo **e** apague os dados locais daquele link — não só marque como inativo. Link esquecido continua atualizando e custando.
9. **Webhook autenticado.** `/webhooks/belvo` valida Basic/Bearer antes de processar qualquer coisa (§7.5). Endpoint de webhook aberto é porta de injeção de dados.
10. **Nada de enviar dados do usuário para serviços de terceiros** — nenhuma API de IA externa, nenhum serviço de analytics, nenhum paste bin. Se a Fase 6 pedir IA, ela entra pela OCI/Oracle como planejado, com os dados permanecendo na mesma instância.
11. **Dependências:** prefira bibliotecas consolidadas e ativamente mantidas; rode `npm audit` e `pip-audit` antes de fechar a entrega e registre o resultado.
12. **Todo código gerado por IA passa por revisão humana antes de ser considerado pronto.** Inclusive este protótipo.
13. **Dinheiro em centavos inteiros ou decimal.** Float em valor monetário é bug de correção, não de estilo.

---

## 13. Fora do escopo

Registrado explicitamente, porque definir o que não se faz é parte de definir o MVP.
**Não implemente nada disto**, mesmo que pareça fácil:

| Funcionalidade | Por que fica de fora |
|---|---|
| Renegociação dentro do app | Exige parcerias comerciais e integração com credores; é a rota de monetização da fase 2 |
| Marketplace de crédito e portabilidade | Depende de escala e de acordos; fase 2 |
| Investimentos e reserva de emergência | Produto adjacente; dilui o posicionamento |
| Iniciação de pagamento (pagar a fatura pelo app) | Aumenta muito o escopo regulatório e de segurança; fase 3 |
| Contas PJ e MEI | Dinâmica de caixa distinta; outra persona |
| Score de crédito e monitoramento de CPF | Já bem servido pelo Serasa; não é diferencial |
| Metas de poupança e orçamento por envelope | Só faz sentido depois da saída da dívida |
| Categorização manual de transações pelo usuário | **Viola o princípio 1** e é o motivo documentado de abandono da persona |
| Resumo semanal / notificação de engajamento | **Viola a regra de parcimônia** (§2) |

---

## 14. Critérios de aceite e fixtures de teste

### 14.1 Fixture canônica — o motor precisa reproduzir estes números

Com as cinco dívidas da §2 e **capacidade de R$ 900/mês**, o `PKG_PLANO` da Fase 5 produziu:

| Estratégia | Meses até a quitação | Juros totais | Primeira dívida quitada |
|---|---:|---:|---:|
| **Avalanche** | 18 | R$ 7.924 | 10º mês |
| **Equilibrado** | 19 | R$ 8.240 | 2º mês |
| **Bola de neve** | 21 | R$ 10.492 | 2º mês |

Diferença Equilibrado × Avalanche: **R$ 316** e 1 mês. Bola de neve custa **R$ 2.568 a mais**
que o avalanche.

**Escreva `test_planner.py` contra esta tabela.** Se o porte em Python divergir, investigue
arredondamento antes de mudar o número esperado — e, se a divergência for legítima
(diferença de arredondamento entre PL/SQL e Python), **documente-a no teste em um
comentário**, com o valor antigo e o novo. Não apague o histórico: esses números estão
publicados no documento entregue da Fase 5.

### 14.2 Outros casos de teste obrigatórios

- Sem dívidas → `meses = 0`, sem data, interface mostra estado vazio adequado.
- Capacidade ≤ soma dos mínimos → o plano não converge: a interface precisa dizer isso de forma útil ("com R$ 700 por mês a dívida não diminui; são necessários pelo menos R$ X") e **não travar em loop**.
- Capacidade ≤ 0 → mesma coisa, sem exceção não tratada.
- Uma dívida só → funciona nas três estratégias, resultados idênticos.
- Empate de taxa / empate de saldo → ordenação determinística pelos desempates da §5.2.
- Juros mensais > soma dos mínimos → flag `divida_cresce` verdadeira e alerta renderizado.
- Dívida com `taxa_origem = 'ESTIMADA'` → badge visível em toda tela que mostra a taxa.
- Consentimento expirado → estado próprio, CTA de reconexão, nenhum dado antigo apresentado como atual.

### 14.3 Definição de pronto

- [ ] Roda com `docker compose up` ou dois comandos documentados no README.
- [ ] `APP_PROVIDER=fixture` sobe sem nenhuma credencial e já mostra a jornada completa com a Juliana.
- [ ] `APP_PROVIDER=belvo` usa as credenciais do `.env` e não contém nenhuma chave no código.
- [ ] Suíte do motor verde, incluindo a fixture da §14.1.
- [ ] As 6 telas da §9 navegáveis em 360 px de largura, com estados de carregando/vazio/erro.
- [ ] Nenhum `console.log` de dado financeiro; nenhum segredo no histórico do Git.
- [ ] `npm audit` e `pip-audit` sem vulnerabilidade alta ou crítica em aberto.

**Específicos da Belvo:**

- [ ] Nenhuma chamada a `api.belvo.com` parte do navegador (confira na aba Network).
- [ ] `POST /api/token/` funciona e o token é gerado **no clique**, não antes.
- [ ] Fluxo do widget testado **ponta a ponta com um banco real**, abrindo em nova aba (§7.3), com o retorno chegando na aba original por `BroadcastChannel` **e** por polling.
- [ ] Bloqueador de popup tratado: `window.open` retornando `null` mostra um link clicável, não um erro silencioso.
- [ ] Callback de sucesso captura `link` e `institution` e persiste o consentimento.
- [ ] `/webhooks/belvo` autenticado, idempotente (webhook duplicado não duplica dado) e respondendo 2xx em menos de 1 s.
- [ ] A tela de espera aparece quando o dado ainda não chegou — nunca "R$ 0,00".
- [ ] Toda listagem da Belvo é paginada (nada de assumir uma página).
- [ ] **A taxa de juros de pelo menos uma dívida real foi conferida contra o extrato** e a normalização está testada. Taxas fora de 0,1%–20% a.m. caem como `ESTIMADA` com badge na tela.
- [ ] `DELETE /api/links/{id}` funciona e apaga os dados locais junto.
- [ ] Nenhum link órfão deixado na conta Belvo ao fim dos testes.

---

## 15. Ordem de implementação sugerida

1. **Domínio primeiro, sem interface.** `planner.py` + `test_planner.py` contra a fixture da §14.1. Até isso passar, não escreva React. É o coração do produto e é o que a banca vai olhar.
2. **Modelos + SQLite + `FixtureProvider`.** Seed com a Juliana e 6 meses de transações.
3. **Endpoints `/raiox` e `/plano/simulacoes`.** Teste pelo `/docs` do FastAPI.
4. **Frontend: `/raiox` e `/plano`.** São as duas telas que provam o produto; se só der tempo de fazer duas bem-feitas, são estas.
5. **Belvo, em paralelo e cedo:** siga a ordem do §7.12 — token → widget em nova aba com banco real → callback → webhook → `accounts`/`bills` → `transactions`. **Faça o teste com um banco real na primeira semana**: é o passo com mais incógnitas (taxa de juros, campos ausentes, comportamento da instituição).
6. **Jornada completa:** `/`, `/cadastro`, `/conectar`, `/inicio`.
7. **F4:** detecção de eventos, alertas, recálculo mensal, marcos.
8. **F5:** estrutura de lições com conteúdo estático; copiloto atrás de feature flag desabilitada.

---

## 16. Decisões ainda em aberto

> Situação em out/2026: 1 (login real), 3 (polling por padrão) e 7 (roda localmente) já foram
> decididas — ver o topo deste arquivo e o README. As demais seguem como registro.

Pergunte ao André antes de decidir sozinho:

1. **Autenticação.** O protótipo tem um usuário só (ele) ou precisa de login real? Isso muda bastante o escopo. *Sugestão: usuário único local na Fase 6.*
2. **Add-ons de enriquecimento.** `INCOMES`, `RECURRING_EXPENSES` e `RISK_INSIGHTS` estão habilitados nessa conta Belvo? Se não, o §7.8 cai no caminho 2 (mediana das transações) e `RISK_INSIGHTS` sai do escopo.
3. **URL pública para webhook.** Vamos subir um túnel (ngrok / Cloudflare) e registrar no dashboard da Belvo, ou o protótipo roda em fallback de polling? Sem URL pública não há webhook.
4. **Termos de uso.** `terms_and_conditions_url` é obrigatório no payload do token e **aparece para o usuário**. Qual URL usar?
5. **Branding.** Logo e ícone do Respira para o widget — existem, ou geramos um placeholder?
6. **Quais instituições** o André vai conectar nos testes? Define o realismo do seed e revela cedo as diferenças de taxa de juros entre bancos.
7. **Entregável da Fase 6:** roda localmente na apresentação, ou precisa estar publicado? Se for publicado, a discussão de segurança muda completamente — dados financeiros reais num host público exigem outro tratamento, e as credenciais da Belvo passam a precisar de um cofre de verdade.
8. **Vídeo/demo:** se houver gravação, use `APP_PROVIDER=fixture` com a Juliana e **não exponha dados bancários reais do André na tela**.
9. **Enunciado da Fase 6** — ainda não disponível quando este arquivo foi escrito. Confira os entregáveis exigidos antes de fechar o escopo.

---

## Referências do projeto (Fase 5)

| Item | Onde |
|---|---|
| Documento completo (58 páginas) | `Fase 5 .../Startup One - Documento - Fase 5.pdf` |
| Esquema de dados Oracle | `Fase 5 .../Oracle/sql/01_schema.sql` |
| Motor de plano em PL/SQL (referência do porte) | `Fase 5 .../Oracle/sql/04_motor_plano.sql` |
| Dados demo da persona | `Fase 5 .../Oracle/sql/00_dados_demo.sql` |
| Respostas da pesquisa (n=10) | `Fase 5 .../Validacao/pesquisa_respostas.csv` |
| Diagramas (persona, jornada, fluxograma, arquitetura) | `Fase 5 .../Diagramas/` |
| Vídeo de apresentação | https://youtu.be/SqLT0RcDZTg |

### Documentação da Belvo

| Item | Onde |
|---|---|
| Guia do produto — OFDA Brasil | https://developers.belvo.com/products/aggregation_brazil/aggregation-brazil-introduction |
| Documentação da API (OpenAPI) | https://developers.belvo.com/apis/belvoopenapispec |
| Widget — visão geral e eventos | https://developers.belvo.com/products/aggregation_brazil/ofda-widget-introduction |
| Widget — parâmetros de inicialização | https://developers.belvo.com/products/aggregation_brazil/ofda-widget-startup-configuration |
| Guia de integração com widget (payload do token) | https://developers.belvo.com/products/aggregation_brazil/aggregation-brazil-integration-widget |
| Webhooks | https://developers.belvo.com/docs/webhooks |
| Erros da API | https://developers.belvo.com/developer_resources/resources-belvo-api-errors |
| Dicionário de dados | https://github.com/belvo-finance/belvo-finance-opensource/tree/main/documentation/data_dictionaries |
| Central de ajuda | https://support.belvo.com/hc/en-us |

**Avisos de integridade:** a persona Juliana é **fictícia**, ancorada em dados secundários
públicos. A validação primária teve **n=10** e **não alcançou o público-alvo** (baixa renda, alto
endividamento) — toda decisão derivada dela é provisória e está marcada como tal neste
arquivo. Não apresente nenhuma dessas conclusões como fato estabelecido na interface ou na
documentação do protótipo.
