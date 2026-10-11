/**
 * Todas as strings do Respira (docs/contexto-produto.md §11). A escrita É o produto.
 *
 * Regras: português do Brasil, segunda pessoa, frases curtas, sempre com o
 * número da própria pessoa, taxa em % ao ano, toda má notícia com o próximo
 * passo. Nada de jargão, culpa, promessa de resultado ou "Open Finance" como
 * se todo mundo soubesse o que é.
 */
import type { Evento, Metodo } from './api';
import { mesAno, meses, nomeMes, diaMes, ordinalMes } from './datas';
import { brl, deDecimalLivre, percentual, type Centavos } from './money';

const r$ = (c: Centavos) => brl(c, { semCentavos: true });
/** Valor que vem como texto no contexto de um evento. */
const r$s = (texto: unknown) => {
  const c = typeof texto === 'string' ? deDecimalLivre(texto) : null;
  return c === null ? '—' : r$(c);
};
const pctAno = (texto: unknown) => (typeof texto === 'string' ? `${percentual(texto, 0)} ao ano` : '');
const plural = (n: number, um: string, varios: string) => (n === 1 ? um : varios);

// --- marca e navegação ---------------------------------------------------------------

export const marca = {
  nome: 'Respira',
  promessa: 'Descubra quando você sai das dívidas',
  naoMovimenta: 'Este app não movimenta o seu dinheiro.',
};

export const nav = {
  inicio: 'Início',
  dividas: 'Dívidas',
  contas: 'Contas',
  raiox: 'Raio-X',
  plano: 'Plano',
  configuracoes: 'Configurações',
};

// --- modalidades -----------------------------------------------------------------------

export const modalidade: Record<string, { nome: string; frase: string }> = {
  CARTAO_FATURA: { nome: 'Fatura do cartão', frase: 'da fatura do cartão' },
  CARTAO_ROTATIVO: { nome: 'Rotativo do cartão', frase: 'do rotativo do cartão' },
  CARTAO_PARCELADO: { nome: 'Fatura parcelada', frase: 'da fatura parcelada' },
  CHEQUE_ESPECIAL: { nome: 'Cheque especial', frase: 'do cheque especial' },
  CREDITO_PESSOAL: { nome: 'Empréstimo pessoal', frase: 'do empréstimo pessoal' },
  CONSIGNADO: { nome: 'Consignado', frase: 'do consignado' },
  FIN_VEICULO: { nome: 'Financiamento de veículo', frase: 'do financiamento do veículo' },
  FIN_IMOVEL: { nome: 'Financiamento imobiliário', frase: 'do financiamento do imóvel' },
  CREDIARIO: { nome: 'Carnê / crediário', frase: 'do carnê' },
  OUTRO: { nome: 'Outra dívida', frase: 'de outra dívida' },
};

export const metodoNome: Record<
  Metodo,
  { titulo: string; curto: string; no: string; logica: string }
> = {
  AVALANCHE: {
    titulo: 'Mais econômico',
    curto: 'mais econômico',
    no: 'no mais econômico',
    logica: 'Começa pela dívida com a maior taxa. Paga menos juros no total.',
  },
  EQUILIBRADO: {
    titulo: 'Equilibrado',
    curto: 'equilibrado',
    no: 'no equilibrado',
    logica: 'Quita a menor dívida primeiro e depois segue pela taxa.',
  },
  SNOWBALL: {
    titulo: 'Bola de neve',
    curto: 'bola de neve',
    no: 'na bola de neve',
    logica: 'Começa pela menor dívida. Vitórias rápidas, mais juros no total.',
  },
};

// --- landing e cadastro ----------------------------------------------------------------------

export const landing = {
  titulo: 'Descubra quando você sai das dívidas',
  subtitulo:
    'O Respira lê suas dívidas direto do seu banco, calcula a data em que você fica livre delas e mostra o que pagar primeiro.',
  passos: [
    'Você autoriza, no app do seu banco, a leitura das suas contas.',
    'Em poucos minutos você vê quanto deve no total e quanto paga de juros.',
    'Você recebe um plano com uma data de saída — e ele se ajusta quando o mês aperta.',
  ],
  cta: 'Criar minha conta',
  entrar: 'Já tenho conta',
  continuar: 'Continuar de onde parei',
  gratuito: 'Gratuito. Sem cartão de crédito.',
};

export const entrar = {
  titulo: 'Entrar',
  email: 'E-mail',
  senha: 'Senha',
  enviar: 'Entrar',
  semConta: 'Ainda não tem conta?',
  criar: 'Criar conta',
  demoTitulo: 'Quer ver como funciona?',
  demoTexto: 'Entre na conta da Juliana, uma pessoa fictícia com cinco dívidas. Nenhum banco real é acessado.',
  demo: 'Entrar como Juliana (demonstração)',
  erros: {
    credenciais_invalidas: 'E-mail ou senha não conferem.',
    muitas_tentativas: 'Muitas tentativas seguidas. Espere 15 minutos e tente de novo.',
    email: 'Digite um e-mail válido.',
    senha: 'Digite sua senha.',
  } as Record<string, string>,
};

