import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';

import { LogoBanco } from '@/components/respira';
import { Button, Card, Carregando, EstadoErro, EstadoVazio, Money, cx } from '@/components/ui';
import { chaves } from '@/hooks/queries';
import { useDebounced } from '@/hooks/useDebounced';
import { api, type ContaBancaria, type Fatura, type FiltroExtrato, type Transacao } from '@/lib/api';
import { pfm as copy, tipoBelvo } from '@/lib/copy';
import { dataCompleta, dataHoraLocal, diaMes } from '@/lib/datas';
import { brl } from '@/lib/money';
import { SituacaoFatura, identificacaoConta } from './Contas';

const DEPOSITO = new Set(['CORRENTE', 'POUPANCA', 'PAGAMENTO']);
type Filtro = 'TODAS' | 'ENTRADA' | 'SAIDA';
type Aba = 'faturas' | 'extrato';

/** Detalhe de uma conta ou cartão: saldo/fatura + extrato paginado. */
export default function ContaDetalhe() {
  const id = Number(useParams().id);
  const detalhe = useQuery({ queryKey: chaves.conta(id), queryFn: () => api.conta(id), enabled: id > 0 });

  if (detalhe.isLoading) return <Carregando />;
  if (detalhe.isError || !detalhe.data) {
    return (
      <EstadoVazio
        titulo="Conta não encontrada"
        texto="Ela pode ter sido desconectada."
        acao={
          <Link to="/contas" className="font-semibold text-blue underline">
            {copy.voltar}
          </Link>
        }
      />
    );
  }
  const { conta, faturas } = detalhe.data;
  const identificacao = identificacaoConta(conta);
  const cartao = conta.tipo === 'CARTAO_CREDITO';
  return (
    <div className="flex flex-col gap-5">
      <Link to="/contas" className="min-h-toque self-start py-2 text-sm font-semibold text-blue">
        {copy.voltar}
      </Link>
      <div>
        <p className="flex items-center gap-2 text-sm text-slate">
          <LogoBanco nome={conta.instituicao} logo={conta.instituicao_logo} tamanho="p" />
          {conta.instituicao}
        </p>
        <h1 className="text-2xl font-bold text-navy">
          {copy.tipo[conta.tipo] ?? conta.tipo}
          {identificacao && <span className="font-normal text-slate"> {identificacao}</span>}
        </h1>
        <p className="text-sm text-slate">{[conta.nome, tipoBelvo(conta.tipo_externo)].filter(Boolean).join(' · ')}</p>
      </div>

      <Resumo conta={conta} />
      {cartao ? <AbasCartao contaId={conta.id} faturas={faturas} /> : <ExtratoConta contaId={conta.id} />}
    </div>
  );
}

