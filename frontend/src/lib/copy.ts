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
  demoTexto: 'Entre na conta da Juliana, uma pessoa fictícia com dívidas em três bancos. Nenhum banco real é acessado.',
  demo: 'Entrar como Juliana (demonstração)',
  erros: {
    credenciais_invalidas: 'E-mail ou senha não conferem.',
    muitas_tentativas: 'Muitas tentativas seguidas. Espere 15 minutos e tente de novo.',
    muitas_demos: 'Muitas demonstrações abertas daqui. Espere uma hora e tente de novo.',
    demos_esgotadas: 'A demonstração está cheia agora. Tente de novo em alguns minutos.',
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
  confirmarSenha: 'Confirme a senha',
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
    confirmarSenha: 'As duas senhas não são iguais.',
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
  modo_publico:
    'Na versão pública, a conexão com bancos reais fica desligada por segurança. Use a demonstração ou inclua dívidas à mão.',
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
  conectado: 'Conta conectada',
  buscando: 'Estamos buscando seus dados no banco',
  texto: 'Isso costuma levar de 30 segundos a 2 minutos.',
  progresso: (prontas: number, total: number) =>
    total ? `${prontas} de ${total} ${total === 1 ? 'etapa' : 'etapas'}` : 'Começando…',
  tempo: (s: number) => (s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, '0')} s`),
  bancoPronto: 'Pronto',
  estados: { RECEBIDO: 'Pronto', AGUARDANDO: 'Buscando…', INDISPONIVEL: 'Indisponível' } as Record<string, string>,
  etapas: {
    ACCOUNTS: { nome: 'Contas e cartões', detalhe: 'saldos, limites, empréstimos' },
    BILLS: { nome: 'Faturas', detalhe: 'valor, mínimo e vencimento' },
    TRANSACTIONS: { nome: 'Transações', detalhe: 'até 12 meses de histórico' },
    INCOMES: { nome: 'Renda', detalhe: 'quanto entra por mês' },
    RECURRING_EXPENSES: { nome: 'Gastos fixos', detalhe: 'contas que se repetem' },
  } as Record<string, { nome: string; detalhe: string }>,
  podeSair: 'Você pode continuar usando o app: os dados aparecem aqui assim que chegarem.',
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
  // O Raio-X responde "quanto e quando"; esta tela, "o quê, onde e em que ordem".
  explicacao: 'Cada dívida em detalhe: contrato, parcelas e a ordem no plano. O resumo, com a data de saída, fica no ',
  explicacaoLink: 'Raio-X',
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
  // N4 (Fase 7): filtrar e ordenar
  ordenar: 'Ordenar',
  ordens: {
    plano: 'Ordem do plano',
    banco: 'Por banco',
    taxa: 'Maior taxa',
    saldo: 'Maior saldo',
    vencimento: 'Próximo vencimento',
  } as Record<string, string>,
  filtrar: 'Filtrar',
  banco: 'Banco ou credor',
  tipo: 'Tipo',
  tipos: {
    cartao: 'Cartão',
    emprestimo: 'Empréstimo',
    financiamento: 'Financiamento',
    cheque: 'Cheque especial',
    manual: 'Incluída à mão',
  } as Record<string, string>,
  situacao: 'Situação',
  situacoes: { atraso: 'Em atraso', estimada: 'Com valor estimado', quitadas: 'Quitadas' } as Record<string, string>,
  limpar: 'Limpar filtros',
  mostrando: (n: number, de: number, total: Centavos) =>
    `Mostrando ${n} de ${de} ${plural(de, 'dívida', 'dívidas')} · ${r$(total)}`,
  nenhumaNoFiltro: 'Nenhuma dívida com esses filtros.',
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
  primeiraQuitada: '1ª dívida quitada',
  recomendado: 'Sugerido para você',
  conferidoOracle: 'Conferido no Oracle',
  conferidoOracleExplica:
    'Este plano foi calculado duas vezes — aqui e por um motor separado dentro do banco de dados Oracle — e os dois deram o mesmo resultado, centavo por centavo.',
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
  // A7: a soma do mês costuma passar do saldo em conta; o pagamento acompanha o salário.
  esteMesAjuda: 'Valores para pagar ao longo do mês, conforme o salário entrar. Nesta ordem; se sobrar, vai para a primeira da lista.',
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
    reiniciarAjuda: 'Volta a Juliana ao começo: os três bancos e as oito dívidas, sem plano.',
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
// --- Rótulos vindos da Belvo, em pt-BR (A6, Fase 7) ---------------------------------
// Único lugar que traduz categorias, subcategorias, tipos de produto e nomes de
// fatura. O que não estiver no dicionário cai em "Outros" — nunca em inglês na tela.

// Taxonomia V2 da Belvo (Fase 7): categoria → nome, e subcategoria → nome.
// A tela mostra a subcategoria quando existe ("Restaurantes e lanchonetes"),
// que diz muito mais do que a categoria ("Alimentação").
type Taxonomia = Record<string, { nome: string; subs: Record<string, string> }>;
const TAXONOMIA: Taxonomia = {
  Transfers: { nome: 'Transferências', subs: {} },
  'Income & Payments': {
    nome: 'Renda e recebimentos',
    subs: {
      Freelance: 'Trabalho autônomo',
      Interest: 'Rendimentos',
      Retirement: 'Aposentadoria',
      Salary: 'Salário',
      Government: 'Benefícios do governo',
      Rent: 'Aluguel recebido',
      Other: 'Outras entradas',
    },
  },
  'Bills & Utilities': {
    nome: 'Contas da casa',
    subs: {
      'Electricity & Energy': 'Luz e gás',
      Rent: 'Aluguel',
      Telecommunications: 'Internet e telefone',
      Water: 'Água',
      Other: 'Outras contas da casa',
    },
  },
  'Credits & Loans': {
    nome: 'Crédito e empréstimos',
    subs: {
      Personal: 'Empréstimo pessoal',
      Auto: 'Financiamento de veículo',
      Mortgage: 'Financiamento imobiliário',
      'Pay Advance': 'Consignado e antecipação',
      'Credit Card': 'Fatura do cartão',
      Instalment: 'Parcelamentos',
      'Interest & Charges': 'Juros e encargos',
      Other: 'Outros créditos',
    },
  },
  'Fees & Charges': {
    nome: 'Tarifas e ajustes',
    subs: {
      Adjustments: 'Ajustes',
      'Bank Fees': 'Tarifas bancárias',
      Chargeback: 'Contestação de compra',
      Refund: 'Estornos',
      'Blocked Balances': 'Saldo bloqueado',
      Alimony: 'Pensão alimentícia',
      Other: 'Outras tarifas',
    },
  },
  'Investments & Savings': {
    nome: 'Investimentos',
    subs: {
      Savings: 'Poupança',
      'Fixed Income': 'Renda fixa',
      Equity: 'Ações',
      'Investment Funds': 'Fundos de investimento',
      Derivatives: 'Derivativos',
      Cryptocurrencies: 'Criptomoedas',
      Other: 'Outros investimentos',
    },
  },
  Taxes: {
    nome: 'Impostos e taxas',
    subs: {
      'Income Tax': 'Imposto de renda',
      'Auto Tax & Fees': 'IPVA e taxas do veículo',
      'Real Estate Tax & Fees': 'IPTU e taxas do imóvel',
      'Government Fees': 'Taxas do governo',
      Donation: 'Doações',
      'Tax Return': 'Restituição',
      Other: 'Outros impostos',
    },
  },
  Deposits: { nome: 'Depósitos', subs: {} },
  'Withdrawal & ATM': { nome: 'Saques', subs: {} },
  'Personal Shopping': {
    nome: 'Compras',
    subs: {
      'Books & News': 'Livros e revistas',
      'Clothing & Accessories': 'Roupas e acessórios',
      Electronics: 'Eletrônicos',
      'E-commerce': 'Compras online',
      Gifts: 'Presentes',
      'Office Supplies': 'Papelaria e escritório',
      'Pet Supplies': 'Pet shop',
      'Department Store': 'Lojas de departamento',
      Other: 'Outras compras',
    },
  },
  'Transport & Travel': {
    nome: 'Transporte e viagens',
    subs: {
      'Auto Expenses': 'Manutenção do veículo',
      'Auto Rental': 'Aluguel de veículo',
      Flights: 'Passagens aéreas',
      Gas: 'Combustível',
      Accommodation: 'Hospedagem',
      'Parking & Tolls': 'Estacionamento e pedágio',
      'Public Transit': 'Transporte público',
      'Taxis & Rideshares': 'Táxi e app de transporte',
      'Mileage Programs': 'Programas de milhas',
      Other: 'Outras despesas de viagem',
    },
  },
  'Online Platforms & Leisure': {
    nome: 'Lazer e assinaturas',
    subs: {
      Gambling: 'Apostas',
      'Music & Audio': 'Música e áudio',
      'Events, Parks and Museums': 'Eventos, parques e museus',
      'Movie & Video': 'Filmes e streaming',
      Gaming: 'Jogos',
      Lottery: 'Loteria',
      'Apps, Software and Cloud Services': 'Apps e serviços digitais',
      Other: 'Outros lazeres',
    },
  },
  'Food & Groceries': {
    nome: 'Alimentação',
    subs: {
      'Alcohol & Tobacco': 'Bebidas e tabaco',
      'Bars & Nightclubs': 'Bares e baladas',
      'Bakery & Coffee': 'Padaria e café',
      Delivery: 'Delivery',
      Restaurants: 'Restaurantes e lanchonetes',
      Groceries: 'Mercado',
      'Convenience Store': 'Lojas de conveniência',
      Other: 'Outros gastos com alimentação',
    },
  },
  'Home & Life': {
    nome: 'Casa e saúde',
    subs: {
      'Home Decor & Appliances': 'Móveis e eletrodomésticos',
      Health: 'Saúde',
      'Gyms & Fitness': 'Academia',
      'Hair & Beauty': 'Beleza',
      'Laundry & Dry Cleaning': 'Lavanderia',
      Pharmacies: 'Farmácia',
      'Veterinary Services': 'Veterinário',
      Education: 'Educação',
      'Professional Services': 'Serviços profissionais',
      Other: 'Outros gastos com casa e saúde',
    },
  },
  Insurance: {
    nome: 'Seguros',
    subs: {
      'Home Insurance': 'Seguro residencial',
      'Auto Insurance': 'Seguro do veículo',
      'Health & Life Insurance': 'Seguro saúde e de vida',
      Other: 'Outros seguros',
    },
  },
  Unknown: { nome: 'Outros', subs: {} },
};

// product_type do Open Finance Brasil (contas, cartões e operações de crédito).
const TIPOS_PRODUTO: Record<string, string> = {
  CONTA_DEPOSITO_A_VISTA: 'Conta corrente',
  CONTA_POUPANCA: 'Poupança',
  CONTA_PAGAMENTO_PRE_PAGA: 'Conta de pagamento',
  EMPRESTIMOS: 'Empréstimo',
  FINANCIAMENTOS: 'Financiamento',
  FINANCIAMENTOS_RURAIS: 'Financiamento rural',
  FINANCIAMENTOS_IMOBILIARIOS: 'Financiamento imobiliário',
  ADIANTAMENTO_A_DEPOSITANTES: 'Cheque especial',
  DIREITOS_CREDITORIOS_DESCONTADOS: 'Antecipação de recebíveis',
  STANDARD: 'Standard',
  GOLD: 'Gold',
  PLATINUM: 'Platinum',
  INFINITE: 'Infinite',
  BLACK: 'Black',
  ELECTRON: 'Electron',
  INTERNACIONAL: 'Internacional',
  NACIONAL: 'Nacional',
  OUTROS: 'Outros',
};

const MESES_EN: Record<string, string> = {
  Jan: 'jan', Feb: 'fev', Mar: 'mar', Apr: 'abr', May: 'mai', Jun: 'jun',
  Jul: 'jul', Aug: 'ago', Sep: 'set', Oct: 'out', Nov: 'nov', Dec: 'dez',
};

const REGIOES: Record<string, string> = {
  'sa-saopaulo-1': 'São Paulo (Brasil)',
  'sa-vinhedo-1': 'Vinhedo (Brasil)',
};

/** "sa-saopaulo-1" → "São Paulo (Brasil)". */
export function regiaoNome(regiao: string | null): string {
  return (regiao && REGIOES[regiao]) || regiao || 'Brasil';
}

/** Categoria da Belvo → nome ("Food & Groceries" → "Alimentação"); desconhecida → "Outros". */
export function categoriaNome(categoria: string | null | undefined): string {
  return (categoria && TAXONOMIA[categoria]?.nome) || 'Outros';
}

/** Subcategoria V2 → nome ("Restaurants" em Food & Groceries → "Restaurantes e lanchonetes"). */
export function subcategoriaNome(categoria: string | null | undefined, sub: string | null | undefined): string | null {
  if (!sub) return null;
  return (categoria && TAXONOMIA[categoria]?.subs[sub]) || null;
}

/**
 * Nome de um grupo de gasto: a categoria principal. As subcategorias da Belvo
 * erram demais para ficar à vista (teste com conta real, Fase 7) — só viram
 * filtro no detalhe da categoria. Chaves antigas "Categoria::Subcategoria"
 * (alertas e links de antes) também caem na categoria.
 */
export function nomeGasto(chave: string | null | undefined): string {
  if (!chave) return 'Outros';
  return categoriaNome(chave.split('::')[0]);
}

/** "EMPRESTIMOS" → "Empréstimo". Fora do dicionário: o código, legível, sem inglês. */
export function tipoBelvo(tipo: string | null): string | null {
  if (!tipo) return null;
  if (TIPOS_PRODUTO[tipo]) return TIPOS_PRODUTO[tipo];
  const t = tipo.replace(/_/g, ' ').toLowerCase().trim();
  return t.charAt(0).toUpperCase() + t.slice(1);
}

/** bill_name da Belvo "Oct-2026" → "out/2026". Outros formatos passam como vieram. */
export function nomeFatura(nome: string | null | undefined): string | null {
  if (!nome) return null;
  const [, mes, ano] = /^([A-Z][a-z]{2})-(\d{4})$/.exec(nome) ?? [];
  const pt = mes ? MESES_EN[mes] : undefined;
  return pt ? `${pt}/${ano}` : nome;
}

export type Tom = 'fato' | 'atencao' | 'conquista' | 'info';

/** ``temPlano``: só diz que algo "já está no seu plano" quando existe um plano ativo (A4). */
export function mensagemEvento(e: Evento, { temPlano }: { temPlano: boolean }): { titulo: string; texto: string; tom: Tom } {
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
        // A5: nomeia a conta, para não parecer contradizer o saldo total da tela.
        texto: `A parcela é de ${r$s(c.parcela)} e ${s('conta') ? `sua conta ${s('conta')} tem` : 'suas contas somam'} ${r$s(c.saldo_conta)}. Faltam ${r$s(c.falta)} até ${diaMes(s('vencimento'))} para não atrasar.`,
      };
    case 'ATRASO_CONFIRMADO':
      return {
        tom: 'fato',
        titulo: `${s('descricao')} está com ${n('dias')} ${plural(n('dias'), 'dia', 'dias')} de atraso`,
        texto: `Pagar a parcela de ${r$s(c.parcela)} interrompe a multa e os juros de atraso. ${temPlano ? 'Ela já está no seu plano.' : 'Ao montar seu plano, ela entra na conta.'}`,
      };
    case 'CHEQUE_ESPECIAL':
      return {
        tom: 'fato',
        titulo: `Você está usando ${r$s(c.usado)} do cheque especial`,
        texto: c.juros_mes
          ? `Ele custa ${pctAno(c.taxa_anual)}: ${r$s(c.juros_mes)} de juros por mês. ${temPlano ? 'No plano, ele tem data para acabar.' : 'Um plano dá a ele uma data para acabar.'}`
          : temPlano
            ? 'No plano, ele tem data para acabar.'
            : 'Um plano dá a ele uma data para acabar.',
      };
    case 'PICO_CATEGORIA': {
      const cat = nomeGasto(s('categoria')).toLowerCase();
      return {
        tom: 'atencao',
        titulo: `Em ${nomeMes(s('mes'))}, o que não é essencial em ${cat} somou ${r$s(c.gasto)}`,
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
  // M3: só aparece quando o backend usa o Oracle.
  ondeFicam: 'Onde ficam os seus dados',
  ondeFicamTexto: (regiao: string) =>
    `Oracle Autonomous AI Database · ${regiao} · criptografado em repouso pela Oracle.`,
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

export const erroRota = {
  titulo: 'Algo não carregou',
  texto: 'Recarregue para continuar. Seus dados estão seguros.',
  recarregar: 'Recarregar',
  inicio: 'Ir para o Início',
};

export const estados = {
  carregando: 'Carregando…',
  erroTitulo: 'Não conseguimos carregar agora',
  erroTexto: 'Tente de novo em instantes. Seus dados estão seguros.',
  tentar: 'Tentar de novo',
  tentando: 'Tentando…',
  // A conexão caiu no meio da espera: a tela continua, e as consultas seguem sozinhas.
  reconectando: 'A conexão oscilou. Continuamos tentando — não precisa fazer nada.',
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
// N1 (Fase 7): todas as transações, de todas as contas, com filtros.
export const transacoes = {
  titulo: 'Todas as transações',
  verTodas: 'Ver todas as transações',
  voltar: 'Suas contas',
  buscar: 'Buscar por descrição ou loja',
  filtros: 'Filtros',
  limpar: 'Limpar filtros',
  carregarMais: 'Carregar mais',
  entradas: 'Entradas',
  saidas: 'Saídas',
  resultado: 'Resultado',
  quantidade: (n: number) => (n === 1 ? '1 transação' : `${n} transações`),
  vazio: 'Nenhuma transação com esses filtros.',
  soDivida: 'Só pagamentos de dívida',
  fluxos: { renda: 'Só renda', gasto: 'Só gastos' } as Record<string, string>,
  soDividaAjuda: 'Quanto você pagou de dívida no período.',
  periodo: 'Período',
  periodos: {
    tudo: 'Tudo',
    mes: 'Este mês',
    mes_passado: 'Mês passado',
    '30': '30 dias',
    '90': '90 dias',
    personalizado: 'Escolher datas',
  } as Record<string, string>,
  de: 'De',
  ate: 'Até',
  contas: 'Banco e conta',
  tipo: 'Tipo',
  tipos: { ENTRADA: 'Entradas', SAIDA: 'Saídas' } as Record<string, string>,
  tipoConta: 'Tipo de conta',
  tiposConta: {
    TUDO: 'Tudo',
    CORRENTE: 'Conta corrente',
    CARTAO: 'Cartão de crédito',
    POUPANCA: 'Poupança',
    INVESTIMENTOS: 'Investimentos',
  } as Record<string, string>,
  direcoes: 'Entradas e saídas',
  todos: 'Todos',
  categorias: 'Categoria',
  valor: 'Valor (R$)',
  valorMin: 'Mínimo',
  valorMax: 'Máximo',
  aplicar: 'Aplicar',
  ordem: 'Ordenar',
  ordens: { recentes: 'Mais recentes', maior_valor: 'Maior valor' } as Record<string, string>,
  chipValor: (min: string | null, max: string | null) =>
    min && max ? `R$ ${min} a R$ ${max}` : min ? `a partir de R$ ${min}` : `até R$ ${max ?? ''}`,
  chipBusca: (b: string) => `"${b}"`,
  chipDatas: (de: string | null, ate: string | null) => [de, ate].filter(Boolean).join(' a ') || 'Datas',
};

// N2 (Fase 7): para onde foi o dinheiro — existe para liberar capacidade para o plano.
export const gastos = {
  titulo: 'Para onde foi o dinheiro',
  subtitulo: (mes: string) => `Gastos de ${mes}, comparados com a sua média dos 3 meses anteriores.`,
  mes: 'Mês',
  media: (valor: string) => `média ${valor}`,
  acimaDaMedia: (pct: number) => `+${pct}% que a sua média`,
  abaixoDaMedia: (pct: number) => `${pct}% abaixo da média`,
  essencial: 'essencial',
  semDados: 'Ainda não há gastos para mostrar neste mês.',
  verTransacoes: (cat: string) => `Ver a evolução e as transações de ${cat}`,
  foraDaConta: 'Fora da conta: pagamentos de dívida e transferências.',
  impacto: (cat: string, valor: string, meses: number, nova: string, atual: string) =>
    `Se o que não é essencial em ${cat} voltasse à sua média, sobrariam ${valor} por mês — sua data de saída chegaria ${meses} ${meses === 1 ? 'mês' : 'meses'} antes: ${nova} em vez de ${atual}.`,
  verDetalhes: 'Toque numa categoria para ver a evolução e as transações.',
  impactoAviso: 'Projeção com o valor que você coloca por mês nas dívidas. O app organiza e projeta; a escolha é sua.',
};

// Detalhe de uma categoria de gasto (feedback do teste com conta real, Fase 7).
export const gastoCategoria = {
  voltar: '← Suas contas',
  evolucao: 'Últimos 12 meses',
  evolucaoAria: (cat: string) => `Gasto com ${cat} nos últimos 12 meses`,
  periodo: 'Período',
  personalizado: 'Escolher datas…',
  de: 'De',
  ate: 'Até',
  subcategoria: 'Tipo de gasto',
  todas: 'Todos',
  subAviso: 'Os tipos vêm da classificação do banco e às vezes erram.',
  totalPeriodo: (periodo: string) => `Total em ${periodo}`,
  noPeriodo: 'no período escolhido',
  semGastos: 'Nenhum gasto nesta categoria no período.',
  verTodas: 'Ver em todas as transações',
};

// N5 (Fase 7): de onde vem o valor do plano — F-7.
export const fluxo = {
  titulo: 'Entradas, gastos e dívida, mês a mês',
  verDeOndeVeio: 'Ver de onde veio',
  esconder: 'Esconder',
  conta: (entradas: string, essenciais: string, reserva: number, capacidade: string) =>
    `Nos últimos 6 meses, num mês típico entraram ${entradas} e os gastos essenciais foram ${essenciais}. ` +
    `A diferença, menos ${reserva}% de reserva para imprevistos, dá ${capacidade} por mês para as dívidas.`,
  // Renda vinda do add-on INCOMES da Belvo: não é a mesma conta das barras.
  contaRendaDetectada: (entradas: string, essenciais: string, reserva: number, capacidade: string) =>
    `Pela renda que o seu banco identificou, entram ${entradas} por mês; os gastos essenciais num mês típico foram ${essenciais}. ` +
    `A diferença, menos ${reserva}% de reserva para imprevistos, dá ${capacidade} por mês para as dívidas.`,
  aplicacoes:
    'Aplicações e resgates automáticos ficam fora de entradas e gastos: é o seu dinheiro mudando de lugar, não renda nem gasto.',
  mediana:
    'Usamos o mês típico (a mediana), não a média: um mês fora da curva — um bônus, uma despesa rara — não puxa o valor para cima nem para baixo.',
  cartao: 'Compras no cartão contam como gasto; o pagamento da fatura aparece em dívida.',
  semHistorico: 'Ainda não há meses completos suficientes para mostrar.',
  series: { entradas: 'Entradas', essenciais: 'Gastos essenciais', outros: 'Outros gastos', divida: 'Pagamentos de dívida', sobra: 'Sobra (entradas − essenciais)' },
  reservaColuna: 'Guardou (usou)',
  tabela: 'Ver em tabela',
};

// Entradas e saídas, mês a mês (feedback do teste com conta real, Fase 7).
export const entradasSaidas = {
  titulo: 'Entradas e saídas',
  entradas: 'Entradas',
  saidas: 'Saídas',
  meses: (n: number) => `${n} meses`,
  periodo: 'Período do gráfico',
  tipo: 'Mostrar',
  media: (tipo: string, n: number, valor: string) => `${tipo}: em média ${valor} por mês nos últimos ${n} meses.`,
  toque: 'Toque numa barra para ver as transações daquele mês.',
  aria: (tipo: string, n: number) => `${tipo} nos últimos ${n} meses`,
  oQueConta: {
    entradas: 'Entradas: o que conta como renda — sem empréstimo recebido, estorno, transferência entre as suas contas nem resgate de aplicação.',
    saidas: 'Saídas: os gastos — sem pagamento de dívida, transferência entre as suas contas nem aplicação.',
  },
  semDados: 'Ainda não há meses completos para mostrar.',
};

// N3 (Fase 7): próximos vencimentos — organiza o que existe, sem alerta novo.
export const vencimentos = {
  titulo: 'Próximos vencimentos',
  verTodos: 'Ver todos os vencimentos',
  janela: (dias: number) => `${dias} dias`,
  janelas: [7, 15, 30],
  vazio: (dias: number) => `Nada vence nos próximos ${dias} dias.`,
  status: { PAGO: 'Pago', PENDENTE: 'Pendente', ATRASADO: 'Atrasado' } as Record<string, string>,
  quando: (dias: number) =>
    dias < 0 ? `venceu há ${-dias} ${dias === -1 ? 'dia' : 'dias'}` : dias === 0 ? 'vence hoje' : dias === 1 ? 'vence amanhã' : `em ${dias} dias`,
  minimo: 'mínimo',
  parcela: 'parcela',
  daFatura: (total: string) => `de ${total} da fatura`,
  noPlano: (valor: string) => `no plano: ${valor}`,
  ajuda: 'Faturas de cartão e parcelas dos seus contratos. Para parcelas, o banco não informa se a do mês já foi paga.',
};

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
  /** A14: "venceu em" quando a data já passou (ou a fatura está atrasada). Datas ISO comparam como texto. */
  vencimento: (iso: string, hoje: string, formatada: string, atrasada = false) =>
    atrasada || iso < hoje ? `venceu em ${formatada}` : `vence em ${formatada}`,
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
    conta: 'Conta',
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
    // Compra parcelada no cartão (Fase 7)
    parcela: 'Parcela',
    parcelaDe: (n: number, total: number) => `${n} de ${total}`,
    lancadaEm: 'Cai na fatura em',
    compraEm: 'Compra em',
  },
  parcelaCurta: (n: number, total: number) => `parcela ${n}/${total}`,
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
    titulo: 'Parabéns: você não tem dívidas',
    texto:
      'Nas contas conectadas não aparece nenhuma dívida — nada para quitar. Se tiver um carnê ou uma dívida com alguém que não aparece aqui, dá para incluir.',
  },
  toqueParaDetalhes: 'Toque numa conta ou cartão para ver os detalhes.',
};