export const cadastro = {
  titulo: 'Criar sua conta',
  subtitulo: 'Não vamos perguntar quanto você deve. Isso a gente descobre junto.',
  email: 'E-mail',
  senha: 'Crie uma senha',
  senhaAjuda: 'Pelo menos 8 caracteres.',
  nome: 'Nome completo',
  nomeAjuda: 'Igual ao do seu banco.',
  cpf: 'CPF',
  cpfAjuda:
    'Seu banco usa o nome e o CPF para confirmar que é você na hora de autorizar. Não mostramos nem compartilhamos com mais ninguém.',
  pergunta: 'Você já tentou um plano para sair das dívidas antes?',
  perguntaAjuda: 'Opcional. Ajuda a sugerir o caminho que combina com você.',
  respostas: { sim: 'Sim, mas não deu certo', nao: 'Não, é a primeira vez', pular: 'Prefiro não responder' },
  enviar: 'Criar conta',
  jaTenho: 'Já tem conta?',
  entrar: 'Entrar',
  faltamCaracteres: (n: number) => `Faltam ${n} ${plural(n, 'caractere', 'caracteres')}.`,
  faltamDigitos: (n: number) => `Faltam ${n} ${plural(n, 'dígito', 'dígitos')}.`,
  erros: {
    email: 'Digite um e-mail completo, como nome@dominio.com.',
    senha: 'Use pelo menos 8 caracteres.',
    nome: 'Escreva nome e sobrenome, só com letras.',
    cpf: 'Esse CPF não é válido. Confira os números.',
    email_em_uso: 'Já existe uma conta com esse e-mail. Tente entrar.',
    cpf_em_uso: 'Já existe uma conta com esse CPF. Tente entrar.',
  } as Record<string, string>,
};

export const conta = {
  sair: 'Sair',
  demo: 'Demonstração',
};

// --- conexão (§9 etapa 3) ------------------------------------------------------------------

export const conectar = {
  titulo: 'Conectar seu banco',
  explicacao:
    'Seu banco vai mostrar uma tela para você autorizar a leitura — e só a leitura — das suas contas, cartões e empréstimos.',
  oQueLemos: 'O que lemos',
  lemos: ['Saldos e extratos das contas', 'Faturas, limites e rotativo dos cartões', 'Empréstimos e financiamentos'],
  oQueNao: 'O que não fazemos',
  naoFazemos: [
    'Não fazemos pagamentos nem transferências',
    'Não vemos nem guardamos sua senha do banco',
    'Não vendemos seus dados',
  ],
  revogar: 'Você pode cancelar a autorização a qualquer momento, em um toque, em Configurações.',
  cta: 'Conectar meu banco',
  ctaOutro: 'Conectar outro banco',
  umPorVez: 'Um banco por vez. Depois você pode conectar outro.',
  manual: 'Tenho um carnê ou dívida que não aparece aqui',
  seguir: 'Ver meu Raio-X',
  aguardando: {
    titulo: 'Continue na aba que abrimos',
    texto:
      'Escolha seu banco e autorize no app ou site dele. Quando terminar, esta tela avança sozinha.',
    concluido: 'Já concluí',
    cancelar: 'Cancelar',
    verificando: 'Verificando…',
    naoChegou: 'Ainda não recebemos a autorização. Se você já concluiu, espere alguns segundos.',
  },
  popupBloqueado: {
    titulo: 'Seu navegador bloqueou a nova aba',
    texto: 'Toque no botão abaixo para abrir a conexão segura.',
    link: 'Abrir conexão segura',
  },
  abrindo: 'Abrindo conexão segura…',
  conectados: (n: number) => `${n} ${plural(n, 'banco conectado', 'bancos conectados')}`,
  parcial: (ok: number, total: number) =>
    `${ok} de ${total} bancos conectados. Os dados que já chegaram aparecem no seu Raio-X.`,
  sucessoAba: {
    titulo: 'Pronto! Seu banco autorizou.',
    texto: 'Pode fechar esta aba e voltar para o Respira.',
    fallback: 'Continuar aqui',
    erro: 'Não conseguimos registrar a autorização.',
  },
  expirado: (banco: string) =>
    `A autorização do ${banco} expirou. Seus dados pararam de atualizar e seu plano está congelado.`,
  expiraEm: (banco: string, dias: number) =>
    `Em ${dias} ${plural(dias, 'dia', 'dias')} a autorização do ${banco} expira: seus dados param de atualizar e seu plano congela.`,
  reconectar: 'Reconectar',
};

