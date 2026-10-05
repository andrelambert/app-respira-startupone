/**
 * Cliente tipado do backend do Respira.
 *
 * O frontend fala SÓ com o nosso backend — nenhuma chamada à Belvo sai do
 * navegador (docs/contexto-produto.md §12.1). Toda resposta é validada com Zod (§12.6).
 */
import { z } from 'zod';

import { deDecimal, type Centavos } from './money';

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

// --- tipos base ------------------------------------------------------------------

const dinheiro = z
  .string()
  .regex(/^-?\d+\.\d{2}$/)
  .transform((v): Centavos => deDecimal(v));
const decimalTexto = z.string().regex(/^-?\d+(\.\d+)?$/);
const data = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const dataHora = z.string().min(10);
const metodo = z.enum(['AVALANCHE', 'SNOWBALL', 'EQUILIBRADO']);
export type Metodo = z.infer<typeof metodo>;

export const configSchema = z.object({
  demo_disponivel: z.boolean(),
  belvo_configurada: z.boolean(),
  webhooks: z.boolean(),
});
export type Config = z.infer<typeof configSchema>;

export const usuarioSchema = z.object({
  apelido: z.string(),
  email: z.string().nullable(),
  nome_completo: z.string().nullable(),
  demo: z.boolean(),
  tem_identificacao: z.boolean(),
  cpf_mascarado: z.string().nullable(),
  ja_desistiu_de_plano: z.boolean().nullable(),
  meses_simulados: z.number().int(),
  hoje: data,
});
export type Usuario = z.infer<typeof usuarioSchema>;

const recursoColeta = z.object({ recurso: z.string(), status: z.string() });
export const consentimentoSchema = z.object({
  id: z.number().int(),
  instituicao: z.string().nullable(),
  instituicao_codigo: z.string().nullable(),
  instituicao_logo: z.string().url().nullable(),
  status: z.enum(['PENDENTE', 'ATIVO', 'EXPIRADO', 'REVOGADO', 'ERRO']),
  concedido_em: dataHora.nullable(),
  expira_em: dataHora.nullable(),
  dias_para_expirar: z.number().int().nullable(),
  revogado_em: dataHora.nullable(),
  ultima_sync_em: dataHora.nullable(),
  erro_codigo: z.string().nullable(),
  coleta: z.array(recursoColeta),
  coleta_concluida: z.boolean(),
});
export type Consentimento = z.infer<typeof consentimentoSchema>;

export const dividaSchema = z.object({
  id: z.number().int(),
  descricao: z.string(),
  instituicao: z.string(),
  modalidade: z.string(),
  origem: z.enum(['OPEN_FINANCE', 'MANUAL']),
  saldo: dinheiro,
  saldo_inicial: dinheiro,
  taxa_mes: decimalTexto,
  taxa_anual: decimalTexto,
  taxa_estimada: z.boolean(),
  juros_mes: dinheiro,
  parcela_minima: dinheiro,
  parcela_estimada: z.boolean(),
  parcelas_restantes: z.number().int().nullable(),
  dia_vencimento: z.number().int().nullable(),
  em_atraso_dias: z.number().int(),
  quitada_em: data.nullable(),
  atualizado_em: dataHora,
});
export type Divida = z.infer<typeof dividaSchema>;

const projecaoSchema = z.object({
  metodo,
  capacidade: dinheiro,
  converge: z.boolean(),
  meses: z.number().int(),
  data_quitacao: data.nullable(),
  juros_totais: dinheiro,
  primeira_quitacao_mes: z.number().int().nullable(),
});
export type Projecao = z.infer<typeof projecaoSchema>;

const capacidadeSchema = z.object({
  valor: dinheiro,
  origem: z.string(),
  entradas: dinheiro.nullable(),
  essenciais: dinheiro.nullable(),
  meses_historico: z.number().int(),
});

export const raioXSchema = z.object({
  coleta_em_andamento: z.boolean(),
  atualizado_em: dataHora.nullable(),
  qtd_dividas: z.number().int(),
  divida_total: dinheiro,
  juros_mes_estimado: dinheiro,
  compromisso_minimo_mes: dinheiro,
  pior_taxa_anual: decimalTexto.nullable(),
  qtd_em_atraso: z.number().int(),
  divida_cresce: z.boolean(),
  crescimento_mensal: dinheiro,
  maior_fonte_juros: dividaSchema.nullable(),
  maior_fonte_juros_valor: dinheiro,
  comprometimento_renda_pct: decimalTexto.nullable(),
  capacidade: capacidadeSchema,
  capacidade_minima: dinheiro.nullable(),
  projecao: projecaoSchema,
  dividas: z.array(dividaSchema),
});
export type RaioX = z.infer<typeof raioXSchema>;

