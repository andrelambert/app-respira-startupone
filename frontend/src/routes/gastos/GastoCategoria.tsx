import { keepPreviousData, useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { lazy, Suspense } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';

import { LinhaTransacao } from '@/components/respira/LinhaTransacao';
import { linkTransacoes } from '@/components/respira/GastosCategoria';
import { Button, Carregando, Chip, EstadoErro, Money } from '@/components/ui';
import { useHoje } from '@/hooks/queries';
import { api } from '@/lib/api';
import { categoriaNome, gastoCategoria as copy, subcategoriaNome, transacoes as copyTransacoes } from '@/lib/copy';
import { dataCompleta, mesAno } from '@/lib/datas';
import { brl } from '@/lib/money';
import { escreverPeriodo, intervaloPeriodo, lerPeriodo, type PeriodoCategoria } from '@/lib/periodoCategoria';

const EvolucaoChart = lazy(() => import('./EvolucaoChart'));

/** Primeiro dia do mês anterior a ``hoje`` (o último mês completo, como no Contas). */
function mesPassado(hoje: string): string {
  const [a, m] = hoje.split('-').map(Number) as [number, number];
  const d = new Date(Date.UTC(a, m - 2, 1));
  return d.toISOString().slice(0, 10);
}

/**
 * Detalhe de uma categoria de gasto (feedback do teste com conta real, Fase 7):
 * a evolução dos últimos 12 meses, o mês num seletor (ou datas à escolha), o
 * filtro pelo tipo de gasto (subcategoria da Belvo) e as transações.
 */
export default function GastoCategoria() {
  const { categoria = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const hoje = useHoje();
  const periodo = lerPeriodo(params, mesPassado(hoje));
  const sub = params.get('sub');
  const nome = categoriaNome(categoria);
  const aplicar = (p: PeriodoCategoria, s: string | null = sub) => setParams(escreverPeriodo(p, s), { replace: true });

  const historico = useQuery({
    queryKey: ['pfm', 'categoria', categoria, sub],
    queryFn: () => api.historicoCategoria(categoria, sub),
    enabled: Boolean(categoria),
    placeholderData: keepPreviousData, // trocar o tipo de gasto não pisca a tela
  });

  const filtro = { ...intervaloPeriodo(periodo, hoje), categorias: sub ? `${categoria}::${sub}` : categoria, direcao: 'SAIDA' };
  const lista = useInfiniteQuery({
    queryKey: ['transacoes', 'lista', filtro],
    queryFn: ({ pageParam, signal }) => api.todasTransacoes(filtro, pageParam, signal),
    initialPageParam: 1,
    getNextPageParam: (ultima) => (ultima.pagina < ultima.paginas ? ultima.pagina + 1 : undefined),
    placeholderData: keepPreviousData,
    enabled: Boolean(categoria),
  });

  if (historico.isLoading) return <Carregando />;
  if (historico.isError || !historico.data) return <EstadoErro onTentar={() => void historico.refetch()} />;
  const h = historico.data;
  const itens = lista.data?.pages.flatMap((p) => p.itens) ?? [];
  const totalPeriodo = lista.data?.pages[0]?.total_saidas;
  const rotuloPeriodo =
    periodo.tipo === 'mes'
      ? mesAno(periodo.mes)
      : periodo.desde || periodo.ate
        ? copyTransacoes.chipDatas(periodo.desde && dataCompleta(periodo.desde), periodo.ate && dataCompleta(periodo.ate))
        : copy.noPeriodo;
  const nomeSub = (s: string) => subcategoriaNome(categoria, s) ?? s;
  const rotuloGrafico = sub ? `${nome} · ${nomeSub(sub)}` : nome;

  return (
    <div className="flex flex-col gap-5">
      <Link to="/contas" className="text-sm font-semibold text-blue">
        {copy.voltar}
      </Link>
      <section aria-labelledby="titulo-categoria">
        <h1 id="titulo-categoria" className="text-2xl font-bold text-navy">
          {nome}
        </h1>
        <p className="text-sm text-slate">{copy.totalPeriodo(rotuloPeriodo)}</p>
        <p className="text-3xl font-bold text-navy" aria-live="polite">
          {totalPeriodo !== undefined ? <Money valor={totalPeriodo} /> : '—'}
        </p>
      </section>

      {/* Evolução: tocar numa barra escolhe o mês. */}
      <section aria-labelledby="titulo-evolucao" className="rounded-2xl border border-line bg-white p-3">
        <h2 id="titulo-evolucao" className="mb-1 text-sm font-semibold text-navy">
          {copy.evolucao}
          {sub && <span className="font-normal text-slate"> · {nomeSub(sub)}</span>}
        </h2>
        <Suspense fallback={<div className="h-48" />}>
          <EvolucaoChart
            meses={h.meses}
            selecionado={periodo.tipo === 'mes' ? periodo.mes : null}
            onEscolher={(mes) => aplicar({ tipo: 'mes', mes })}
            rotulo={copy.evolucaoAria(rotuloGrafico)}
          />
        </Suspense>
        <table className="sr-only">
          <caption>{copy.evolucaoAria(rotuloGrafico)}</caption>
          <tbody>
            {h.meses.map((m) => (
              <tr key={m.mes}>
                <th scope="row">{mesAno(m.mes)}</th>
                <td>{brl(m.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Período: um mês no seletor, ou datas à escolha. */}
      <div className="flex flex-col gap-2">
        <label className="flex flex-col gap-1 text-sm text-slate">
          {copy.periodo}
          <select
            value={periodo.tipo === 'mes' ? periodo.mes : 'personalizado'}
            onChange={(e) => {
              const v = e.target.value;
              if (v !== 'personalizado') aplicar({ tipo: 'mes', mes: v });
              else {
                // Começa nas datas do que a pessoa estava vendo.
                const atual = intervaloPeriodo(periodo, hoje);
                aplicar({ tipo: 'personalizado', desde: atual.desde ?? null, ate: atual.ate ?? null });
              }
            }}
            className="min-h-toque rounded-lg border border-line bg-white px-2 text-navy"
          >
            {[...h.meses].reverse().map((m) => (
              <option key={m.mes} value={m.mes}>
                {mesAno(m.mes)}
              </option>
            ))}
            <option value="personalizado">{copy.personalizado}</option>
          </select>
        </label>
        {periodo.tipo === 'personalizado' && (
          <div className="grid grid-cols-2 gap-2">
            <label className="flex flex-col gap-1 text-sm text-slate">
              {copy.de}
              <input
                type="date"
                value={periodo.desde ?? ''}
                max={periodo.ate ?? undefined}
                onChange={(e) => aplicar({ ...periodo, desde: e.target.value || null })}
                className="min-h-toque rounded-lg border border-line bg-white px-2 text-navy"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-slate">
              {copy.ate}
              <input
                type="date"
                value={periodo.ate ?? ''}
                min={periodo.desde ?? undefined}
                onChange={(e) => aplicar({ ...periodo, ate: e.target.value || null })}
                className="min-h-toque rounded-lg border border-line bg-white px-2 text-navy"
              />
            </label>
          </div>
        )}
      </div>

      {/* Tipo de gasto (subcategoria): só aqui, como filtro — a Belvo erra bastante nelas. */}
      {h.subcategorias.length > 1 && (
        <div className="flex flex-col gap-1">
          <p className="text-sm text-slate">{copy.subcategoria}</p>
          <nav aria-label={copy.subcategoria} className="flex flex-wrap gap-2">
            <Chip ativo={!sub} onClick={() => aplicar(periodo, null)}>
              {copy.todas}
            </Chip>
            {h.subcategorias.map((s) => (
              <Chip key={s.subcategoria} ativo={sub === s.subcategoria} onClick={() => aplicar(periodo, s.subcategoria)}>
                {nomeSub(s.subcategoria)}
              </Chip>
            ))}
          </nav>
          <p className="text-xs text-slate">{copy.subAviso}</p>
        </div>
      )}

      {lista.isLoading ? (
        <Carregando />
      ) : lista.isError ? (
        <EstadoErro onTentar={() => void lista.refetch()} />
      ) : itens.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-line bg-white p-4 text-sm text-slate">{copy.semGastos}</p>
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
          {copyTransacoes.carregarMais}
        </Button>
      )}
      {periodo.tipo === 'mes' && !sub && (
        <Link to={linkTransacoes(categoria, periodo.mes)} className="text-sm font-semibold text-blue underline">
          {copy.verTodas}
        </Link>
      )}
    </div>
  );
}
