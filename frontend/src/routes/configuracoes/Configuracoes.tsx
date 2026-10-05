import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router';

import { LogoBanco, NaoMovimenta } from '@/components/respira';
import { Badge, Button, Card, Carregando, EstadoErro, Icone, LinkBotao } from '@/components/ui';
import { chavesFinanceiras, useConsentimentos, useUsuario } from '@/hooks/queries';
import { api, ApiError, type Consentimento } from '@/lib/api';
import { conectar, erroConexao, privacidade as copy } from '@/lib/copy';
import { carimbo, dataCompleta } from '@/lib/datas';

/**
 * Configurações: dados da conta + privacidade (o que é lido, revogação em um
 * toque, exclusão real — §9, §12.8).
 */
export default function Configuracoes() {
  const { data: usuario, isLoading } = useUsuario();
  const consentimentos = useConsentimentos();
  if (isLoading || consentimentos.isLoading) return <Carregando />;
  if (!usuario) return <Navigate to="/entrar" replace />;
  if (consentimentos.isError) return <EstadoErro onTentar={() => void consentimentos.refetch()} />;
  const lista = consentimentos.data ?? [];

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-2xl font-bold text-navy">{copy.titulo}</h1>
      </div>

      <Card className="flex flex-col gap-3">
        <h2 className="font-semibold text-navy">{copy.seusDados}</h2>
        <dl className="flex flex-col gap-3 text-sm">
          <Dado rotulo={copy.nome} valor={usuario.nome_completo ?? usuario.apelido} />
          <Dado rotulo={copy.email} valor={usuario.email} />
          <Dado rotulo={copy.cpf} valor={usuario.cpf_mascarado} ajuda={usuario.cpf_mascarado ? copy.cpfAjuda : undefined} />
        </dl>
      </Card>

      <div>
        <h2 className="text-lg font-bold text-navy">{copy.privacidadeTitulo}</h2>
        <p className="mt-1 text-slate">{copy.intro}</p>
      </div>
      <NaoMovimenta />

      <section className="flex flex-col gap-2">
        <h2 className="font-semibold text-navy">{copy.conexoes}</h2>
        {lista.length === 0 ? (
          <p className="text-sm text-slate">{copy.semConexoes}</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {lista.map((c) => (
              <Conexao key={c.id} c={c} />
            ))}
          </ul>
        )}
        {lista.some((c) => c.status === 'ATIVO') && <Atualizar />}
        <LinkBotao to="/conectar" variante="secundario">
          {lista.some((c) => c.status === 'ATIVO') ? conectar.ctaOutro : conectar.cta}
        </LinkBotao>
        <p className="text-sm text-slate">{copy.outrosCanais}</p>
      </section>

      <Card>
        <h2 className="mb-2 font-semibold text-navy">{copy.lemosTitulo}</h2>
        <ul className="flex flex-col gap-1 text-sm">
          {conectar.lemos.map((t) => (
            <li key={t} className="flex gap-2">
              <span className="mt-0.5 text-green-ink">{Icone.check}</span>
              {t}
            </li>
          ))}
        </ul>
        <h2 className="mb-2 mt-4 font-semibold text-navy">{copy.naoAcessamosTitulo}</h2>
        <ul className="flex flex-col gap-1 text-sm">
          {copy.naoAcessamos.map((t) => (
            <li key={t} className="flex gap-2">
              <span className="mt-0.5 text-navy">{Icone.cadeado}</span>
              {t}
            </li>
          ))}
        </ul>
      </Card>

      {usuario.demo ? <p className="text-sm text-slate">{copy.demoNaoExclui}</p> : <ExcluirConta />}
    </div>
  );
}

function Dado({ rotulo, valor, ajuda }: { rotulo: string; valor: string | null | undefined; ajuda?: string }) {
  return (
    <div>
      <dt className="text-slate">{rotulo}</dt>
      <dd className="font-medium text-ink tabular break-all">{valor || '—'}</dd>
      {ajuda && <p className="text-xs text-slate">{ajuda}</p>}
    </div>
  );
}

