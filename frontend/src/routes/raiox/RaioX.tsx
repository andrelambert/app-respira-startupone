import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router';

import {
  AtualizadoEm,
  AvisosConsentimento,
  DebtComposition,
  PayoffDate,
  corPorCusto,
} from '@/components/respira';
import {
  BarraIndeterminada,
  Card,
  Carregando,
  EstadoErro,
  EstadoVazio,
  Icone,
  LinkBotao,
  Money,
  cx,
} from '@/components/ui';
import { MesQueVem } from '@/components/respira/MesQueVem';
import { SemDividas } from '@/components/respira/SemDividas';
import { EsperaColeta } from '@/components/respira/EsperaColeta';
import { chaves, useConsentimentos, useUsuario } from '@/hooks/queries';
import { api, type Consentimento, type Divida, type RaioX as TRaioX } from '@/lib/api';
import {
  alerta,
  alertaDividaCresce,
  alertaMinimo,
  alertaMinimoProximo,
  coleta as copyColeta,
  conectar,
  divida as copyDivida,
  fraseRaioX,
  metodoNome,
  raiox as copy,
} from '@/lib/copy';
import { percentual, sub } from '@/lib/money';

// Quantas linhas cabem antes da data de quitação sem rolar num celular de 360 px (§9).
// Linhas com rótulo ficaram mais altas: 4 cabem com a data na mesma tela em 360 px.
const LINHAS_NA_DOBRA = 4;

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
  // Erro só vira tela de erro quando não há nada para mostrar. Se uma consulta
  // falhar no meio da coleta (servidor reiniciando, rede oscilando), a tela de
  // espera — ou os dados — continuam, e as consultas seguem a cada 5 s.
  if (!raiox.data) return <EstadoErro onTentar={() => void raiox.refetch()} tentando={raiox.isFetching} />;

  const r = raiox.data;
  const oscilou = raiox.isError;
  const lista = consentimentos.data ?? [];
  const algumaConcluida = lista.some((c) => c.status === 'ATIVO' && c.coleta_concluida);

  // Nunca "R$ 0,00" no lugar de "ainda buscando" (§7.5).
  if (r.coleta_em_andamento && (!algumaConcluida || r.qtd_dividas === 0)) {
    return <EsperaColeta consentimentos={lista} oscilou={oscilou} />;
  }
  if (r.qtd_dividas === 0) {
    return lista.some((c) => c.status === 'ATIVO') ? (
      <div className="flex flex-col gap-5">
        <SemDividas />
        <MesQueVem />
      </div>
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
          {r.dividas.slice(0, LINHAS_NA_DOBRA).map((d, i) => (
            <LinhaDivida key={d.id} d={d} cor={corPorCusto(i)} />
          ))}
          {r.dividas.length > LINHAS_NA_DOBRA && (
            <li>
              <Link to="/dividas" className="flex min-h-toque items-center px-3 text-sm font-semibold text-blue">
                {copy.verTodas(r.dividas.length - LINHAS_NA_DOBRA)}
              </Link>
            </li>
          )}
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

      {/* 5. O alerta do mínimo — o insight mais valioso, nunca implícito. Se o total
          não cresce, a dívida que cresce sozinha (o rotativo) ganha o alerta. */}
      {!r.divida_cresce &&
        r.dividas
          .filter((d) => d.cresce_no_minimo)
          .map((d) => (
            <Card key={d.id} tom="fato" as="div" className="flex flex-col gap-1">
              <p className="flex items-start gap-2 font-semibold text-rose-ink">
                <span className="mt-1">{Icone.alerta}</span>
                {alertaDividaCresce(d.descricao, sub(d.juros_mes, d.parcela_minima))}
              </p>
              <p className="text-sm text-ink">
                {alertaMinimoProximo}{' '}
                <Link to="/licoes/so-o-minimo" className="font-semibold text-blue underline">
                  {alerta.saibaMais}
                </Link>
              </p>
            </Card>
          ))}
      {r.divida_cresce && (
        <Card tom="fato" as="div" className="flex flex-col gap-1">
          <p className="flex items-start gap-2 font-semibold text-rose-ink">
            <span className="mt-1">{Icone.alerta}</span>
            {alertaMinimo(r.crescimento_mensal)}
          </p>
          <p className="text-sm text-ink">
            {alertaMinimoProximo}{' '}
            <Link to="/licoes/so-o-minimo" className="font-semibold text-blue underline">
              {alerta.saibaMais}
            </Link>
          </p>
        </Card>
      )}

      {/* Cabe no mês que vem? A dívida não vive sozinha: fatura e gastos fixos também saem. */}
      <MesQueVem />

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
      {/* O detalhe de cada dívida (contrato, parcelas, extrato) mora na aba Dívidas. */}
      <LinkBotao to="/dividas" variante="secundario" largo>
        {copy.detalhes}
      </LinkBotao>
      <Link to="/dividas/nova" className="min-h-toque text-center text-sm font-semibold text-blue underline">
        {conectar.manual}
      </Link>
    </div>
  );
}

function LinhaDivida({ d, cor }: { d: Divida; cor: string }) {
  const cara = Number(d.taxa_anual.split('.')[0]) >= 100;
  return (
    <li className="flex items-center gap-3 px-3 py-2.5">
      <span aria-hidden="true" className="h-10 w-1.5 shrink-0 rounded-full" style={{ background: cor }} />
      <div className="min-w-0 flex-1">
        {/* Hierarquia (teste com usuária): primeiro o nome e o valor; depois os
            detalhes, menores e cada um com rótulo — juros, mínimo, vencimento. */}
        <div className="flex items-baseline justify-between gap-2">
          <span className="truncate text-base font-semibold text-navy">{d.descricao}</span>
          <Money valor={d.saldo} semCentavos className="text-lg font-bold text-navy" />
        </div>
        <dl className="mt-0.5 flex flex-wrap items-baseline gap-x-3 text-xs text-slate">
          <div className="flex items-baseline gap-1">
            <dt>{copy.rotulos.juros}</dt>
            <dd className={cx('font-semibold', cara ? 'text-rose-ink' : 'text-ink')}>
              {percentual(d.taxa_anual, 0)} {copy.rotulos.aoAno}
              {d.taxa_estimada && (
                <span className="ml-1 font-normal text-amber-ink" title={copyDivida.estimadaAjuda}>
                  ({copy.rotulos.estimada})
                </span>
              )}
            </dd>
          </div>
          <div className="flex items-baseline gap-1">
            <dt>{copy.rotulos.minimo}</dt>
            <dd className="text-ink">
              <Money valor={d.parcela_minima} semCentavos />
            </dd>
          </div>
          {d.dia_vencimento && (
            <div className="flex items-baseline gap-1">
              <dt>{copy.rotulos.vence}</dt>
              <dd className="text-ink">{copy.rotulos.dia(d.dia_vencimento)}</dd>
            </div>
          )}
        </dl>
        {d.em_atraso_dias > 0 && <p className="text-xs font-semibold text-rose-ink">{copyDivida.atraso(d.em_atraso_dias)}</p>}
      </div>
    </li>
  );
}

