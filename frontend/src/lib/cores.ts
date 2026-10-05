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
