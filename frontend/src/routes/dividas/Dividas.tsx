import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';

import { LogoBanco } from '@/components/respira';
import { SemDividas } from '@/components/respira/SemDividas';
import {
  Badge,
  BarraProgresso,
  Card,
  Carregando,
  EstadoErro,
  EstadoVazio,
  Icone,
  LinkBotao,
  Money,
  cx,
} from '@/components/ui';
import { chaves, useConsentimentos, useHoje, usePlanoAtivo } from '@/hooks/queries';
import { api, type Divida, type PlanoAtivo } from '@/lib/api';
import { conectar, divida as copyDivida, dividas as copy, modalidade } from '@/lib/copy';
import { inicioDoMesMais, mesAno } from '@/lib/datas';
import {
  escreverFiltrosDividas,
  filtrarDividas,
  lerFiltrosDividas,
  SEM_FILTRO,
  temFiltro,
  type FiltrosDividas,
  type OrdemDividas,
  type Situacao,
  type TipoDivida,
} from '@/lib/filtrosDividas';
import { soma, sub } from '@/lib/money';

/** Taxa a partir da qual a taxa aparece como fato de custo alto (mesma regra do DebtCard). */
const TAXA_ANUAL_ALTA = 100;

/**
 * Todas as dívidas, por credor: o que a pessoa deve, em que contrato, e o papel
 * de cada uma no plano. O Raio-X responde "quanto e quando"; esta tela responde
 * "o quê, onde e em que ordem".
 */
export default function Dividas() {
  // Abertas e quitadas: o filtro "Quitadas" (N4) usa as segundas.
  const dividas = useQuery({ queryKey: [...chaves.dividas, 'todas'], queryFn: () => api.dividas(true) });
  const plano = usePlanoAtivo();
  const consentimentos = useConsentimentos();
  const hoje = useHoje();
  const [params, setParams] = useSearchParams();
  const filtros = lerFiltrosDividas(params);
  const aplicar = (f: FiltrosDividas) => setParams(escreverFiltrosDividas(f), { replace: true });

  if (dividas.isLoading || consentimentos.isLoading) return <Carregando />;
  if (dividas.isError || !dividas.data) return <EstadoErro onTentar={() => void dividas.refetch()} />;

  const lista = dividas.data.filter((d) => d.saldo > 0);
  if (lista.length === 0 && filtros.situacao !== 'quitadas') {
    if ((consentimentos.data ?? []).some((c) => c.status === 'ATIVO')) return <SemDividas />;
    return (
      <EstadoVazio
        titulo={copy.vazio.titulo}
        texto={copy.vazio.texto}
        acao={
          <div className="flex flex-wrap gap-2">
            <LinkBotao to="/conectar">{conectar.cta}</LinkBotao>
            <LinkBotao to="/dividas/nova" variante="secundario">
              {conectar.manual}
            </LinkBotao>
          </div>
        }
      />
    );
  }

  const p = plano.data ?? null;
  const ordemPlano = new Map((p?.cronograma ?? []).map((i) => [i.divida_id, i.ordem]));
  const filtradas = filtrarDividas(dividas.data, filtros, { ordemPlano, hoje });
  const ordem = filtros.ordem ?? (ordemPlano.size > 0 ? 'plano' : 'banco');
  const grupos = agruparPorCredor(filtradas);
  const bancos = [...new Set(dividas.data.map((d) => d.instituicao))].sort((a, b) => a.localeCompare(b, 'pt-BR'));
  const quitadas = dividas.data.length - lista.length;

  return (
    <div className="flex flex-col gap-5">
      <section aria-labelledby="titulo-dividas">
        <h1 id="titulo-dividas" className="text-base font-medium text-slate">
          {copy.titulo}
        </h1>
        {/* Total de todas as abertas: o mesmo número do Raio-X (A17), com ou sem filtro. */}
        <p className="text-4xl font-bold leading-tight text-navy">
          <Money valor={soma(lista.map((d) => d.saldo))} semCentavos />
        </p>
        <p className="mt-1 text-sm text-slate">
          {copy.resumo(lista.length, new Set(lista.map((d) => d.instituicao)).size, soma(lista.map((d) => d.parcela_minima)))}
        </p>
        <p className="mt-2 text-sm text-slate">
          {copy.explicacao}
          <Link to="/raiox" className="font-semibold text-blue underline">
            {copy.explicacaoLink}
          </Link>
          .
        </p>
      </section>

      <ResumoPlano plano={p} carregando={plano.isLoading} />

      <PainelFiltros filtros={filtros} aplicar={aplicar} ordem={ordem} temPlano={ordemPlano.size > 0} bancos={bancos} />

      {temFiltro(filtros) && (
        <p className="text-sm text-slate" aria-live="polite">
          {copy.mostrando(
            filtradas.length,
            filtros.situacao === 'quitadas' ? quitadas : lista.length,
            soma(filtradas.map((d) => d.saldo)),
          )}
        </p>
      )}

      {filtradas.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-line bg-white p-4 text-sm text-slate">{copy.nenhumaNoFiltro}</p>
      ) : ordem === 'banco' ? (
        grupos.map((g) => (
          <section key={g.credor} aria-label={g.credor} className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <LogoBanco nome={g.credor} logo={g.logo} />
              <h2 className="min-w-0 flex-1 truncate font-semibold text-navy">{g.credor}</h2>
              <Money valor={g.total} semCentavos className="shrink-0 font-semibold text-navy" />
            </div>
            <ul className="flex flex-col gap-3">
              {g.dividas.map((d) => (
                <CartaoDivida key={d.id} d={d} plano={p} />
              ))}
            </ul>
          </section>
        ))
      ) : (
        <ul className="flex flex-col gap-3" aria-label={copy.ordens[ordem]}>
          {filtradas.map((d) => (
            <CartaoDivida key={d.id} d={d} plano={p} mostrarBanco />
          ))}
        </ul>
      )}

      <Link to="/dividas/nova" className="min-h-toque text-center text-sm font-semibold text-blue underline">
        {conectar.manual}
      </Link>
    </div>
  );
}

