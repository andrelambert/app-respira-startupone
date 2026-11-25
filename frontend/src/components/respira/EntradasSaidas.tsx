import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { lazy, Suspense, useState } from 'react';
import { Link, useNavigate } from 'react-router';

import { Carregando, Chip, EstadoErro } from '@/components/ui';
import { useVisaoGeral } from '@/hooks/queries';
import { api, type FluxoMensal } from '@/lib/api';
import { entradasSaidas as copy } from '@/lib/copy';
import { mesAno } from '@/lib/datas';
import { escreverFiltros, FILTROS_VAZIOS, type Filtros } from '@/lib/filtrosTransacoes';
import { brl, soma, type Centavos } from '@/lib/money';
import { fimDoMes } from '@/lib/periodoCategoria';

const EntradasSaidasChart = lazy(() => import('./EntradasSaidasChart'));

export type TipoFluxo = 'entradas' | 'saidas';
const PERIODOS = [3, 6, 12] as const;

/** O valor de cada barra — as mesmas regras do filtro fluxo=renda/gasto do backend. */
export function valorDoMes(m: FluxoMensal['meses'][number], tipo: TipoFluxo): Centavos {
  return tipo === 'entradas' ? m.entradas : soma([m.essenciais, m.outros_gastos]);
}

/**
 * Tocar numa barra → "Todas as transações" com os filtros daquela barra à vista:
 * tipo, o mês e todas as contas e cartões. Saídas vêm com "só gastos" (a lista
 * soma o valor da barra); entradas, sem filtro extra — a pedido, depois do
 * teste com conta real, a lista mostra todas as entradas do mês.
 */
export function linkDaBarra(mes: string, tipo: TipoFluxo, contas: number[]): string {
  const f: Filtros = {
    ...FILTROS_VAZIOS,
    periodo: 'personalizado',
    desde: mes,
    ate: fimDoMes(mes),
    direcao: tipo === 'entradas' ? 'ENTRADA' : 'SAIDA',
    fluxo: tipo === 'entradas' ? null : 'gasto',
    contas: contas.length <= 20 ? contas : [], // o backend aceita até 20; acima disso, "todas" é o mesmo
  };
  return `/transacoes?${escreverFiltros(f).toString()}`;
}

/**
 * Entradas e saídas, mês a mês (teste com conta real, Fase 7): um gráfico só,
 * com seletor de tipo e de período; passar o mouse mostra o valor exato e
 * tocar leva às transações daquele mês.
 */
export function EntradasSaidas() {
  const [tipo, setTipo] = useState<TipoFluxo>('entradas');
  const [meses, setMeses] = useState<(typeof PERIODOS)[number]>(6);
  const navigate = useNavigate();
  const visao = useVisaoGeral();
  const q = useQuery({
    queryKey: ['pfm', 'fluxo-mensal', meses],
    queryFn: () => api.fluxoMensal(meses),
    placeholderData: keepPreviousData, // trocar o período não pisca a tela
  });

  if (q.isLoading) return <Carregando />;
  if (q.isError || !q.data) return <EstadoErro onTentar={() => void q.refetch()} />;
  const lista = q.data.meses;
  const valores = lista.map((m) => ({ mes: m.mes, valor: valorDoMes(m, tipo) }));
  const temDado = valores.some((v) => v.valor > 0);
  const media = valores.length ? (Math.round(soma(valores.map((v) => v.valor)) / valores.length) as Centavos) : (0 as Centavos);
  const contas = (visao.data?.bancos ?? []).flatMap((b) => b.contas.map((c) => c.id));
  const nomeTipo = tipo === 'entradas' ? copy.entradas : copy.saidas;

  return (
    <section aria-labelledby="entradas-saidas-titulo" className="flex flex-col gap-3">
      <h2 id="entradas-saidas-titulo" className="font-semibold text-navy">
        {copy.titulo}
      </h2>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div role="group" aria-label={copy.tipo} className="flex gap-2">
          {(['entradas', 'saidas'] as const).map((t) => (
            <Chip key={t} ativo={tipo === t} onClick={() => setTipo(t)} tom={t === 'entradas' ? 'entrada' : 'saida'}>
              {t === 'entradas' ? copy.entradas : copy.saidas}
            </Chip>
          ))}
        </div>
        <div role="group" aria-label={copy.periodo} className="flex gap-1">
          {PERIODOS.map((n) => (
            <Chip key={n} ativo={meses === n} onClick={() => setMeses(n)}>
              {copy.meses(n)}
            </Chip>
          ))}
        </div>
      </div>
      {!temDado ? (
        <p className="rounded-2xl border border-dashed border-line bg-white p-4 text-sm text-slate">{copy.semDados}</p>
      ) : (
        <>
          <p className="text-ink" aria-live="polite">
            {copy.media(nomeTipo, meses, brl(media))}
          </p>
          <div className="rounded-2xl border border-line bg-white p-3">
            <Suspense fallback={<div className="h-52" />}>
              <EntradasSaidasChart
                valores={valores}
                tipo={tipo}
                rotulo={copy.aria(nomeTipo, meses)}
                onEscolher={(mes) => navigate(linkDaBarra(mes, tipo, contas))}
              />
            </Suspense>
            {/* A mesma informação para leitor de tela, com o link de cada mês. */}
            <ul className="sr-only">
              {valores.map((v) => (
                <li key={v.mes}>
                  <Link to={linkDaBarra(v.mes, tipo, contas)}>{`${mesAno(v.mes)}: ${brl(v.valor)}`}</Link>
                </li>
              ))}
            </ul>
          </div>
          <p className="text-xs text-slate">{copy.toque}</p>
          <p className="text-xs text-slate">{copy.oQueConta[tipo]}</p>
        </>
      )}
    </section>
  );
}
