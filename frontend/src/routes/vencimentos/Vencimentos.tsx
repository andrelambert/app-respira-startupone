import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router';

import { ListaVencimentos } from '@/components/respira/ListaVencimentos';
import { Carregando, EstadoErro, cx } from '@/components/ui';
import { chaves } from '@/hooks/queries';
import { api } from '@/lib/api';
import { vencimentos as copy } from '@/lib/copy';

/** Próximos vencimentos (N3, F-5 "não sei quando vence cada coisa"). A janela fica na URL. */
export default function Vencimentos() {
  const [params, setParams] = useSearchParams();
  const pedido = Number(params.get('dias'));
  const dias = copy.janelas.includes(pedido) ? pedido : 30;
  const q = useQuery({
    queryKey: chaves.vencimentos(dias),
    queryFn: () => api.vencimentos(dias),
    placeholderData: keepPreviousData,
  });

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold text-navy">{copy.titulo}</h1>
        <p className="mt-1 text-sm text-slate">{copy.ajuda}</p>
      </div>
      <div role="group" aria-label="Vencimentos nos próximos" className="flex gap-2">
        {copy.janelas.map((d) => (
          <button
            key={d}
            type="button"
            aria-pressed={dias === d}
            onClick={() => setParams(d === 30 ? {} : { dias: String(d) }, { replace: true })}
            className={cx(
              'min-h-toque rounded-full border px-4 text-sm font-semibold',
              dias === d ? 'border-navy bg-navy text-white' : 'border-line bg-white text-navy',
            )}
          >
            {copy.janela(d)}
          </button>
        ))}
      </div>
      {q.isLoading ? (
        <Carregando />
      ) : q.isError || !q.data ? (
        <EstadoErro onTentar={() => void q.refetch()} />
      ) : q.data.itens.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-line bg-white p-4 text-sm text-slate">{copy.vazio(dias)}</p>
      ) : (
        <div className={cx('transition-opacity', q.isPlaceholderData && 'opacity-50')} aria-busy={q.isFetching}>
          <ListaVencimentos itens={q.data.itens} />
        </div>
      )}
    </div>
  );
}