/** Erros do widget traduzidos (callbacks de saída/evento, §7.4). */
export const errosConexao: Record<string, string> = {
  institution_down: 'O banco está fora do ar agora. Tente de novo em alguns minutos.',
  login_error: 'O banco não conseguiu confirmar seu acesso. Confira seus dados de login no app do banco e tente de novo.',
  too_many_sessions: 'Há muitas sessões abertas com o banco. Feche o app do banco e tente de novo.',
  unexpected_error: 'Algo deu errado do lado do banco. Tente de novo em alguns minutos.',
  ACCESS_TOKEN_NOT_VALID: 'A conexão demorou demais e expirou. Vamos começar de novo — leva menos de um minuto.',
  session_expired_ob: 'A conexão demorou demais e expirou. Vamos começar de novo — leva menos de um minuto.',
  institution_disabled: 'Esse banco está temporariamente indisponível para conexão.',
  consent_rejected: 'A autorização não foi concluída no banco. Se quiser, tente de novo.',
  link_de_outro_usuario: 'Essa autorização não é desta conta. Comece a conexão de novo por aqui.',
  link_nao_encontrado: 'Não encontramos essa autorização. Comece a conexão de novo por aqui.',
  cadastro_incompleto: 'Precisamos do seu nome completo e CPF para o banco confirmar que é você.',
  token_falhou: 'Não conseguimos abrir a conexão segura agora. Tente de novo em instantes.',
  belvo_nao_configurada:
    'A conexão com bancos ainda não está configurada: faltam as chaves da Belvo no backend/.env.',
  popup: 'Seu navegador bloqueou a nova aba.',
  abandono: 'Você saiu antes de autorizar. Sem problema — dá para tentar quando quiser.',
  servidor_indisponivel: 'Não conseguimos falar com o servidor do Respira. Confira se ele está rodando.',
  offline: 'Você está sem internet.',
  padrao: 'Não deu certo desta vez. Tente de novo em alguns minutos.',
};

export function erroConexao(codigo?: string | null): string {
  if (!codigo) return errosConexao.abandono!;
  return errosConexao[codigo] ?? errosConexao.padrao!;
}

// --- tela de espera da coleta (§7.5) ------------------------------------------------------------

export const coleta = {
  titulo: 'Conectamos sua conta. Estamos buscando seus dados no banco.',
  texto: 'Isso costuma levar de 30 segundos a 2 minutos.',
  recursos: {
    ACCOUNTS: 'contas',
    BILLS: 'faturas',
    TRANSACTIONS: 'transações',
    OWNERS: 'cadastro',
    INCOMES: 'renda',
    RECURRING_EXPENSES: 'gastos fixos',
  } as Record<string, string>,
  demorou: {
    titulo: 'Está demorando mais que o normal',
    texto:
      'Alguns bancos levam mais tempo para enviar os dados. Você pode tentar buscar de novo agora, ou fechar o app — quando voltar, o que tiver chegado estará aqui.',
    recarregar: 'Buscar de novo',
  },
};

// --- Raio-X (F2) ------------------------------------------------------------------------------

export const raiox = {
  titulo: 'Seu Raio-X',
  voceDeve: 'Você deve',
  emCompromissos: (n: number) => `em ${n} ${plural(n, 'compromisso', 'compromissos')}`,
  listaTitulo: 'Do mais caro para o mais barato',
  verTodas: (resto: number) => `+ ${resto} ${resto === 1 ? 'compromisso' : 'compromissos'} · ver todas as dívidas`,
  detalhes: 'Ver cada dívida, por banco',
  saiEm: 'Seguindo o plano, você sai das dívidas em',
  projecao: 'Projeção com',
  porMes: (valor: Centavos) => `${r$(valor)} por mês`,
  naoConverge: (cap: Centavos, minimo: Centavos | null) =>
    minimo
      ? `Com ${r$(cap)} por mês a dívida não diminui. São necessários pelo menos ${r$(minimo)} por mês.`
      : `Com ${r$(cap)} por mês a dívida não diminui.`,
  semHistorico:
    'Ainda não temos histórico suficiente para calcular quanto sobra por mês. No plano, você escolhe um valor que cabe no seu bolso.',
  cta: 'Ver meu plano de saída',
  composicao: 'Quanto cada uma pesa no total',
  comprometimento: (minimos: Centavos, renda: Centavos, pct: string) =>
    `Os mínimos somam ${r$(minimos)} por mês — ${percentual(pct, 0)} do que entra na sua conta (${r$(renda)}).`,
  vazio: {
    titulo: 'Nenhuma dívida encontrada',
    texto: 'Nas contas conectadas não apareceu nenhuma dívida. Se você tem carnê ou dívida com alguém, dá para incluir.',
  },
  semConexao: {
    titulo: 'Seu Raio-X aparece aqui',
    texto: 'Conecte seu banco para ver quanto você deve no total — sem digitar nada.',
  },
};

