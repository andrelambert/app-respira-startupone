import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';

import { Button, Card, Icone, LinkBotao } from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { avisarAbaOriginal } from '@/lib/conexao';
import { conectar, erroConexao } from '@/lib/copy';

/** Callback de sucesso — roda NA ABA NOVA (§7.3, §7.4). */
export default function Sucesso() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [estado, setEstado] = useState<'enviando' | 'ok' | { erro: string | null }>('enviando');
  const enviado = useRef(false);

  useEffect(() => {
    if (enviado.current) return; // StrictMode monta duas vezes em dev
    enviado.current = true;
    const link = params.get('link') ?? '';
    const institution = params.get('institution') ?? '';
    api
      .callback(link, institution)
      .then((c) => {
        avisarAbaOriginal({ tipo: 'sucesso', consentimentoId: c.id });
        setEstado('ok');
        // Só fecha se foi aberta por script; se não, o botão abaixo resolve.
        window.setTimeout(() => window.close(), 1500);
      })
      .catch((e: unknown) => setEstado({ erro: e instanceof ApiError ? e.codigo : null }));
  }, [params]);

  if (estado === 'enviando') {
    return <p role="status" className="pt-8 text-slate">{conectar.abrindo}</p>;
  }
  if (estado === 'ok') {
    return (
      <Card tom="progresso" className="mt-6 flex flex-col gap-3">
        <h1 className="flex items-center gap-2 text-2xl font-bold text-green-ink">
          {Icone.check}
          {conectar.sucessoAba.titulo}
        </h1>
        <p>{conectar.sucessoAba.texto}</p>
        <Button variante="secundario" onClick={() => navigate('/raiox')}>
          {conectar.sucessoAba.fallback}
        </Button>
      </Card>
    );
  }
  return (
    <Card tom="atencao" className="mt-6 flex flex-col gap-3">
      <h1 className="text-xl font-bold text-amber-ink">{conectar.sucessoAba.erro}</h1>
      <p role="alert">{erroConexao(estado.erro)}</p>
      <LinkBotao to="/conectar">Tentar de novo</LinkBotao>
    </Card>
  );
}