const itemPlanoSchema = z.object({
  divida_id: z.number().int(),
  descricao: z.string(),
  ordem: z.number().int(),
  valor_mensal: dinheiro,
  mes_quitacao: z.number().int().nullable(),
  juros_pagos: dinheiro,
});
export type ItemPlano = z.infer<typeof itemPlanoSchema>;

const estrategiaSchema = projecaoSchema.extend({
  itens: z.array(itemPlanoSchema),
  trajetoria: z.array(dinheiro),
  /** Pagar só os mínimos de hoje, no mesmo horizonte desta estratégia. */
  so_minimo: z
    .object({
      converge: z.boolean(),
      meses: z.number().int(),
      juros_no_horizonte: dinheiro,
      saldo_no_horizonte: dinheiro,
    })
    .nullable(),
});
export type Estrategia = z.infer<typeof estrategiaSchema>;

export const simulacoesSchema = z.object({
  capacidade: dinheiro,
  capacidade_calculada: capacidadeSchema,
  capacidade_minima: dinheiro.nullable(),
  compromisso_minimo_mes: dinheiro,
  pre_selecionado: metodo,
  motivo_pre_selecao: z.enum(['PADRAO', 'JA_DESISTIU']),
  estrategias: z.array(estrategiaSchema),
});
export type Simulacoes = z.infer<typeof simulacoesSchema>;

export const planoAtivoSchema = z.object({
  id: z.number().int(),
  metodo,
  status: z.string(),
  capacidade_mensal: dinheiro,
  capacidade_origem: z.string(),
  criado_em: dataHora,
  meses_projetados: z.number().int(),
  data_quitacao_original: data.nullable(),
  juros_totais_original: dinheiro,
  economia_vs_minimo: dinheiro.nullable(),
  divida_inicial: dinheiro,
  divida_atual: dinheiro,
  abatido: dinheiro,
  progresso_pct: decimalTexto,
  projecao_atual: projecaoSchema,
  este_mes: z.array(
    z.object({
      divida_id: z.number().int(),
      descricao: z.string(),
      instituicao: z.string(),
      valor: dinheiro,
      dia_vencimento: z.number().int().nullable(),
      ordem: z.number().int(),
      e_minimo: z.boolean(),
    }),
  ),
  cronograma: z.array(itemPlanoSchema),
  acompanhamentos: z.array(
    z.object({
      mes_referencia: data,
      previsto: dinheiro,
      realizado: dinheiro,
      data_quitacao_anterior: data.nullable(),
      data_quitacao_nova: data.nullable(),
    }),
  ),
  hoje: data,
});
export type PlanoAtivo = z.infer<typeof planoAtivoSchema>;

export const eventoSchema = z.object({
  id: z.number().int(),
  tipo: z.enum([
    'ENTRADA_ROTATIVO',
    'ATRASO_IMINENTE',
    'ATRASO_CONFIRMADO',
    'PICO_CATEGORIA',
    'DESVIO_PLANO',
    'DIVIDA_QUITADA',
    'CHEQUE_ESPECIAL',
    'OPORTUNIDADE_PORTABILIDADE',
  ]),
  severidade: z.number().int(),
  divida_id: z.number().int().nullable(),
  contexto: z.record(z.string(), z.unknown()),
  detectado_em: dataHora,
  notificado_em: dataHora.nullable(),
  licao: z.string().nullable(),
});
export type Evento = z.infer<typeof eventoSchema>;

export const licaoSchema = z.object({
  slug: z.string(),
  titulo: z.string(),
  corpo: z.string(),
  tipo_evento: z.string().nullable(),
});
export type Licao = z.infer<typeof licaoSchema>;

// --- PFM: contas, faturas e extrato ---------------------------------------------------

const faturaSchema = z.object({
  id: z.number().int(),
  nome: z.string(),
  vencimento: data.nullable(),
  total: dinheiro,
  minimo: dinheiro.nullable(),
  pago: dinheiro,
  em_aberto: dinheiro,
  encargos: dinheiro,
  parcelada: z.boolean(),
  situacao: z.enum(['PAGA', 'EM_ABERTO', 'PARCIAL', 'ATRASADA']),
  pagamentos: z.array(z.object({ data: data.nullable(), valor: dinheiro })),
});
export type Fatura = z.infer<typeof faturaSchema>;

