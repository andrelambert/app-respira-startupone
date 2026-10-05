import { forwardRef, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode } from 'react';
import { Link, type LinkProps } from 'react-router';

import { estados } from '@/lib/copy';
import { brl, type Centavos } from '@/lib/money';

export function cx(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ');
}

// --- Button ----------------------------------------------------------------------------

type Variante = 'primario' | 'secundario' | 'fantasma' | 'perigo';

const variantes: Record<Variante, string> = {
  primario: 'bg-blue text-white hover:bg-blue-700 disabled:bg-slate-400',
  secundario: 'border border-line bg-white text-navy hover:bg-light disabled:text-slate',
  fantasma: 'text-blue hover:bg-blue-soft disabled:text-slate',
  perigo: 'border border-rose bg-white text-rose-ink hover:bg-rose-soft',
};

const base =
  'inline-flex min-h-toque items-center justify-center gap-2 rounded-xl px-5 py-3 text-base font-semibold transition-colors disabled:cursor-not-allowed';

export function Button({
  variante = 'primario',
  largo = false,
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variante?: Variante; largo?: boolean }) {
  return (
    <button
      type="button"
      className={cx(base, variantes[variante], largo && 'w-full', className)}
      {...props}
    />
  );
}

export function LinkBotao({
  variante = 'primario',
  largo = false,
  className,
  ...props
}: LinkProps & { variante?: Variante; largo?: boolean }) {
  return <Link className={cx(base, variantes[variante], largo && 'w-full', className)} {...props} />;
}

// --- Card --------------------------------------------------------------------------------

export function Card({
  children,
  className,
  tom = 'neutro',
  as: Tag = 'section',
}: {
  children: ReactNode;
  className?: string;
  tom?: 'neutro' | 'plano' | 'progresso' | 'atencao' | 'fato' | 'acao';
  as?: 'section' | 'div' | 'article' | 'li';
}) {
  const tons = {
    neutro: 'bg-white border-line',
    plano: 'bg-purple-soft border-purple/30',
    progresso: 'bg-green-soft border-green/30',
    atencao: 'bg-amber-soft border-amber/40',
    fato: 'bg-rose-soft border-rose/30',
    acao: 'bg-blue-soft border-blue/30',
  };
  return <Tag className={cx('rounded-2xl border p-4', tons[tom], className)}>{children}</Tag>;
}

// --- Money ------------------------------------------------------------------------------

export function Money({
  valor,
  semCentavos,
  className,
}: {
  valor: Centavos;
  semCentavos?: boolean;
  className?: string;
}) {
  return <span className={cx('tabular whitespace-nowrap', className)}>{brl(valor, { semCentavos })}</span>;
}

// --- Badge -----------------------------------------------------------------------------

export function Badge({
  children,
  tom = 'neutro',
  icone,
  title,
}: {
  children: ReactNode;
  tom?: 'neutro' | 'estimada' | 'fato' | 'progresso' | 'plano';
  icone?: ReactNode;
  title?: string;
}) {
  const tons = {
    neutro: 'bg-light text-slate border-line',
    estimada: 'bg-amber-soft text-amber-ink border-amber/40',
    fato: 'bg-rose-soft text-rose-ink border-rose/30',
    progresso: 'bg-green-soft text-green-ink border-green/30',
    plano: 'bg-purple-soft text-purple border-purple/30',
  };
  return (
    <span
      title={title}
      className={cx(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium',
        tons[tom],
      )}
    >
      {icone}
      {children}
    </span>
  );
}

// --- ícones (SVG inline: nada de biblioteca de ícones no bundle) ----------------------------

const svg = 'h-4 w-4 shrink-0';
export const Icone = {
  alerta: (
    <svg className={svg} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M10 2 1 18h18L10 2Zm0 5 .1 6h-.2L10 7Zm0 8.5a1 1 0 1 1 0 2 1 1 0 0 1 0-2Z" />
    </svg>
  ),
  info: (
    <svg className={svg} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M10 1a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm1 14H9V9h2v6Zm-1-8a1.2 1.2 0 1 1 0-2.4A1.2 1.2 0 0 1 10 7Z" />
    </svg>
  ),
  check: (
    <svg className={svg} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M8 13.6 4.4 10 3 11.4l5 5 9-9L15.6 6 8 13.6Z" />
    </svg>
  ),
  cadeado: (
    <svg className={svg} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M10 1a5 5 0 0 0-5 5v3H4a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-8a1 1 0 0 0-1-1h-1V6a5 5 0 0 0-5-5Zm-3 8V6a3 3 0 1 1 6 0v3H7Z" />
    </svg>
  ),
  estrela: (
    <svg className={svg} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="m10 1 2.7 5.6 6.1.9-4.4 4.3 1 6.1L10 15l-5.4 2.9 1-6.1L1.2 7.5l6.1-.9L10 1Z" />
    </svg>
  ),
  relogio: (
    <svg className={svg} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M10 1a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm1 9.4 3.3 2-1 1.7L9 11.5V5h2v5.4Z" />
    </svg>
  ),
};

// --- formulário ----------------------------------------------------------------------------

export type EstadoCampo = 'neutro' | 'valido' | 'invalido';

/**
 * Campo de formulário com validação inline. ``estado`` pinta a borda (verde /
 * vermelha) e sempre vem com ícone — o estado nunca depende só da cor (§10).
 * ``erro`` sozinho (sem ``estado``) continua funcionando como antes.
 */
