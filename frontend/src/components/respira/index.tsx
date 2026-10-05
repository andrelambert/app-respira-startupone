import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router';

import { Badge, Button, Card, Icone, Money, cx } from '@/components/ui';
import { chaves } from '@/hooks/queries';
import { api, type Consentimento, type Divida, type Evento } from '@/lib/api';
import {
  alerta,
  conectar,
  divida as copyDivida,
  estados,
  inicio,
  marca,
  mensagemEvento,
  modalidade,
  raiox as copyRaioX,
  type Tom,
} from '@/lib/copy';
import { carimbo, diaMes, mesAno, meses } from '@/lib/datas';
import { soma, type Centavos } from '@/lib/money';

// --- "Este app não movimenta o seu dinheiro" ---------------------------------------------------
// O elemento MAIS visível da tela de conexão (9 de 10 na validação, docs/contexto-produto.md §2).

export function NaoMovimenta({ grande = false }: { grande?: boolean }) {
  return (
    <p
      className={cx(
        'flex items-start gap-3 rounded-2xl bg-navy text-white',
        grande ? 'p-5 text-2xl leading-tight font-bold' : 'p-3 text-base font-semibold',
      )}
    >
      <span className={cx('mt-1 shrink-0', grande && '[&>svg]:h-6 [&>svg]:w-6')}>{Icone.cadeado}</span>
      {marca.naoMovimenta}
    </p>
  );
}

// --- PayoffDate --------------------------------------------------------------------------------

export function PayoffDate({
  data,
  mesesRestantes,
  rotulo,
  tamanho = 'grande',
}: {
  data: string;
  mesesRestantes: number;
  rotulo: string;
  tamanho?: 'grande' | 'medio';
}) {
  return (
    <div>
      <p className="text-sm font-medium text-slate">{rotulo}</p>
      <p
        className={cx(
          'font-bold text-purple first-letter:uppercase',
          tamanho === 'grande' ? 'text-4xl leading-tight' : 'text-2xl',
        )}
      >
        {mesAno(data)}
      </p>
      <p className="text-sm text-slate">{inicio.faltam(mesesRestantes)}</p>
    </div>
  );
}

// --- DebtCard ----------------------------------------------------------------------------------

/** Taxa a partir da qual o custo é destacado como fato (rosa). */
const TAXA_ANUAL_ALTA = 100;

export function DebtCard({ d, cor }: { d: Divida; cor?: string }) {
  const anual = Number(d.taxa_anual.split('.')[0]);
  const cara = anual >= TAXA_ANUAL_ALTA;
  return (
    <Card as="li" className="flex flex-col gap-2">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          {cor && <span aria-hidden="true" className="mt-1.5 h-3 w-3 shrink-0 rounded-sm" style={{ background: cor }} />}
          <div className="min-w-0">
            <h3 className="font-semibold text-navy">{d.descricao}</h3>
            <p className="text-sm text-slate">{modalidade[d.modalidade]?.nome ?? d.modalidade}</p>
          </div>
        </div>
        <Money valor={d.saldo} className="text-lg font-bold text-navy" />
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        <span className={cx('font-semibold', cara ? 'text-rose-ink' : 'text-ink')}>
          {copyDivida.taxaAno(d.taxa_anual)}
        </span>
        <span className="text-slate">
          {copyDivida.minimo} <Money valor={d.parcela_minima} />
        </span>
        {d.dia_vencimento && <span className="text-slate">{copyDivida.vence(d.dia_vencimento)}</span>}
      </div>
      <div className="flex flex-wrap gap-2">
        {d.em_atraso_dias > 0 && (
          <Badge tom="fato" icone={Icone.relogio}>
            {copyDivida.atraso(d.em_atraso_dias)}
          </Badge>
        )}
        {d.taxa_estimada && (
          <Badge tom="estimada" icone={Icone.info} title={copyDivida.estimadaAjuda}>
            {copyDivida.estimada}
          </Badge>
        )}
        {d.parcela_estimada && (
          <Badge tom="estimada" icone={Icone.info} title={copyDivida.parcelaEstimadaAjuda}>
            {copyDivida.parcelaEstimada}
          </Badge>
        )}
        {d.origem === 'MANUAL' && <Badge>{copyDivida.manual}</Badge>}
      </div>
      {(d.taxa_estimada || d.parcela_estimada) && (
        <p className="text-xs text-slate">
          {d.parcela_estimada ? copyDivida.parcelaEstimadaAjuda : copyDivida.estimadaAjuda}{' '}
          <Link to={`/dividas/${d.id}`} className="font-semibold text-blue underline">
            {copyDivida.conferir}
          </Link>
        </p>
      )}
    </Card>
  );
}

