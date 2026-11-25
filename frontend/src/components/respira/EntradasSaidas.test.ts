import { describe, expect, it } from 'vitest';

import { lerFiltros } from '@/lib/filtrosTransacoes';
import { centavos } from '@/lib/money';

import { linkDaBarra, valorDoMes } from './EntradasSaidas';

describe('entradas e saídas (Contas)', () => {
  it('a barra de saídas soma os gastos (essenciais + outros), sem dívida', () => {
    const m = {
      mes: '2026-10-01',
      entradas: centavos(530000),
      essenciais: centavos(335000),
      outros_gastos: centavos(70000),
      pagamentos_divida: centavos(175500),
      sobra: centavos(195000),
      reserva: centavos(0),
    };
    expect(valorDoMes(m, 'entradas')).toBe(530000);
    expect(valorDoMes(m, 'saidas')).toBe(405000);
  });

  it('tocar na barra abre as transações com todos os filtros à vista', () => {
    const link = linkDaBarra('2026-02-01', 'entradas', [3, 7]);
    expect(link.startsWith('/transacoes?')).toBe(true);
    expect(lerFiltros(new URLSearchParams(link.split('?')[1]))).toMatchObject({
      periodo: 'personalizado',
      desde: '2026-02-01',
      ate: '2026-02-28',
      direcao: 'ENTRADA',
      fluxo: 'renda',
      contas: [3, 7],
    });
    const saidas = lerFiltros(new URLSearchParams(linkDaBarra('2026-10-01', 'saidas', []).split('?')[1]));
    expect(saidas).toMatchObject({ direcao: 'SAIDA', fluxo: 'gasto', contas: [] });
  });
});
