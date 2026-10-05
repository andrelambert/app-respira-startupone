/**
 * Dinheiro em centavos inteiros (docs/contexto-produto.md §6.2 e §12.13).
 *
 * A API devolve valores como string decimal ("2080.00"). A conversão aqui é
 * feita por manipulação de texto — nenhum valor monetário passa por float.
 * `Centavos` é um inteiro seguro até R$ 90 trilhões.
 */

export type Centavos = number & { readonly __centavos: unique symbol };

const DECIMAL = /^(-)?(\d+)(?:\.(\d{1,2}))?$/;

export function centavos(valor: number): Centavos {
  if (!Number.isSafeInteger(valor)) throw new Error('centavos precisam ser inteiros');
  return valor as Centavos;
}

/** "2080.00" → 208000 centavos. */
export function deDecimal(texto: string): Centavos {
  const m = DECIMAL.exec(texto.trim());
  if (!m) throw new Error(`valor monetário inválido: ${texto}`);
  const [, sinal, inteiro = '0', fracao = ''] = m;
  const total = Number(inteiro) * 100 + Number(fracao.padEnd(2, '0'));
  return centavos(sinal ? -total : total);
}

/**
 * Decimal com qualquer número de casas ("312.4166", "80") → centavos,
 * arredondando a terceira casa metade para cima. Usado nos números que vêm
 * dentro do contexto dos eventos.
 */
export function deDecimalLivre(texto: string): Centavos | null {
  const m = /^(-)?(\d+)(?:\.(\d+))?$/.exec(texto.trim());
  if (!m) return null;
  const [, sinal, inteiro = '0', fracao = ''] = m;
  const f = fracao.padEnd(3, '0');
  const total = Number(inteiro) * 100 + Number(f.slice(0, 2)) + (Number(f[2]) >= 5 ? 1 : 0);
  return centavos(sinal ? -total : total);
}

/** 90000 → "900.00" (formato que a API aceita). */
export function paraDecimal(c: Centavos): string {
  const neg = c < 0;
  const abs = Math.abs(c);
  return `${neg ? '-' : ''}${Math.trunc(abs / 100)}.${String(abs % 100).padStart(2, '0')}`;
}

function agrupar(inteiro: number): string {
  return String(inteiro).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

/** Arredonda para reais inteiros, metade para cima (como o ROUND do Oracle). */
export function reaisInteiros(c: Centavos): number {
  const abs = Math.abs(c);
  const r = Math.trunc(abs / 100) + (abs % 100 >= 50 ? 1 : 0);
  return c < 0 ? -r : r;
}

/**
 * Formata em BRL. `semCentavos` arredonda para reais inteiros — é o que vai
 * nas frases ("R$ 8.260", "R$ 733"); os centavos ficam para listas e detalhes.
 */
export function brl(c: Centavos, opcoes: { semCentavos?: boolean } = {}): string {
  const neg = c < 0;
  if (opcoes.semCentavos) {
    return `${neg ? '−' : ''}R$ ${agrupar(Math.abs(reaisInteiros(c)))}`;
  }
  const abs = Math.abs(c);
  const texto = `${agrupar(Math.trunc(abs / 100))},${String(abs % 100).padStart(2, '0')}`;
  return `${neg ? '−' : ''}R$ ${texto}`;
}

export function soma(valores: Centavos[]): Centavos {
  return centavos(valores.reduce((acc, v) => acc + v, 0));
}

export function sub(a: Centavos, b: Centavos): Centavos {
  return centavos(a - b);
}

/**
 * Lê o que a pessoa digitou ("1.234,56", "380", "R$ 95,5") em centavos.
 * Devolve null se não der para interpretar sem ambiguidade.
 */
export function deEntradaUsuario(texto: string): Centavos | null {
  const limpo = texto.replace(/[R$\s ]/g, '');
  if (!limpo) return null;
  if (!/^\d{1,3}(\.\d{3})*(,\d{1,2})?$|^\d+(,\d{1,2})?$/.test(limpo)) return null;
  const [inteiro = '0', fracao = ''] = limpo.replace(/\./g, '').split(',');
  return centavos(Number(inteiro) * 100 + Number(fracao.padEnd(2, '0')));
}

/** Percentual com vírgula: "436.22" → "436,2%". */
export function percentual(texto: string, casas = 1): string {
  const [inteiro = '0', fracao = ''] = texto.split('.');
  if (casas === 0) {
    const arred = Number(inteiro) + (Number((fracao + '0')[0]) >= 5 ? 1 : 0);
    return `${agrupar(arred)}%`;
  }
  // arredondamento em texto, sem float
  const digitos = (fracao + '0'.repeat(casas + 1)).slice(0, casas + 1);
  let n = BigInt(inteiro + digitos.slice(0, casas));
  if (Number(digitos[casas]) >= 5) n += 1n;
  const s = n.toString().padStart(casas + 1, '0');
  return `${agrupar(Number(s.slice(0, -casas)))},${s.slice(-casas)}%`;
}

/** Taxa mensal em fração ("0.150200") → "15,02% ao mês". */
export function taxaMensal(fracao: string): string {
  const [inteiro = '0', dec = ''] = fracao.split('.');
  const pontosBase = (dec + '000000').slice(0, 6); // 6 casas da fração
  const comoPercentual = `${Number(inteiro) * 100 + Number(pontosBase.slice(0, 2))}.${pontosBase.slice(2)}`;
  return percentual(comoPercentual, 2);
}