// --- Composição da dívida (§10: "qual parte do total cada compromisso ocupa, ordenado por custo")
// Barra empilhada em CSS — sem biblioteca de gráfico no caminho crítico.
// Rampa ordinal navy validada (dataviz validate_palette --ordinal): mais escuro = mais caro.

export const RAMPA_CUSTO = ['#12314F', '#28507A', '#41709F', '#6690BD', '#8AA8CC'];

export function corPorCusto(indice: number): string {
  return RAMPA_CUSTO[Math.min(indice, RAMPA_CUSTO.length - 1)]!;
}

export function DebtComposition({ dividas }: { dividas: Divida[] }) {
  const total = soma(dividas.map((d) => d.saldo));
  if (total <= 0) return null;
  return (
    <figure className="flex flex-col gap-2">
      <figcaption className="text-sm font-semibold text-navy">{copyRaioX.composicao}</figcaption>
      <div className="flex h-5 w-full gap-[2px] overflow-hidden rounded-md" role="img" aria-label={
        dividas.map((d) => `${d.descricao}: ${Math.round((d.saldo / total) * 100)}%`).join('; ')
      }>
        {dividas.map((d, i) => (
          <div
            key={d.id}
            title={`${d.descricao} — ${Math.round((d.saldo / total) * 100)}%`}
            style={{ width: `${(d.saldo / total) * 100}%`, background: corPorCusto(i) }}
            className="h-full first:rounded-l-md last:rounded-r-md"
          />
        ))}
      </div>
    </figure>
  );
}

// --- AlertBanner (sempre com valor em reais — regra de parcimônia) -------------------------------

const tomCard: Record<Tom, 'fato' | 'atencao' | 'progresso' | 'acao'> = {
  fato: 'fato',
  atencao: 'atencao',
  conquista: 'progresso',
  info: 'acao',
};
const tomIcone: Record<Tom, JSX.Element> = {
  fato: Icone.alerta,
  atencao: Icone.relogio,
  conquista: Icone.estrela,
  info: Icone.info,
};
const tomCor: Record<Tom, string> = {
  fato: 'text-rose-ink',
  atencao: 'text-amber-ink',
  conquista: 'text-green-ink',
  info: 'text-blue',
};

export function AlertBanner({ evento }: { evento: Evento }) {
  const qc = useQueryClient();
  const visto = useMutation({
    mutationFn: () => api.eventoVisto(evento.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: chaves.eventos }),
  });
  const m = mensagemEvento(evento);
  return (
    <Card as="li" tom={tomCard[m.tom]} className="flex flex-col gap-2">
      <h3 className={cx('flex items-start gap-2 font-semibold', tomCor[m.tom])}>
        <span className="mt-0.5">{tomIcone[m.tom]}</span>
        {m.titulo}
      </h3>
      <p className="text-sm text-ink">{m.texto}</p>
      <div className="flex flex-wrap gap-2">
        <Button variante="secundario" className="min-h-toque px-3 py-1 text-sm" onClick={() => visto.mutate()} disabled={visto.isPending}>
          {alerta.entendi}
        </Button>
        {evento.licao && (
          <Link
            to={`/licoes/${evento.licao}`}
            className="inline-flex min-h-toque items-center px-3 text-sm font-semibold text-blue underline"
          >
            {alerta.saibaMais}
          </Link>
        )}
      </div>
    </Card>
  );
}

// --- MilestoneBadge ------------------------------------------------------------------------------

export function MilestoneBadge({ evento }: { evento: Evento }) {
  const c = evento.contexto;
  const descricao = typeof c.descricao === 'string' ? c.descricao : '';
  const data = typeof c.data === 'string' ? c.data : evento.detectado_em.slice(0, 10);
  return (
    <li className="flex items-center gap-3 rounded-xl bg-green-soft p-3">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-green text-white [&>svg]:h-5 [&>svg]:w-5">
        {Icone.check}
      </span>
      <div>
        <p className="font-semibold text-green-ink">{descricao}</p>
        <p className="text-sm text-slate">quitada em {diaMes(data)}</p>
      </div>
    </li>
  );
}

// --- Atualizado em (nunca mostrar dado velho como atual, §7.10) -----------------------------------

