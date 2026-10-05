import { useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router';

import { Card, LinkBotao } from '@/components/ui';
import { api } from '@/lib/api';
import { avisarAbaOriginal } from '@/lib/conexao';
import { erroConexao } from '@/lib/copy';
import { codigoSeguro } from './Saida';

/** Callback de evento: `error` é fatal, `warning` não (§7.4). */
export default function Evento() {
  const [params] = useSearchParams();
  const erro = codigoSeguro(params.get('error'));
  const aviso = codigoSeguro(params.get('warning'));
  const fatal = Boolean(erro);
  const codigo = erro ?? aviso;
  const enviado = useRef(false);

  useEffect(() => {
    if (enviado.current) return;
    enviado.current = true;
    avisarAbaOriginal({ tipo: 'evento', codigo, fatal });
    void api.saida({ codigo: codigo ?? undefined, etapa: 'evento', fatal }).catch(() => {});
  }, [codigo, fatal]);

  return (
    <Card tom={fatal ? 'atencao' : 'acao'} className="mt-6 flex flex-col gap-3">
      <h1 className="text-xl font-bold text-navy">{fatal ? 'A conexão foi interrompida' : 'O banco mandou um aviso'}</h1>
      <p role="alert">{erroConexao(codigo)}</p>
      <LinkBotao to="/conectar">{fatal ? 'Tentar de novo' : 'Voltar para a conexão'}</LinkBotao>
    </Card>
  );
}
