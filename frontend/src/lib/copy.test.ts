import { describe, expect, it } from 'vitest';

import type { Evento } from './api';
import { alertaMinimo, erroConexao, fraseAcompanhamento, fraseComparacao, fraseRaioX, mensagemEvento } from './copy';
import { centavos } from './money';

const nbsp = (s: string) => s.replace(/ /g, ' ');

describe('frases canônicas do docs/contexto-produto.md §11', () => {
  it('Raio-X', () => {
    expect(
      nbsp(
        fraseRaioX({
          total: centavos(826000),
          qtd: 5,
          jurosMes: centavos(73320),
          maiorValor: centavos(31242),
          maiorModalidade: 'CARTAO_ROTATIVO',
        }),
      ),
    ).toBe(
      'Você deve R$ 8.260 em 5 compromissos e paga R$ 733 por mês só em juros; R$ 312 disso vem do rotativo do cartão.',
    );
  });

  it('Raio-X sem juros (só fatura do cartão em dia)', () => {
    expect(
      nbsp(fraseRaioX({ total: centavos(180000), qtd: 1, jurosMes: centavos(0), maiorValor: centavos(0), maiorModalidade: null })),
    ).toBe('Você deve R$ 1.800 em 1 compromisso, e ele não cobra juros hoje.');
  });

  it('alerta do mínimo', () => {
    expect(nbsp(alertaMinimo(centavos(1020)))).toBe(
      'Pagando só o mínimo, sua dívida não diminui — ela cresce R$ 10 por mês.',
    );
  });

  it('comparação equilibrado × mais econômico', () => {
    expect(
      nbsp(
        fraseComparacao(
          { metodo: 'EQUILIBRADO', meses: 19, juros: centavos(823999), primeira: 2 },
          { meses: 18, juros: centavos(792369), primeira: 10 },
        ),
      ),
    ).toBe(
      'Pelo caminho equilibrado você fica livre em 19 meses e paga R$ 316 a mais de juros do que pelo mais econômico, que leva 18 — só que nele a primeira dívida some no 10º mês, e no equilibrado ela some já no 2º.',
    );
  });

  it('bola de neve usa o artigo certo', () => {
    expect(
      nbsp(
        fraseComparacao(
          { metodo: 'SNOWBALL', meses: 21, juros: centavos(1049156), primeira: 2 },
          { meses: 18, juros: centavos(792369), primeira: 10 },
        ),
      ),
    ).toContain('R$ 2.568 a mais de juros');
  });

  it('mês ruim sem linguagem de falha', () => {
    const f = nbsp(
      fraseAcompanhamento({
        mes: '2026-10-01',
        previsto: centavos(90000),
        realizado: centavos(72000),
        dataAnterior: '2028-04-01',
        dataNova: '2028-05-01',
      }),
    );
    expect(f).toBe('Em outubro entraram R$ 180 a menos no plano; sua data nova é maio de 2028.');
    expect(f).not.toMatch(/falh|atrasad|reprov/i);
  });

  it('erros do widget sempre em português, nunca código cru', () => {
    expect(erroConexao('institution_down')).toMatch(/fora do ar/);
    expect(erroConexao('codigo_que_nao_existe')).toMatch(/Não deu certo/);
    expect(erroConexao(null)).toMatch(/saiu antes/);
  });

  it('alerta de evento carrega valor em reais (regra de parcimônia)', () => {
    const e: Evento = {
      id: 1,
      tipo: 'ENTRADA_ROTATIVO',
      severidade: 3,
      divida_id: 1,
      contexto: { instituicao: 'Banco A', saldo: '2080.00', taxa_anual: '436.2163', juros_mes: '312.42' },
      detectado_em: '2026-10-03T00:00:00Z',
      notificado_em: null,
      licao: 'rotativo',
    };
    const m = mensagemEvento(e);
    expect(nbsp(m.texto)).toContain('R$ 312 de juros por mês');
    expect(m.texto).toContain('436% ao ano');
    expect(m.tom).toBe('fato');
  });

  it('desvio do plano é atenção, nunca fato/vermelho', () => {
    const m = mensagemEvento({
      id: 2,
      tipo: 'DESVIO_PLANO',
      severidade: 2,
      divida_id: null,
      contexto: {
        mes: '2026-10-01',
        falta: '240.00',
        data_anterior: '2028-04-01',
        data_nova: '2028-05-01',
        reposicao_mensal: '80',
        meses_reposicao: 3,
      },
      detectado_em: '2026-11-01T00:00:00Z',
      notificado_em: null,
      licao: 'plano-dobra',
    });
    expect(m.tom).toBe('atencao');
    expect(nbsp(m.texto)).toBe(
      'Sua data nova é maio de 2028. Colocando R$ 80 a mais nos próximos 3 meses, você repõe o que faltou.',
    );
  });
});
