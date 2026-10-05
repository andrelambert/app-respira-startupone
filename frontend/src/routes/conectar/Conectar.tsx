import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router';

import { LogoBanco, NaoMovimenta } from '@/components/respira';
import { Button, Card, Carregando, Icone, LinkBotao } from '@/components/ui';
import { useConfig, useConsentimentos, useUsuario } from '@/hooks/queries';
import { api, ApiError } from '@/lib/api';
import { abrirAbaVazia, ouvirConexao } from '@/lib/conexao';
import { conectar, erroConexao } from '@/lib/copy';

type Estado =
  | { tipo: 'inicio' }
  | { tipo: 'abrindo' }
  | { tipo: 'aguardando'; id: number; aba: Window | null }
  | { tipo: 'bloqueado'; id: number; url: string }
  | { tipo: 'erro'; codigo: string | null };

/** Etapa 3 — Conexão (§9). Ponto de maior atrito do funil. */
export default function Conectar() {
  const { data: usuario, isLoading } = useUsuario();
  if (isLoading) return <Carregando />;
  if (!usuario) return <Navigate to="/entrar" replace />;
  return <Fluxo demo={usuario.demo} />;
}

function Fluxo({ demo }: { demo: boolean }) {
  const { data: config } = useConfig();
  const semBelvo = !demo && config !== undefined && !config.belvo_configurada;
  const [params] = useSearchParams();
  const reconectar = params.get('reconectar') || undefined;
  const [estado, setEstado] = useState<Estado>({ tipo: 'inicio' });
  const navigate = useNavigate();
  const { data: consentimentos = [] } = useConsentimentos();
  const ativos = consentimentos.filter((c) => c.status === 'ATIVO');

  function onConectar() {
    // Síncrono no clique: abre a aba ANTES de buscar o token (§7.3).
    const aba = abrirAbaVazia(conectar.abrindo);
    setEstado({ tipo: 'abrindo' });
    api
      .widgetToken(reconectar)
      .then(({ consentimento_id, widget_url }) => {
        if (aba) {
          aba.location.href = widget_url;
          setEstado({ tipo: 'aguardando', id: consentimento_id, aba });
        } else {
          setEstado({ tipo: 'bloqueado', id: consentimento_id, url: widget_url });
        }
      })
      .catch((e: unknown) => {
        aba?.close();
        setEstado({ tipo: 'erro', codigo: e instanceof ApiError ? e.codigo : null });
      });
  }

  if (estado.tipo === 'aguardando' || estado.tipo === 'bloqueado') {
    return (
      <Aguardando
        id={estado.id}
        urlBloqueada={estado.tipo === 'bloqueado' ? estado.url : null}
        onCancelar={() => {
          if (estado.tipo === 'aguardando') estado.aba?.close();
          setEstado({ tipo: 'inicio' });
        }}
        onErro={(codigo) => setEstado({ tipo: 'erro', codigo })}
        onSucesso={() => navigate('/raiox')}
      />
    );
  }

  return (
    <div className="flex flex-col gap-5 pt-2">
      {/* O elemento mais visível da tela, acima de qualquer outro texto. */}
      <NaoMovimenta grande />
      <div>
        <h1 className="text-2xl font-bold text-navy">{conectar.titulo}</h1>
        <p className="mt-2 text-ink">{conectar.explicacao}</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Card>
          <h2 className="mb-2 font-semibold text-navy">{conectar.oQueLemos}</h2>
          <ul className="flex flex-col gap-1 text-sm">
            {conectar.lemos.map((t) => (
              <li key={t} className="flex gap-2">
                <span className="mt-0.5 text-green-ink">{Icone.check}</span>
                {t}
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <h2 className="mb-2 font-semibold text-navy">{conectar.oQueNao}</h2>
          <ul className="flex flex-col gap-1 text-sm">
            {conectar.naoFazemos.map((t) => (
              <li key={t} className="flex gap-2">
                <span className="mt-0.5 text-navy">{Icone.cadeado}</span>
                {t}
              </li>
            ))}
          </ul>
        </Card>
      </div>
      <p className="text-sm text-slate">{conectar.revogar}</p>

      {semBelvo && estado.tipo !== 'erro' && (
        <Card tom="atencao" className="flex items-start gap-2" as="div">
          <span className="mt-0.5 text-amber-ink">{Icone.alerta}</span>
          <p className="text-sm text-amber-ink">{erroConexao('belvo_nao_configurada')}</p>
        </Card>
      )}

      {estado.tipo === 'erro' && (
        <Card tom="atencao" className="flex items-start gap-2" as="div">
          <span className="mt-0.5 text-amber-ink">{Icone.alerta}</span>
          <p role="alert" className="text-sm text-amber-ink">
            {erroConexao(estado.codigo)}
          </p>
        </Card>
      )}

      {ativos.length > 0 && (
        <Card tom="progresso" as="div">
          <p className="flex items-center gap-2 font-semibold text-green-ink">
            {Icone.check}
            {conectar.conectados(ativos.length)}
          </p>
          <ul className="mt-2 flex flex-wrap gap-3">
            {ativos.map((c) => (
              <li key={c.id} className="flex items-center gap-2 text-sm text-ink">
                <LogoBanco nome={c.instituicao} logo={c.instituicao_logo} tamanho="p" />
                {c.instituicao}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="flex flex-col gap-2">
        <Button largo onClick={onConectar} disabled={estado.tipo === 'abrindo'}>
          {ativos.length ? conectar.ctaOutro : conectar.cta}
        </Button>
        <p className="text-center text-sm text-slate">{conectar.umPorVez}</p>
        {ativos.length > 0 && (
          <LinkBotao to="/raiox" variante="secundario" largo>
            {conectar.seguir}
          </LinkBotao>
        )}
      </div>

      {/* Sempre presente: o que não trafega pelo banco entra por cadastro assistido. */}
      <Link to="/dividas/nova" className="min-h-toque text-center text-sm font-semibold text-blue underline">
        {conectar.manual}
      </Link>
    </div>
  );
}

function Aguardando({
  id,
  urlBloqueada,
  onCancelar,
  onErro,
  onSucesso,
}: {
  id: number;
  urlBloqueada: string | null;
  onCancelar: () => void;
  onErro: (codigo: string | null) => void;
  onSucesso: () => void;
}) {
  const [verificou, setVerificou] = useState(false);
  const callbacks = useRef({ onErro, onSucesso });
  callbacks.current = { onErro, onSucesso };

  // 1) Aviso da aba nova (BroadcastChannel / storage).
  useEffect(
    () =>
      ouvirConexao((msg) => {
        if (msg.tipo === 'sucesso') callbacks.current.onSucesso();
        else if (msg.tipo === 'saida' || msg.fatal) callbacks.current.onErro(msg.codigo);
      }),
    [],
  );

  // 2) Fonte de verdade: o backend, a cada 5 s (o usuário pode fechar a aba na mão).
  const coleta = useQuery({
    queryKey: ['coleta', id],
    queryFn: () => api.coleta(id),
    refetchInterval: 5000,
  });
  useEffect(() => {
    const c = coleta.data;
    if (!c) return;
    if (c.status === 'ATIVO') callbacks.current.onSucesso();
    if (c.status === 'ERRO') callbacks.current.onErro(c.erro_codigo);
  }, [coleta.data]);

  return (
    <div className="flex flex-col gap-5 pt-4" aria-live="polite">
      {urlBloqueada ? (
        <Card tom="acao" className="flex flex-col gap-3">
          <h1 className="text-xl font-bold text-navy">{conectar.popupBloqueado.titulo}</h1>
          <p>{conectar.popupBloqueado.texto}</p>
          {/* Um clique direto num link nunca é bloqueado. */}
          <a
            href={urlBloqueada}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-toque items-center justify-center rounded-xl bg-blue px-5 font-semibold text-white"
          >
            {conectar.popupBloqueado.link}
          </a>
        </Card>
      ) : (
        <div>
          <h1 className="text-2xl font-bold text-navy">{conectar.aguardando.titulo}</h1>
          <p className="mt-2 text-ink">{conectar.aguardando.texto}</p>
        </div>
      )}
      <NaoMovimenta />
      {verificou && !coleta.isFetching && coleta.data?.status === 'PENDENTE' && (
        <p className="text-sm text-slate">{conectar.aguardando.naoChegou}</p>
      )}
      <div className="flex flex-col gap-2">
        <Button
          largo
          onClick={() => {
            setVerificou(true);
            void coleta.refetch();
          }}
          disabled={coleta.isFetching}
        >
          {coleta.isFetching ? conectar.aguardando.verificando : conectar.aguardando.concluido}
        </Button>
        <Button largo variante="secundario" onClick={onCancelar}>
          {conectar.aguardando.cancelar}
        </Button>
      </div>
    </div>
  );
}
