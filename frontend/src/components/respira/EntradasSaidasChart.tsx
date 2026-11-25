import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { COR_FLUXO } from '@/lib/cores';
import { mesAno, nomeMes } from '@/lib/datas';
import { brl, centavos, type Centavos } from '@/lib/money';

import type { TipoFluxo } from './EntradasSaidas';

// Entradas em verde, saídas em vermelho — como os botões (teste com conta real).
const COR_SAIDAS = '#E11D48';

/** Gráfico de entradas ou saídas (carregado sob demanda: Recharts fica fora do bundle inicial). */
export default function EntradasSaidasChart({
  valores,
  tipo,
  rotulo,
  onEscolher,
}: {
  valores: { mes: string; valor: Centavos }[];
  tipo: TipoFluxo;
  rotulo: string;
  onEscolher: (mes: string) => void;
}) {
  // Coordenadas em reais só para o desenho; nenhuma conta de dinheiro aqui.
  const dados = valores.map((v) => ({
    mes: v.mes,
    rotulo: `${nomeMes(v.mes).slice(0, 3)}${valores.length > 6 ? '' : `/${v.mes.slice(2, 4)}`}`,
    valor: v.valor / 100,
  }));
  return (
    <div className="h-52 w-full" role="img" aria-label={rotulo}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={dados} margin={{ top: 8, right: 4, bottom: 0, left: 0 }} barCategoryGap="20%">
          <CartesianGrid stroke="#E2E8F0" vertical={false} />
          <XAxis
            dataKey="rotulo"
            tickLine={false}
            axisLine={{ stroke: '#E2E8F0' }}
            tick={{ fill: '#64748B', fontSize: 11 }}
            interval={0}
          />
          <YAxis
            width={56}
            tickLine={false}
            axisLine={false}
            tick={{ fill: '#64748B', fontSize: 11 }}
            tickFormatter={(v: number) =>
              v >= 1000 ? `${(v / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mil` : String(v)
            }
          />
          {/* Valor exato, com centavos, ao passar o mouse (ou tocar). */}
          <Tooltip
            cursor={{ fill: '#F1F5F9' }}
            formatter={(v) => [brl(centavos(Math.round(Number(v) * 100)) as Centavos), '']}
            labelFormatter={(_, p) => (p?.[0] ? mesAno(String(p[0].payload.mes)) : '')}
            separator=""
            contentStyle={{ borderRadius: 12, borderColor: '#E2E8F0', fontSize: 13 }}
          />
          <Bar
            dataKey="valor"
            fill={tipo === 'entradas' ? COR_FLUXO.entradas : COR_SAIDAS}
            radius={[3, 3, 0, 0]}
            className="cursor-pointer"
            onClick={(d) => onEscolher(String((d as unknown as { mes: string }).mes))}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
