import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router';

import {
  Badge,
  BarraIndeterminada,
  Button,
  Card,
  Carregando,
  EstadoErro,
  EstadoVazio,
  Icone,
  LinkBotao,
  Money,
  cx,
} from '@/components/ui';
import { LogoBanco } from '@/components/respira';
import { chavesFinanceiras, useVisaoGeral } from '@/hooks/queries';
import { api, type Banco, type ContaBancaria } from '@/lib/api';
import { coleta as copyColeta, pfm as copy, tipoBelvo } from '@/lib/copy';
import { carimbo, diaMes } from '@/lib/datas';
import { soma, type Centavos } from '@/lib/money';

const DEPOSITO = new Set(['CORRENTE', 'POUPANCA', 'PAGAMENTO']);

/** PFM — o que está conectado, saldos e faturas, por banco. */
export default function Contas() {
  const [params, setParams] = useSearchParams();
  const visao = useVisaoGeral();
  const dados = visao.data;

  if (visao.isLoading) return <Carregando />;
  if (visao.isError || !dados) return <EstadoErro onTentar={() => void visao.refetch()} />;
  if (dados.bancos.length === 0) {
    return (
      <EstadoVazio
        titulo={copy.semBancos.titulo}
        texto={copy.semBancos.texto}
        acao={<LinkBotao to="/conectar">{copy.conectarOutro.replace('+ ', '')}</LinkBotao>}
      />
    );
  }

  const selecionado = Number(params.get('banco')) || null;
  const bancos = selecionado ? dados.bancos.filter((b) => b.consentimento_id === selecionado) : dados.bancos;
  const contas = bancos.flatMap((b) => b.contas);
  const emConta = soma(contas.filter((c) => DEPOSITO.has(c.tipo)).map((c) => c.saldo));
  const faturas = soma(
    contas.map((c) => (c.fatura_atual && c.fatura_atual.situacao !== 'PAGA' ? c.fatura_atual.em_aberto : (0 as Centavos))),
  );

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-bold text-navy">{copy.titulo}</h1>

      {/* Alternar entre bancos */}
      <nav aria-label="Bancos" className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 [scrollbar-width:none]">
        <Chip ativo={!selecionado} onClick={() => setParams({})}>
          {copy.todos}
        </Chip>
        {dados.bancos.map((b) => (
          <Chip
            key={b.consentimento_id}
            ativo={selecionado === b.consentimento_id}
            onClick={() => setParams({ banco: String(b.consentimento_id) })}
          >
            <LogoBanco nome={b.instituicao} logo={b.instituicao_logo} tamanho="p" />
            {b.instituicao ?? 'Banco'}
          </Chip>
        ))}
        <Link
          to="/conectar"
          className="flex min-h-toque shrink-0 items-center rounded-full border border-dashed border-blue px-4 text-sm font-semibold text-blue"
        >
          {copy.conectarOutro}
        </Link>
      </nav>

      <div className="grid grid-cols-2 gap-3">
        <Card as="div">
          <p className="text-sm text-slate">{copy.emConta}</p>
          <Money valor={emConta} className="text-xl font-bold text-navy" />
        </Card>
        <Card as="div">
          <p className="text-sm text-slate">{copy.faturasAbertas}</p>
          <Money valor={faturas} className="text-xl font-bold text-navy" />
        </Card>
      </div>

      {bancos.map((b) => (
        <SecaoBanco key={b.consentimento_id} banco={b} />
      ))}
    </div>
  );
}

function Chip({ ativo, onClick, children }: { ativo: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={ativo}
      onClick={onClick}
      className={cx(
        'inline-flex min-h-toque shrink-0 items-center gap-2 rounded-full border px-4 text-sm font-semibold',
        ativo ? 'border-navy bg-navy text-white' : 'border-line bg-white text-navy',
      )}
    >
      {children}
    </button>
  );
}

function SecaoBanco({ banco }: { banco: Banco }) {
  const qc = useQueryClient();
  const invalidar = () => Promise.all(chavesFinanceiras.map((k) => qc.invalidateQueries({ queryKey: k })));
  const atualizar = useMutation({ mutationFn: api.sync, onSettled: invalidar });
  const nome = banco.instituicao ?? 'banco';
  const coletando = banco.status === 'ATIVO' && !banco.coleta_concluida;

  return (
    <section className="flex flex-col gap-3" aria-labelledby={`banco-${banco.consentimento_id}`}>
      <div className="flex items-center gap-2">
        <LogoBanco nome={banco.instituicao} logo={banco.instituicao_logo} />
        <div className="min-w-0 flex-1">
          <h2 id={`banco-${banco.consentimento_id}`} className="truncate font-semibold text-navy">
            {nome}
          </h2>
          {banco.ultima_sync_em && <p className="text-xs text-slate">{copy.atualizado(carimbo(banco.ultima_sync_em))}</p>}
        </div>
        {banco.status !== 'ATIVO' && <Badge tom="estimada">{banco.status === 'EXPIRADO' ? 'Expirada' : 'Com problema'}</Badge>}
        <Button
          variante="fantasma"
          className="px-3 text-sm"
          onClick={() => atualizar.mutate()}
          disabled={atualizar.isPending || coletando}
        >
          {copy.atualizar}
        </Button>
      </div>

      {coletando && (
        <Card tom="acao" as="div" className="flex flex-col gap-2" >
          <p className="text-sm text-ink" aria-live="polite">{copy.coletando}</p>
          <BarraIndeterminada rotulo={copy.coletando} />
          <ul className="flex flex-wrap gap-x-3 text-xs">
            {banco.coleta
              .filter((r) => r.recurso !== 'OWNERS')
              .map((r) => (
                <li key={r.recurso} className={cx('flex items-center gap-1', r.status === 'RECEBIDO' ? 'text-green-ink' : 'text-slate')}>
                  {r.status === 'RECEBIDO' ? Icone.check : Icone.relogio}
                  {copyColeta.recursos[r.recurso] ?? r.recurso}
                </li>
              ))}
          </ul>
        </Card>
      )}

      <ul className="flex flex-col gap-2">
        {banco.contas.map((c) => (
          <CartaoConta key={c.id} c={c} />
        ))}
      </ul>

    </section>
  );
}

