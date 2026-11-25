/**
 * Filtros da tela "Todas as transações" (N1, Fase 7) — refletidos na URL, para
 * o botão voltar e o link compartilhado funcionarem. Funções puras: a tela só
 * lê e grava ``URLSearchParams``.
 */
import { addDays, endOfMonth, format, parseISO, startOfMonth, subMonths } from 'date-fns';

export type Periodo = 'tudo' | 'mes' | 'mes_passado' | '30' | '90' | 'personalizado';
export type Ordem = 'recentes' | 'maior_valor';
export type Direcao = 'ENTRADA' | 'SAIDA';
/** As mesmas regras do gráfico de entradas e saídas: só renda / só gastos (sem dívida, transferência nem aplicação). */
export type Fluxo = 'renda' | 'gasto';
/** Tudo (null) · conta corrente · cartão · poupança · investimentos (aplicações e resgates). */
export type TipoConta = 'CORRENTE' | 'CARTAO' | 'POUPANCA' | 'INVESTIMENTOS';
export const TIPOS_CONTA: TipoConta[] = ['CORRENTE', 'CARTAO', 'POUPANCA', 'INVESTIMENTOS'];

export type Filtros = {
  periodo: Periodo;
  desde: string | null; // só no personalizado (yyyy-MM-dd)
  ate: string | null;
  contas: number[];
  direcao: Direcao | null;
  categorias: string[];
  busca: string;
  valorMin: string | null; // reais, como digitado ("100" ou "100,50")
  valorMax: string | null;
  soDivida: boolean;
  fluxo: Fluxo | null;
  tipoConta: TipoConta | null;
  ordem: Ordem;
};

export const FILTROS_VAZIOS: Filtros = {
  periodo: 'tudo',
  desde: null,
  ate: null,
  contas: [],
  direcao: null,
  categorias: [],
  busca: '',
  valorMin: null,
  valorMax: null,
  soDivida: false,
  fluxo: null,
  tipoConta: null,
  ordem: 'recentes',
};

const PERIODOS: Periodo[] = ['tudo', 'mes', 'mes_passado', '30', '90', 'personalizado'];
const DATA = /^\d{4}-\d{2}-\d{2}$/;
const MAX_LISTA = 20; // o backend recusa listas maiores

