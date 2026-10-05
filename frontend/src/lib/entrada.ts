/**
 * Máscaras, sanitização e validações de campos de formulário.
 *
 * Regra da casa: o campo já impede o que não faz sentido digitar (letra no
 * CPF, espaço no e-mail) e formata sozinho — a pessoa nunca precisa saber o
 * formato certo. A validação de verdade é repetida no backend (Pydantic).
 */

export function somenteDigitos(valor: string, max?: number): string {
  const d = valor.replace(/\D/g, '');
  return max === undefined ? d : d.slice(0, max);
}

/** "52998224725" → "529.982.247-25", formatando enquanto digita. */
export function formatarCpf(valor: string): string {
  const d = somenteDigitos(valor, 11);
  if (d.length <= 3) return d;
  if (d.length <= 6) return `${d.slice(0, 3)}.${d.slice(3)}`;
  if (d.length <= 9) return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6)}`;
  return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
}

/** Algoritmo oficial dos dígitos verificadores do CPF (módulo 11). */
export function cpfValido(cpf: string): boolean {
  const d = somenteDigitos(cpf);
  if (d.length !== 11 || /^(\d)\1{10}$/.test(d)) return false;
  for (const n of [9, 10]) {
    let soma = 0;
    for (let i = 0; i < n; i++) soma += Number(d[i]) * (n + 1 - i);
    if (((soma * 10) % 11) % 10 !== Number(d[n])) return false;
  }
  return true;
}

/** E-mail nunca tem espaço: remove qualquer espaço digitado ou colado. */
export function semEspacos(valor: string): string {
  return valor.replace(/\s/g, '');
}

/** nome@dominio.tld — domínio com ponto e terminação de pelo menos 2 letras. */
export const EMAIL_RE = /^[^\s@]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}$/;

export function emailValido(email: string): boolean {
  return email.length <= 254 && EMAIL_RE.test(email);
}

export const SENHA_MINIMO = 8;

/** Nome e sobrenome, só letras (com acento), espaço, apóstrofo e hífen. */
export function nomeCompletoValido(nome: string): boolean {
  const n = nome.trim();
  return /^[A-Za-zÀ-ÿ' .-]+$/.test(n) && n.split(/\s+/).filter((p) => p.length >= 2).length >= 2;
}

/** Nome não aceita número nem símbolo estranho, e não acumula espaços. */
export function sanitizarNome(valor: string): string {
  return valor.replace(/[^A-Za-zÀ-ÿ' .-]/g, '').replace(/\s{2,}/g, ' ').replace(/^\s+/, '');
}

/** Valor em reais digitado: só dígitos, ponto e vírgula; uma vírgula, 2 casas. */
export function sanitizarDinheiro(valor: string): string {
  const limpo = valor.replace(/[^\d.,]/g, '');
  const [inteiro = '', ...resto] = limpo.split(',');
  return resto.length ? `${inteiro},${resto.join('').replace(/\./g, '').slice(0, 2)}` : inteiro;
}

/** Percentual digitado ("3,5"): dígitos e uma vírgula/ponto, até 4 casas. */
export function sanitizarPercentual(valor: string): string {
  const limpo = valor.replace(/[^\d.,]/g, '').replace('.', ',');
  const [inteiro = '', ...resto] = limpo.split(',');
  return resto.length ? `${inteiro.slice(0, 2)},${resto.join('').replace(/[.,]/g, '').slice(0, 4)}` : inteiro.slice(0, 2);
}

type ComOnChange = { onChange: (e: { target: { value: string } }) => unknown };

/**
 * Envolve o ``register`` do react-hook-form para transformar o valor antes de
 * ele ser lido (máscara/sanitização) — o campo continua não controlado.
 */
export function comMascara<T extends ComOnChange>(registro: T, transformar: (v: string) => string): T {
  return {
    ...registro,
    onChange: (e: { target: { value: string } }) => {
      const novo = transformar(e.target.value);
      if (novo !== e.target.value) e.target.value = novo;
      return registro.onChange(e);
    },
  };
}
