import { describe, expect, it } from 'vitest';
import { dataHoraLocal } from './datas';

describe('dataHoraLocal', () => {
  it('mostra o horário de Brasília que veio do backend, sem reconverter fuso', () => {
    expect(dataHoraLocal('2026-09-05T22:30:00-03:00')).toBe('5 de setembro de 2026, 22:30');
  });

  it('sem hora reconhecível, mostra só a data', () => {
    expect(dataHoraLocal('2026-09-05')).toBe('5 de setembro de 2026');
  });
});
