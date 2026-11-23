import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import type { FluxoMensal } from '@/lib/api';
import { fluxo as copy } from '@/lib/copy';
import { nomeMes } from '@/lib/datas';
import { COR_FLUXO } from '@/lib/cores';
import { brl, centavos, type Centavos } from '@/lib/money';


/** Gráfico do N5 (carregado sob demanda: Recharts fica fora do bundle inicial). */
export default function FluxoChart({ meses }: { meses: FluxoMensal['meses'] }) {
  // Coordenadas em reais só para o desenho; nenhuma conta de dinheiro aqui.
  const dados = meses.map((m) => ({
    mes: nomeMes(m.mes).slice(0, 3),
    entradas: m.entradas / 100,
    essenciais: m.essenciais / 100,
    outros: m.outros_gastos / 100,
    divida: m.pagamentos_divida / 100,
    sobra: m.sobra / 100,
  }));
  return (
    <div className="h-60 w-full" role="img" aria-label={copy.titulo}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={dados} margin={{ top: 8, right: 4, bottom: 0, left: 0 }} barGap={1} barCategoryGap="18%">
          <CartesianGrid stroke="#E2E8F0" vertical={false} />
          <XAxis dataKey="mes" tickLine={false} axisLine={{ stroke: '#E2E8F0' }} tick={{ fill: '#64748B', fontSize: 12 }} />
          <YAxis
            width={44}
            tickLine={false}
            axisLine={false}
            tick={{ fill: '#64748B', fontSize: 12 }}
            tickFormatter={(v: number) => (v === 0 ? '0' : `${Math.round(v / 1000)} mil`)}
          />
          <Tooltip
            formatter={(v, nome) => [
              brl(centavos(Math.round(Number(v) * 100)) as Centavos, { semCentavos: true }),
              copy.series[nome as keyof typeof copy.series] ?? String(nome),
            ]}
            contentStyle={{ borderRadius: 12, borderColor: '#E2E8F0', fontSize: 13 }}
          />
          {/* Um stackId por grupo: o Recharts desenha os grupos na ordem declarada. */}
          <Bar dataKey="entradas" stackId="entradas" fill={COR_FLUXO.entradas} radius={[3, 3, 0, 0]} />
          <Bar dataKey="essenciais" stackId="gastos" fill={COR_FLUXO.essenciais} />
          <Bar dataKey="outros" stackId="gastos" fill={COR_FLUXO.outros} radius={[3, 3, 0, 0]} />
          <Bar dataKey="divida" stackId="divida" fill={COR_FLUXO.divida} radius={[3, 3, 0, 0]} />
          <Line dataKey="sobra" type="monotone" stroke={COR_FLUXO.sobra} strokeWidth={2.5} dot={{ r: 3 }} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
