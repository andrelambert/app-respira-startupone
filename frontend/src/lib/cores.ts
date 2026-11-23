import type { Metodo } from './api';

/**
 * Cores das três estratégias nos gráficos. Validadas com o `validate_palette`
 * do dataviz em modo claro, todos os pares (CVD ΔE ≥ 9,2; normal ≥ 27,6). O
 * aqua fica abaixo de 3:1 de contraste: por isso há legenda, rótulo e tabela.
 */
export const COR_METODO: Record<Metodo, string> = {
  AVALANCHE: '#7C3AED',
  EQUILIBRADO: '#eb6834',
  SNOWBALL: '#1baf7a',
};

// Cores do design system (§10): verde = entrada, azul = gasto essencial,
// cinza = outros gastos, roxo = dívida/plano, navy = a linha da sobra.
export const COR_FLUXO = {
  entradas: '#059669',
  essenciais: '#2563EB',
  outros: '#94A3B8',
  divida: '#7C3AED',
  sobra: '#12314F',
} as const;
