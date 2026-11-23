/**
 * Filtrar e ordenar dívidas (N4, Fase 7 — F-6 "a lista é longa; queria ver
 * primeiro as de juros mais altos"). Funções puras; os filtros moram na URL.
 */
import type { Divida } from './api';

export type OrdemDividas = 'banco' | 'plano' | 'taxa' | 'saldo' | 'vencimento';
export type TipoDivida = 'cartao' | 'emprestimo' | 'financiamento' | 'cheque' | 'manual';
export type Situacao = 'atraso' | 'estimada' | 'quitadas';

export type FiltrosDividas = {
  ordem: OrdemDividas | null; // null = padrão (plano, se houver; senão banco)
  bancos: string[];
  tipos: TipoDivida[];
  situacao: Situacao | null;
};

export const SEM_FILTRO: FiltrosDividas = { ordem: null, bancos: [], tipos: [], situacao: null };

const ORDENS: OrdemDividas[] = ['banco', 'plano', 'taxa', 'saldo', 'vencimento'];
const TIPOS: TipoDivida[] = ['cartao', 'emprestimo', 'financiamento', 'cheque', 'manual'];
const SITUACOES: Situacao[] = ['atraso', 'estimada', 'quitadas'];

/** Tipo exibido no filtro. "Incluída à mão" vale para qualquer modalidade manual. */
export function tipoDe(d: Pick<Divida, 'modalidade' | 'origem'>): TipoDivida {
  if (d.origem === 'MANUAL') return 'manual';
  if (d.modalidade.startsWith('CARTAO_')) return 'cartao';
  if (d.modalidade === 'CHEQUE_ESPECIAL') return 'cheque';
  if (d.modalidade.startsWith('FIN_')) return 'financiamento';
  return 'emprestimo'; // CREDITO_PESSOAL, CONSIGNADO, CREDIARIO, OUTRO
}

const lista = (v: string | null, max = 20) =>
  (v ?? '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, max);

export function lerFiltrosDividas(p: URLSearchParams): FiltrosDividas {
  const ordem = p.get('ordem') as OrdemDividas | null;
  const situacao = p.get('situacao') as Situacao | null;
  return {
    ordem: ordem && ORDENS.includes(ordem) ? ordem : null,
    bancos: lista(p.get('bancos')),
    tipos: lista(p.get('tipos')).filter((t): t is TipoDivida => TIPOS.includes(t as TipoDivida)),
    situacao: situacao && SITUACOES.includes(situacao) ? situacao : null,
  };
}

export function escreverFiltrosDividas(f: FiltrosDividas): URLSearchParams {
  const p = new URLSearchParams();
  if (f.ordem) p.set('ordem', f.ordem);
  if (f.bancos.length) p.set('bancos', f.bancos.join(','));
  if (f.tipos.length) p.set('tipos', f.tipos.join(','));
  if (f.situacao) p.set('situacao', f.situacao);
  return p;
}

/** Dias até o próximo vencimento pelo dia do mês; sem dia, vai para o fim. */
export function diasAteVencimento(dia: number | null, hoje: string): number {
  if (!dia) return Number.POSITIVE_INFINITY;
  const d = Number(hoje.slice(8, 10));
  return dia >= d ? dia - d : dia + 31 - d;
}

/**
 * Aplica filtros e ordem. ``ordemPlano``: id da dívida → posição no plano ativo.
 * Atrasadas vencem "agora" na ordem por vencimento: são as mais urgentes.
 */
export function filtrarDividas(
  dividas: Divida[],
  f: FiltrosDividas,
  { ordemPlano, hoje }: { ordemPlano: Map<number, number>; hoje: string },
): Divida[] {
  const ordem = f.ordem ?? (ordemPlano.size > 0 ? 'plano' : 'banco');
  const out = dividas.filter(
    (d) =>
      (f.situacao === 'quitadas' ? d.saldo <= 0 : d.saldo > 0) &&
      (f.situacao !== 'atraso' || d.em_atraso_dias > 0) &&
      (f.situacao !== 'estimada' || d.taxa_estimada || d.parcela_estimada) &&
      (f.bancos.length === 0 || f.bancos.includes(d.instituicao)) &&
      (f.tipos.length === 0 || f.tipos.includes(tipoDe(d))),
  );
  const taxa = (d: Divida) => Number(d.taxa_mes);
  const desempate = (a: Divida, b: Divida) => a.id - b.id;
  const cmp: Record<OrdemDividas, (a: Divida, b: Divida) => number> = {
    banco: (a, b) => a.instituicao.localeCompare(b.instituicao, 'pt-BR') || taxa(b) - taxa(a) || desempate(a, b),
    plano: (a, b) =>
      (ordemPlano.get(a.id) ?? Number.MAX_SAFE_INTEGER) - (ordemPlano.get(b.id) ?? Number.MAX_SAFE_INTEGER) ||
      desempate(a, b),
    taxa: (a, b) => taxa(b) - taxa(a) || b.saldo - a.saldo || desempate(a, b),
    saldo: (a, b) => b.saldo - a.saldo || taxa(b) - taxa(a) || desempate(a, b),
    vencimento: (a, b) => {
      const da = a.em_atraso_dias > 0 ? -a.em_atraso_dias : diasAteVencimento(a.dia_vencimento, hoje);
      const db = b.em_atraso_dias > 0 ? -b.em_atraso_dias : diasAteVencimento(b.dia_vencimento, hoje);
      return da - db || desempate(a, b);
    },
  };
  return out.sort(cmp[ordem]);
}

export function temFiltro(f: FiltrosDividas): boolean {
  return f.bancos.length > 0 || f.tipos.length > 0 || f.situacao !== null;
}
