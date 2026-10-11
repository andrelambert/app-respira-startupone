import { addMonths, differenceInCalendarDays, format, parseISO, startOfMonth } from 'date-fns';
import { ptBR } from 'date-fns/locale';

/** "2028-04-01" → "abril de 2028" */
export function mesAno(iso: string): string {
  return format(parseISO(iso), "MMMM 'de' yyyy", { locale: ptBR });
}

/** "2026-10-12" → "12 de outubro" */
export function diaMes(iso: string): string {
  return format(parseISO(iso), "d 'de' MMMM", { locale: ptBR });
}

/** "2027-10-04" → "4 de outubro de 2027" */
export function dataCompleta(iso: string): string {
  return format(parseISO(iso), "d 'de' MMMM 'de' yyyy", { locale: ptBR });
}

/** "2026-10-03T21:00:00Z" → "3 de out., 21:00" */
export function carimbo(iso: string): string {
  return format(parseISO(iso), "d 'de' MMM', 'HH:mm", { locale: ptBR });
}

/**
 * "2026-09-05T22:30:00-03:00" → "5 de setembro de 2026, 22:30".
 * Lê a data e a hora do próprio texto, sem passar pelo fuso do navegador: o
 * backend já converteu para o horário de Brasília.
 */
export function dataHoraLocal(iso: string): string {
  const [, dia, hh, mm] = /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})/.exec(iso) ?? [];
  return dia ? `${dataCompleta(dia)}, ${hh}:${mm}` : dataCompleta(iso.slice(0, 10));
}

/** "2026-10-11", 3 → "2027-01-01": primeiro dia do mês, ``n`` meses à frente. */
export function inicioDoMesMais(iso: string, n: number): string {
  return format(addMonths(startOfMonth(parseISO(iso)), n), 'yyyy-MM-dd');
}

/** Só o nome do mês: "setembro" */
export function nomeMes(iso: string): string {
  return format(parseISO(iso), 'MMMM', { locale: ptBR });
}

export function diasAte(iso: string, hoje: Date = new Date()): number {
  return differenceInCalendarDays(parseISO(iso), hoje);
}

export function meses(n: number): string {
  return n === 1 ? '1 mês' : `${n} meses`;
}

export function ordinalMes(n: number): string {
  return `${n}º mês`;
}