function lista(v: string | null): string[] {
  return (v ?? '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, MAX_LISTA);
}

/** Valor em reais digitado → decimal com ponto ("1.234,50" → "1234.50"); inválido → null. */
export function valorDecimal(v: string | null): string | null {
  if (!v) return null;
  const limpo = v.trim().replace(/\./g, '').replace(',', '.');
  return /^\d{1,10}(\.\d{1,2})?$/.test(limpo) ? limpo : null;
}

export function lerFiltros(p: URLSearchParams): Filtros {
  const periodo = p.get('periodo') as Periodo | null;
  const direcao = p.get('tipo');
  const bruto = (k: string) => {
    const v = p.get(k);
    return v && DATA.test(v) ? v : null;
  };
  const desde = bruto('desde');
  const ate = bruto('ate');
  return {
    periodo: periodo && PERIODOS.includes(periodo) ? periodo : desde || ate ? 'personalizado' : 'tudo',
    desde,
    ate,
    contas: lista(p.get('contas'))
      .map(Number)
      .filter((n) => Number.isInteger(n) && n > 0),
    direcao: direcao === 'ENTRADA' || direcao === 'SAIDA' ? direcao : null,
    categorias: lista(p.get('categorias')),
    busca: (p.get('busca') ?? '').slice(0, 60),
    valorMin: valorDecimal(p.get('min')) ? p.get('min') : null,
    valorMax: valorDecimal(p.get('max')) ? p.get('max') : null,
    soDivida: p.get('divida') === '1',
    tipoConta: TIPOS_CONTA.includes(p.get('conta_tipo') as TipoConta) ? (p.get('conta_tipo') as TipoConta) : null,
    fluxo: p.get('fluxo') === 'renda' || p.get('fluxo') === 'gasto' ? (p.get('fluxo') as Fluxo) : null,
    ordem: p.get('ordem') === 'maior_valor' ? 'maior_valor' : 'recentes',
  };
}

/** Só grava o que difere do padrão: a URL fica curta e legível. */
export function escreverFiltros(f: Filtros): URLSearchParams {
  const p = new URLSearchParams();
  if (f.periodo !== 'tudo' && f.periodo !== 'personalizado') p.set('periodo', f.periodo);
  if (f.periodo === 'personalizado') {
    if (f.desde) p.set('desde', f.desde);
    if (f.ate) p.set('ate', f.ate);
  }
  if (f.contas.length) p.set('contas', f.contas.join(','));
  if (f.direcao) p.set('tipo', f.direcao);
  if (f.categorias.length) p.set('categorias', f.categorias.join(','));
  if (f.busca.trim()) p.set('busca', f.busca.trim());
  if (f.valorMin) p.set('min', f.valorMin);
  if (f.valorMax) p.set('max', f.valorMax);
  if (f.soDivida) p.set('divida', '1');
  if (f.fluxo) p.set('fluxo', f.fluxo);
  if (f.tipoConta) p.set('conta_tipo', f.tipoConta);
  if (f.ordem !== 'recentes') p.set('ordem', f.ordem);
  return p;
}

/** Período → datas, a partir do "hoje" do usuário (a demo pode estar no futuro). */
export function intervalo(f: Filtros, hoje: string): { desde?: string; ate?: string } {
  const h = parseISO(hoje);
  const iso = (d: Date) => format(d, 'yyyy-MM-dd');
  switch (f.periodo) {
    case 'mes':
      return { desde: iso(startOfMonth(h)), ate: hoje };
    case 'mes_passado': {
      const m = subMonths(h, 1);
      return { desde: iso(startOfMonth(m)), ate: iso(endOfMonth(m)) };
    }
    case '30':
    case '90':
      return { desde: iso(addDays(h, -Number(f.periodo))), ate: hoje };
    case 'personalizado':
      return { ...(f.desde ? { desde: f.desde } : {}), ...(f.ate ? { ate: f.ate } : {}) };
    default:
      // "Tudo" é o que já aconteceu: parcelas futuras de compras no cartão
      // (accounting_date à frente) só aparecem escolhendo datas futuras.
      return { ate: hoje };
  }
}

/** Parâmetros da API ``GET /transacoes`` (sem a página). */
export function paraApi(f: Filtros, hoje: string): Record<string, string> {
  const r: Record<string, string> = { ...intervalo(f, hoje) } as Record<string, string>;
  if (f.contas.length) r.contas = f.contas.join(',');
  if (f.direcao) r.direcao = f.direcao;
  if (f.categorias.length) r.categorias = f.categorias.join(',');
  if (f.busca.trim()) r.busca = f.busca.trim();
  const min = valorDecimal(f.valorMin);
  const max = valorDecimal(f.valorMax);
  if (min) r.valor_min = min;
  if (max) r.valor_max = max;
  if (f.soDivida) r.so_divida = 'true';
  if (f.fluxo) r.fluxo = f.fluxo;
  if (f.tipoConta) r.tipo_conta = f.tipoConta;
  if (f.ordem !== 'recentes') r.ordem = f.ordem;
  return r;
}

export type Chip = { chave: string; rotulo: string; remover: (f: Filtros) => Filtros };

/** Um chip removível por filtro ativo. ``nomes`` traduz conta e categoria para a tela. */
export function chips(
  f: Filtros,
  nomes: { periodo: (p: Periodo, f: Filtros) => string; conta: (id: number) => string; categoria: (c: string) => string; direcao: (d: Direcao) => string; valor: (min: string | null, max: string | null) => string; soDivida: string; fluxo: (f: Fluxo) => string; busca: (b: string) => string },
): Chip[] {
  const out: Chip[] = [];
  if (f.periodo !== 'tudo')
    out.push({ chave: 'periodo', rotulo: nomes.periodo(f.periodo, f), remover: (x) => ({ ...x, periodo: 'tudo', desde: null, ate: null }) });
  for (const id of f.contas)
    out.push({ chave: `conta-${id}`, rotulo: nomes.conta(id), remover: (x) => ({ ...x, contas: x.contas.filter((c) => c !== id) }) });
  for (const c of f.categorias)
    out.push({ chave: `cat-${c}`, rotulo: nomes.categoria(c), remover: (x) => ({ ...x, categorias: x.categorias.filter((y) => y !== c) }) });
  if (f.busca.trim()) out.push({ chave: 'busca', rotulo: nomes.busca(f.busca.trim()), remover: (x) => ({ ...x, busca: '' }) });
  if (f.valorMin || f.valorMax)
    out.push({ chave: 'valor', rotulo: nomes.valor(f.valorMin, f.valorMax), remover: (x) => ({ ...x, valorMin: null, valorMax: null }) });
  if (f.soDivida) out.push({ chave: 'divida', rotulo: nomes.soDivida, remover: (x) => ({ ...x, soDivida: false }) });
  if (f.fluxo) out.push({ chave: 'fluxo', rotulo: nomes.fluxo(f.fluxo), remover: (x) => ({ ...x, fluxo: null }) });
  return out;
}

/**
 * Botões Entradas e Saídas: os dois ligados = sem filtro (``null``). Desligar um
 * deixa só o outro; desligar o último não vale — a lista nunca fica vazia por isso.
 */
export function alternarDirecao(atual: Direcao | null, tocado: Direcao): Direcao | null {
  const outro: Direcao = tocado === 'ENTRADA' ? 'SAIDA' : 'ENTRADA';
  if (atual === null) return outro; // desliga o tocado
  if (atual === tocado) return atual; // é o único ligado: continua
  return null; // religa o tocado: os dois
}
