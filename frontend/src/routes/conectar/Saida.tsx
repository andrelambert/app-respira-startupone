import { useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router';

import { Button, Card, LinkBotao } from '@/components/ui';
import { api } from '@/lib/api';
import { avisarAbaOriginal } from '@/lib/conexao';
import { erroConexao } from '@/lib/copy';

/** Só códigos seguros seguem para o backend e para a tela; nada de texto livre do banco. */
export function codigoSeguro(v: string | null): string | null {
  if (!v) return null;
  const limpo = v.replace(/[^A-Za-z0-9_.-]/g, '').slice(0, 80);
  return limpo || null;
}

/** Callback de saída — "não deu certo desta vez", com o motivo em português (§7.4). */
export default function Saida() {
  const [params] = useSearchParams();
  const codigo = codigoSeguro(params.get('last_encountered_error_code'));
  const etapa = codigoSeguro(params.get('meta_data_step'));
  const banco = params.get('meta_data_institution_name');
  const enviado = useRef(false);

  useEffect(() => {
    if (enviado.current) return;
    enviado.current = true;
    avisarAbaOriginal({ tipo: 'saida', codigo });
    void api.saida({ codigo: codigo ?? undefined, etapa: etapa ?? undefined, fatal: true }).catch(() => {});
  }, [codigo, etapa]);

  return (
    <Card tom="atencao" className="mt-6 flex flex-col gap-3">
      <h1 className="text-xl font-bold text-navy">Não deu certo desta vez{banco ? ` com o ${banco.slice(0, 60)}` : ''}</h1>
      <p role="alert">{erroConexao(codigo)}</p>
      <LinkBotao to="/conectar">Tentar de novo</LinkBotao>
      <Button variante="fantasma" onClick={() => window.close()}>
        Fechar esta aba
      </Button>
    </Card>
  );
}
