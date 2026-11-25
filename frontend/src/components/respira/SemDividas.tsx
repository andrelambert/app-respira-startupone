import { Card, Icone, LinkBotao } from '@/components/ui';
import { conectar, pfm as copy } from '@/lib/copy';

/**
 * Banco conectado e nenhuma dívida aberta: é uma boa notícia, não um "conecte
 * seu banco" (teste com conta real, Fase 7). Mesmo estado no Raio-X, nas
 * Dívidas, no Plano e no Início.
 */
export function SemDividas() {
  return (
    <Card tom="progresso" as="div" className="flex flex-col items-start gap-3">
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-green/15 text-green-ink [&>svg]:h-5 [&>svg]:w-5">
        {Icone.check}
      </span>
      <h2 className="text-lg font-semibold text-navy">{copy.semDividas.titulo}</h2>
      <p className="text-ink">{copy.semDividas.texto}</p>
      <div className="flex flex-wrap gap-2">
        <LinkBotao to="/contas">{copy.verContas}</LinkBotao>
        <LinkBotao to="/dividas/nova" variante="secundario">
          {conectar.manual}
        </LinkBotao>
      </div>
    </Card>
  );
}
