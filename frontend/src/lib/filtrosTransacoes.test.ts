import { describe, expect, it } from 'vitest';

import { chips, escreverFiltros, FILTROS_VAZIOS, intervalo, lerFiltros, paraApi, valorDecimal } from './filtrosTransacoes';

const url = (q: string) => new URLSearchParams(q);

describe('filtros de "Todas as transações" na URL (N1)', () => {
  it('ida e volta: o que vai para a URL volta igual', () => {
    const f = {
      ...FILTROS_VAZIOS,
      periodo: 'mes_passado' as const,
      contas: [3, 7],
      direcao: 'SAIDA' as const,
      categorias: ['Food & Groceries', 'Bills & Utilities'],
      busca: 'ifood',
      valorMin: '50',
      valorMax: '1.000,50',
      soDivida: true,
      ordem: 'maior_valor' as const,
    };
    expect(lerFiltros(escreverFiltros(f))).toEqual(f);
  });

  it('sem filtro, a URL fica vazia', () => {
    expect(escreverFiltros(FILTROS_VAZIOS).toString()).toBe('');
    expect(lerFiltros(url(''))).toEqual(FILTROS_VAZIOS);
  });

  it('valores estranhos na URL são ignorados, não quebram a tela', () => {
    const f = lerFiltros(url('periodo=ontem&tipo=X&contas=1,a,-2,3&desde=31/12/2026&min=abc&ordem=zzz'));
    expect(f.periodo).toBe('tudo');
    expect(f.direcao).toBeNull();
    expect(f.contas).toEqual([1, 3]);
    expect(f.desde).toBeNull();
    expect(f.valorMin).toBeNull();
    expect(f.ordem).toBe('recentes');
  });

  it('listas acima de 20 itens são cortadas (o backend recusaria)', () => {
    const muitas = Array.from({ length: 30 }, (_, i) => i + 1).join(',');
    expect(lerFiltros(url(`contas=${muitas}`)).contas).toHaveLength(20);
  });

  it('período usa o "hoje" do usuário (a demo pode estar no futuro)', () => {
    expect(intervalo({ ...FILTROS_VAZIOS, periodo: 'mes' }, '2027-02-23')).toEqual({ desde: '2027-02-01', ate: '2027-02-23' });
    expect(intervalo({ ...FILTROS_VAZIOS, periodo: 'mes_passado' }, '2027-03-15')).toEqual({ desde: '2027-02-01', ate: '2027-02-28' });
    expect(intervalo({ ...FILTROS_VAZIOS, periodo: '30' }, '2026-11-23')).toEqual({ desde: '2026-10-24', ate: '2026-11-23' });
    expect(intervalo(FILTROS_VAZIOS, '2026-11-23')).toEqual({});
  });

  it('valor em reais digitado vira decimal para a API', () => {
    expect(valorDecimal('1.234,50')).toBe('1234.50');
    expect(valorDecimal('100')).toBe('100');
    expect(valorDecimal('-5')).toBeNull();
    const p = paraApi({ ...FILTROS_VAZIOS, valorMin: '1.000', soDivida: true, contas: [2] }, '2026-11-23');
    expect(p).toEqual({ valor_min: '1000', so_divida: 'true', contas: '2' });
  });

  it('um chip por filtro, e remover tira só aquele', () => {
    const f = { ...FILTROS_VAZIOS, contas: [1, 2], soDivida: true, busca: 'pix' };
    const nomes = {
      periodo: () => 'p', conta: (id: number) => `conta ${id}`, categoria: (c: string) => c,
      direcao: (d: string) => d, valor: () => 'v', soDivida: 'só dívida', busca: (b: string) => `"${b}"`,
    };
    const lista = chips(f, nomes);
    expect(lista.map((c) => c.rotulo)).toEqual(['conta 1', 'conta 2', '"pix"', 'só dívida']);
    expect(lista[0]!.remover(f).contas).toEqual([2]);
    expect(lista[3]!.remover(f).soDivida).toBe(false);
  });
});
