import { Link } from 'react-router';

import { LogoBanco } from '@/components/respira';
import { Badge, Icone } from '@/components/ui';
import type { Vencimento } from '@/lib/api';
import { vencimentos as copy } from '@/lib/copy';
import { diaMes } from '@/lib/datas';
import { brl } from '@/lib/money';

const TOM = { PAGO: 'progresso', PENDENTE: 'neutro', ATRASADO: 'fato' } as const;
const ICONE = { PAGO: Icone.check, PENDENTE: Icone.relogio, ATRASADO: Icone.alerta };

/** Lista de vencimentos (N3): data, credor, valor e status — com ícone e rótulo, nunca só cor. */
export function ListaVencimentos({ itens }: { itens: Vencimento[] }) {
  return (
    <ul className="flex flex-col divide-y divide-line rounded-2xl border border-line bg-white">
      {itens.map((v) => {
        const destino = v.conta_id ? `/contas/${v.conta_id}` : v.divida_id ? '/dividas' : null;
        const conteudo = (
          <div className="flex items-start gap-3 px-4 py-3">
            <LogoBanco nome={v.credor} logo={v.banco_logo} />
            <div className="min-w-0 flex-1">
              <p className="line-clamp-2 break-words font-medium text-ink">{v.descricao}</p>
              <p className="text-xs text-slate">
                {diaMes(v.data)} · {copy.quando(v.dias)}
              </p>
              {/* Só quando o plano manda pagar diferente do mínimo/parcela — senão repete o número. */}
              {v.valor_plano !== null && v.valor_plano !== v.valor && v.status !== 'PAGO' && (
                <p className="text-xs font-medium text-purple">{copy.noPlano(brl(v.valor_plano))}</p>
              )}
            </div>
            <div className="flex shrink-0 flex-col items-end gap-1">
              <span className="tabular font-semibold text-ink">{brl(v.valor)}</span>
              <span className="text-xs text-slate">
                {v.tipo === 'FATURA' && v.valor_total !== null && v.valor_total !== v.valor
                  ? copy.daFatura(brl(v.valor_total))
                  : v.tipo === 'FATURA'
                    ? copy.minimo
                    : copy.parcela}
              </span>
              <Badge tom={TOM[v.status]} icone={ICONE[v.status]}>
                {copy.status[v.status]}
              </Badge>
            </div>
          </div>
        );
        return (
          <li key={`${v.tipo}-${v.conta_id ?? ''}-${v.divida_id ?? ''}-${v.data}`}>
            {destino ? (
              <Link to={destino} className="block hover:bg-light">
                {conteudo}
              </Link>
            ) : (
              conteudo
            )}
          </li>
        );
      })}
    </ul>
  );
}
