import { describe, expect, it } from 'vitest';

import { gastos as copy } from '@/lib/copy';
import { lerFiltros } from '@/lib/filtrosTransacoes';

import { linkTransacoes } from './GastosCategoria';

describe('gastos por categoria (N2)', () => {
  it('tocar na barra abre "Todas as transações" no mês e na categoria', () => {
    const link = linkTransacoes('Online Platforms & Leisure', '2026-10-01');
    expect(link.startsWith('/transacoes?')).toBe(true);
    const f = lerFiltros(new URLSearchParams(link.split('?')[1]));
    expect(f).toMatchObject({
      periodo: 'personalizado',
      desde: '2026-10-01',
      ate: '2026-10-31',
      categorias: ['Online Platforms & Leisure'],
      direcao: 'SAIDA',
    });
    expect(lerFiltros(new URLSearchParams(linkTransacoes('X', '2027-02-01').split('?')[1])).ate).toBe('2027-02-28');
  });

  it('a frase liga o corte à data de saída', () => {
    expect(copy.impacto('delivery', 'R$ 220,00', 2, 'janeiro de 2028', 'março de 2028')).toBe(
      'Se delivery voltasse à sua média, sobrariam R$ 220,00 por mês — sua data de saída chegaria 2 meses antes: janeiro de 2028 em vez de março de 2028.',
    );
    expect(copy.impacto('x', 'R$ 50,00', 1, 'a', 'b')).toContain('1 mês antes');
  });
});