/** Cartão: faturas e extrato em abas. A aba fica na URL (?aba=extrato) e sobrevive ao "voltar". */
function AbasCartao({ contaId, faturas }: { contaId: number; faturas: Fatura[] }) {
  const [params, setParams] = useSearchParams();
  const aba: Aba = params.get('aba') === 'extrato' ? 'extrato' : 'faturas';
  const abas: Aba[] = ['faturas', 'extrato'];

  function escolher(a: Aba) {
    setParams(a === 'faturas' ? {} : { aba: a }, { replace: true });
  }
  // Setas trocam de aba (padrão WAI-ARIA de tabs).
  function teclado(ev: React.KeyboardEvent) {
    if (ev.key !== 'ArrowLeft' && ev.key !== 'ArrowRight') return;
    ev.preventDefault();
    const proxima = abas[(abas.indexOf(aba) + 1) % abas.length]!;
    escolher(proxima);
    document.getElementById(`aba-${proxima}`)?.focus();
  }

  return (
    <div className="flex flex-col gap-4">
      <div role="tablist" aria-label={copy.abasCartao} onKeyDown={teclado} className="grid grid-cols-2 border-b border-line">
        {abas.map((a) => (
          <button
            key={a}
            id={`aba-${a}`}
            type="button"
            role="tab"
            aria-selected={aba === a}
            aria-controls={`painel-${a}`}
            tabIndex={aba === a ? 0 : -1}
            onClick={() => escolher(a)}
            // Sublinhado, não "pílula": não confunde com o filtro Todas/Entradas/Saídas.
            className={cx(
              '-mb-px min-h-toque border-b-2 text-base font-semibold',
              aba === a ? 'border-blue text-navy' : 'border-transparent text-slate hover:text-navy',
            )}
          >
            {copy.abas[a]}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`painel-${aba}`} aria-labelledby={`aba-${aba}`} className="flex flex-col gap-4">
        {aba === 'faturas' ? <Faturas faturas={faturas} /> : <ExtratoConta contaId={contaId} cartao />}
      </div>
    </div>
  );
}

function Resumo({ conta }: { conta: ContaBancaria }) {
  if (DEPOSITO.has(conta.tipo)) {
    return (
      <Card className="flex flex-col gap-1">
        <p className="text-sm text-slate">{copy.saldo}</p>
        <Money valor={conta.saldo} className="text-4xl font-bold text-navy" />
        {conta.disponivel !== null && (
          <p className="text-sm text-slate">
            {copy.disponivel} <Money valor={conta.disponivel} />
            {conta.limite_cheque_especial > 0 && ` · ${copy.limiteChequeEspecial(conta.limite_cheque_especial)}`}
          </p>
        )}
        {(conta.agencia || conta.numero_conta) && (
          <dl className="mt-2 grid grid-cols-2 gap-2 border-t border-line pt-3 text-sm">
            {conta.agencia && (
              <div>
                <dt className="text-slate">{copy.agencia}</dt>
                <dd className="font-semibold text-ink tabular">{conta.agencia}</dd>
              </div>
            )}
            {conta.numero_conta && (
              <div>
                <dt className="text-slate">{copy.conta}</dt>
                <dd className="font-semibold text-ink tabular">{conta.numero_conta}</dd>
              </div>
            )}
          </dl>
        )}
      </Card>
    );
  }
  if (conta.tipo === 'CARTAO_CREDITO') {
    return (
      <Card className="flex flex-col gap-3">
        <div className="grid grid-cols-3 gap-2 text-sm">
          <Valor rotulo={copy.usado} valor={conta.saldo} />
          {conta.disponivel !== null && <Valor rotulo={copy.disponivel} valor={conta.disponivel} />}
          {conta.limite_credito !== null && <Valor rotulo={copy.limite} valor={conta.limite_credito} />}
        </div>
      </Card>
    );
  }
  return (
    <Card className="flex flex-col gap-1">
      <p className="text-sm text-slate">{copy.saldoDevedor}</p>
      <Money valor={conta.saldo} className="text-4xl font-bold text-navy" />
    </Card>
  );
}

function Valor({ rotulo, valor }: { rotulo: string; valor: Parameters<typeof brl>[0] }) {
  return (
    <div>
      <p className="text-slate">{rotulo}</p>
      <Money valor={valor} className="font-semibold text-navy" />
    </div>
  );
}

function Faturas({ faturas }: { faturas: Fatura[] }) {
  const [atual, ...anteriores] = faturas;
  if (!atual) {
    return (
      <Card as="div">
        <p className="text-sm text-slate">{copy.semFatura}</p>
      </Card>
    );
  }
  const aberta = atual.situacao !== 'PAGA';
  return (
    <>
      <Card tom={atual.situacao === 'ATRASADA' ? 'fato' : atual.situacao === 'PAGA' ? 'progresso' : 'neutro'} className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-sm text-slate">{copy.faturaAtual}</p>
            {/* Título: bill_name, como a Belvo manda (ex.: Sep-2026). */}
            <h2 className="text-lg font-bold text-navy">{atual.nome || copy.faturaAtual}</h2>
          </div>
          <SituacaoFatura situacao={atual.situacao} />
        </div>
        <Money valor={aberta ? atual.em_aberto : atual.total} className="text-4xl font-bold text-navy" />
        {atual.vencimento && (
          <p className="text-sm text-slate">
            {atual.situacao === 'ATRASADA' ? copy.venceu(dataCompleta(atual.vencimento)) : copy.vence(dataCompleta(atual.vencimento))}
          </p>
        )}
        <dl className="grid grid-cols-3 gap-2 text-sm">
          <div>
            <dt className="text-slate">Total</dt>
            <dd className="font-semibold text-ink">
              <Money valor={atual.total} />
            </dd>
          </div>
          {/* Mínimo só interessa enquanto não foi coberto pelos pagamentos. */}
          {aberta && atual.minimo !== null && atual.pago < atual.minimo && (
            <div>
              <dt className="text-slate">{copy.minimo}</dt>
              <dd className="font-semibold text-ink">
                <Money valor={atual.minimo} />
              </dd>
            </div>
          )}
          <div>
            <dt className="text-slate">{copy.pago}</dt>
            <dd className="font-semibold text-ink">
              <Money valor={atual.pago} />
            </dd>
          </div>
        </dl>
        <PagamentosFatura fatura={atual} />
      </Card>
      {anteriores.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="font-semibold text-navy">{copy.faturas}</h2>
          <ul className="flex flex-col divide-y divide-line rounded-2xl border border-line bg-white">
            {anteriores.map((f) => (
              <li key={f.id} className="flex flex-col gap-2 px-4 py-3 text-sm">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-bold text-navy">{f.nome || (f.vencimento ? diaMes(f.vencimento) : '—')}</p>
                    {f.vencimento && <p className="text-xs text-slate">{copy.vence(dataCompleta(f.vencimento))}</p>}
                  </div>
                  <Money valor={f.total} className="shrink-0 font-semibold text-navy" />
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <SituacaoFatura situacao={f.situacao} />
                  {f.parcelada && <span className="text-xs text-slate">{copy.parcelada}</span>}
                  {/* Mínimo só enquanto ainda não foi coberto pelos pagamentos. */}
                  {f.situacao !== 'PAGA' && f.minimo !== null && f.pago < f.minimo && (
                    <span className="text-xs text-ink">{copy.minimoAPagar(f.minimo)}</span>
                  )}
                </div>
                <PagamentosFatura fatura={f} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

/** payments[] da fatura: data e valor de cada pagamento, do mais antigo ao mais novo. */
function PagamentosFatura({ fatura }: { fatura: Fatura }) {
  if (fatura.pagamentos.length === 0) return null;
  return (
    <div className="flex flex-col gap-1 border-t border-line pt-2">
      <p className="text-xs font-semibold text-slate">{copy.pagamentos}</p>
      <ul className="flex flex-col gap-1">
        {fatura.pagamentos.map((p, i) => (
          <li key={`${p.data}-${i}`} className="flex items-center justify-between gap-3 text-sm">
            <span className="text-ink">{p.data ? copy.pagoEm(dataCompleta(p.data)) : copy.pago}</span>
            <Money valor={p.valor} className="font-semibold text-green-ink" />
          </li>
        ))}
      </ul>
    </div>
  );
}

function ExtratoConta({ contaId, cartao = false }: { contaId: number; cartao?: boolean }) {
  const [filtro, setFiltro] = useState<Filtro>('TODAS');
  const [busca, setBusca] = useState('');
  const [pagina, setPagina] = useState(1);
  const [dias, setDias] = useState(0); // 0 = tudo
  const buscaDebounced = useDebounced(busca.trim(), 300);
  const topo = useRef<HTMLHeadingElement>(null);

  // Mudou filtro ou busca: volta para a primeira página.
  useEffect(() => setPagina(1), [filtro, buscaDebounced, dias]);

  const params: FiltroExtrato = {
    pagina,
    ...(filtro !== 'TODAS' ? { direcao: filtro } : {}),
    ...(buscaDebounced ? { busca: buscaDebounced } : {}),
    ...(dias ? { dias } : {}),
  };
  const extrato = useQuery({
    queryKey: chaves.extrato(contaId, params),
    queryFn: ({ signal }) => api.extrato(contaId, params, signal),
    placeholderData: keepPreviousData,
  });

  function irPara(p: number) {
    setPagina(p);
    topo.current?.scrollIntoView({ block: 'start' });
  }

  const e = extrato.data;
  return (
    <section className="flex flex-col gap-3" aria-labelledby="extrato">
      {/* Dentro da aba do cartão o título repete a aba: fica só para leitor de tela. */}
      <h2 id="extrato" ref={topo} className={cx('scroll-mt-20 font-semibold text-navy', cartao && 'sr-only')}>
        {copy.extrato}
      </h2>
      <div role="group" aria-label="Filtrar por tipo" className="grid grid-cols-3 gap-1 rounded-xl bg-white p-1 border border-line">
        {(['TODAS', 'ENTRADA', 'SAIDA'] as Filtro[]).map((f) => (
          <button
            key={f}
            type="button"
            aria-pressed={filtro === f}
            onClick={() => setFiltro(f)}
            className={cx(
              'min-h-toque rounded-lg text-sm font-semibold',
              filtro === f ? 'bg-navy text-white' : 'text-navy hover:bg-light',
            )}
          >
            {copy.filtros[f]}
          </button>
        ))}
      </div>
      <div role="group" aria-label="Período" className="-mx-4 flex gap-2 overflow-x-auto px-4 [scrollbar-width:none]">
        {[0, 30, 60, 90, 120].map((d) => (
          <button
            key={d}
            type="button"
            aria-pressed={dias === d}
            onClick={() => setDias(d)}
            className={cx(
              'min-h-9 shrink-0 rounded-full border px-3 text-sm font-semibold',
              dias === d ? 'border-navy bg-navy text-white' : 'border-line bg-white text-navy',
            )}
          >
            {copy.periodos[d]}
          </button>
        ))}
      </div>
      <label className="flex flex-col gap-1">
        <span className="sr-only">{copy.buscar}</span>
        <input
          type="search"
          value={busca}
          onChange={(ev) => setBusca(ev.target.value)}
          maxLength={60}
          placeholder={`${copy.buscar} — ${copy.buscarExemplo}`}
          className="min-h-toque rounded-xl border border-line bg-white px-3 text-base outline-none focus:border-blue"
        />
      </label>

      {extrato.isLoading ? (
        <Carregando />
      ) : extrato.isError || !e ? (
        <EstadoErro onTentar={() => void extrato.refetch()} />
      ) : (
        <div className={cx('flex flex-col gap-3 transition-opacity', extrato.isPlaceholderData && 'opacity-50')} aria-busy={extrato.isFetching}>
          <p className="flex flex-wrap gap-x-4 text-sm text-slate" aria-live="polite">
            <span>{copy.quantidade(e.total)}</span>
            {filtro !== 'SAIDA' && (
              <span>
                {copy.entradas} <span className="font-semibold text-green-ink">+{brl(e.total_entradas)}</span>
              </span>
            )}
            {filtro !== 'ENTRADA' && (
              <span>
                {copy.saidas} <span className="font-semibold text-ink">−{brl(e.total_saidas)}</span>
              </span>
            )}
          </p>
          {e.itens.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-line bg-white p-4 text-sm text-slate">{copy.semTransacoes}</p>
          ) : (
            <ul className="flex flex-col divide-y divide-line rounded-2xl border border-line bg-white">
              {e.itens.map((t) => (
                <LinhaTransacao key={t.id} t={t} cartao={cartao} />
              ))}
            </ul>
          )}
          {e.paginas > 1 && (
            <nav aria-label="Paginação" className="flex items-center justify-between gap-2">
              <Button variante="secundario" onClick={() => irPara(pagina - 1)} disabled={pagina <= 1 || extrato.isFetching}>
                {copy.anterior}
              </Button>
              <span className="text-sm text-slate">{copy.pagina(e.pagina, e.paginas)}</span>
              <Button variante="secundario" onClick={() => irPara(pagina + 1)} disabled={pagina >= e.paginas || extrato.isFetching}>
                {copy.proxima}
              </Button>
            </nav>
          )}
        </div>
      )}
    </section>
  );
}

function LinhaTransacao({ t, cartao }: { t: Transacao; cartao: boolean }) {
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
            {diaMes(t.data)} · {t.categoria ?? copy.semCategoria}
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
          {/* Categoria, subcategoria e tipo de operação: exatamente como a Belvo manda. */}
          <Detalhe rotulo={copy.detalhe.categoria} valor={t.categoria} />
          <Detalhe rotulo={copy.detalhe.subcategoria} valor={t.subcategoria} />
          <Detalhe rotulo={copy.detalhe.tipoOperacao} valor={t.tipo_operacao} />
          {/* Estabelecimento e final do cartão só existem em transação de cartão. */}
          {cartao && <Detalhe rotulo={copy.detalhe.finalCartao} valor={t.final_cartao} />}
          {cartao && <Detalhe rotulo={copy.detalhe.fatura} valor={t.fatura} />}
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