/** "Você deve R$ 8.260 em 5 compromissos e paga R$ 733 por mês só em juros; R$ 312 disso vem do rotativo do cartão." */
export function fraseRaioX(p: {
  total: Centavos;
  qtd: number;
  jurosMes: Centavos;
  maiorValor: Centavos;
  maiorModalidade: string | null;
}): string {
  if (p.jurosMes <= 0) {
    return `Você deve ${r$(p.total)} em ${p.qtd} ${plural(p.qtd, 'compromisso', 'compromissos')}, e ${plural(p.qtd, 'ele não cobra', 'nenhum deles cobra')} juros hoje.`;
  }
  const base = `Você deve ${r$(p.total)} em ${p.qtd} ${plural(p.qtd, 'compromisso', 'compromissos')} e paga ${r$(p.jurosMes)} por mês só em juros`;
  if (!p.maiorModalidade || p.qtd < 2 || p.maiorValor <= 0) return `${base}.`;
  const origem = modalidade[p.maiorModalidade]?.frase ?? 'de uma das dívidas';
  return `${base}; ${r$(p.maiorValor)} disso vem ${origem}.`;
}

/** O insight obrigatório do F2. */
export function alertaMinimo(crescimento: Centavos): string {
  return `Pagando só o mínimo, sua dívida não diminui — ela cresce ${r$(crescimento)} por mês.`;
}
export const alertaMinimoProximo = 'O plano abaixo mostra quanto por mês faz a dívida começar a cair.';
/** O total não cresce, mas uma dívida sim (o rotativo, quase sempre): o insight não pode sumir. */
export function alertaDividaCresce(descricao: string, crescimento: Centavos): string {
  return `${descricao}: pagando só o mínimo, ela não diminui — cresce ${r$(crescimento)} por mês.`;
}

// --- dívida (DebtCard) --------------------------------------------------------------------------

export const divida = {
  taxaAno: (taxaAnual: string) => `${percentual(taxaAnual, 0)} ao ano`,
  estimada: 'taxa estimada',
  estimadaAjuda:
    'O banco não informou a taxa desta dívida. Usamos a média do Banco Central para esse tipo de crédito.',
  parcelaEstimada: 'parcela estimada',
  parcelaEstimadaAjuda: 'O banco não informa o valor da parcela. Confira no seu contrato e corrija se precisar.',
  conferir: 'Conferir',
  minimo: 'mínimo',
  vence: (dia: number) => `vence dia ${dia}`,
  atraso: (dias: number) => `${dias} ${plural(dias, 'dia', 'dias')} em atraso`,
  jurosMes: (c: Centavos) => `${r$(c)} de juros por mês`,
  manual: 'incluída por você',
  quitada: 'quitada',
  cresce: (c: Centavos) => `pagando só o mínimo, cresce ${r$(c)} por mês`,
};

// --- dívidas (lista por banco) --------------------------------------------------------------------

export const dividas = {
  titulo: 'Suas dívidas',
  resumo: (qtd: number, credores: number, parcelas: Centavos) =>
    `${qtd} ${plural(qtd, 'compromisso', 'compromissos')} em ${credores} ${plural(credores, 'credor', 'credores')} · ${r$(parcelas)} de parcelas por mês`,
  livreEm: (mesAno: string) => `Seguindo o seu plano, você fica livre em ${mesAno}.`,
  semPlano: 'Você ainda não escolheu um plano para pagar tudo isso.',
  verPlano: 'Ver o plano',
  montarPlano: 'Montar meu plano',
  parcelasPagas: (pagas: number, total: number) => `${pagas} de ${total} parcelas pagas`,
  contratado: (c: Centavos) => `contratado: ${r$(c)}`,
  terminaEm: (mesAno: string) => `contrato até ${mesAno}`,
  ordem: (n: number) => `${n}ª na ordem de pagamento`,
  esteMes: (c: Centavos) => `este mês: ${r$(c)}`,
  quitadaEm: (mesAno: string) => `quitada em ${mesAno}`,
  verExtrato: 'Ver extrato',
  progresso: 'Parcelas do contrato já pagas',
  vazio: {
    titulo: 'Nenhuma dívida por aqui',
    texto: 'Conecte um banco ou inclua uma dívida que não aparece no Open Finance.',
  },
};

// --- plano (F3) ------------------------------------------------------------------------------------

