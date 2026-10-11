import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router';

import { LogoBanco } from '@/components/respira';
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
import { chaves, usePlanoAtivo } from '@/hooks/queries';
import { api, type Divida, type PlanoAtivo } from '@/lib/api';
import { conectar, divida as copyDivida, dividas as copy, modalidade } from '@/lib/copy';
import { inicioDoMesMais, mesAno } from '@/lib/datas';
import { soma, sub } from '@/lib/money';

/** Taxa a partir da qual a taxa aparece como fato de custo alto (mesma regra do DebtCard). */
const TAXA_ANUAL_ALTA = 100;

/**
 * Todas as dívidas, por credor: o que a pessoa deve, em que contrato, e o papel
 * de cada uma no plano. O Raio-X responde "quanto e quando"; esta tela responde
 * "o quê, onde e em que ordem".
 */
export default function Dividas() {
  const dividas = useQuery({ queryKey: chaves.dividas, queryFn: api.dividas });
  const plano = usePlanoAtivo();

  if (dividas.isLoading) return <Carregando />;
  if (dividas.isError || !dividas.data) return <EstadoErro onTentar={() => void dividas.refetch()} />;

  const lista = dividas.data.filter((d) => d.saldo > 0);
  if (lista.length === 0) {
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

  const grupos = agruparPorCredor(lista);
  const p = plano.data ?? null;

  return (
    <div className="flex flex-col gap-5">
      <section aria-labelledby="titulo-dividas">
        <h1 id="titulo-dividas" className="text-base font-medium text-slate">
          {copy.titulo}
        </h1>
        <p className="text-4xl font-bold leading-tight text-navy">
          <Money valor={soma(lista.map((d) => d.saldo))} semCentavos />
        </p>
        <p className="mt-1 text-sm text-slate">
          {copy.resumo(lista.length, grupos.length, soma(lista.map((d) => d.parcela_minima)))}
        </p>
      </section>

      <ResumoPlano plano={p} carregando={plano.isLoading} />

      {grupos.map((g) => (
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
      ))}

      <Link to="/dividas/nova" className="min-h-toque text-center text-sm font-semibold text-blue underline">
        {conectar.manual}
      </Link>
    </div>
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

function CartaoDivida({ d, plano }: { d: Divida; plano: PlanoAtivo | null }) {
  const anual = Number(d.taxa_anual.split('.')[0]);
  const item = plano?.cronograma.find((i) => i.divida_id === d.id);
  const esteMes = plano?.este_mes.find((i) => i.divida_id === d.id);
  const temContrato = d.parcelas_total !== null && d.parcelas_total > 0 && d.parcelas_pagas !== null;
  // O banco já está no título do grupo: no cartão, só o produto.
  const titulo = semCredor(d);
  const tipo = modalidade[d.modalidade]?.nome ?? d.modalidade;
  return (
    <Card as="li" className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-navy">{titulo}</h3>
          {tipo.toLowerCase() !== titulo.toLowerCase() && <p className="text-sm text-slate">{tipo}</p>}
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
