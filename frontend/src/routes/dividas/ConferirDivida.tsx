import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router';

import { DebtCard } from '@/components/respira';
import { Button, Campo, Carregando, EstadoErro, EstadoVazio, LinkBotao } from '@/components/ui';
import { chaves, chavesFinanceiras } from '@/hooks/queries';
import { api } from '@/lib/api';
import { corrigir as copy, manual } from '@/lib/copy';
import { sanitizarDinheiro, sanitizarPercentual } from '@/lib/entrada';
import { deEntradaUsuario, paraDecimal } from '@/lib/money';

/** Corrige o que o banco não entrega (parcela/taxa estimadas). */
export default function ConferirDivida() {
  const { id } = useParams();
  const dividas = useQuery({ queryKey: chaves.dividas, queryFn: api.dividas });
  const d = dividas.data?.find((x) => String(x.id) === id);
  const [parcela, setParcela] = useState('');
  const [taxa, setTaxa] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const qc = useQueryClient();
  const navigate = useNavigate();
  const salvar = useMutation({
    mutationFn: (dados: { parcela?: string; taxa_mes_percentual?: string }) => api.atualizarDivida(Number(id), dados),
    onSuccess: async () => {
      await Promise.all(chavesFinanceiras.map((k) => qc.invalidateQueries({ queryKey: k })));
      navigate('/raiox');
    },
  });

  if (dividas.isLoading) return <Carregando />;
  if (dividas.isError) return <EstadoErro onTentar={() => void dividas.refetch()} />;
  if (!d) return <EstadoVazio titulo="Dívida não encontrada" texto="Ela pode ter sido quitada ou removida." acao={<LinkBotao to="/raiox">Raio-X</LinkBotao>} />;

  function enviar() {
    const dados: { parcela?: string; taxa_mes_percentual?: string } = {};
    if (parcela) {
      const c = deEntradaUsuario(parcela);
      if (c === null || c <= 0) return setErro(manual.erros.valor);
      dados.parcela = paraDecimal(c);
    }
    if (taxa) {
      const n = Number(taxa.replace(',', '.'));
      if (!/^\d{1,2}([.,]\d{1,4})?$/.test(taxa) || n < 0.1 || n > 20) return setErro(manual.erros.taxa);
      dados.taxa_mes_percentual = taxa.replace(',', '.');
    }
    setErro(null);
    if (Object.keys(dados).length) salvar.mutate(dados);
  }

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-bold text-navy">{copy.titulo}</h1>
      <ul>
        <DebtCard d={d} />
      </ul>
      <p className="text-sm text-slate">{copy.ajuda}</p>
      {d.parcela_estimada && (
        <Campo name="parcela" rotulo={copy.parcela} inputMode="decimal" placeholder="R$ 0,00" value={parcela} onChange={(e) => setParcela(sanitizarDinheiro(e.target.value))} />
      )}
      {d.taxa_estimada && (
        <Campo name="taxa" rotulo={copy.taxa} ajuda={manual.taxaAjuda} inputMode="decimal" placeholder="3,5" value={taxa} onChange={(e) => setTaxa(sanitizarPercentual(e.target.value))} />
      )}
      {erro && (
        <p role="alert" className="text-sm text-amber-ink">
          {erro}
        </p>
      )}
      <Button largo onClick={enviar} disabled={salvar.isPending}>
        {copy.salvar}
      </Button>
    </div>
  );
}
