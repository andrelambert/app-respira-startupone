import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router';

import { Button, Card, Icone } from '@/components/ui';
import { chaves, useConfig } from '@/hooks/queries';
import { api, ApiError, type Usuario } from '@/lib/api';
import { entrar as copy, erroConexao } from '@/lib/copy';

/** Atalho para quem quer testar (e para a banca): entra na conta fictícia da
 *  Juliana. Aparece na landing e no Entrar; some se a demo estiver desligada.
 *  A demo vai direto ao Raio-X — os dados chegam em segundo plano e a tela de
 *  espera mostra o progresso. ``destino`` só existe quando há um "volta". */
export function DemoJuliana({ destino = '/raiox' }: { destino?: string }) {
  const { data: config } = useConfig();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const demo = useMutation({
    mutationFn: api.entrarDemo,
    onSuccess: (u: Usuario) => {
      qc.clear(); // nada do usuário anterior fica em cache
      qc.setQueryData(chaves.usuario, u);
      navigate(destino, { replace: true });
    },
  });

  if (!config?.demo_disponivel) return null;
  const erro = demo.error instanceof ApiError ? demo.error.codigo : demo.error ? 'padrao' : null;

  return (
    <Card as="div" className="flex flex-col gap-2 border-dashed">
      <h2 className="font-semibold text-navy">{copy.demoTitulo}</h2>
      <p className="text-sm text-slate">{copy.demoTexto}</p>
      <Button variante="secundario" onClick={() => demo.mutate()} disabled={demo.isPending}>
        {copy.demo}
      </Button>
      {erro && (
        <p role="alert" className="flex items-center gap-2 text-sm text-rose-ink">
          {Icone.alerta}
          {copy.erros[erro] ?? erroConexao(erro)}
        </p>
      )}
    </Card>
  );
}
