import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { lazy, Suspense, useState } from 'react';
import { Navigate, useNavigate } from 'react-router';

import { JurosEvitados } from '@/components/respira';
import { Badge, Button, Card, Carregando, EstadoErro, EstadoVazio, Icone, LinkBotao, Money, cx } from '@/components/ui';
import { chaves, chavesFinanceiras, usePlanoAtivo, useUsuario } from '@/hooks/queries';
import { useDebounced } from '@/hooks/useDebounced';
import { api, ApiError, type Estrategia, type Metodo, type Simulacoes } from '@/lib/api';
import { COR_METODO } from '@/lib/cores';
import { conectar, erroConexao, fraseComparacao, metodoNome, plano as copy, raiox as copyRaioX } from '@/lib/copy';
import { mesAno, meses, ordinalMes } from '@/lib/datas';
import { brl, centavos, paraDecimal, reaisInteiros, type Centavos } from '@/lib/money';

const TrajectoryChart = lazy(() => import('@/components/respira/TrajectoryChart'));
const PASSO_REAIS = 10;

/** Etapa 5 — Plano (§9). */
export default function Plano() {
  const { data: usuario, isLoading } = useUsuario();
  const base = useQuery({
    queryKey: chaves.simulacoes(undefined),
    queryFn: () => api.simulacoes(),
    enabled: Boolean(usuario),
  });
  const ativo = usePlanoAtivo();

  if (isLoading) return <Carregando />;
  if (!usuario) return <Navigate to="/entrar" replace />;
  if (base.isLoading || ativo.isLoading) return <Carregando />;
  if (base.isError || !base.data) return <EstadoErro onTentar={() => void base.refetch()} />;
  if (base.data.estrategias.every((e) => e.itens.length === 0)) {
    return (
      <EstadoVazio
        titulo={copyRaioX.semConexao.titulo}
        texto={copyRaioX.semConexao.texto}
        acao={<LinkBotao to="/conectar">{conectar.cta}</LinkBotao>}
      />
    );
  }
  return (
    <Simulador
      base={base.data}
      capacidadeAtiva={ativo.data?.capacidade_mensal ?? null}
      metodoAtivo={ativo.data?.metodo ?? null}
    />
  );
}

function capacidadeInicial(s: Simulacoes): number {
  const calc = reaisInteiros(s.capacidade_calculada.valor);
  if (calc > 0) return calc;
  // Sem histórico: começa no piso que converge, arredondado para cima.
  const piso = s.capacidade_minima ? reaisInteiros(s.capacidade_minima) : reaisInteiros(s.compromisso_minimo_mes);
  return Math.ceil(piso / 50) * 50;
}