export const plano = {
  titulo: 'Seu plano de saída',
  subtitulo: 'Três caminhos para a mesma saída. A diferença está em quanto custa e quando vem a primeira vitória.',
  slider: 'Quanto você pode colocar por mês',
  sliderAjuda: (calculada: Centavos) =>
    `Calculamos ${r$(calculada)} a partir do que entrou e saiu da sua conta nos últimos meses, já guardando 10% para imprevistos.`,
  sliderSemHistorico: 'Escolha um valor que caiba no seu bolso. Você pode mudar quando quiser.',
  voltarCalculado: 'Voltar ao valor calculado',
  livreEm: 'Livre em',
  juros: 'Juros no total',
  primeiraVitoria: 'Primeira dívida some no',
  recomendado: 'Sugerido para você',
  motivo: {
    PADRAO: 'Sugerimos o mais econômico porque ele custa menos juros no total.',
    JA_DESISTIU:
      'Sugerimos o equilibrado porque você contou que já tentou antes: ver uma dívida sumir logo ajuda a seguir em frente.',
  },
  escolha: 'A escolha é sua — os três continuam aqui.',
  ativar: 'Começar este plano',
  ativando: 'Preparando seu plano…',
  trajetoria: 'Quanto você vai dever, mês a mês',
  trajetoriaAjuda: 'Projeção. A data se ajusta conforme os meses acontecem.',
  cronograma: 'Ordem de pagamento',
  morreNo: (mes: number) => `quitada no ${ordinalMes(mes)}`,
  esteMes: (c: Centavos) => `${r$(c)} este mês`,
  soMinimo: (
    juros: Centavos,
    saldo: Centavos,
    horizonte: number,
    jurosPlano: Centavos,
    converge: boolean,
  ) =>
    converge
      ? `Pagando só os mínimos de hoje, você pagaria ${r$(juros)} de juros. Pelo plano, ${r$(jurosPlano)}.`
      : `Pagando só os mínimos de hoje, em ${meses(horizonte)} você teria pago ${r$(juros)} de juros e ainda deveria ${r$(saldo)}. Pelo plano, paga ${r$(jurosPlano)} e termina sem dever nada.`,
  jurosEvitados: 'Juros evitados',
  projecaoAviso: 'Tudo aqui é projeção, feita com os dados de hoje.',
  ativado: 'Plano ativado',
};

/** A frase que faz o trabalho da comparação (§4 F3). */
export function fraseComparacao(
  escolhida: { metodo: Metodo; meses: number; juros: Centavos; primeira: number | null },
  economica: { meses: number; juros: Centavos; primeira: number | null },
): string {
  if (escolhida.metodo === 'AVALANCHE') {
    const p = escolhida.primeira ? ` A primeira dívida some no ${ordinalMes(escolhida.primeira)}.` : '';
    return `Pelo caminho mais econômico você fica livre em ${meses(escolhida.meses)} e paga ${r$(escolhida.juros)} de juros no total.${p}`;
  }
  const { curto: nome, no } = metodoNome[escolhida.metodo];
  const diff = (escolhida.juros - economica.juros) as Centavos;
  const custo =
    diff > 0
      ? `paga ${r$(diff)} a mais de juros do que pelo mais econômico, que leva ${economica.meses}`
      : `paga o mesmo de juros que o mais econômico, que leva ${economica.meses}`;
  const vitoria =
    escolhida.primeira && economica.primeira && escolhida.primeira < economica.primeira
      ? ` — só que nele a primeira dívida some no ${ordinalMes(economica.primeira)}, e ${no} ela some já no ${escolhida.primeira}º.`
      : '.';
  return `Pelo caminho ${nome} você fica livre em ${meses(escolhida.meses)} e ${custo}${vitoria}`;
}

// --- início (F4) -------------------------------------------------------------------------------------

export const inicio = {
  saudacao: (apelido: string) => `Oi, ${apelido}`,
  livreEm: 'Você fica livre das dívidas em',
  faltam: (n: number) => `faltam ${meses(n)}`,
  abatido: (abatido: Centavos, inicial: Centavos) => `${r$(abatido)} de ${r$(inicial)} já pagos`,
  esteMes: 'O que fazer este mês',
  esteMesAjuda: 'Nesta ordem. Se sobrar, vai para a primeira da lista.',
  minimo: 'só o mínimo',
  principal: 'prioridade',
  alertas: 'Precisa da sua atenção',
  marcos: 'Dívidas quitadas',
  semMarcos: 'Cada dívida quitada aparece aqui, com a data.',
  historico: 'Mês a mês',
  previstoRealizado: (realizado: Centavos, previsto: Centavos) => `${r$(realizado)} de ${r$(previsto)} previstos`,
  semPlano: {
    titulo: 'Você ainda não tem um plano',
    texto: 'Veja seu Raio-X e escolha o caminho de saída. Leva um minuto.',
    cta: 'Ver meu Raio-X',
  },
  concluido: {
    titulo: 'Você saiu das dívidas.',
    texto: 'Todas as dívidas do plano foram quitadas.',
  },
  copiloto: 'Copiloto',
  copilotoEmBreve: 'Em breve: tire dúvidas sobre suas dívidas em linguagem simples. Ainda não está disponível.',
  demo: {
    titulo: 'Modo demonstração',
    texto: 'Simule a passagem de um mês para ver o plano se ajustar. Só existe na conta da Juliana.',
    seguir: 'Simular mês seguindo o plano',
    dificil: 'Simular um mês difícil',
    reiniciar: 'Reiniciar demonstração',
    reiniciarAjuda: 'Volta a Juliana ao começo: as cinco dívidas, sem plano.',
  },
};

