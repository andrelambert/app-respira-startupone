import { describe, expect, it } from 'vitest';

import { escreverPeriodo, fimDoMes, intervaloPeriodo, lerPeriodo, linkCategoria } from './periodoCategoria';

const q = (s: string) => new URLSearchParams(s);

describe('período do detalhe da categoria', () => {
  it('sem nada na URL, vale o mês padrão; mês inválido também cai nele', () => {
    expect(lerPeriodo(q(''), '2026-10-01')).toEqual({ tipo: 'mes', mes: '2026-10-01' });
    expect(lerPeriodo(q('mes=2026-13'), '2026-10-01')).toEqual({ tipo: 'mes', mes: '2026-10-01' });
    expect(lerPeriodo(q('mes=2026-07'), '2026-10-01')).toEqual({ tipo: 'mes', mes: '2026-07-01' });
  });

  it('datas à escolha vão e voltam pela URL, com o tipo de gasto', () => {
    const per = { tipo: 'personalizado' as const, desde: '2026-05-10', ate: '2026-09-02' };
    const p = escreverPeriodo(per, 'Delivery');
    expect(lerPeriodo(p, '2026-10-01')).toEqual(per);
    expect(p.get('sub')).toBe('Delivery');
    expect(lerPeriodo(q('periodo=personalizado&desde=x'), '2026-10-01')).toEqual({ tipo: 'personalizado', desde: null, ate: null });
  });

  it('intervalo para a API: o mês corrente para em hoje; datas invertidas se acertam', () => {
    expect(intervaloPeriodo({ tipo: 'mes', mes: '2026-10-01' }, '2026-11-25')).toEqual({ desde: '2026-10-01', ate: '2026-10-31' });
    expect(intervaloPeriodo({ tipo: 'mes', mes: '2026-11-01' }, '2026-11-25')).toEqual({ desde: '2026-11-01', ate: '2026-11-25' });
    expect(intervaloPeriodo({ tipo: 'personalizado', desde: '2026-09-30', ate: '2026-09-01' }, '2026-11-25')).toEqual({
      desde: '2026-09-01',
      ate: '2026-09-30',
    });
    expect(intervaloPeriodo({ tipo: 'personalizado', desde: null, ate: '2026-09-01' }, '2026-11-25')).toEqual({ ate: '2026-09-01' });
    expect(fimDoMes('2028-02-01')).toBe('2028-02-29');
  });

  it('o link do Contas leva à categoria no mês que a pessoa olhava', () => {
    expect(linkCategoria('Food & Groceries', '2026-10-01')).toBe('/gastos/Food%20%26%20Groceries?mes=2026-10');
  });
});