function Simulador({
  base,
  capacidadeAtiva,
  metodoAtivo,
}: {
  base: Simulacoes;
  capacidadeAtiva: Centavos | null;
  metodoAtivo: Metodo | null;
}) {
  const calculada = reaisInteiros(base.capacidade_calculada.valor);
  const [reais, setReais] = useState(() =>
    capacidadeAtiva !== null ? reaisInteiros(capacidadeAtiva) : capacidadeInicial(base),
  );
  const [metodo, setMetodo] = useState<Metodo>(metodoAtivo ?? base.pre_selecionado);
  const debounced = useDebounced(reais, 200);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const sim = useQuery({
    queryKey: chaves.simulacoes(String(debounced)),
    queryFn: ({ signal }) => api.simulacoes(`${debounced}.00`, signal),
    placeholderData: keepPreviousData,
    initialData: debounced === calculada ? base : undefined,
  });
  const dados = sim.data ?? base;
  const por = Object.fromEntries(dados.estrategias.map((e) => [e.metodo, e])) as Record<Metodo, Estrategia>;
  const escolhida = por[metodo]!;
  const economica = por.AVALANCHE!;

  const piso = reaisInteiros(base.compromisso_minimo_mes);
  const min = Math.max(50, Math.floor((piso * 0.8) / 50) * 50);
  const referencia = Math.max(calculada, base.capacidade_minima ? reaisInteiros(base.capacidade_minima) : 0, piso);
  const max = Math.max(Math.ceil((referencia * 2) / 50) * 50, min + 500);

  const ativar = useMutation({
    mutationFn: () => api.ativarPlano(metodo, paraDecimal(centavos(reais * 100))),
    onSuccess: async () => {
      await Promise.all(chavesFinanceiras.map((k) => qc.invalidateQueries({ queryKey: k })));
      navigate('/inicio');
    },
  });

  const converge = escolhida.converge;
  const recalculando = reais !== debounced || sim.isPlaceholderData || sim.isFetching;

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-2xl font-bold text-navy">{copy.titulo}</h1>
        <p className="mt-1 text-slate">{copy.subtitulo}</p>
      </div>

      {/* Slider de capacidade — a data se move em tempo real (requisito, não enfeite) */}
      <Card className="flex flex-col gap-3">
        <label htmlFor="capacidade" className="font-semibold text-navy">
          {copy.slider}
        </label>
        <p className="text-4xl font-bold text-navy tabular">{brl(centavos(reais * 100), { semCentavos: true })}</p>
        <input
          id="capacidade"
          type="range"
          min={min}
          max={max}
          step={PASSO_REAIS}
          value={Math.min(Math.max(reais, min), max)}
          onChange={(e) => setReais(Number(e.target.value))}
          aria-valuetext={`${brl(centavos(reais * 100), { semCentavos: true })} por mês`}
          className="h-11 w-full cursor-pointer accent-purple"
        />
        <p className="text-sm text-slate">
          {calculada > 0 ? copy.sliderAjuda(base.capacidade_calculada.valor) : copy.sliderSemHistorico}
        </p>
        {calculada > 0 && reais !== calculada && (
          <Button variante="fantasma" className="self-start px-0" onClick={() => setReais(calculada)}>
            {copy.voltarCalculado}
          </Button>
        )}
        {/* aria-live nos recálculos do slider (§10). Enquanto recalcula, o valor
            anterior fica esmaecido — nunca apresentado como atual. */}
        <p
          aria-live="polite"
          aria-busy={recalculando}
          className={cx('font-semibold transition-opacity', converge ? 'text-purple' : 'text-amber-ink', recalculando && 'opacity-40')}
        >
          {converge && escolhida.data_quitacao
            ? `${copy.livreEm} ${mesAno(escolhida.data_quitacao)} (${meses(escolhida.meses)})`
            : copyRaioX.naoConverge(centavos(reais * 100), base.capacidade_minima)}
        </p>
      </Card>

      {/* A frase de comparação faz o trabalho — não a tabela */}
      {converge && economica.converge && (
        <p className="text-lg leading-snug text-ink">
          {fraseComparacao(
            { metodo, meses: escolhida.meses, juros: escolhida.juros_totais, primeira: escolhida.primeira_quitacao_mes },
            { meses: economica.meses, juros: economica.juros_totais, primeira: economica.primeira_quitacao_mes },
          )}
        </p>
      )}

      <fieldset className="flex flex-col gap-3">
        <legend className="sr-only">Escolha o caminho</legend>
        {(['AVALANCHE', 'EQUILIBRADO', 'SNOWBALL'] as Metodo[]).map((m) => (
          <StrategyCard
            key={m}
            e={por[m]!}
            selecionado={metodo === m}
            sugerido={base.pre_selecionado === m}
            onSelecionar={() => setMetodo(m)}
          />
        ))}
        <p className="text-sm text-slate">
          {copy.motivo[base.motivo_pre_selecao]} {copy.escolha}
        </p>
      </fieldset>

      {converge && (
        <Card className="flex flex-col gap-3">
          <h2 className="font-semibold text-navy">{copy.trajetoria}</h2>
          <Suspense fallback={<div className="h-56 animate-pulse rounded-xl bg-light" />}>
            <TrajectoryChart estrategias={dados.estrategias} selecionado={metodo} />
          </Suspense>
          <p className="text-xs text-slate">{copy.trajetoriaAjuda}</p>
        </Card>
      )}

      {converge && escolhida.so_minimo && (
        <Card tom="progresso" className="flex flex-col gap-3">
          <h2 className="font-semibold text-green-ink">{copy.jurosEvitados}</h2>
          <p className="text-sm text-ink">
            {copy.soMinimo(
              escolhida.so_minimo.juros_no_horizonte,
              escolhida.so_minimo.saldo_no_horizonte,
              escolhida.so_minimo.meses,
              escolhida.juros_totais,
              escolhida.so_minimo.converge,
            )}
          </p>
          <JurosEvitados
            plano={escolhida.juros_totais}
            soMinimo={escolhida.so_minimo.juros_no_horizonte}
            rotuloPlano={`Pelo plano (${metodoNome[metodo].curto})`}
            rotuloMinimo={`Só os mínimos, em ${meses(escolhida.so_minimo.meses)}`}
          />
        </Card>
      )}

      {converge && (
        <Card className="flex flex-col gap-2">
          <h2 className="font-semibold text-navy">{copy.cronograma}</h2>
          <ol className="flex flex-col divide-y divide-line">
            {escolhida.itens.map((i) => (
              <li key={i.divida_id} className="flex items-center justify-between gap-3 py-2">
                <div className="min-w-0">
                  <p className="truncate font-medium text-ink">
                    {i.ordem + 1}. {i.descricao}
                  </p>
                  {i.mes_quitacao && <p className="text-xs text-slate">{copy.morreNo(i.mes_quitacao)}</p>}
                </div>
                <Money valor={i.valor_mensal} semCentavos className="shrink-0 text-sm font-semibold text-navy" />
              </li>
            ))}
          </ol>
          <p className="text-xs text-slate">Valor de cada uma no primeiro mês.</p>
        </Card>
      )}

      <p className="text-xs text-slate">{copy.projecaoAviso}</p>
      {ativar.isError && (
        <p role="alert" className="text-sm text-amber-ink">
          {erroConexao(ativar.error instanceof ApiError ? ativar.error.codigo : null)}
        </p>
      )}
      <Button largo onClick={() => ativar.mutate()} disabled={!converge || ativar.isPending}>
        {ativar.isPending ? copy.ativando : copy.ativar}
      </Button>
    </div>
  );
}