export function CartaoConta({ c }: { c: ContaBancaria }) {
  // Na lista, a conta corrente fica só com o tipo; o número completo está no detalhe.
  const final = DEPOSITO.has(c.tipo) ? null : identificacaoConta(c);
  return (
    <li>
      <Link
        to={`/contas/${c.id}`}
        className="flex flex-col gap-2 rounded-2xl border border-line bg-white p-4 transition-colors hover:border-blue"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            {/* Título: o tipo (category traduzida). Embaixo, name e type da Belvo. */}
            <p className="truncate font-bold text-navy">
              {copy.tipo[c.tipo] ?? c.tipo}
              {final && <span className="font-normal text-slate"> {final}</span>}
            </p>
            <p className="truncate text-xs text-slate">
              {[c.nome, tipoBelvo(c.tipo_externo)].filter(Boolean).join(' · ')}
            </p>
          </div>
          <ResumoValor c={c} />
        </div>
        {c.tipo === 'CARTAO_CREDITO' && <ResumoCartao c={c} />}
      </Link>
    </li>
  );
}

function ResumoValor({ c }: { c: ContaBancaria }) {
  if (DEPOSITO.has(c.tipo)) {
    return (
      <div className="text-right">
        <Money valor={c.saldo} className="text-lg font-bold text-navy" />
        {c.disponivel !== null && c.disponivel !== c.saldo && (
          <p className="text-xs text-slate">
            {copy.disponivel} <Money valor={c.disponivel} />
          </p>
        )}
      </div>
    );
  }
  if (c.tipo === 'CARTAO_CREDITO') {
    const f = c.fatura_atual;
    return f ? <Money valor={f.situacao === 'PAGA' ? f.total : f.em_aberto} className="text-lg font-bold text-navy" /> : null;
  }
  return (
    <div className="text-right">
      <Money valor={c.saldo} className="text-lg font-bold text-navy" />
      <p className="text-xs text-slate">{copy.saldoDevedor.toLowerCase()}</p>
    </div>
  );
}

function ResumoCartao({ c }: { c: ContaBancaria }) {
  const f = c.fatura_atual;
  const pct = c.limite_credito && c.limite_credito > 0 ? Math.min(100, (c.saldo / c.limite_credito) * 100) : null;
  return (
    <div className="flex flex-col gap-2">
      {f ? (
        <p className="flex flex-wrap items-center gap-2 text-sm text-slate">
          <SituacaoFatura situacao={f.situacao} />
          {f.vencimento && (f.situacao === 'ATRASADA' ? copy.venceu(diaMes(f.vencimento)) : copy.vence(diaMes(f.vencimento)))}
        </p>
      ) : (
        <p className="text-sm text-slate">{copy.semFatura}</p>
      )}
      {pct !== null && c.limite_credito !== null && (
        <div className="flex flex-col gap-1">
          <div className="h-2 w-full overflow-hidden rounded-full bg-light" role="img" aria-label={`${Math.round(pct)}% do limite usado`}>
            <div className="h-full rounded-full bg-navy" style={{ width: `${pct}%` }} />
          </div>
          <p className="flex justify-between text-xs text-slate">
            <span>
              {copy.usado} <Money valor={c.saldo} />
            </span>
            <span>
              {copy.limite} <Money valor={c.limite_credito} />
            </span>
          </p>
        </div>
      )}
    </div>
  );
}

export function SituacaoFatura({ situacao }: { situacao: string }) {
  const tom = situacao === 'PAGA' ? 'progresso' : situacao === 'ATRASADA' ? 'fato' : situacao === 'PARCIAL' ? 'estimada' : 'neutro';
  const icone = situacao === 'PAGA' ? Icone.check : situacao === 'ATRASADA' ? Icone.alerta : Icone.relogio;
  return (
    <Badge tom={tom} icone={icone}>
      {copy.situacao[situacao] ?? situacao}
    </Badge>
  );
}

/** Conta de depósito: número completo com dígito (00893456-7). Cartão e crédito: só o final (••3456). */
export function identificacaoConta(c: ContaBancaria): string | null {
  if (DEPOSITO.has(c.tipo) && c.numero_conta) return c.numero_conta;
  return c.numero_final ? `••${c.numero_final}` : null;
}