/** "Mês ruim" sem linguagem de falha (§9 etapa 6). */
export function fraseAcompanhamento(a: {
  mes: string;
  previsto: Centavos;
  realizado: Centavos;
  dataAnterior: string | null;
  dataNova: string | null;
}): string {
  const falta = (a.previsto - a.realizado) as Centavos;
  if (falta <= 0) {
    return a.dataNova
      ? `Em ${nomeMes(a.mes)} entraram ${r$(a.realizado)} no plano. Sua data continua ${mesAno(a.dataNova)}.`
      : `Em ${nomeMes(a.mes)} entraram ${r$(a.realizado)} no plano.`;
  }
  const data =
    a.dataNova && a.dataAnterior && a.dataNova !== a.dataAnterior
      ? `sua data nova é ${mesAno(a.dataNova)}`
      : a.dataNova
        ? `sua data continua ${mesAno(a.dataNova)}`
        : 'recalculamos sua data';
  return `Em ${nomeMes(a.mes)} entraram ${r$(falta)} a menos no plano; ${data}.`;
}

// --- alertas (§8.3) — sempre ação concreta + valor em reais ----------------------------------------

/** Categorias da Belvo (enum de TransactionOpenFinanceBrazil.category) em português. */
const categoriaNome: Record<string, string> = {
  'Online Platforms & Leisure': 'delivery, streaming e lazer',
  'Food & Groceries': 'mercado',
  'Personal Shopping': 'compras pessoais',
  'Transport & Travel': 'transporte',
  'Bills & Utilities': 'contas da casa',
  'Home & Life': 'casa e saúde',
  'Fees & Charges': 'tarifas',
  'Credits & Loans': 'crédito e empréstimos',
  'Income & Payments': 'renda e recebimentos',
  'Investments & Savings': 'investimentos',
  Deposits: 'depósitos',
  Transfers: 'transferências',
  Taxes: 'impostos',
  Insurance: 'seguros',
  'Withdrawal & ATM': 'saques',
  Unknown: 'outros',
};

export type Tom = 'fato' | 'atencao' | 'conquista' | 'info';

export function mensagemEvento(e: Evento): { titulo: string; texto: string; tom: Tom } {
  const c = e.contexto;
  const s = (k: string) => (typeof c[k] === 'string' ? (c[k] as string) : '');
  const n = (k: string) => (typeof c[k] === 'number' ? (c[k] as number) : 0);
  switch (e.tipo) {
    case 'ENTRADA_ROTATIVO':
      return {
        tom: 'fato',
        titulo: `Sua fatura do ${s('instituicao')} entrou no rotativo`,
        texto: `São ${r$s(c.saldo)} a ${pctAno(c.taxa_anual)}: ${r$s(c.juros_mes)} de juros por mês. Pagar mais que o mínimo nesta fatura já reduz os juros do próximo mês.`,
      };
    case 'ATRASO_IMINENTE':
      return {
        tom: 'atencao',
        titulo: `${s('descricao')} vence ${n('dias') === 0 ? 'hoje' : `em ${n('dias')} ${plural(n('dias'), 'dia', 'dias')}`}`,
        texto: `A parcela é de ${r$s(c.parcela)} e sua conta tem ${r$s(c.saldo_conta)}. Faltam ${r$s(c.falta)} até ${diaMes(s('vencimento'))} para não atrasar.`,
      };
    case 'ATRASO_CONFIRMADO':
      return {
        tom: 'fato',
        titulo: `${s('descricao')} está com ${n('dias')} ${plural(n('dias'), 'dia', 'dias')} de atraso`,
        texto: `Pagar a parcela de ${r$s(c.parcela)} interrompe a multa e os juros de atraso. Ela já está no seu plano.`,
      };
    case 'CHEQUE_ESPECIAL':
      return {
        tom: 'fato',
        titulo: `Você está usando ${r$s(c.usado)} do cheque especial`,
        texto: c.juros_mes
          ? `Ele custa ${pctAno(c.taxa_anual)}: ${r$s(c.juros_mes)} de juros por mês. No plano, ele tem data para acabar.`
          : 'No plano, ele tem data para acabar.',
      };
    case 'PICO_CATEGORIA': {
      const cat = categoriaNome[s('categoria')] ?? s('categoria').toLowerCase();
      return {
        tom: 'atencao',
        titulo: `Em ${nomeMes(s('mes'))}, ${cat} somou ${r$s(c.gasto)}`,
        texto: `São ${r$s(c.excesso)} acima do normal (${r$s(c.normal)}). Se voltar ao normal, esse valor pode ir para o plano.`,
      };
    }
    case 'DESVIO_PLANO': {
      const novaData = s('data_nova');
      const anterior = s('data_anterior');
      const data =
        novaData && anterior && novaData !== anterior
          ? `Sua data nova é ${mesAno(novaData)}`
          : novaData
            ? `Sua data continua ${mesAno(novaData)}`
            : 'Recalculamos sua data';
      return {
        tom: 'atencao',
        titulo: `Em ${nomeMes(s('mes'))} entraram ${r$s(c.falta)} a menos no plano`,
        texto: `${data}. Colocando ${r$s(c.reposicao_mensal)} a mais nos próximos ${n('meses_reposicao')} meses, você repõe o que faltou.`,
      };
    }
    case 'DIVIDA_QUITADA':
      return {
        tom: 'conquista',
        titulo: `${s('descricao')}: quitada!`,
        texto: `Os ${r$s(c.parcela_liberada)} por mês que iam para ela agora vão para a próxima da fila.`,
      };
    default:
      return { tom: 'info', titulo: 'Novidade no seu plano', texto: '' };
  }
}