/** Recoleta manual — o fallback quando não há webhook (§7.5). */
function Atualizar() {
  const qc = useQueryClient();
  const sync = useMutation({
    mutationFn: api.sync,
    onSettled: () => Promise.all(chavesFinanceiras.map((k) => qc.invalidateQueries({ queryKey: k }))),
  });
  return (
    <Button variante="fantasma" className="self-start" onClick={() => sync.mutate()} disabled={sync.isPending}>
      {sync.isPending ? '…' : copy.atualizar}
    </Button>
  );
}

function Conexao({ c }: { c: Consentimento }) {
  const [confirmando, setConfirmando] = useState(false);
  const qc = useQueryClient();
  const revogar = useMutation({
    mutationFn: () => api.revogar(c.id),
    onSuccess: () => Promise.all(chavesFinanceiras.map((k) => qc.invalidateQueries({ queryKey: k }))),
  });
  const banco = c.instituicao ?? 'banco';
  const tom = c.status === 'ATIVO' ? 'progresso' : c.status === 'REVOGADO' ? 'neutro' : 'estimada';

  return (
    <Card as="li" className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-2 font-semibold text-navy">
          <LogoBanco nome={c.instituicao} logo={c.instituicao_logo} />
          {banco}
        </span>
        <Badge tom={tom}>{copy.status[c.status] ?? c.status}</Badge>
      </div>
      <p className="text-sm text-slate">
        {c.status === 'REVOGADO' && c.revogado_em
          ? `revogada em ${carimbo(c.revogado_em)}`
          : [c.expira_em && copy.expiraEm(dataCompleta(c.expira_em.slice(0, 10))), c.ultima_sync_em && copy.atualizado(carimbo(c.ultima_sync_em))]
              .filter(Boolean)
              .join(' · ')}
      </p>
      {c.status !== 'REVOGADO' &&
        (confirmando ? (
          <div className="flex flex-col gap-2 rounded-xl bg-light p-3">
            <p className="text-sm text-ink">{copy.revogarConfirma(banco)}</p>
            <div className="flex gap-2">
              <Button variante="perigo" onClick={() => revogar.mutate()} disabled={revogar.isPending}>
                {copy.revogarSim}
              </Button>
              <Button variante="secundario" onClick={() => setConfirmando(false)}>
                {copy.cancelar}
              </Button>
            </div>
          </div>
        ) : (
          <Button variante="perigo" className="self-start" onClick={() => setConfirmando(true)}>
            {copy.revogar}
          </Button>
        ))}
      {revogar.isError && (
        <p role="alert" className="text-sm text-amber-ink">
          {erroConexao(revogar.error instanceof ApiError ? revogar.error.codigo : null)}
        </p>
      )}
    </Card>
  );
}

function ExcluirConta() {
  const [confirmando, setConfirmando] = useState(false);
  const qc = useQueryClient();
  const navigate = useNavigate();
  const excluir = useMutation({
    mutationFn: api.excluirConta,
    onSuccess: () => {
      qc.clear();
      navigate('/', { replace: true });
    },
  });
  return (
    <Card className="flex flex-col gap-2">
      <h2 className="font-semibold text-navy">{copy.excluirTitulo}</h2>
      <p className="text-sm text-slate">{copy.excluirTexto}</p>
      {confirmando ? (
        <div className="flex flex-col gap-2">
          <p className="text-sm font-semibold text-ink">{copy.excluirConfirma}</p>
          <div className="flex gap-2">
            <Button variante="perigo" onClick={() => excluir.mutate()} disabled={excluir.isPending}>
              {copy.excluirSim}
            </Button>
            <Button variante="secundario" onClick={() => setConfirmando(false)}>
              {copy.cancelar}
            </Button>
          </div>
        </div>
      ) : (
        <Button variante="perigo" className="self-start" onClick={() => setConfirmando(true)}>
          {copy.excluir}
        </Button>
      )}
      {excluir.isError && (
        <p role="alert" className="text-sm text-amber-ink">
          {erroConexao(excluir.error instanceof ApiError ? excluir.error.codigo : null)}
        </p>
      )}
    </Card>
  );
}