export const Campo = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement> & {
    rotulo: string;
    ajuda?: string;
    erro?: string;
    estado?: EstadoCampo;
    mensagem?: string; // texto sob o campo (vermelho se inválido, verde se válido)
    sufixo?: ReactNode; // ex.: botão "Mostrar" da senha
  }
>(function Campo({ rotulo, ajuda, erro, estado, mensagem, sufixo, id, className, ...props }, ref) {
  const campoId = id ?? props.name;
  const ajudaId = `${campoId}-ajuda`;
  const msgId = `${campoId}-msg`;
  const efetivo: EstadoCampo = estado ?? (erro ? 'invalido' : 'neutro');
  const texto = efetivo === 'invalido' ? (mensagem ?? erro) : efetivo === 'valido' ? mensagem : undefined;
  return (
    <div className={cx('flex flex-col gap-1', className)}>
      <label htmlFor={campoId} className="text-sm font-semibold text-navy">
        {rotulo}
      </label>
      {ajuda && (
        <p id={ajudaId} className="text-sm text-slate">
          {ajuda}
        </p>
      )}
      <div className="relative">
        <input
          ref={ref}
          id={campoId}
          aria-invalid={efetivo === 'invalido' ? true : undefined}
          aria-describedby={[ajuda && ajudaId, msgId].filter(Boolean).join(' ')}
          className={cx(
            'min-h-toque w-full rounded-xl border-2 bg-white px-3 py-2 text-base text-ink outline-none transition-colors',
            efetivo === 'invalido' && 'border-rose',
            efetivo === 'valido' && 'border-green',
            efetivo === 'neutro' && 'border-line focus:border-blue',
            sufixo ? 'pr-28' : efetivo !== 'neutro' && 'pr-10',
          )}
          {...props}
        />
        <div className="absolute inset-y-0 right-2 flex items-center gap-1">
          {efetivo === 'valido' && <span className="text-green-ink [&>svg]:h-5 [&>svg]:w-5">{Icone.check}</span>}
          {efetivo === 'invalido' && <span className="text-rose-ink [&>svg]:h-5 [&>svg]:w-5">{Icone.alerta}</span>}
          {sufixo}
        </div>
      </div>
      {/* Sempre presente para o leitor de tela anunciar quando o texto muda. */}
      <p
        id={msgId}
        aria-live="polite"
        className={cx('min-h-5 text-sm', efetivo === 'invalido' ? 'text-rose-ink' : 'text-green-ink')}
      >
        {texto}
      </p>
    </div>
  );
});

/** Botão "Mostrar/Ocultar" para campo de senha. */
export function BotaoVerSenha({ visivel, onAlternar }: { visivel: boolean; onAlternar: () => void }) {
  return (
    <button
      type="button"
      onClick={onAlternar}
      aria-pressed={visivel}
      aria-label={visivel ? 'Ocultar senha' : 'Mostrar senha'}
      className="min-h-toque px-2 text-sm font-semibold text-blue"
    >
      {visivel ? 'Ocultar' : 'Mostrar'}
    </button>
  );
}

// --- estados (§6.5: carregando, vazio, erro, offline) --------------------------------------

export function Carregando({ texto = estados.carregando }: { texto?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex flex-col gap-3 py-8">
      <span className="sr-only">{texto}</span>
      <div className="h-6 w-2/3 animate-pulse rounded bg-line" />
      <div className="h-12 w-1/2 animate-pulse rounded bg-line" />
      <div className="h-24 w-full animate-pulse rounded-2xl bg-line" />
      <div className="h-24 w-full animate-pulse rounded-2xl bg-line" />
    </div>
  );
}

export function BarraIndeterminada({ rotulo }: { rotulo: string }) {
  return (
    <div
      role="progressbar"
      aria-label={rotulo}
      aria-busy="true"
      className="relative h-2 w-full overflow-hidden rounded-full bg-blue-soft"
    >
      <div className="barra-indeterminada absolute inset-y-0 w-2/5 rounded-full bg-blue" />
    </div>
  );
}

export function EstadoVazio({
  titulo,
  texto,
  acao,
}: {
  titulo: string;
  texto: string;
  acao?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-2xl border border-dashed border-line bg-white p-6">
      <h2 className="text-lg font-semibold text-navy">{titulo}</h2>
      <p className="text-slate">{texto}</p>
      {acao}
    </div>
  );
}

export function EstadoErro({
  titulo = estados.erroTitulo,
  texto = estados.erroTexto,
  onTentar,
}: {
  titulo?: string;
  texto?: string;
  onTentar?: () => void;
}) {
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-2xl border border-line bg-white p-6">
      <h2 className="flex items-center gap-2 text-lg font-semibold text-navy">
        <span className="text-amber">{Icone.alerta}</span>
        {titulo}
      </h2>
      <p className="text-slate">{texto}</p>
      {onTentar && (
        <Button variante="secundario" onClick={onTentar}>
          {estados.tentar}
        </Button>
      )}
    </div>
  );
}

export function BarraProgresso({ pct, rotulo }: { pct: number; rotulo: string }) {
  const v = Math.max(0, Math.min(100, pct));
  return (
    <div
      role="progressbar"
      aria-label={rotulo}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(v)}
      className="h-3 w-full overflow-hidden rounded-full bg-white"
    >
      <div className="h-full rounded-full bg-green transition-[width]" style={{ width: `${v}%` }} />
    </div>
  );
}