export const alerta = {
  entendi: 'Entendi',
  saibaMais: 'Entenda',
};

// --- privacidade -----------------------------------------------------------------------------------

export const privacidade = {
  titulo: 'Configurações',
  seusDados: 'Seus dados',
  nome: 'Nome completo',
  email: 'E-mail',
  cpf: 'CPF',
  cpfAjuda: 'Mostramos só parte do CPF. Ele é usado apenas para o banco confirmar que é você.',
  privacidadeTitulo: 'Privacidade e bancos',
  intro: 'Você controla o que o Respira lê. Tudo aqui vale na hora.',
  lemosTitulo: 'O que lemos, com a sua autorização',
  naoAcessamosTitulo: 'O que não acessamos',
  naoAcessamos: [
    'Senhas do banco — você autoriza no app do próprio banco',
    'Pagamentos ou transferências — este app não movimenta o seu dinheiro',
    'Investimentos e previdência',
  ],
  conexoes: 'Bancos conectados',
  semConexoes: 'Nenhum banco conectado.',
  revogar: 'Revogar e apagar dados',
  revogarConfirma: (banco: string) =>
    `Revogar a autorização do ${banco} e apagar do Respira todos os dados que vieram dele?`,
  revogarSim: 'Sim, revogar',
  cancelar: 'Cancelar',
  revogado: 'Autorização revogada e dados apagados.',
  outrosCanais:
    'Você também pode ver e cancelar autorizações no app do seu banco ou no Meu Portal Belvo (meuportal.belvo.com).',
  status: {
    ATIVO: 'Ativa',
    EXPIRADO: 'Expirada',
    REVOGADO: 'Revogada',
    ERRO: 'Com problema',
    PENDENTE: 'Pendente',
  } as Record<string, string>,
  expiraEm: (data: string) => `válida até ${data}`,
  atualizado: (quando: string) => `atualizado em ${quando}`,
  atualizar: 'Buscar dados novos agora',
  demoNaoExclui: 'A conta de demonstração não pode ser excluída. Use "Reiniciar demonstração" na tela inicial.',
  excluirTitulo: 'Excluir minha conta',
  excluirTexto:
    'Revoga todas as autorizações nos bancos e apaga todos os seus dados do Respira. Não dá para desfazer.',
  excluir: 'Excluir conta e dados',
  excluirConfirma: 'Tem certeza? Tudo será apagado agora.',
  excluirSim: 'Sim, excluir tudo',
};

// --- cadastro manual assistido (§7.9) ----------------------------------------------------------------

export const manual = {
  titulo: 'Incluir uma dívida',
  subtitulo:
    'Carnês, crediário de loja e dívidas com pessoas conhecidas não chegam pelo banco. Sem elas, o total fica errado.',
  credor: 'Com quem é a dívida?',
  credorExemplo: 'Ex.: Loja D, tia Cida',
  tipo: 'Que tipo de dívida é?',
  tipos: { CREDIARIO: 'Carnê ou crediário de loja', OUTRO: 'Dívida com pessoa conhecida ou outra' },
  saldo: 'Quanto falta pagar?',
  saldoAjuda: 'Some as parcelas que ainda faltam, se não souber o valor exato.',
  parcela: 'Valor da parcela',
  taxa: 'Juros ao mês (opcional)',
  taxaAjuda: "Está no carnê, geralmente ao lado de 'juros ao mês'. Se não souber, deixe em branco que estimamos.",
  dia: 'Dia do vencimento (opcional)',
  atraso: 'Está atrasada? Há quantos dias? (opcional)',
  salvar: 'Incluir no meu Raio-X',
  erros: {
    credor: 'Diga com quem é a dívida.',
    valor: 'Digite um valor, como 380 ou 1.250,50.',
    taxa: 'Use um número entre 0,1 e 20 — por exemplo 3,5.',
    dia: 'Use um dia entre 1 e 31.',
  },
};

export const corrigir = {
  titulo: 'Conferir dívida',
  parcela: 'Valor da parcela',
  taxa: 'Juros ao mês',
  salvar: 'Salvar',
  ajuda: 'Só corrija o que o banco não informou. O saldo continua vindo do banco.',
};