function StrategyCard({
  e,
  selecionado,
  sugerido,
  onSelecionar,
}: {
  e: Estrategia;
  selecionado: boolean;
  sugerido: boolean;
  onSelecionar: () => void;
}) {
  const nome = metodoNome[e.metodo];
  return (
    <label
      className={cx(
        'flex cursor-pointer flex-col gap-2 rounded-2xl border-2 bg-white p-4 transition-colors',
        selecionado ? 'border-purple bg-purple-soft' : 'border-line',
      )}
    >
      <div className="flex items-center gap-3">
        <input
          type="radio"
          name="metodo"
          checked={selecionado}
          onChange={onSelecionar}
          className="h-5 w-5 accent-purple"
        />
        <span aria-hidden="true" className="h-3 w-3 rounded-full" style={{ background: COR_METODO[e.metodo] }} />
        <span className="font-semibold text-navy">{nome.titulo}</span>
        {sugerido && (
          <Badge tom="plano" icone={Icone.estrela}>
            {copy.recomendado}
          </Badge>
        )}
      </div>
      <p className="text-sm text-slate">{nome.logica}</p>
      {e.converge ? (
        <dl className="grid grid-cols-3 gap-2 text-sm">
          <div>
            <dt className="text-slate">{copy.livreEm}</dt>
            <dd className="font-semibold text-ink">{meses(e.meses)}</dd>
          </div>
          <div>
            <dt className="text-slate">{copy.juros}</dt>
            <dd className="font-semibold text-ink">
              <Money valor={e.juros_totais} semCentavos />
            </dd>
          </div>
          <div>
            <dt className="text-slate">1ª vitória</dt>
            <dd className="font-semibold text-ink">{e.primeira_quitacao_mes ? ordinalMes(e.primeira_quitacao_mes) : '—'}</dd>
          </div>
        </dl>
      ) : (
        <p className="text-sm font-semibold text-amber-ink">Com esse valor, este caminho não termina.</p>
      )}
    </label>
  );
}
