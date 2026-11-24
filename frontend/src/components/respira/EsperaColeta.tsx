import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { LogoBanco } from '@/components/respira';
import { BarraProgresso, Button, Card, cx } from '@/components/ui';
import { chavesFinanceiras } from '@/hooks/queries';
import { api, type Consentimento } from '@/lib/api';
import { coleta as copy, estados } from '@/lib/copy';

const LIMITE_ESPERA_MS = 3 * 60 * 1000;
// O cadastro do titular (OWNERS) não é lido (minimização, §12.7): fora da lista.
const ORDEM = ['ACCOUNTS', 'BILLS', 'TRANSACTIONS', 'INCOMES', 'RECURRING_EXPENSES'];

type Estado = 'RECEBIDO' | 'AGUARDANDO' | 'INDISPONIVEL';

/**
 * Espera da coleta depois de conectar um banco (§7.5): nunca "R$ 0,00" no lugar
 * de "ainda buscando". Mostra o progresso real (quantas etapas já chegaram), um
 * cartão por banco com cada recurso numa linha, e o tempo de espera. As
 * consultas ao backend seguem a cada 5 s; o backend consulta a Belvo a cada 5 s.
 */
export function EsperaColeta({ consentimentos, oscilou = false }: { consentimentos: Consentimento[]; oscilou?: boolean }) {
  const [inicio] = useState(() => Date.now());
  const [agora, setAgora] = useState(() => Date.now());
  const qc = useQueryClient();
  useEffect(() => {
    const t = window.setInterval(() => setAgora(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, []);
  const sync = useMutation({
    mutationFn: api.sync,
    onSettled: () => chavesFinanceiras.forEach((k) => void qc.invalidateQueries({ queryKey: k })),
  });

  const segundos = Math.max(0, Math.floor((agora - inicio) / 1000));
  const demorou = agora - inicio > LIMITE_ESPERA_MS;
  const bancos = consentimentos.filter((c) => c.status === 'ATIVO');
  const etapas = bancos.flatMap((c) => c.coleta.filter((r) => ORDEM.includes(r.recurso)));
  const prontas = etapas.filter((r) => r.status !== 'AGUARDANDO').length;
  const pct = etapas.length ? (prontas / etapas.length) * 100 : 5;

  return (
    <div className="flex flex-col gap-5 pt-2">
      {demorou ? (
        <Card tom="atencao" className="flex flex-col gap-3">
          <h1 className="text-xl font-bold text-navy">{copy.demorou.titulo}</h1>
          <p className="text-ink">{copy.demorou.texto}</p>
          <Button onClick={() => sync.mutate()} disabled={sync.isPending} aria-busy={sync.isPending}>
            {sync.isPending ? estados.tentando : copy.demorou.recarregar}
          </Button>
        </Card>
      ) : (
        <section aria-labelledby="espera-titulo" className="flex flex-col items-center gap-4 pt-4 text-center">
          <span
            aria-hidden="true"
            className="flex h-16 w-16 items-center justify-center rounded-full bg-blue/10 text-blue"
          >
            <svg viewBox="0 0 24 24" className="h-8 w-8 motion-safe:animate-spin [animation-duration:2.4s]" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M21 12a9 9 0 0 1-15.5 6.2" />
              <path d="M3 12A9 9 0 0 1 18.5 5.8" />
              <path d="M18.5 2v3.8h-3.8" />
              <path d="M5.5 22v-3.8h3.8" />
            </svg>
          </span>
          <div className="flex flex-col gap-1">
            <p className="text-sm font-semibold uppercase tracking-wide text-green-ink">{copy.conectado}</p>
            <h1 id="espera-titulo" className="text-2xl font-bold leading-tight text-navy">
              {copy.buscando}
            </h1>
            <p className="text-slate">{copy.texto}</p>
          </div>
        </section>
      )}

      <div className="flex flex-col gap-2" aria-live="polite">
        <BarraProgresso pct={pct} rotulo={copy.progresso(prontas, etapas.length)} sobreBranco />
        <p className="flex justify-between text-sm text-slate">
          <span>{copy.progresso(prontas, etapas.length)}</span>
          <span className="tabular">{copy.tempo(segundos)}</span>
        </p>
        {oscilou && (
          <p role="status" className="rounded-xl bg-amber-soft px-3 py-2 text-sm text-amber-ink">
            {estados.reconectando}
          </p>
        )}
      </div>

      <ul className="flex flex-col gap-3">
        {bancos.map((c) => (
          <li key={c.id}>
            <Card as="div" className="flex flex-col gap-3">
              <div className="flex items-center gap-3">
                <LogoBanco nome={c.instituicao ?? ''} logo={c.instituicao_logo} />
                <p className="min-w-0 flex-1 truncate font-semibold text-navy">{c.instituicao}</p>
                {c.coleta_concluida && <span className="text-sm font-semibold text-green-ink">{copy.bancoPronto}</span>}
              </div>
              <ul className="flex flex-col divide-y divide-line">
                {c.coleta
                  .filter((r) => ORDEM.includes(r.recurso))
                  .sort((a, b) => ORDEM.indexOf(a.recurso) - ORDEM.indexOf(b.recurso))
                  .map((r) => (
                    <LinhaRecurso key={r.recurso} recurso={r.recurso} estado={r.status as Estado} />
                  ))}
              </ul>
            </Card>
          </li>
        ))}
      </ul>

      <p className="text-center text-sm text-slate">{copy.podeSair}</p>
    </div>
  );
}

function LinhaRecurso({ recurso, estado }: { recurso: string; estado: Estado }) {
  const info = copy.etapas[recurso] ?? { nome: recurso, detalhe: '' };
  return (
    <li className="flex items-center gap-3 py-2.5">
      <IconeEstado estado={estado} />
      <div className="min-w-0 flex-1">
        <p className={cx('font-medium', estado === 'AGUARDANDO' ? 'text-ink' : 'text-navy')}>{info.nome}</p>
        <p className="text-xs text-slate">{info.detalhe}</p>
      </div>
      {/* Estado sempre escrito, não só pela cor do ícone (§10). */}
      <span
        className={cx(
          'shrink-0 text-sm',
          estado === 'RECEBIDO' && 'font-semibold text-green-ink',
          estado === 'AGUARDANDO' && 'text-slate',
          estado === 'INDISPONIVEL' && 'text-amber-ink',
        )}
      >
        {copy.estados[estado]}
      </span>
    </li>
  );
}

function IconeEstado({ estado }: { estado: Estado }) {
  if (estado === 'RECEBIDO') {
    return (
      <span aria-hidden="true" className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-green/15 text-green-ink">
        <svg viewBox="0 0 20 20" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M5 10.5l3 3 7-7" />
        </svg>
      </span>
    );
  }
  if (estado === 'INDISPONIVEL') {
    return (
      <span aria-hidden="true" className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-amber/15 text-amber-ink">
        <svg viewBox="0 0 20 20" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
          <path d="M6 10h8" />
        </svg>
      </span>
    );
  }
  return (
    <span aria-hidden="true" className="flex h-7 w-7 shrink-0 items-center justify-center">
      <span className="h-5 w-5 rounded-full border-2 border-line border-t-blue motion-safe:animate-spin" />
    </span>
  );
}
