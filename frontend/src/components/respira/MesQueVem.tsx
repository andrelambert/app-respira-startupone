import { useQuery } from '@tanstack/react-query';

import { Card, Icone, Money, cx } from '@/components/ui';
import { api } from '@/lib/api';
import { mesQueVem as copy } from '@/lib/copy';
import { brl, type Centavos } from '@/lib/money';

/**
 * Cabe no mês que vem? (teste com usuária, Fase 7). O que entra num mês típico
 * contra o que já está previsto sair: a fatura aberta do cartão, as parcelas das
 * dívidas e os essenciais pagos pela conta. Falta não é reprovação: âmbar, com
 * o próximo passo (§10).
 */
export function MesQueVem() {
  const q = useQuery({ queryKey: ['pfm', 'proximo-mes'], queryFn: api.proximoMes });
  const d = q.data;
  if (!d || d.entradas === null || d.sobra === null) return null;
  const falta = d.sobra < 0;
  return (
    <Card tom={falta ? 'atencao' : 'neutro'} className="flex flex-col gap-2">
      <h2 className="font-semibold text-navy">{copy.titulo}</h2>
      <dl className="flex flex-col gap-1 text-sm">
        <Linha rotulo={copy.entra} valor={d.entradas} forte />
        <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-slate">{copy.previsto}</p>
        {d.faturas_cartao > 0 && <Linha rotulo={copy.fatura} valor={d.faturas_cartao} />}
        {d.parcelas_dividas > 0 && <Linha rotulo={copy.parcelas} valor={d.parcelas_dividas} />}
        {d.essenciais_conta !== null && d.essenciais_conta > 0 && <Linha rotulo={copy.essenciais} valor={d.essenciais_conta} />}
      </dl>
      <p className={cx('flex items-start gap-2 font-semibold', falta ? 'text-amber-ink' : 'text-green-ink')} aria-live="polite">
        <span className="mt-0.5">{falta ? Icone.alerta : Icone.check}</span>
        {falta ? copy.falta(brl(Math.abs(d.sobra) as Centavos)) : copy.sobra(brl(d.sobra))}
      </p>
      <p className="text-xs text-slate">{copy.nota}</p>
    </Card>
  );
}

function Linha({ rotulo, valor, forte }: { rotulo: string; valor: Centavos; forte?: boolean }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className={forte ? 'text-ink' : 'text-slate'}>{rotulo}</dt>
      <dd className={cx('tabular', forte ? 'font-semibold text-ink' : 'text-ink')}>
        {forte ? '' : '−'}
        <Money valor={valor} />
      </dd>
    </div>
  );
}
