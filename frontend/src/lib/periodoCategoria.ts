/**
 * Período do detalhe de uma categoria de gasto: um mês (o seletor) ou datas
 * escolhidas. Fica na URL — voltar e compartilhar funcionam. Funções puras.
 */

export type PeriodoCategoria =
  | { tipo: 'mes'; mes: string } // yyyy-MM-01
  | { tipo: 'personalizado'; desde: string | null; ate: string | null }; // yyyy-MM-dd

const MES = /^\d{4}-(0[1-9]|1[0-2])$/;
const DATA = /^\d{4}-\d{2}-\d{2}$/;

/** Último dia do mês de uma data ISO "yyyy-mm-01". */
export function fimDoMes(iso: string): string {
  const [a, m] = iso.split('-').map(Number) as [number, number];
  const ultimo = new Date(Date.UTC(a, m, 0)).getUTCDate();
  return `${iso.slice(0, 8)}${String(ultimo).padStart(2, '0')}`;
}

/** ``padrao``: mês (yyyy-MM-01) quando a URL não diz nada. */
export function lerPeriodo(p: URLSearchParams, padrao: string): PeriodoCategoria {
  const desde = p.get('desde');
  const ate = p.get('ate');
  if (p.get('periodo') === 'personalizado' || (desde && DATA.test(desde)) || (ate && DATA.test(ate))) {
    return {
      tipo: 'personalizado',
      desde: desde && DATA.test(desde) ? desde : null,
      ate: ate && DATA.test(ate) ? ate : null,
    };
  }
  const mes = p.get('mes');
  return { tipo: 'mes', mes: mes && MES.test(mes) ? `${mes}-01` : padrao };
}

export function escreverPeriodo(per: PeriodoCategoria, sub: string | null): URLSearchParams {
  const p = new URLSearchParams();
  if (per.tipo === 'mes') p.set('mes', per.mes.slice(0, 7));
  else {
    p.set('periodo', 'personalizado');
    if (per.desde) p.set('desde', per.desde);
    if (per.ate) p.set('ate', per.ate);
  }
  if (sub) p.set('sub', sub);
  return p;
}

/** Datas para a API. O mês corrente para em ``hoje``: parcela futura do cartão não é gasto ainda. */
export function intervaloPeriodo(per: PeriodoCategoria, hoje: string): { desde?: string; ate?: string } {
  if (per.tipo === 'mes') {
    const fim = fimDoMes(per.mes);
    return { desde: per.mes, ate: fim < hoje ? fim : hoje };
  }
  // Datas invertidas: vale o intervalo que a pessoa quis dizer.
  const [a, b] = per.desde && per.ate && per.desde > per.ate ? [per.ate, per.desde] : [per.desde, per.ate];
  return { ...(a ? { desde: a } : {}), ...(b ? { ate: b } : {}) };
}

/** Link do Contas para o detalhe de uma categoria, já no mês que a pessoa olhava. */
export function linkCategoria(categoria: string, mes: string): string {
  return `/gastos/${encodeURIComponent(categoria)}?${escreverPeriodo({ tipo: 'mes', mes }, null).toString()}`;
}