const contaSchema = z.object({
  id: z.number().int(),
  consentimento_id: z.number().int().nullable(),
  instituicao: z.string(),
  instituicao_logo: z.string().url().nullable(),
  tipo: z.enum(['CORRENTE', 'POUPANCA', 'PAGAMENTO', 'CARTAO_CREDITO', 'EMPRESTIMO', 'FINANCIAMENTO', 'ADIANTAMENTO', 'OUTRO']),
  nome: z.string(),
  numero_final: z.string().nullable(),
  tipo_externo: z.string().nullable(),
  agencia: z.string().nullable(),
  numero_conta: z.string().nullable(),
  saldo: dinheiro,
  disponivel: dinheiro.nullable(),
  limite_credito: dinheiro.nullable(),
  limite_cheque_especial: dinheiro,
  usado_cheque_especial: dinheiro,
  fatura_atual: faturaSchema.nullable(),
  atualizado_em: dataHora,
});
export type ContaBancaria = z.infer<typeof contaSchema>;

export const visaoGeralSchema = z.object({
  bancos: z.array(
    z.object({
      consentimento_id: z.number().int(),
      instituicao: z.string().nullable(),
      instituicao_codigo: z.string().nullable(),
      instituicao_logo: z.string().url().nullable(),
      status: z.string(),
      ultima_sync_em: dataHora.nullable(),
      expira_em: dataHora.nullable(),
      coleta_concluida: z.boolean(),
      coleta: z.array(recursoColeta),
      contas: z.array(contaSchema),
    }),
  ),
  saldo_em_contas: dinheiro,
  faturas_em_aberto: dinheiro,
  qtd_dividas: z.number().int(),
  hoje: data,
});
export type VisaoGeral = z.infer<typeof visaoGeralSchema>;
export type Banco = VisaoGeral['bancos'][number];

export const contaDetalheSchema = z.object({ conta: contaSchema, faturas: z.array(faturaSchema) });

const transacaoSchema = z.object({
  id: z.number().int(),
  data,
  descricao: z.string(),
  estabelecimento: z.string().nullable(),
  estabelecimento_site: z.string().nullable(),
  categoria: z.string().nullable(),
  subcategoria: z.string().nullable(),
  // Horário de Brasília, já convertido pelo backend (ex.: 2026-09-05T22:30:00-03:00).
  transacionado_em: z.string().regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/).nullable(),
  tipo_operacao: z.string().nullable(),
  final_cartao: z.string().regex(/^\d{1,4}$/).nullable(), // só o final (PCI)
  fatura: z.string().nullable(), // bill_name da fatura em que a compra entrou
  valor: dinheiro,
  direcao: z.enum(['ENTRADA', 'SAIDA']),
});
export type Transacao = z.infer<typeof transacaoSchema>;

export const extratoSchema = z.object({
  itens: z.array(transacaoSchema),
  pagina: z.number().int(),
  por_pagina: z.number().int(),
  total: z.number().int(),
  paginas: z.number().int(),
  total_entradas: dinheiro,
  total_saidas: dinheiro,
});
export type Extrato = z.infer<typeof extratoSchema>;
export type FiltroExtrato = {
  pagina: number;
  direcao?: 'ENTRADA' | 'SAIDA';
  busca?: string;
  dias?: number; // últimos N dias
};

// --- transporte ----------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly codigo: string,
  ) {
    super(`${status} ${codigo}`);
  }
}

async function chamar<T>(
  caminho: string,
  schema: z.ZodType<T> | null,
  init: RequestInit = {},
): Promise<T> {
  const metodoHttp = (init.method ?? 'GET').toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body) headers.set('Content-Type', 'application/json');
  // Exigido pelo backend em toda escrita: força preflight de CORS (anti-CSRF).
  if (metodoHttp !== 'GET') headers.set('X-Respira', '1');

  let resp: Response;
  try {
    // Cookie de sessão HttpOnly: o navegador envia, o JavaScript nunca lê.
    resp = await fetch(`${API_URL}${caminho}`, { ...init, headers, credentials: 'include' });
  } catch {
    throw new ApiError(0, navigator.onLine ? 'servidor_indisponivel' : 'offline');
  }
  if (!resp.ok) {
    let codigo = `http_${resp.status}`;
    try {
      const corpo: unknown = await resp.json();
      if (corpo && typeof corpo === 'object' && 'detail' in corpo && typeof corpo.detail === 'string') {
        codigo = corpo.detail;
      }
    } catch {
      /* corpo não-JSON: fica o código HTTP */
    }
    throw new ApiError(resp.status, codigo);
  }
  if (schema === null || resp.status === 204) return undefined as T;
  const json: unknown = await resp.json();
  const r = schema.safeParse(json);
  if (!r.success) {
    // Sem dado do usuário no log: só o caminho e o formato que falhou.
    console.error('resposta_invalida', caminho, r.error.issues.map((i) => i.path.join('.')));
    throw new ApiError(500, 'resposta_invalida');
  }
  return r.data;
}

