/**
 * A3 (Fase 7): depois de um deploy, a aba aberta ainda aponta para os chunks
 * antigos, que não existem mais. Recarregar uma vez busca o index.html novo.
 * A guarda em sessionStorage impede laço se o erro persistir.
 */
const CHAVE = 'respira-recarga-chunk';
const JANELA_MS = 30_000;

const PADROES = [
  'Failed to fetch dynamically imported module',
  'Importing a module script failed',
  'error loading dynamically imported module',
  'ChunkLoadError',
];

export function ehFalhaDeChunk(erro: unknown): boolean {
  if (!(erro instanceof Error)) return false;
  const texto = `${erro.name} ${erro.message}`;
  return PADROES.some((p) => texto.includes(p));
}

/** Devolve true se pode recarregar agora (e registra a tentativa). */
export function podeRecarregar(agora: number = Date.now()): boolean {
  try {
    const anterior = Number(sessionStorage.getItem(CHAVE) ?? 0);
    if (agora - anterior < JANELA_MS) return false;
    sessionStorage.setItem(CHAVE, String(agora));
    return true;
  } catch {
    return false; // sem sessionStorage (modo privado restrito): não arrisca laço
  }
}
