import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router';

import { Button, Carregando, EstadoErro } from '@/components/ui';
import { chaves } from '@/hooks/queries';
import { api } from '@/lib/api';
import { licao as copy } from '@/lib/copy';

/** Microlição — conteúdo estático curado, casado por regra (F5). */
export default function Licao() {
  const { slug = '' } = useParams();
  const navigate = useNavigate();
  const q = useQuery({ queryKey: chaves.licao(slug), queryFn: () => api.licao(slug), staleTime: Infinity });
  if (q.isLoading) return <Carregando />;
  if (q.isError || !q.data) return <EstadoErro onTentar={() => void q.refetch()} />;
  return (
    <article className="flex flex-col gap-4">
      <p className="text-sm font-semibold uppercase tracking-wide text-purple">{copy.titulo}</p>
      <h1 className="text-2xl font-bold text-navy">{q.data.titulo}</h1>
      {q.data.corpo.split('\n\n').map((p) => (
        <p key={p} className="leading-relaxed text-ink">
          {p}
        </p>
      ))}
      <Button variante="secundario" className="self-start" onClick={() => navigate(-1)}>
        {copy.voltar}
      </Button>
    </article>
  );
}