const json = (corpo: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(corpo) });

export const api = {
  config: () => chamar('/config', configSchema),
  usuario: () => chamar('/usuarios/me', usuarioSchema),
  registrar: (dados: {
    email: string;
    senha: string;
    nome_completo: string;
    cpf: string;
    ja_desistiu_de_plano: boolean | null;
  }) => chamar('/auth/registrar', usuarioSchema, json(dados)),
  entrar: (email: string, senha: string) => chamar('/auth/entrar', usuarioSchema, json({ email, senha })),
  entrarDemo: () => chamar('/auth/demo', usuarioSchema, { method: 'POST' }),
  sair: () => chamar('/auth/sair', null, { method: 'POST' }),
  excluirConta: () => chamar('/usuarios/me', null, { method: 'DELETE' }),

  consentimentos: () => chamar('/consentimentos', z.array(consentimentoSchema)),
  coleta: (id: number) => chamar(`/consentimentos/${id}/coleta`, consentimentoSchema),
  widgetToken: (instituicao?: string) =>
    chamar(
      '/consentimentos/widget-token',
      z.object({ consentimento_id: z.number().int(), widget_url: z.string().url() }),
      json(instituicao ? { instituicao } : {}),
    ),
  callback: (link: string, institution: string) =>
    chamar('/consentimentos/callback', consentimentoSchema, json({ link, institution })),
  saida: (dados: { codigo?: string; etapa?: string; fatal: boolean }) =>
    chamar('/consentimentos/saida', null, json(dados)),
  revogar: (id: number) => chamar(`/consentimentos/${id}`, null, { method: 'DELETE' }),
  sync: () => chamar('/sync', z.object({ itens: z.number() }), { method: 'POST' }),

  raiox: () => chamar('/raiox', raioXSchema),
  visaoGeral: () => chamar('/pfm/visao-geral', visaoGeralSchema),
  conta: (id: number) => chamar(`/contas/${id}`, contaDetalheSchema),
  extrato: (id: number, f: FiltroExtrato, sinal?: AbortSignal) => {
    const q = new URLSearchParams({ pagina: String(f.pagina), por_pagina: '20' });
    if (f.direcao) q.set('direcao', f.direcao);
    if (f.busca) q.set('busca', f.busca);
    if (f.dias) q.set('dias', String(f.dias));
    return chamar(`/contas/${id}/transacoes?${q.toString()}`, extratoSchema, { signal: sinal });
  },
  dividas: () => chamar('/dividas', z.array(dividaSchema)),
  criarDivida: (dados: {
    credor: string;
    modalidade: string;
    saldo: string;
    parcela: string;
    taxa_mes_percentual?: string;
    dia_vencimento?: number;
    em_atraso_dias?: number;
  }) => chamar('/dividas', dividaSchema, json(dados)),
  atualizarDivida: (
    id: number,
    dados: { parcela?: string; taxa_mes_percentual?: string; dia_vencimento?: number },
  ) => chamar(`/dividas/${id}`, dividaSchema, { method: 'PATCH', body: JSON.stringify(dados) }),

  simulacoes: (capacidade?: string, sinal?: AbortSignal) =>
    chamar(
      `/plano/simulacoes${capacidade ? `?capacidade=${encodeURIComponent(capacidade)}` : ''}`,
      simulacoesSchema,
      { signal: sinal },
    ),
  ativarPlano: (metodoEscolhido: Metodo, capacidade: string) =>
    chamar('/plano', planoAtivoSchema, json({ metodo: metodoEscolhido, capacidade })),
  planoAtivo: () => chamar('/plano/ativo', planoAtivoSchema),
  recalcular: () => chamar('/plano/recalcular', planoAtivoSchema, { method: 'POST' }),

  eventos: (naoNotificados = false) =>
    chamar(`/eventos${naoNotificados ? '?nao_notificados=true' : ''}`, z.array(eventoSchema)),
  eventoVisto: (id: number) => chamar(`/eventos/${id}/visto`, eventoSchema, { method: 'POST' }),
  licao: (slug: string) => chamar(`/licoes/${encodeURIComponent(slug)}`, licaoSchema),

  // só na conta de demonstração
  autorizarFixture: (access_token: string, instituicao: string) =>
    chamar(
      '/fixture/widget/autorizar',
      z.object({ link: z.string(), institution: z.string() }),
      json({ access_token, instituicao }),
    ),
  demoReiniciar: () => chamar('/demo/reiniciar', null, { method: 'POST' }),
  demoAvancarMes: (mes_dificil: boolean) =>
    chamar('/demo/avancar-mes', planoAtivoSchema, json({ mes_dificil })),
};
