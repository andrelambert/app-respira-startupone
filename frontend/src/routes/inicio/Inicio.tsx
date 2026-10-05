import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, Navigate } from 'react-router';

import {
  AlertBanner,
  AtualizadoEm,
  AvisosConsentimento,
  MilestoneBadge,
  PayoffDate,
} from '@/components/respira';
import {
  Badge,
  BarraProgresso,
  Button,
  Card,
  Carregando,
  EstadoErro,
  EstadoVazio,
  Icone,
  LinkBotao,
  Money,
} from '@/components/ui';
import {
  chaves,
  chavesFinanceiras,
  useConsentimentos,
  useEventos,
  usePlanoAtivo,
  useUsuario,
  useVisaoGeral,
} from '@/hooks/queries';
import { api, type PlanoAtivo } from '@/lib/api';
import { fraseAcompanhamento, inicio as copy, pfm as copyPfm, raiox as copyRaioX } from '@/lib/copy';
import { nomeMes } from '@/lib/datas';

const COPILOTO_LIGADO = import.meta.env.VITE_FEATURE_COPILOTO === 'true';

/** Etapa 6 — Execução (§9). Responde "quando isso acaba" logo no topo. */
export default function Inicio() {
  const { data: usuario, isLoading } = useUsuario();
  const plano = usePlanoAtivo();
  const eventos = useEventos();
  const consentimentos = useConsentimentos();
  const visao = useVisaoGeral();

  if (isLoading || plano.isLoading) return <Carregando />;
  if (!usuario) return <Navigate to="/entrar" replace />;
  if (plano.isError) return <EstadoErro onTentar={() => void plano.refetch()} />;

  const lista = consentimentos.data ?? [];
  const syncs = lista.map((c) => c.ultima_sync_em).filter((v): v is string => Boolean(v)).sort();
  const pendentes = (eventos.data ?? []).filter((e) => !e.notificado_em && e.tipo !== 'DIVIDA_QUITADA');
  const marcos = (eventos.data ?? []).filter((e) => e.tipo === 'DIVIDA_QUITADA');

  return (
    <div className="flex flex-col gap-5">
      <AvisosConsentimento consentimentos={lista} />
      <h1 className="text-xl font-semibold text-navy">{copy.saudacao(usuario.apelido)}</h1>

      {plano.data ? (
        <ComPlano p={plano.data} />
      ) : visao.data && visao.data.bancos.length > 0 && visao.data.qtd_dividas === 0 ? (
        <EstadoVazio
          titulo={copyPfm.semDividas.titulo}
          texto={copyPfm.semDividas.texto}
          acao={<LinkBotao to="/contas">{copyPfm.verContas}</LinkBotao>}
        />
      ) : (
        <EstadoVazio
          titulo={copy.semPlano.titulo}
          texto={copy.semPlano.texto}
          acao={<LinkBotao to="/raiox">{copy.semPlano.cta}</LinkBotao>}
        />
      )}

      {visao.data && visao.data.bancos.length > 0 && (
        <Link to="/contas" className="grid grid-cols-2 gap-3">
          <Card as="div">
            <p className="text-sm text-slate">{copyPfm.emConta}</p>
            <Money valor={visao.data.saldo_em_contas} className="text-xl font-bold text-navy" />
          </Card>
          <Card as="div">
            <p className="text-sm text-slate">{copyPfm.faturasAbertas}</p>
            <Money valor={visao.data.faturas_em_aberto} className="text-xl font-bold text-navy" />
          </Card>
        </Link>
      )}

      {pendentes.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="font-semibold text-navy">{copy.alertas}</h2>
          <ul className="flex flex-col gap-2">
            {pendentes.map((e) => (
              <AlertBanner key={e.id} evento={e} />
            ))}
          </ul>
        </section>
      )}

      {plano.data && (
        <section className="flex flex-col gap-2">
          <h2 className="font-semibold text-navy">{copy.marcos}</h2>
          {marcos.length ? (
            <ul className="flex flex-col gap-2">
              {marcos.map((e) => (
                <MilestoneBadge key={e.id} evento={e} />
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate">{copy.semMarcos}</p>
          )}
        </section>
      )}

      {plano.data && plano.data.acompanhamentos.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="font-semibold text-navy">{copy.historico}</h2>
          <ul className="flex flex-col divide-y divide-line rounded-2xl border border-line bg-white">
            {[...plano.data.acompanhamentos].reverse().map((a) => (
              <li key={a.mes_referencia} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                <span className="font-medium capitalize text-ink">{nomeMes(a.mes_referencia)}</span>
                <span className="text-slate">{copy.previstoRealizado(a.realizado, a.previsto)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {usuario.demo && <PainelDemo comPlano={Boolean(plano.data && plano.data.divida_atual > 0)} />}

      <Card as="div" className="flex flex-col gap-1 opacity-80">
        <p className="flex items-center gap-2 font-semibold text-navy">
          {copy.copiloto} <Badge>em breve</Badge>
        </p>
        <p className="text-sm text-slate">{copy.copilotoEmBreve}</p>
        <Button variante="secundario" disabled={!COPILOTO_LIGADO} className="mt-2 self-start">
          Perguntar
        </Button>
      </Card>

      <AtualizadoEm iso={syncs[0]} />
    </div>
  );
}

function ComPlano({ p }: { p: PlanoAtivo }) {
  const proj = p.projecao_atual;
  const ultimo = p.acompanhamentos.at(-1);
  if (p.divida_atual <= 0) {
    return (
      <Card tom="progresso" className="flex flex-col gap-2">
        <p className="flex items-center gap-2 text-2xl font-bold text-green-ink">
          {Icone.estrela}
          {copy.concluido.titulo}
        </p>
        <p>{copy.concluido.texto}</p>
      </Card>
    );
  }
  const primeiraExtra = p.este_mes.find((i) => !i.e_minimo);
  return (
    <>
      <Card tom="plano" className="flex flex-col gap-3">
        {proj.converge && proj.data_quitacao ? (
          <PayoffDate data={proj.data_quitacao} mesesRestantes={proj.meses} rotulo={copy.livreEm} />
        ) : (
          <p className="font-semibold text-amber-ink">{copyRaioX.naoConverge(p.capacidade_mensal, null)}</p>
        )}
        <BarraProgresso pct={Number(p.progresso_pct)} rotulo="Quanto da dívida já foi pago" />
        <p className="text-sm text-slate">{copy.abatido(p.abatido, p.divida_inicial)}</p>
      </Card>

      {ultimo && (
        <Card tom={ultimo.realizado < ultimo.previsto ? 'atencao' : 'progresso'} as="div">
          <p className="text-sm text-ink">
            {fraseAcompanhamento({
              mes: ultimo.mes_referencia,
              previsto: ultimo.previsto,
              realizado: ultimo.realizado,
              dataAnterior: ultimo.data_quitacao_anterior,
              dataNova: ultimo.data_quitacao_nova,
            })}
          </p>
        </Card>
      )}

      <section className="flex flex-col gap-2">
        <h2 className="font-semibold text-navy">{copy.esteMes}</h2>
        <p className="text-sm text-slate">{copy.esteMesAjuda}</p>
        <ol className="flex flex-col divide-y divide-line rounded-2xl border border-line bg-white">
          {p.este_mes.map((i) => (
            <li key={i.divida_id} className="flex items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0">
                <p className="truncate font-medium text-ink">{i.descricao}</p>
                <p className="flex flex-wrap items-center gap-2 text-xs text-slate">
                  {i.dia_vencimento && <span>dia {i.dia_vencimento}</span>}
                  {i === primeiraExtra ? <Badge tom="plano">{copy.principal}</Badge> : i.e_minimo && <span>{copy.minimo}</span>}
                </p>
              </div>
              <Money valor={i.valor} className="shrink-0 font-semibold text-navy" />
            </li>
          ))}
        </ol>
      </section>
    </>
  );
}

function PainelDemo({ comPlano }: { comPlano: boolean }) {
  const qc = useQueryClient();
  const atualizar = () =>
    Promise.all([...chavesFinanceiras, chaves.usuario].map((k) => qc.invalidateQueries({ queryKey: k })));
  const avancar = useMutation({ mutationFn: (dificil: boolean) => api.demoAvancarMes(dificil), onSuccess: atualizar });
  const reiniciar = useMutation({ mutationFn: api.demoReiniciar, onSuccess: atualizar });
  const ocupado = avancar.isPending || reiniciar.isPending;
  return (
    <Card as="div" className="flex flex-col gap-3 border-dashed">
      <p className="font-semibold text-navy">{copy.demo.titulo}</p>
      {comPlano && (
        <>
          <p className="text-sm text-slate">{copy.demo.texto}</p>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button variante="secundario" onClick={() => avancar.mutate(false)} disabled={ocupado}>
              {copy.demo.seguir}
            </Button>
            <Button variante="secundario" onClick={() => avancar.mutate(true)} disabled={ocupado}>
              {copy.demo.dificil}
            </Button>
          </div>
        </>
      )}
      <p className="text-sm text-slate">{copy.demo.reiniciarAjuda}</p>
      <Button variante="fantasma" className="self-start" onClick={() => reiniciar.mutate()} disabled={ocupado}>
        {copy.demo.reiniciar}
      </Button>
    </Card>
  );
}
