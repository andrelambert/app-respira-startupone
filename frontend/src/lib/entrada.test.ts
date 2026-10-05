import { describe, expect, it } from 'vitest';

import {
  cpfValido,
  emailValido,
  formatarCpf,
  nomeCompletoValido,
  sanitizarDinheiro,
  sanitizarNome,
  sanitizarPercentual,
  semEspacos,
} from './entrada';

describe('CPF', () => {
  it('formata enquanto digita e descarta o que não é número', () => {
    expect(formatarCpf('529')).toBe('529');
    expect(formatarCpf('5299')).toBe('529.9');
    expect(formatarCpf('5299822')).toBe('529.982.2');
    expect(formatarCpf('5299822472')).toBe('529.982.247-2');
    expect(formatarCpf('52998224725')).toBe('529.982.247-25');
    expect(formatarCpf('abc529.982x247-25999')).toBe('529.982.247-25'); // letras fora, máx. 11 dígitos
  });

  it('valida os dígitos verificadores', () => {
    expect(cpfValido('529.982.247-25')).toBe(true);
    expect(cpfValido('529.982.247-24')).toBe(false);
    expect(cpfValido('111.111.111-11')).toBe(false); // todos iguais passam no módulo 11, mas não existem
    expect(cpfValido('529.982.247')).toBe(false);
  });
});

describe('e-mail', () => {
  it('não aceita espaço', () => {
    expect(semEspacos(' andre @ exemplo.com ')).toBe('andre@exemplo.com');
  });

  it('exige @dominio.tld', () => {
    expect(emailValido('andre@exemplo.com')).toBe(true);
    expect(emailValido('andre@exemplo.com.br')).toBe(true);
    expect(emailValido('andre@exemplo')).toBe(false);
    expect(emailValido('andre@exemplo.c')).toBe(false);
    expect(emailValido('andre.exemplo.com')).toBe(false);
    expect(emailValido('@exemplo.com')).toBe(false);
  });
});

describe('nome e valores', () => {
  it('nome completo tem nome e sobrenome, só letras', () => {
    expect(nomeCompletoValido('Juliana Ramos')).toBe(true);
    expect(nomeCompletoValido('Juliana')).toBe(false);
    expect(sanitizarNome('Ju1iana  Ram@s')).toBe('Juiana Rams');
  });

  it('dinheiro e percentual só com dígitos e uma vírgula', () => {
    expect(sanitizarDinheiro('R$ 1.234,567')).toBe('1.234,56');
    expect(sanitizarDinheiro('95,5,0')).toBe('95,50');
    expect(sanitizarPercentual('3.5')).toBe('3,5');
    expect(sanitizarPercentual('a12,34567')).toBe('12,3456');
  });
});
