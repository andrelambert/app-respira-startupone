import { useEffect } from 'react';
import { useRouteError } from 'react-router';

import { Button, Icone } from '@/components/ui';
import { erroRota as copy } from '@/lib/copy';
import { ehFalhaDeChunk, podeRecarregar } from '@/lib/recarga';

/**
 * Tela própria para erro de rota (A3, Fase 7) — no lugar da tela técnica do
 * React Router. Importada direto (não lazy): precisa existir justamente quando
 * um chunk não carrega.
 */
export default function ErroRota() {
  const erro = useRouteError();
  const recarregarSozinho = ehFalhaDeChunk(erro) && podeRecarregar();

  useEffect(() => {
    if (recarregarSozinho) window.location.reload();
  }, [recarregarSozinho]);

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-4 p-6">
      <div role="alert" className="flex flex-col items-start gap-3 rounded-2xl border border-line bg-white p-6">
        <h1 className="flex items-center gap-2 text-lg font-semibold text-navy">
          <span className="text-amber">{Icone.alerta}</span>
          {copy.titulo}
        </h1>
        <p className="text-slate">{copy.texto}</p>
        <Button onClick={() => window.location.reload()}>{copy.recarregar}</Button>
        <a href="/inicio" className="font-semibold text-blue underline-offset-2 hover:underline">
          {copy.inicio}
        </a>
      </div>
    </main>
  );
}
