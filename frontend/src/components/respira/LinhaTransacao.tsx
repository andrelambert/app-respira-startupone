import { useState } from 'react';

import { cx } from '@/components/ui';
import type { Transacao } from '@/lib/api';
import { categoriaNome, nomeFatura, pfm as copy, subcategoriaNome } from '@/lib/copy';
import { dataCompleta, dataHoraLocal, diaMes } from '@/lib/datas';
import { brl } from '@/lib/money';

/**
 * Uma transação do extrato; tocar abre o detalhe. ``banco``: mostra de qual
 * banco/conta ela veio (tela "Todas as transações", N1).
 */
export function LinhaTransacao({
  t,
  cartao,
  banco,
}: {
  t: Transacao;
  cartao: boolean;
  banco?: { nome: string | null; logo: string | null; conta: string | null };
}) {
  const [aberta, setAberta] = useState(false);
  const entrada = t.direcao === 'ENTRADA';
  const abs = Math.abs(t.valor) as typeof t.valor;
  const valor = `${entrada ? '+' : '−'}${brl(abs)}`;
  return (
    <li>
      <button
        type="button"
        aria-expanded={aberta}
        aria-controls={`tx-${t.id}`}
        onClick={() => setAberta((v) => !v)}
        className="flex min-h-toque w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-light"
      >
        <div className="min-w-0">
          <p className="truncate font-medium text-ink">{(cartao && t.estabelecimento) || t.descricao || '—'}</p>
          <p className="truncate text-xs text-slate">
            {diaMes(t.data)} · {t.categoria ? categoriaNome(t.categoria) : copy.semCategoria}
            {banco?.nome ? ` · ${banco.nome}` : ''}
          </p>
        </div>
        {/* Sinal + cor: a direção nunca depende só da cor (§10). */}
        <span className={cx('tabular shrink-0 font-semibold', entrada ? 'text-green-ink' : 'text-ink')}>{valor}</span>
      </button>
      {aberta && (
        <dl id={`tx-${t.id}`} className="grid grid-cols-2 gap-x-3 gap-y-2 bg-light px-4 py-3 text-sm">
          <Detalhe rotulo={copy.detalhe.descricao} valor={t.descricao} largo />
          {t.transacionado_em ? (
            <Detalhe rotulo={copy.detalhe.dataHora} valor={dataHoraLocal(t.transacionado_em)} />
          ) : (
            <Detalhe rotulo={copy.detalhe.data} valor={dataCompleta(t.data)} />
          )}
          <Detalhe rotulo={copy.detalhe.valor} valor={valor} />
          {banco && <Detalhe rotulo={copy.detalhe.conta} valor={[banco.nome, banco.conta].filter(Boolean).join(' · ')} />}
          {/* Categoria e subcategoria da Belvo, traduzidas (A6). */}
          <Detalhe rotulo={copy.detalhe.categoria} valor={t.categoria && categoriaNome(t.categoria)} />
          <Detalhe rotulo={copy.detalhe.subcategoria} valor={subcategoriaNome(t.subcategoria)} />
          <Detalhe rotulo={copy.detalhe.tipoOperacao} valor={t.tipo_operacao} />
          {/* Estabelecimento e final do cartão só existem em transação de cartão. */}
          {cartao && <Detalhe rotulo={copy.detalhe.finalCartao} valor={t.final_cartao} />}
          {cartao && <Detalhe rotulo={copy.detalhe.fatura} valor={nomeFatura(t.fatura)} />}
          {cartao && <Detalhe rotulo={copy.detalhe.estabelecimento} valor={t.estabelecimento} />}
          {cartao && t.estabelecimento_site && (
            <div>
              <dt className="text-slate">{copy.detalhe.site}</dt>
              <dd className="truncate">
                <a href={t.estabelecimento_site} target="_blank" rel="noopener noreferrer" className="font-medium text-blue underline">
                  {t.estabelecimento_site.replace(/^https:\/\//, '')}
                </a>
              </dd>
            </div>
          )}
        </dl>
      )}
    </li>
  );
}

function Detalhe({ rotulo, valor, largo }: { rotulo: string; valor: string | null | undefined; largo?: boolean }) {
  return (
    <div className={largo ? 'col-span-2' : undefined}>
      <dt className="text-slate">{rotulo}</dt>
      <dd className="break-words font-medium text-ink">{valor || '—'}</dd>
    </div>
  );
}