/** N4: ordem sempre visível; filtros num painel recolhível. */
function PainelFiltros({
  filtros,
  aplicar,
  ordem,
  temPlano,
  bancos,
}: {
  filtros: FiltrosDividas;
  aplicar: (f: FiltrosDividas) => void;
  ordem: OrdemDividas;
  temPlano: boolean;
  bancos: string[];
}) {
  const ordens: OrdemDividas[] = temPlano
    ? ['plano', 'taxa', 'saldo', 'vencimento', 'banco']
    : ['banco', 'taxa', 'saldo', 'vencimento'];
  const alternar = <T,>(xs: T[], v: T) => (xs.includes(v) ? xs.filter((x) => x !== v) : [...xs, v]);
  const qtd = filtros.bancos.length + filtros.tipos.length + (filtros.situacao ? 1 : 0);
  // Aberto se a URL já trouxe filtros; depois, só a pessoa fecha (desmarcar o
  // último filtro não pode recolher o painel no meio do uso).
  const [aberto, setAberto] = useState(qtd > 0);
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-2 text-sm text-slate">
          {copy.ordenar}
          <select
            value={ordem}
            onChange={(e) => aplicar({ ...filtros, ordem: e.target.value as OrdemDividas })}
            className="min-h-toque rounded-lg border border-line bg-white px-2 text-sm text-navy"
          >
            {ordens.map((o) => (
              <option key={o} value={o}>
                {copy.ordens[o]}
              </option>
            ))}
          </select>
        </label>
        {qtd > 0 && (
          <button
            type="button"
            onClick={() => aplicar({ ...SEM_FILTRO, ordem: filtros.ordem })}
            className="min-h-toque px-2 text-sm font-semibold text-blue underline"
          >
            {copy.limpar}
          </button>
        )}
      </div>
      <details
        className="rounded-2xl border border-line bg-white"
        open={aberto}
        onToggle={(e) => setAberto(e.currentTarget.open)}
      >
        <summary className="flex min-h-toque cursor-pointer items-center px-4 text-sm font-semibold text-navy">
          {copy.filtrar}
          {qtd > 0 ? ` (${qtd})` : ''}
        </summary>
        <div className="flex flex-col gap-3 px-4 pb-4">
          <Grupo titulo={copy.situacao}>
            {(['atraso', 'estimada', 'quitadas'] as Situacao[]).map((sit) => (
              <Opcao
                key={sit}
                ativo={filtros.situacao === sit}
                onClick={() => aplicar({ ...filtros, situacao: filtros.situacao === sit ? null : sit })}
              >
                {copy.situacoes[sit]}
              </Opcao>
            ))}
          </Grupo>
          <Grupo titulo={copy.tipo}>
            {(['cartao', 'emprestimo', 'financiamento', 'cheque', 'manual'] as TipoDivida[]).map((t) => (
              <Opcao key={t} ativo={filtros.tipos.includes(t)} onClick={() => aplicar({ ...filtros, tipos: alternar(filtros.tipos, t) })}>
                {copy.tipos[t]}
              </Opcao>
            ))}
          </Grupo>
          <Grupo titulo={copy.banco}>
            {bancos.map((b) => (
              <Opcao key={b} ativo={filtros.bancos.includes(b)} onClick={() => aplicar({ ...filtros, bancos: alternar(filtros.bancos, b) })}>
                {b}
              </Opcao>
            ))}
          </Grupo>
        </div>
      </details>
    </div>
  );
}