// --- estados gerais ------------------------------------------------------------------------------------

export const estados = {
  carregando: 'Carregando…',
  erroTitulo: 'Não conseguimos carregar agora',
  erroTexto: 'Tente de novo em instantes. Seus dados estão seguros.',
  tentar: 'Tentar de novo',
  offline: 'Você está sem internet. Mostrando os últimos dados carregados.',
  atualizadoEm: (quando: string) => `Atualizado em ${quando}`,
  voltar: 'Voltar',
};

export const licao = {
  titulo: 'Entenda',
  voltar: 'Voltar',
};

// --- PFM: contas, faturas e extrato ------------------------------------------------------

/** ``type`` da Belvo (ex.: CONTA_DEPOSITO_A_VISTA) em texto legível. */
export function tipoBelvo(tipo: string | null): string | null {
  if (!tipo) return null;
  const t = tipo.replace(/_/g, ' ').toLowerCase().trim();
  return t.charAt(0).toUpperCase() + t.slice(1);
}

export const pfm = {
  titulo: 'Suas contas',
  todos: 'Todos',
  conectarOutro: '+ Conectar banco',
  emConta: 'Em conta',
  faturasAbertas: 'Faturas em aberto',
  semBancos: {
    titulo: 'Nenhum banco conectado',
    texto: 'Conecte seu banco para ver saldos, cartões, faturas e extrato num lugar só.',
  },
  coletando: 'Buscando seus dados no banco…',
  atualizado: (quando: string) => `atualizado em ${quando}`,
  atualizar: 'Atualizar',
  cancelar: 'Cancelar',
  tipo: {
    CORRENTE: 'Conta corrente',
    POUPANCA: 'Poupança',
    PAGAMENTO: 'Conta de pagamento',
    CARTAO_CREDITO: 'Cartão de crédito',
    EMPRESTIMO: 'Empréstimo',
    FINANCIAMENTO: 'Financiamento',
    ADIANTAMENTO: 'Cheque especial',
    OUTRO: 'Outro produto',
  } as Record<string, string>,
  saldo: 'Saldo',
  disponivel: 'Disponível',
  limiteChequeEspecial: (c: Centavos) => `limite do cheque especial: ${r$(c)}`,
  saldoDevedor: 'Saldo devedor',
  limite: 'Limite',
  usado: 'Usado',
  faturaAtual: 'Fatura atual',
  semFatura: 'Nenhuma fatura recebida ainda.',
  vence: (data: string) => `vence em ${data}`,
  venceu: (data: string) => `venceu em ${data}`,
  minimo: 'Mínimo',
  pago: 'Pago',
  faltaPagar: 'Falta pagar',
  faturas: 'Faturas anteriores',
  pagamentos: 'Pagamentos',
  pagoEm: (data: string) => `Pago em ${data}`,
  minimoAPagar: (c: Centavos) => `Mínimo a pagar: ${r$(c)}`,
  situacao: {
    PAGA: 'Paga',
    EM_ABERTO: 'Em aberto',
    PARCIAL: 'Paga em parte',
    ATRASADA: 'Atrasada',
  } as Record<string, string>,
  parcelada: 'parcelada',
  extrato: 'Extrato',
  periodos: { 0: 'Tudo', 30: '30 dias', 60: '60 dias', 90: '90 dias', 120: '120 dias' } as Record<number, string>,
  agencia: 'Agência',
  conta: 'Conta',
  semCategoria: 'Sem categoria',
  abasCartao: 'Faturas e extrato do cartão',
  abas: { faturas: 'Faturas', extrato: 'Extrato' },
  detalhe: {
    descricao: 'Descrição',
    data: 'Data',
    dataHora: 'Data e hora',
    tipoOperacao: 'Tipo de operação',
    finalCartao: 'Final do cartão',
    fatura: 'Fatura',
    valor: 'Valor',
    categoria: 'Categoria',
    subcategoria: 'Subcategoria',
    estabelecimento: 'Estabelecimento',
    site: 'Site',
  },
  filtros: { TODAS: 'Todas', ENTRADA: 'Entradas', SAIDA: 'Saídas' },
  buscar: 'Buscar no extrato',
  buscarExemplo: 'ex.: mercado, pix, salário',
  entradas: 'Entradas',
  saidas: 'Saídas',
  semTransacoes: 'Nenhuma transação encontrada com esses filtros.',
  pagina: (p: number, total: number) => `Página ${p} de ${total}`,
  anterior: 'Anterior',
  proxima: 'Próxima',
  quantidade: (n: number) => `${n} ${plural(n, 'transação', 'transações')}`,
  voltar: '← Suas contas',
  verContas: 'Ver minhas contas',
  semDividas: {
    titulo: 'Nenhuma dívida nas contas conectadas',
    texto: 'Nada para quitar por aqui. Acompanhe saldos, faturas e extrato em Contas.',
  },
};
