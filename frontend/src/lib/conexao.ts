/**
 * O widget abre em NOVA ABA, nunca em iframe (docs/contexto-produto.md §7.3): o passo seguinte
 * é o site do banco, que quase sempre proíbe ser enquadrado.
 *
 * As callbacks caem na aba nova; ela avisa a aba original por
 * BroadcastChannel (fallback: evento `storage`). A aba original NÃO confia só
 * nisso — também faz polling do backend, que é a fonte de verdade.
 */

const CANAL = 'respira-belvo';

export type MensagemConexao =
  | { tipo: 'sucesso'; consentimentoId: number }
  | { tipo: 'saida'; codigo: string | null }
  | { tipo: 'evento'; codigo: string | null; fatal: boolean };

export function avisarAbaOriginal(msg: MensagemConexao): void {
  try {
    const bc = new BroadcastChannel(CANAL);
    bc.postMessage(msg);
    bc.close();
  } catch {
    /* navegador sem BroadcastChannel: só o fallback abaixo */
  }
  try {
    // O evento `storage` dispara nas OUTRAS abas da mesma origem.
    localStorage.setItem(CANAL, JSON.stringify({ ...msg, t: Date.now() }));
    localStorage.removeItem(CANAL);
  } catch {
    /* storage bloqueado: o polling da aba original cobre */
  }
}

function valida(dado: unknown): MensagemConexao | null {
  if (!dado || typeof dado !== 'object' || !('tipo' in dado)) return null;
  const d = dado as Record<string, unknown>;
  if (d.tipo === 'sucesso' && typeof d.consentimentoId === 'number') {
    return { tipo: 'sucesso', consentimentoId: d.consentimentoId };
  }
  const codigo = typeof d.codigo === 'string' ? d.codigo.slice(0, 80) : null;
  if (d.tipo === 'saida') return { tipo: 'saida', codigo };
  if (d.tipo === 'evento') return { tipo: 'evento', codigo, fatal: d.fatal !== false };
  return null;
}

export function ouvirConexao(callback: (msg: MensagemConexao) => void): () => void {
  let bc: BroadcastChannel | null = null;
  try {
    bc = new BroadcastChannel(CANAL);
    bc.onmessage = (ev: MessageEvent) => {
      const msg = valida(ev.data);
      if (msg) callback(msg);
    };
  } catch {
    bc = null;
  }
  const onStorage = (ev: StorageEvent) => {
    if (ev.key !== CANAL || !ev.newValue) return;
    try {
      const msg = valida(JSON.parse(ev.newValue));
      if (msg) callback(msg);
    } catch {
      /* ignora conteúdo inválido */
    }
  };
  window.addEventListener('storage', onStorage);
  return () => {
    bc?.close();
    window.removeEventListener('storage', onStorage);
  };
}

/**
 * Precisa ser chamado DIRETAMENTE no handler do clique, de forma síncrona —
 * se o fetch do token vier antes, o navegador trata como popup não solicitado.
 * Devolve null se o bloqueador de popup barrou.
 */
export function abrirAbaVazia(texto: string): Window | null {
  const aba = window.open('', '_blank');
  if (!aba) return null;
  try {
    // A aba vai para o widget e depois para o banco: ela não precisa (nem
    // deve) conseguir mexer nesta aba. A conversa entre as duas é só pelo canal.
    aba.opener = null;
    aba.document.title = 'Respira';
    aba.document.body.style.font = '16px system-ui, sans-serif';
    aba.document.body.style.padding = '24px';
    aba.document.body.textContent = texto;
  } catch {
    /* sem acesso ao documento: segue só com a navegação */
  }
  return aba;
}
