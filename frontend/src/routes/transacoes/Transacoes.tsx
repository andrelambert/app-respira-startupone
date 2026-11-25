import { keepPreviousData, useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router';

import { LinhaTransacao } from '@/components/respira/LinhaTransacao';
import { Button, Carregando, Chip, EstadoErro, cx } from '@/components/ui';
import { useHoje, useVisaoGeral } from '@/hooks/queries';
import { useDebounced } from '@/hooks/useDebounced';
import { api } from '@/lib/api';
import { categoriaNome, nomeGasto, pfm as copyPfm, tipoBelvo, transacoes as copy } from '@/lib/copy';
import { dataCompleta } from '@/lib/datas';
import {
  chips,
  escreverFiltros,
  FILTROS_VAZIOS,
  lerFiltros,
  alternarDirecao,
  paraApi,
  TIPOS_CONTA,
  type Direcao,
  type Filtros,
  type Ordem,
  type Periodo,
} from '@/lib/filtrosTransacoes';
import { brl } from '@/lib/money';

/**
 * Todas as transações (N1, Fase 7 — F-1 "não achei onde ver todas as compras
 * juntas", F-2 "só consigo filtrar entrada/saída"). Os filtros moram na URL.
 */
export default function Transacoes() {
  const [params, setParams] = useSearchParams();
  const filtros = lerFiltros(params);
  const hoje = useHoje();
  const [aberto, setAberto] = useState(false);
  const [busca, setBusca] = useState(filtros.busca);
  const buscaDebounced = useDebounced(busca, 300);

  const aplicar = (f: Filtros) => setParams(escreverFiltros(f), { replace: true });

  // A busca digitada vai para a URL com debounce (sem uma entrada no histórico por tecla).
  useEffect(() => {
    if (buscaDebounced.trim() !== filtros.busca.trim()) aplicar({ ...filtros, busca: buscaDebounced });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [buscaDebounced]);

  const visao = useVisaoGeral();
  const categorias = useQuery({ queryKey: ['transacoes', 'categorias'], queryFn: api.categoriasTransacoes });
  const contas = (visao.data?.bancos ?? []).flatMap((b) =>
    b.contas.map((c) => ({
      id: c.id,
      rotulo: [b.instituicao, c.nome || copyPfm.tipo[c.tipo] || tipoBelvo(c.tipo_externo)].filter(Boolean).join(' · '),
    })),
  );
  const nomeConta = (id: number) => contas.find((c) => c.id === id)?.rotulo ?? `Conta ${id}`;

  const apiParams = paraApi(filtros, hoje);
  const lista = useInfiniteQuery({
    queryKey: ['transacoes', 'lista', apiParams],
    queryFn: ({ pageParam, signal }) => api.todasTransacoes(apiParams, pageParam, signal),
    initialPageParam: 1,
    getNextPageParam: (ultima) => (ultima.pagina < ultima.paginas ? ultima.pagina + 1 : undefined),
    placeholderData: keepPreviousData,
  });
  const resumo = lista.data?.pages[0];
  const itens = lista.data?.pages.flatMap((p) => p.itens) ?? [];

  const ativos = chips(filtros, {
    periodo: (p, f) =>
      p === 'personalizado'
        ? copy.chipDatas(f.desde && dataCompleta(f.desde), f.ate && dataCompleta(f.ate))
        : copy.periodos[p] ?? p,
    conta: nomeConta,
    categoria: nomeGasto, // categoria ou subcategoria (vindo de uma barra de gastos)
    direcao: (d) => copy.tipos[d] ?? d,
    valor: copy.chipValor,
    soDivida: copy.soDivida,
    fluxo: (f) => copy.fluxos[f] ?? f,
    busca: copy.chipBusca,
  });

  return (
    <div className="flex flex-col gap-4">
      <div>
        <Link to="/contas" className="text-sm font-semibold text-blue">
          ← {copy.voltar}
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-navy">{copy.titulo}</h1>
      </div>

      <label className="flex flex-col gap-1">
        <span className="sr-only">{copy.buscar}</span>
        <input
          type="search"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          maxLength={60}
          placeholder={copy.buscar}
          className="min-h-toque rounded-xl border border-line bg-white px-3 text-base outline-none focus:border-blue"
        />
      </label>

      {/* Sempre à vista: tipo de conta (um por vez) e entradas/saídas (as duas ligadas = tudo). */}
      <nav aria-label={copy.tipoConta} className="flex flex-wrap gap-2">
        <Chip ativo={!filtros.tipoConta} onClick={() => aplicar({ ...filtros, tipoConta: null })}>
          {copy.tiposConta.TUDO}
        </Chip>
        {TIPOS_CONTA.map((t) => (
          <Chip key={t} ativo={filtros.tipoConta === t} onClick={() => aplicar({ ...filtros, tipoConta: t })}>
            {copy.tiposConta[t]}
          </Chip>
        ))}
      </nav>
      <div role="group" aria-label={copy.direcoes} className="flex gap-2">
        {(['ENTRADA', 'SAIDA'] as Direcao[]).map((d) => (
          <Chip key={d} ativo={filtros.direcao === null || filtros.direcao === d} onClick={() => aplicar({ ...filtros, direcao: alternarDirecao(filtros.direcao, d) })}>
            {copy.tipos[d]}
          </Chip>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          aria-pressed={filtros.soDivida}
          onClick={() => aplicar({ ...filtros, soDivida: !filtros.soDivida })}
          className={cx(
            'min-h-toque rounded-full border px-3 text-sm font-semibold',
            filtros.soDivida ? 'border-purple bg-purple text-white' : 'border-line bg-white text-navy',
          )}
        >
          {copy.soDivida}
        </button>
        <Button
          variante="secundario"
          className="min-h-toque px-3 py-1 text-sm"
          aria-expanded={aberto}
          aria-controls="painel-filtros"
          onClick={() => setAberto((v) => !v)}
        >
          {copy.filtros}
          {ativos.length > 0 ? ` (${ativos.length})` : ''}
        </Button>
      </div>

      {aberto && (
        <PainelFiltros
          filtros={filtros}
          aplicar={aplicar}
          contas={contas}
          categorias={categorias.data ?? []}
        />
      )}

      {ativos.length > 0 && (
        <ul aria-label="Filtros ativos" className="flex flex-wrap gap-2">
          {ativos.map((c) => (
            <li key={c.chave}>
              <button
                type="button"
                onClick={() => {
                  const novo = c.remover(filtros);
                  if (c.chave === 'busca') setBusca('');
                  aplicar(novo);
                }}
                className="flex min-h-9 items-center gap-1 rounded-full bg-navy px-3 text-sm font-semibold text-white"
                aria-label={`Remover filtro: ${c.rotulo}`}
              >
                {c.rotulo} <span aria-hidden="true">×</span>
              </button>
            </li>
          ))}
          <li>
            <button
              type="button"
              onClick={() => {
                setBusca('');
                aplicar(FILTROS_VAZIOS);
              }}
              className="min-h-9 px-2 text-sm font-semibold text-blue underline"
            >
              {copy.limpar}
            </button>
          </li>
        </ul>
      )}

      {lista.isLoading ? (
        <Carregando />
      ) : lista.isError || !resumo ? (
        <EstadoErro onTentar={() => void lista.refetch()} />
      ) : (
        <div
          className={cx('flex flex-col gap-3 transition-opacity', lista.isPlaceholderData && 'opacity-50')}
          aria-busy={lista.isFetching}
        >
          {/* Uma linha por valor: em 360 px, três valores lado a lado se encostam. */}
          <dl className="flex flex-col gap-1 rounded-2xl border border-line bg-white p-4 text-sm" aria-live="polite">
            <div className="flex justify-between gap-3">
              <dt className="text-slate">{copy.entradas}</dt>
              <dd className="tabular font-semibold text-green-ink">+{brl(resumo.total_entradas)}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate">{copy.saidas}</dt>
              <dd className="tabular font-semibold text-ink">−{brl(resumo.total_saidas)}</dd>
            </div>
            <div className="flex justify-between gap-3 border-t border-line pt-1">
              <dt className="font-semibold text-navy">{copy.resultado}</dt>
              <dd className={cx('tabular font-semibold', resumo.resultado >= 0 ? 'text-green-ink' : 'text-ink')}>
                {resumo.resultado >= 0 ? '+' : '−'}
                {brl(Math.abs(resumo.resultado) as typeof resumo.resultado)}
              </dd>
            </div>
          </dl>
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm text-slate">{copy.quantidade(resumo.total)}</p>
            <label className="flex items-center gap-1 text-sm text-slate">
              <span className="sr-only">{copy.ordem}</span>
              <select
                value={filtros.ordem}
                onChange={(e) => aplicar({ ...filtros, ordem: e.target.value as Ordem })}
                className="min-h-toque rounded-lg border border-line bg-white px-2 text-sm text-navy"
              >
                {(['recentes', 'maior_valor'] as Ordem[]).map((o) => (
                  <option key={o} value={o}>
                    {copy.ordens[o]}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {itens.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-line bg-white p-4 text-sm text-slate">{copy.vazio}</p>
          ) : (
            <ul className="flex flex-col divide-y divide-line rounded-2xl border border-line bg-white">
              {itens.map((t) => (
                <LinhaTransacao
                  key={t.id}
                  t={t}
                  cartao={Boolean(t.final_cartao)}
                  banco={{ nome: t.banco, logo: t.banco_logo, conta: t.conta_nome }}
                />
              ))}
            </ul>
          )}
          {lista.hasNextPage && (
            <Button variante="secundario" onClick={() => void lista.fetchNextPage()} disabled={lista.isFetchingNextPage}>
              {copy.carregarMais}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

function PainelFiltros({
  filtros,
  aplicar,
  contas,
  categorias,
}: {
  filtros: Filtros;
  aplicar: (f: Filtros) => void;
  contas: { id: number; rotulo: string }[];
  categorias: string[];
}) {
  const [min, setMin] = useState(filtros.valorMin ?? '');
  const [max, setMax] = useState(filtros.valorMax ?? '');
  const alternar = <T,>(lista: T[], v: T) => (lista.includes(v) ? lista.filter((x) => x !== v) : [...lista, v]);

  return (
    <section id="painel-filtros" aria-label={copy.filtros} className="flex flex-col gap-4 rounded-2xl border border-line bg-white p-4">
      <Grupo titulo={copy.periodo}>
        {(['tudo', 'mes', 'mes_passado', '30', '90', 'personalizado'] as Periodo[]).map((p) => (
          <Opcao key={p} ativo={filtros.periodo === p} onClick={() => aplicar({ ...filtros, periodo: p })}>
            {copy.periodos[p]}
          </Opcao>
        ))}
      </Grupo>
      {filtros.periodo === 'personalizado' && (
        <div className="grid grid-cols-2 gap-2">
          <label className="flex flex-col gap-1 text-sm text-slate">
            {copy.de}
            <input
              type="date"
              value={filtros.desde ?? ''}
              max={filtros.ate ?? undefined}
              onChange={(e) => aplicar({ ...filtros, desde: e.target.value || null })}
              className="min-h-toque rounded-lg border border-line px-2 text-navy"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm text-slate">
            {copy.ate}
            <input
              type="date"
              value={filtros.ate ?? ''}
              min={filtros.desde ?? undefined}
              onChange={(e) => aplicar({ ...filtros, ate: e.target.value || null })}
              className="min-h-toque rounded-lg border border-line px-2 text-navy"
            />
          </label>
        </div>
      )}

      {contas.length > 0 && (
        <Grupo titulo={copy.contas}>
          {contas.map((c) => (
            <Opcao
              key={c.id}
              ativo={filtros.contas.includes(c.id)}
              onClick={() => aplicar({ ...filtros, contas: alternar(filtros.contas, c.id) })}
            >
              {c.rotulo}
            </Opcao>
          ))}
        </Grupo>
      )}

      {categorias.length > 0 && (
        <Grupo titulo={copy.categorias}>
          {categorias.map((c) => (
            <Opcao
              key={c}
              ativo={filtros.categorias.includes(c)}
              onClick={() => aplicar({ ...filtros, categorias: alternar(filtros.categorias, c) })}
            >
              {categoriaNome(c)}
            </Opcao>
          ))}
        </Grupo>
      )}

      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-semibold text-navy">{copy.valor}</legend>
        <div className="grid grid-cols-[1fr_1fr_auto] items-end gap-2">
          <label className="flex flex-col gap-1 text-sm text-slate">
            {copy.valorMin}
            <input
              inputMode="decimal"
              value={min}
              maxLength={13}
              onChange={(e) => setMin(e.target.value)}
              className="min-h-toque rounded-lg border border-line px-2 text-navy"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm text-slate">
            {copy.valorMax}
            <input
              inputMode="decimal"
              value={max}
              maxLength={13}
              onChange={(e) => setMax(e.target.value)}
              className="min-h-toque rounded-lg border border-line px-2 text-navy"
            />
          </label>
          <Button
            variante="secundario"
            className="min-h-toque px-3 py-1 text-sm"
            onClick={() => aplicar({ ...filtros, valorMin: min.trim() || null, valorMax: max.trim() || null })}
          >
            {copy.aplicar}
          </Button>
        </div>
      </fieldset>
    </section>
  );
}

function Grupo({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div role="group" aria-label={titulo} className="flex flex-col gap-2">
      <p className="text-sm font-semibold text-navy">{titulo}</p>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  );
}

function Opcao({ ativo, onClick, children }: { ativo: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={ativo}
      onClick={onClick}
      className={cx(
        'min-h-9 rounded-full border px-3 text-sm font-semibold',
        ativo ? 'border-navy bg-navy text-white' : 'border-line bg-white text-navy',
      )}
    >
      {children}
    </button>
  );
}
