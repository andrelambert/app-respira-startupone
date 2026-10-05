import { useQuery } from '@tanstack/react-query';

import { api, ApiError } from '@/lib/api';

export const chaves = {
  config: ['config'] as const,
  usuario: ['usuario'] as const,
  consentimentos: ['consentimentos'] as const,
  raiox: ['raiox'] as const,
  simulacoes: (capacidade: string | undefined) => ['simulacoes', capacidade ?? 'calculada'] as const,
  planoAtivo: ['plano', 'ativo'] as const,
  eventos: ['eventos'] as const,
  licao: (slug: string) => ['licao', slug] as const,
  dividas: ['dividas'] as const,
  visaoGeral: ['pfm', 'visao-geral'] as const,
  conta: (id: number) => ['pfm', 'conta', id] as const,
  extrato: (id: number, filtro: object) => ['pfm', 'extrato', id, filtro] as const,
};

/** Tudo que depende do dado financeiro — invalidado junto após mudanças. */
export const chavesFinanceiras = [
  chaves.raiox,
  ['simulacoes'],
  chaves.planoAtivo,
  chaves.eventos,
  chaves.dividas,
  chaves.consentimentos,
  ['pfm'],
];

export function useConfig() {
  return useQuery({ queryKey: chaves.config, queryFn: api.config, staleTime: Infinity });
}

export function useUsuario() {
  return useQuery({
    queryKey: chaves.usuario,
    queryFn: async () => {
      try {
        return await api.usuario();
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
  });
}

export function useConsentimentos(polling = false) {
  return useQuery({
    queryKey: chaves.consentimentos,
    queryFn: api.consentimentos,
    refetchInterval: polling ? 5000 : false,
  });
}

export function usePlanoAtivo() {
  return useQuery({
    queryKey: chaves.planoAtivo,
    queryFn: async () => {
      try {
        return await api.planoAtivo();
      } catch (e) {
        if (e instanceof ApiError && e.codigo === 'sem_plano') return null;
        throw e;
      }
    },
  });
}

export function useEventos() {
  return useQuery({ queryKey: chaves.eventos, queryFn: () => api.eventos(false) });
}

/** Visão geral do PFM. Enquanto algum banco ainda está coletando, atualiza a cada 5 s. */
export function useVisaoGeral() {
  return useQuery({
    queryKey: chaves.visaoGeral,
    queryFn: api.visaoGeral,
    refetchInterval: (q) =>
      q.state.data?.bancos.some((b) => b.status === 'ATIVO' && !b.coleta_concluida) ? 5000 : false,
  });
}