export function AtualizadoEm({ iso }: { iso: string | null | undefined }) {
  if (!iso) return null;
  return <p className="text-xs text-slate">{estados.atualizadoEm(carimbo(iso))}</p>;
}

// --- Avisos de consentimento (expirado / expirando aos 30 e 7 dias) ---------------------------------

export function AvisosConsentimento({ consentimentos }: { consentimentos: Consentimento[] }) {
  type Aviso = { c: Consentimento; texto: string; tom: 'fato' | 'atencao' };
  const avisos = consentimentos.flatMap((c): Aviso[] => {
    const banco = c.instituicao ?? 'banco';
    if (c.status === 'EXPIRADO') return [{ c, texto: conectar.expirado(banco), tom: 'fato' }];
    // Aviso antecipado aos 30 e aos 7 dias (§7.10).
    if (c.status === 'ATIVO' && c.dias_para_expirar !== null && c.dias_para_expirar <= 30) {
      return [{ c, texto: conectar.expiraEm(banco, Math.max(c.dias_para_expirar, 0)), tom: 'atencao' }];
    }
    return [];
  });
  if (!avisos.length) return null;
  return (
    <ul className="flex flex-col gap-2">
      {avisos.map(({ c, texto, tom }) => (
        <Card as="li" key={c.id} tom={tom} className="flex flex-col gap-2">
          <p className={cx('flex items-start gap-2 text-sm font-semibold', tom === 'fato' ? 'text-rose-ink' : 'text-amber-ink')}>
            <span className="mt-0.5">{Icone.relogio}</span>
            {texto}
          </p>
          <Link
            to={`/conectar?reconectar=${encodeURIComponent(c.instituicao_codigo ?? '')}`}
            className="inline-flex min-h-toque items-center self-start rounded-xl bg-blue px-4 text-sm font-semibold text-white"
          >
            {conectar.reconectar}
          </Link>
        </Card>
      ))}
    </ul>
  );
}

// --- Juros evitados (§10) — barras em CSS, uma escala só ----------------------------------------------

export function JurosEvitados({
  plano,
  soMinimo,
  rotuloPlano,
  rotuloMinimo,
}: {
  plano: Centavos;
  soMinimo: Centavos;
  rotuloPlano: string;
  rotuloMinimo: string;
}) {
  const max = Math.max(plano, soMinimo, 1);
  const linhas = [
    { rotulo: rotuloMinimo, valor: soMinimo, cor: '#8AA8CC' },
    { rotulo: rotuloPlano, valor: plano, cor: '#7C3AED' },
  ];
  return (
    <dl className="flex flex-col gap-2">
      {linhas.map((l) => (
        <div key={l.rotulo} className="flex flex-col gap-1">
          <dt className="flex justify-between text-sm text-slate">
            <span>{l.rotulo}</span>
            <Money valor={l.valor} semCentavos className="font-semibold text-ink" />
          </dt>
          <dd className="h-3 w-full rounded-r bg-light">
            <div className="h-full rounded-r" style={{ width: `${(l.valor / max) * 100}%`, background: l.cor }} />
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function TextoMeses({ n }: { n: number }) {
  return <>{meses(n)}</>;
}

// --- Logo do banco (catálogo da Belvo) ----------------------------------------------

const TAMANHOS = { p: 'h-5 w-5 text-[9px]', m: 'h-9 w-9 text-xs', g: 'h-12 w-12 text-sm' };

/**
 * Logo da instituição, vindo do catálogo da Belvo. Sem logo — ou se a imagem
 * não carregar — mostra as iniciais. Decorativo: o nome do banco sempre está
 * escrito ao lado, então ``alt`` fica vazio.
 */
export function LogoBanco({
  nome,
  logo,
  tamanho = 'm',
}: {
  nome: string | null | undefined;
  logo: string | null | undefined;
  tamanho?: keyof typeof TAMANHOS;
}) {
  const [falhou, setFalhou] = useState(false);
  const classes = cx('shrink-0 overflow-hidden rounded-full', TAMANHOS[tamanho]);
  if (logo && !falhou) {
    return (
      <img
        src={logo}
        alt=""
        aria-hidden="true"
        loading="lazy"
        referrerPolicy="no-referrer"
        onError={() => setFalhou(true)}
        className={cx(classes, 'border border-line bg-white object-contain p-0.5')}
      />
    );
  }
  const iniciais = (nome ?? '?')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join('');
  return (
    <span aria-hidden="true" className={cx(classes, 'flex items-center justify-center bg-navy font-bold text-white')}>
      {iniciais}
    </span>
  );
}
