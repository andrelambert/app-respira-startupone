import { describe, expect, it } from 'vitest';

import {
  brl,
  centavos,
  deDecimal,
  deEntradaUsuario,
  paraDecimal,
  percentual,
  reaisInteiros,
  taxaMensal,
} from './money';

describe('money', () => {
  it('converte decimal da API para centavos sem float', () => {
    expect(deDecimal('2080.00')).toBe(208000);
    expect(deDecimal('0.1')).toBe(10);
    expect(deDecimal('-12.34')).toBe(-1234);
    expect(deDecimal('7923.69')).toBe(792369);
    expect(() => deDecimal('1e3')).toThrow();
  });

  it('volta para o formato da API', () => {
    expect(paraDecimal(centavos(90000))).toBe('900.00');
    expect(paraDecimal(centavos(5))).toBe('0.05');
    expect(paraDecimal(centavos(-1234))).toBe('-12.34');
  });

  it('formata em BRL com e sem centavos', () => {
    expect(brl(centavos(826000))).toBe('R$ 8.260,00');
    expect(brl(centavos(73320), { semCentavos: true })).toBe('R$ 733');
    expect(brl(centavos(31242), { semCentavos: true })).toBe('R$ 312');
    expect(brl(centavos(1020), { semCentavos: true })).toBe('R$ 10');
    expect(brl(centavos(123456789))).toBe('R$ 1.234.567,89');
  });

  it('arredonda metade para cima', () => {
    expect(reaisInteiros(centavos(792369))).toBe(7924);
    expect(reaisInteiros(centavos(823999))).toBe(8240);
    expect(reaisInteiros(centavos(1049156))).toBe(10492);
    expect(reaisInteiros(centavos(150))).toBe(2);
    expect(reaisInteiros(centavos(149))).toBe(1);
  });

  it('lê o que a pessoa digita', () => {
    expect(deEntradaUsuario('380')).toBe(38000);
    expect(deEntradaUsuario('1.234,56')).toBe(123456);
    expect(deEntradaUsuario('R$ 95,5')).toBe(9550);
    expect(deEntradaUsuario('12,345')).toBeNull();
    expect(deEntradaUsuario('abc')).toBeNull();
    expect(deEntradaUsuario('')).toBeNull();
  });

  it('formata percentuais e taxas', () => {
    expect(percentual('436.22')).toBe('436,2%');
    expect(percentual('436.26', 0)).toBe('436%');
    expect(percentual('15.06', 0)).toBe('15%');
    expect(percentual('1234.5', 0)).toBe('1.235%');
    expect(taxaMensal('0.150200')).toBe('15,02%');
    expect(taxaMensal('0.035000')).toBe('3,50%');
  });
});
