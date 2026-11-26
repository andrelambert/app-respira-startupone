import { describe, expect, it } from 'vitest';

import { alerta, fluxo, mesQueVem, plano } from './copy';
import { centavos } from './money';

// Teste com usuária (Fase 7): textos que respondem ao que ela não entendeu.
describe('textos do teste com usuária', () => {
  it('o plano parte de todos os gastos e mostra o teto cortando o não essencial', () => {
    expect(plano.sliderAjuda(centavos(127818))).toContain('menos o que você costuma gastar (tudo, inclusive o cartão)');
    expect(plano.cortando(centavos(175500))).toMatch(/daria para colocar até R\$\s1\.755 por mês/);
  });

  it('como os meses fecharam', () => {
    expect(fluxo.fechamento(0, 6)).toBe('Você fechou os 6 meses no negativo — a diferença saiu da reserva ou do saldo.');
    expect(fluxo.fechamento(6, 6)).toBe('Você fechou os 6 meses no positivo.');
    expect(fluxo.fechamento(2, 6)).toBe('Você fechou 2 de 6 meses no positivo.');
  });

  it('o mês que vem fala em valor, sem culpa', () => {
    expect(mesQueVem.falta('R$ 156,00')).toMatch(/^Faltam R\$ 156,00/);
    expect(mesQueVem.sobra('R$ 429,53')).toBe('Sobram R$ 429,53 para o resto do mês.');
  });

  it('botões do alerta dizem o que fazem', () => {
    expect([alerta.entendi, alerta.saibaMais]).toEqual(['Ok, entendi', 'Ver explicação']);
  });
});
