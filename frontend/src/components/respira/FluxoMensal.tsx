import { useQuery } from '@tanstack/react-query';
import { lazy, Suspense } from 'react';

import { Carregando, EstadoErro } from '@/components/ui';
import { api } from '@/lib/api';
import { COR_FLUXO } from '@/lib/cores';
import { fluxo as copy } from '@/lib/copy';
import { nomeMes } from '@/lib/datas';
import { brl } from '@/lib/money';

const FluxoChart = lazy(() => import('./FluxoChart'));
const sem = { semCentavos: true };
const mesCurto = (iso: string) => `${nomeMes(iso).slice(0, 3)}/${iso.slice(2, 4)}`;

/**
 * N5 (F-7 "de onde veio o 'você pode pagar R$ 1.755'?"): entradas × gastos ×
 * dívida dos 6 meses que a capacidade usa, a linha da sobra e a conta em uma
 * frase. Resumo em texto e tabela para quem não vê o gráfico.
 */
export function FluxoMensal({ id }: { id?: string }) {
  const q = useQuery({ queryKey: ['pfm', 'fluxo-mensal'], queryFn: api.fluxoMensal });
  if (q.isLoading) return <Carregando />;
  if (q.isError || !q.data) return <EstadoErro onTentar={() => void q.refetch()} />;
  const f = q.data;
  const temDado = f.meses.some((m) => m.entradas > 0 || m.essenciais > 0);

  return (
    <section id={id} aria-labelledby={`${id ?? 'fluxo'}-titulo`} className="flex scroll-mt-20 flex-col gap-3">
      <h2 id={`${id ?? 'fluxo'}-titulo`} className="font-semibold text-navy">
        {copy.titulo}
      </h2>
      {!temDado || f.entradas_mediana === null || f.essenciais_mediana === null ? (
        <p className="rounded-2xl border border-dashed border-line bg-white p-4 text-sm text-slate">{copy.semHistorico}</p>
      ) : (
        <>
          <p className="text-ink">{copy.conta(brl(f.entradas_mediana), brl(f.essenciais_mediana), f.reserva_pct, brl(f.capacidade))}</p>
          <div className="rounded-2xl border border-line bg-white p-3">
            <ul className="mb-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-ink" aria-label="Legenda">
              {(['entradas', 'essenciais', 'outros', 'divida', 'sobra'] as const).map((k) => (
                <li key={k} className="flex items-center gap-1.5">
                  <span
                    aria-hidden="true"
                    className={k === 'sobra' ? 'h-0.5 w-4 rounded' : 'h-2.5 w-2.5 rounded-sm'}
                    style={{ background: COR_FLUXO[k] }}
                  />
                  {copy.series[k]}
                </li>
              ))}
            </ul>
            <Suspense fallback={<div className="h-60" />}>
              <FluxoChart meses={f.meses} />
            </Suspense>
          </div>
          <p className="text-xs text-slate">{copy.mediana}</p>
          <p className="text-xs text-slate">{copy.cartao}</p>
          <details className="text-sm">
            <summary className="min-h-toque cursor-pointer font-semibold text-blue">{copy.tabela}</summary>
            <div className="overflow-x-auto">
              <table className="mt-2 w-full min-w-[30rem] text-right text-xs tabular">
                <thead className="text-slate">
                  <tr>
                    <th className="py-1 text-left font-medium">Mês</th>
                    <th className="font-medium">{copy.series.entradas}</th>
                    <th className="font-medium">{copy.series.essenciais}</th>
                    <th className="font-medium">{copy.series.outros}</th>
                    <th className="font-medium">{copy.series.divida}</th>
                    <th className="font-medium">Sobra</th>
                  </tr>
                </thead>
                <tbody className="text-ink">
                  {f.meses.map((m) => (
                    <tr key={m.mes} className="border-t border-line">
                      <th scope="row" className="py-1 pr-2 text-left font-medium">
                        {mesCurto(m.mes)}
                      </th>
                      <td className="px-1">{brl(m.entradas, sem)}</td>
                      <td className="px-1">{brl(m.essenciais, sem)}</td>
                      <td className="px-1">{brl(m.outros_gastos, sem)}</td>
                      <td className="px-1">{brl(m.pagamentos_divida, sem)}</td>
                      <td className="pl-1 font-semibold">{brl(m.sobra, sem)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </section>
  );
}
