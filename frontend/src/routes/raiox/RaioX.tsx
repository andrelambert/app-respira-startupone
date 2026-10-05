import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router';

import {
  AtualizadoEm,
  AvisosConsentimento,
  DebtCard,
  DebtComposition,
  PayoffDate,
  corPorCusto,
} from '@/components/respira';
import {
  BarraIndeterminada,
  Badge,
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
import { chaves, chavesFinanceiras, useConsentimentos, useUsuario } from '@/hooks/queries';
import { api, type Consentimento, type Divida, type RaioX as TRaioX } from '@/lib/api';
import {
  alertaMinimo,
  alertaMinimoProximo,
  coleta as copyColeta,
  conectar,
  divida as copyDivida,
  fraseRaioX,
  metodoNome,
  pfm,
  raiox as copy,
} from '@/lib/copy';
import { percentual } from '@/lib/money';

const LIMITE_ESPERA_MS = 3 * 60 * 1000;

/** Etapa 4 — Diagnóstico (§9). O momento de verdade. */
export default function RaioX() {
  const { data: usuario, isLoading: carregandoUsuario } = useUsuario();
  const [coletando, setColetando] = useState(false);
  const raiox = useQuery({
    queryKey: chaves.raiox,
    queryFn: api.raiox,
    enabled: Boolean(usuario),
    refetchInterval: coletando ? 5000 : false,
  });
  const consentimentos = useConsentimentos(coletando);
  useEffect(() => setColetando(Boolean(raiox.data?.coleta_em_andamento)), [raiox.data?.coleta_em_andamento]);

  if (carregandoUsuario) return <Carregando />;
  if (!usuario) return <Navigate to="/entrar" replace />;
  if (raiox.isLoading) return <Carregando />;
  if (raiox.isError || !raiox.data) return <EstadoErro onTentar={() => void raiox.refetch()} />;

  const r = raiox.data;
  const lista = consentimentos.data ?? [];
  const algumaConcluida = lista.some((c) => c.status === 'ATIVO' && c.coleta_concluida);

  // Nunca "R$ 0,00" no lugar de "ainda buscando" (§7.5).
  if (r.coleta_em_andamento && (!algumaConcluida || r.qtd_dividas === 0)) {
    return <EsperaColeta consentimentos={lista} />;
  }
  if (r.qtd_dividas === 0) {
    return lista.some((c) => c.status === 'ATIVO') ? (
      <EstadoVazio
        titulo={copy.vazio.titulo}
        texto={copy.vazio.texto}
        acao={
          <div className="flex flex-wrap gap-2">
            <LinkBotao to="/contas">{pfm.verContas}</LinkBotao>
            <LinkBotao to="/dividas/nova" variante="secundario">
              {conectar.manual}
            </LinkBotao>
          </div>
        }
      />
    ) : (
      <EstadoVazio
        titulo={copy.semConexao.titulo}
        texto={copy.semConexao.texto}
        acao={<LinkBotao to="/conectar">{conectar.cta}</LinkBotao>}
      />
    );
  }
  return <Diagnostico r={r} consentimentos={lista} />;
}

function Diagnostico({ r, consentimentos }: { r: TRaioX; consentimentos: Consentimento[] }) {
  const p = r.projecao;
  return (
    <div className="flex flex-col gap-5">
      <AvisosConsentimento consentimentos={consentimentos} />
      {r.coleta_em_andamento && (
        <div className="flex flex-col gap-2" aria-live="polite">
          <p className="text-sm text-slate">{copyColeta.titulo}</p>
          <BarraIndeterminada rotulo={copyColeta.titulo} />
        </div>
      )}

      {/* 1. Total consolidado */}
      <section aria-labelledby="total">
        <h1 id="total" className="text-base font-medium text-slate">
          {copy.voceDeve}
        </h1>
        <p className="text-5xl font-bold leading-none text-navy">
          <Money valor={r.divida_total} semCentavos />
        </p>
        <p className="mt-1 text-slate">{copy.emCompromissos(r.qtd_dividas)}</p>
      </section>

      {/* 2. Lista por custo efetivo (compacta: a data precisa caber sem rolar em 360 px) */}
      <section aria-label={copy.listaTitulo}>
        <ul className="divide-y divide-line rounded-2xl border border-line bg-white">
          {r.dividas.map((d, i) => (
            <LinhaDivida key={d.id} d={d} cor={corPorCusto(i)} />
          ))}
        </ul>
      </section>

      {/* 3. Data de quitação, na mesma tela */}
      <Card tom="plano" className="flex flex-col gap-1">
        {p.converge && p.data_quitacao ? (
          <>
            <PayoffDate data={p.data_quitacao} mesesRestantes={p.meses} rotulo={copy.saiEm} tamanho="medio" />
            <p className="text-sm text-slate">
              {copy.projecao} {copy.porMes(p.capacidade)} · caminho {metodoNome[p.metodo].curto}
            </p>
          </>
        ) : r.capacidade.meses_historico === 0 && p.capacidade <= 0 ? (
          <p className="text-ink">{copy.semHistorico}</p>
        ) : (
          <p className="font-semibold text-ink">{copy.naoConverge(p.capacidade, r.capacidade_minima)}</p>
        )}
      </Card>

      {/* 4. A frase do custo */}
      <p className="text-lg leading-snug text-ink">
        {fraseRaioX({
          total: r.divida_total,
          qtd: r.qtd_dividas,
          jurosMes: r.juros_mes_estimado,
          maiorValor: r.maior_fonte_juros_valor,
          maiorModalidade: r.maior_fonte_juros?.modalidade ?? null,
        })}
      </p>

      {/* 5. O alerta do mínimo — o insight mais valioso, nunca implícito */}
      {r.divida_cresce && (
        <Card tom="fato" as="div" className="flex flex-col gap-1">
          <p className="flex items-start gap-2 font-semibold text-rose-ink">
            <span className="mt-1">{Icone.alerta}</span>
            {alertaMinimo(r.crescimento_mensal)}
          </p>
          <p className="text-sm text-ink">
            {alertaMinimoProximo}{' '}
            <Link to="/licoes/so-o-minimo" className="font-semibold text-blue underline">
              Entenda
            </Link>
          </p>
        </Card>
      )}

      {/* 6. CTA único */}
      <LinkBotao to="/plano" largo>
        {copy.cta}
      </LinkBotao>

      <AtualizadoEm iso={r.atualizado_em} />

      {/* Detalhes, abaixo da dobra */}
      <DebtComposition dividas={r.dividas} />
      {r.comprometimento_renda_pct && r.capacidade.entradas && (
        <p className="text-sm text-slate">
          {copy.comprometimento(r.compromisso_minimo_mes, r.capacidade.entradas, r.comprometimento_renda_pct)}
        </p>
      )}
      <ul className="flex flex-col gap-3">
        {r.dividas.map((d, i) => (
          <DebtCard key={d.id} d={d} cor={corPorCusto(i)} />
        ))}
      </ul>
      <Link to="/dividas/nova" className="min-h-toque text-center text-sm font-semibold text-blue underline">
        {conectar.manual}
      </Link>
    </div>
  );
}

function LinhaDivida({ d, cor }: { d: Divida; cor: string }) {
  const cara = Number(d.taxa_anual.split('.')[0]) >= 100;
  return (
    <li className="flex items-center gap-3 px-3 py-2">
      <span aria-hidden="true" className="h-8 w-1.5 shrink-0 rounded-full" style={{ background: cor }} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <span className="truncate font-semibold text-navy">{d.descricao}</span>
          <Money valor={d.saldo} semCentavos className="font-semibold text-navy" />
        </div>
        <div className="flex flex-wrap items-center gap-x-2 text-xs text-slate">
          <span className={cx('font-semibold', cara ? 'text-rose-ink' : 'text-ink')}>
            {percentual(d.taxa_anual, 0)} a.a.
          </span>
          {d.taxa_estimada && (
            <Badge tom="estimada" title={copyDivida.estimadaAjuda}>
              {copyDivida.estimada}
            </Badge>
          )}
          <span>
            mín. <Money valor={d.parcela_minima} semCentavos />
          </span>
          {d.dia_vencimento && <span>dia {d.dia_vencimento}</span>}
          {d.em_atraso_dias > 0 && (
            <span className="font-semibold text-rose-ink">{copyDivida.atraso(d.em_atraso_dias)}</span>
          )}
        </div>
      </div>
    </li>
  );
}

function EsperaColeta({ consentimentos }: { consentimentos: Consentimento[] }) {
  const [inicio] = useState(() => Date.now());
  const [agora, setAgora] = useState(() => Date.now());
  const qc = useQueryClient();
  useEffect(() => {
    const t = window.setInterval(() => setAgora(Date.now()), 5000);
    return () => window.clearInterval(t);
  }, []);
  const sync = useMutation({
    mutationFn: api.sync,
    onSettled: () => chavesFinanceiras.forEach((k) => void qc.invalidateQueries({ queryKey: k })),
  });
  const demorou = agora - inicio > LIMITE_ESPERA_MS;
  const emColeta = consentimentos.filter((c) => c.status === 'ATIVO' && !c.coleta_concluida);

  return (
    <div className="flex flex-col gap-5 pt-4" aria-live="polite">
      {demorou ? (
        <Card tom="atencao" className="flex flex-col gap-3">
          <h1 className="text-xl font-bold text-navy">{copyColeta.demorou.titulo}</h1>
          <p>{copyColeta.demorou.texto}</p>
          <Button onClick={() => sync.mutate()} disabled={sync.isPending}>
            {copyColeta.demorou.recarregar}
          </Button>
        </Card>
      ) : (
        <>
          <h1 className="text-2xl font-bold leading-tight text-navy">{copyColeta.titulo}</h1>
          <p className="text-ink">{copyColeta.texto}</p>
          <BarraIndeterminada rotulo={copyColeta.titulo} />
        </>
      )}
      {emColeta.map((c) => (
        <Card key={c.id} as="div">
          <p className="mb-2 font-semibold text-navy">{c.instituicao}</p>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
            {c.coleta
              .filter((r) => r.recurso !== 'OWNERS')
              .map((r) => (
                <li key={r.recurso} className={cx('flex items-center gap-1', r.status === 'RECEBIDO' ? 'text-green-ink' : 'text-slate')}>
                  {r.status === 'RECEBIDO' ? Icone.check : Icone.relogio}
                  {copyColeta.recursos[r.recurso] ?? r.recurso}
                  {r.status === 'AGUARDANDO' && '…'}
                  {r.status === 'INDISPONIVEL' && ' (indisponível)'}
                </li>
              ))}
          </ul>
        </Card>
      ))}
    </div>
  );
}
