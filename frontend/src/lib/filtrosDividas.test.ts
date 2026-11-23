import { describe, expect, it } from 'vitest';

import type { Divida } from './api';
import {
  diasAteVencimento,
  escreverFiltrosDividas,
  filtrarDividas,
  lerFiltrosDividas,
  SEM_FILTRO,
  tipoDe,
} from './filtrosDividas';
import { centavos } from './money';

function d(id: number, o: Partial<Divida>): Divida {
  return {
    id, descricao: `D${id}`, instituicao: 'Banco', modalidade: 'CREDITO_PESSOAL', origem: 'OPEN_FINANCE',
    saldo: centavos(100000), saldo_inicial: centavos(100000), taxa_mes: '0.05', taxa_anual: '79.59',
    taxa_estimada: false, juros_mes: centavos(5000), parcela_minima: centavos(10000), parcela_estimada: false,
    parcelas_restantes: null, dia_vencimento: 10, em_atraso_dias: 0, quitada_em: null,
    atualizado_em: '2026-11-23T00:00:00Z', instituicao_logo: null, conta_id: null, cresce_no_minimo: false,
    valor_contratado: null, parcelas_total: null, parcelas_pagas: null, contrato_inicio: null, contrato_fim: null,
    ...o,
  };
}

const JULIANA = [
  d(1, { instituicao: 'Nubank', modalidade: 'CARTAO_ROTATIVO', taxa_mes: '0.1502', saldo: centavos(208000), dia_vencimento: 12, taxa_estimada: true }),
  d(2, { instituicao: 'Caixa', taxa_mes: '0.0644', saldo: centavos(42000), dia_vencimento: 15, em_atraso_dias: 39 }),
  d(3, { instituicao: 'Itaú', modalidade: 'FIN_VEICULO', taxa_mes: '0.0199', saldo: centavos(680000), dia_vencimento: 10 }),
  d(4, { instituicao: 'Loja D', modalidade: 'CREDIARIO', origem: 'MANUAL', taxa_mes: '0.035', saldo: centavos(38000), dia_vencimento: 25 }),
  d(5, { instituicao: 'Itaú', modalidade: 'CHEQUE_ESPECIAL', taxa_mes: '0.0749', saldo: centavos(0) }),
];
const ctx = { ordemPlano: new Map<number, number>(), hoje: '2026-11-23' };
const ids = (xs: Divida[]) => xs.map((x) => x.id);

describe('filtrar e ordenar dívidas (N4)', () => {
  it('tipos', () => {
    expect(JULIANA.map(tipoDe)).toEqual(['cartao', 'emprestimo', 'financiamento', 'manual', 'cheque']);
  });

  it('ordens: maior taxa, maior saldo, próximo vencimento (atrasada primeiro)', () => {
    expect(ids(filtrarDividas(JULIANA, { ...SEM_FILTRO, ordem: 'taxa' }, ctx))).toEqual([1, 2, 4, 3]);
    expect(ids(filtrarDividas(JULIANA, { ...SEM_FILTRO, ordem: 'saldo' }, ctx))).toEqual([3, 1, 2, 4]);
    // hoje é dia 23: dia 25 vence em 2 dias; 10 e 12 só no mês que vem
    expect(ids(filtrarDividas(JULIANA, { ...SEM_FILTRO, ordem: 'vencimento' }, ctx))).toEqual([2, 4, 3, 1]);
  });

  it('com plano ativo, o padrão é a ordem do plano', () => {
    const ordemPlano = new Map([[1, 0], [2, 1], [4, 2], [3, 3]]);
    expect(ids(filtrarDividas(JULIANA, SEM_FILTRO, { ...ctx, ordemPlano }))).toEqual([1, 2, 4, 3]);
  });

  it('filtros: banco, tipo e situação; quitada só aparece no filtro de quitadas', () => {
    expect(ids(filtrarDividas(JULIANA, { ...SEM_FILTRO, bancos: ['Itaú'] }, ctx))).toEqual([3]);
    expect(ids(filtrarDividas(JULIANA, { ...SEM_FILTRO, tipos: ['cartao', 'manual'] }, ctx)).sort()).toEqual([1, 4]);
    expect(ids(filtrarDividas(JULIANA, { ...SEM_FILTRO, situacao: 'atraso' }, ctx))).toEqual([2]);
    expect(ids(filtrarDividas(JULIANA, { ...SEM_FILTRO, situacao: 'estimada' }, ctx))).toEqual([1]);
    expect(ids(filtrarDividas(JULIANA, { ...SEM_FILTRO, situacao: 'quitadas' }, ctx))).toEqual([5]);
  });

  it('URL: ida e volta, e valores estranhos ignorados', () => {
    const f = { ordem: 'taxa' as const, bancos: ['Itaú', 'Loja D'], tipos: ['cartao' as const], situacao: 'atraso' as const };
    expect(lerFiltrosDividas(escreverFiltrosDividas(f))).toEqual(f);
    expect(lerFiltrosDividas(new URLSearchParams('ordem=x&tipos=cartao,foo&situacao=y'))).toEqual({
      ...SEM_FILTRO,
      tipos: ['cartao'],
    });
  });

  it('dias até o vencimento', () => {
    expect(diasAteVencimento(25, '2026-11-23')).toBe(2);
    expect(diasAteVencimento(5, '2026-11-23')).toBe(13);
    expect(diasAteVencimento(null, '2026-11-23')).toBe(Number.POSITIVE_INFINITY);
  });
});