function Grupo({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div role="group" aria-label={titulo} className="flex flex-col gap-2">
      <p className="text-sm font-semibold text-navy">{titulo}</p>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  );
}

function Opcao({ ativo, onClick, children }: { ativo: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={ativo}
      onClick={onClick}
      className={cx(
        'min-h-9 rounded-full border px-3 text-sm font-semibold',
        ativo ? 'border-navy bg-navy text-white' : 'border-line bg-white text-navy',
      )}
    >
      {children}
    </button>
  );
}

function ResumoPlano({ plano, carregando }: { plano: PlanoAtivo | null; carregando: boolean }) {
  if (carregando) return null;
  const data = plano?.projecao_atual.data_quitacao;
  return (
    <Card tom="plano" className="flex flex-col gap-3">
      <p className="text-ink">{plano && data ? copy.livreEm(mesAno(data)) : copy.semPlano}</p>
      <LinkBotao to="/plano" variante={plano ? 'secundario' : 'primario'}>
        {plano ? copy.verPlano : copy.montarPlano}
      </LinkBotao>
    </Card>
  );
}

function CartaoDivida({ d, plano, mostrarBanco = false }: { d: Divida; plano: PlanoAtivo | null; mostrarBanco?: boolean }) {
  const anual = Number(d.taxa_anual.split('.')[0]);
  const item = plano?.cronograma.find((i) => i.divida_id === d.id);
  const esteMes = plano?.este_mes.find((i) => i.divida_id === d.id);
  const temContrato = d.parcelas_total !== null && d.parcelas_total > 0 && d.parcelas_pagas !== null;
  // Agrupado por banco, o banco está no título do grupo; em lista plana (N4), vai no cartão.
  const titulo = mostrarBanco ? d.descricao : semCredor(d);
  const tipo = modalidade[d.modalidade]?.nome ?? d.modalidade;
  return (
    <Card as="li" className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          {mostrarBanco && <LogoBanco nome={d.instituicao} logo={d.instituicao_logo} />}
          <div className="min-w-0">
            <h3 className="font-semibold text-navy">{titulo}</h3>
            {tipo.toLowerCase() !== titulo.toLowerCase() && <p className="text-sm text-slate">{tipo}</p>}
          </div>
        </div>
        <Money valor={d.saldo} className="shrink-0 text-lg font-bold text-navy" />
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        <span className={cx('font-semibold', anual >= TAXA_ANUAL_ALTA ? 'text-rose-ink' : 'text-ink')}>
          {copyDivida.taxaAno(d.taxa_anual)}
        </span>
        <span className="text-slate">
          {copyDivida.minimo} <Money valor={d.parcela_minima} />
        </span>
        {d.dia_vencimento && <span className="text-slate">{copyDivida.vence(d.dia_vencimento)}</span>}
      </div>

      {temContrato && (
        <div className="flex flex-col gap-1">
          <div className="flex items-baseline justify-between gap-2 text-sm">
            <span className="text-ink">{copy.parcelasPagas(d.parcelas_pagas!, d.parcelas_total!)}</span>
            {d.contrato_fim && <span className="text-xs text-slate">{copy.terminaEm(mesAno(d.contrato_fim))}</span>}
          </div>
          <BarraProgresso pct={(d.parcelas_pagas! / d.parcelas_total!) * 100} rotulo={copy.progresso} sobreBranco />
          {d.valor_contratado !== null && (
            <span className="text-xs text-slate">{copy.contratado(d.valor_contratado)}</span>
          )}
        </div>
      )}

      {/* Estado sempre com ícone + texto, nunca só cor (§10). */}
      <div className="flex flex-wrap gap-2">
        {d.em_atraso_dias > 0 && (
          <Badge tom="fato" icone={Icone.relogio}>
            {copyDivida.atraso(d.em_atraso_dias)}
          </Badge>
        )}
        {d.cresce_no_minimo && (
          <Badge tom="fato" icone={Icone.alerta}>
            {copyDivida.cresce(sub(d.juros_mes, d.parcela_minima))}
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

      {item && plano && (
        <p className="flex flex-wrap gap-x-2 border-t border-line pt-2 text-sm">
          <span className="font-semibold text-purple">{copy.ordem(item.ordem + 1)}</span>
          {esteMes && <span className="text-ink">{copy.esteMes(esteMes.valor)}</span>}
          {item.mes_quitacao && (
            <span className="text-slate">{copy.quitadaEm(mesAno(inicioDoMesMais(plano.hoje, item.mes_quitacao)))}</span>
          )}
        </p>
      )}

      <div className="flex flex-wrap gap-x-4">
        {d.conta_id && (
          <Link to={`/contas/${d.conta_id}`} className="min-h-toque py-2 text-sm font-semibold text-blue">
            {copy.verExtrato}
          </Link>
        )}
        {(d.taxa_estimada || d.parcela_estimada || d.origem === 'MANUAL') && (
          <Link to={`/dividas/${d.id}`} className="min-h-toque py-2 text-sm font-semibold text-blue">
            {copyDivida.conferir}
          </Link>
        )}
      </div>
    </Card>
  );
}

/** "Fatura parcelada Itaú" → "Fatura parcelada" (o credor aparece no título do grupo). */
function semCredor(d: Divida): string {
  const sufixo = ` ${d.instituicao}`;
  return d.descricao.endsWith(sufixo) ? d.descricao.slice(0, -sufixo.length) : d.descricao;
}

type Grupo = { credor: string; logo: string | null; total: ReturnType<typeof soma>; dividas: Divida[] };

/** Por credor, do maior saldo ao menor; dentro de cada um, da taxa mais cara à mais barata. */
function agruparPorCredor(lista: Divida[]): Grupo[] {
  const mapa = new Map<string, Divida[]>();
  for (const d of lista) mapa.set(d.instituicao, [...(mapa.get(d.instituicao) ?? []), d]);
  return [...mapa.entries()]
    .map(([credor, ds]) => ({
      credor,
      logo: ds.find((d) => d.instituicao_logo)?.instituicao_logo ?? null,
      total: soma(ds.map((d) => d.saldo)),
      dividas: [...ds].sort((a, b) => Number(b.taxa_mes) - Number(a.taxa_mes)),
    }))
    .sort((a, b) => b.total - a.total);
}
