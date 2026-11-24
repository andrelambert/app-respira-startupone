import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router';

import { Card, Carregando, EstadoErro, cx } from '@/components/ui';
import { api } from '@/lib/api';
import { gastos as copy, nomeGasto } from '@/lib/copy';
import { mesAno } from '@/lib/datas';
import { escreverFiltros, FILTROS_VAZIOS } from '@/lib/filtrosTransacoes';
import { brl, type Centavos } from '@/lib/money';

/** Último dia do mês de uma data ISO "yyyy-mm-01". */
function fimDoMes(iso: string): string {
  const [a, m] = iso.split('-').map(Number) as [number, number];
  const ultimo = new Date(Date.UTC(a, m, 0)).getUTCDate();
  return `${iso.slice(0, 8)}${String(ultimo).padStart(2, '0')}`;
}

/** Link para "Todas as transações" já filtrado na categoria e no mês (N2 → N1). */
export function linkTransacoes(categoria: string, mes: string): string {
  const p = escreverFiltros({
    ...FILTROS_VAZIOS,
    periodo: 'personalizado',
    desde: mes,
    ate: fimDoMes(mes),
    categorias: [categoria],
    direcao: 'SAIDA',
  });
  return `/transacoes?${p.toString()}`;
}

/**
 * Para onde foi o dinheiro (N2, Fase 7 — F-3 "quanto gasto com cada coisa",
 * F-4 "onde cortar"). Barras em HTML/CSS: cada uma é texto legível por leitor
 * de tela, sem biblioteca de gráfico no bundle.
 */
export function GastosCategoria() {
  const [mes, setMes] = useState<string | undefined>(undefined);
  const q = useQuery({ queryKey: ['pfm', 'categorias', mes ?? 'padrao'], queryFn: () => api.gastosCategoria(mes) });

  if (q.isLoading) return <Carregando />;
  if (q.isError || !q.data) return <EstadoErro onTentar={() => void q.refetch()} />;
  const d = q.data;
  const maior = Math.max(1, ...d.categorias.map((c) => Math.max(c.total, c.media_3m ?? 0)));
  const imp = d.impacto_plano;

  return (
    <section aria-labelledby="gastos-titulo" className="flex flex-col gap-3">
      <div className="flex items-end justify-between gap-2">
        <h2 id="gastos-titulo" className="font-semibold text-navy">
          {copy.titulo}
        </h2>
        <label className="flex items-center gap-1 text-sm text-slate">
          <span className="sr-only">{copy.mes}</span>
          <select
            value={d.mes.slice(0, 7)}
            onChange={(e) => setMes(e.target.value)}
            className="min-h-toque rounded-lg border border-line bg-white px-2 text-sm text-navy first-letter:uppercase"
          >
            {[...d.meses_disponiveis].reverse().map((m) => (
              <option key={m} value={m.slice(0, 7)}>
                {mesAno(m)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="text-sm text-slate">{copy.subtitulo(mesAno(d.mes))}</p>

      {imp && (
        <Card tom="plano" className="flex flex-col gap-1">
          <p className="text-ink">
            {copy.impacto(
              nomeGasto(imp.categoria).toLowerCase(),
              brl(imp.valor_mensal),
              imp.meses_antecipados,
              mesAno(imp.data_nova),
              mesAno(imp.data_atual),
            )}
          </p>
          <p className="text-xs text-slate">{copy.impactoAviso}</p>
        </Card>
      )}

      {d.categorias.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-line bg-white p-4 text-sm text-slate">{copy.semDados}</p>
      ) : (
        <ul className="flex flex-col gap-1 rounded-2xl border border-line bg-white p-2">
          {d.categorias.map((c) => {
            const pct = c.variacao !== null ? Math.round(Number(c.variacao) * 100) : null;
            const acima = pct !== null && pct >= 10;
            const nome = nomeGasto(c.categoria);
            return (
              <li key={c.categoria}>
                <Link
                  to={linkTransacoes(c.categoria, d.mes)}
                  aria-label={`${nome}: ${brl(c.total)}${c.media_3m !== null ? `, ${copy.media(brl(c.media_3m))}` : ''}${acima ? `, ${copy.acimaDaMedia(pct)}` : ''}. ${copy.verTransacoes(nome)}`}
                  className="flex flex-col gap-1 rounded-xl px-2 py-2 hover:bg-light"
                >
                  <div className="flex items-baseline justify-between gap-2 text-sm">
                    <span className="min-w-0 truncate font-medium text-ink">
                      {nome}
                      {c.essencial && <span className="ml-1 text-xs font-normal text-slate">· {copy.essencial}</span>}
                    </span>
                    <span className="tabular shrink-0 font-semibold text-ink">{brl(c.total)}</span>
                  </div>
                  <div className="relative h-2.5 rounded-full bg-light" aria-hidden="true">
                    <div
                      className={cx('h-full rounded-full', acima && !c.essencial ? 'bg-amber' : 'bg-blue')}
                      style={{ width: `${(c.total / maior) * 100}%` }}
                    />
                    {c.media_3m !== null && (
                      <div
                        className="absolute -top-0.5 h-3.5 w-0.5 rounded bg-navy"
                        style={{ left: `calc(${(c.media_3m / maior) * 100}% - 1px)` }}
                        title={copy.media(brl(c.media_3m as Centavos))}
                      />
                    )}
                  </div>
                  <div className="flex justify-between gap-2 text-xs text-slate">
                    <span>{c.media_3m !== null ? copy.media(brl(c.media_3m)) : ''}</span>
                    {acima && <span className="font-semibold text-amber-ink">{copy.acimaDaMedia(pct)}</span>}
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
      <p className="text-xs text-slate">{copy.foraDaConta}</p>
    </section>
  );
}
