import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import type { HistoricoCategoria } from '@/lib/api';
import { nomeMes } from '@/lib/datas';
import { brl, centavos, type Centavos } from '@/lib/money';

const SELECIONADO = '#2563EB';
const OUTROS = '#94A3B8';

/**
 * Evolução de uma categoria nos últimos 12 meses (carregado sob demanda:
 * Recharts fica fora do bundle inicial). O mês escolhido fica em azul; tocar
 * numa barra escolhe aquele mês. A tabela equivalente fica na tela, para
 * leitor de tela.
 */
export default function EvolucaoChart({
  meses,
  selecionado,
  onEscolher,
  rotulo,
}: {
  meses: HistoricoCategoria['meses'];
  selecionado: string | null;
  onEscolher: (mes: string) => void;
  rotulo: string;
}) {
  // Coordenadas em reais só para o desenho; nenhuma conta de dinheiro aqui.
  const dados = meses.map((m) => ({ mes: m.mes, rotulo: nomeMes(m.mes).slice(0, 3), total: m.total / 100 }));
  return (
    <div className="h-48 w-full" role="img" aria-label={rotulo}>
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
            tickFormatter={(v: number) => (v >= 1000 ? `${(v / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mil` : String(v))}
          />
          <Tooltip
            cursor={{ fill: '#F1F5F9' }}
            formatter={(v) => [brl(centavos(Math.round(Number(v) * 100)) as Centavos), '']}
            labelFormatter={(_, p) => (p?.[0] ? nomeMes(String(p[0].payload.mes)) : '')}
            separator=""
            contentStyle={{ borderRadius: 12, borderColor: '#E2E8F0', fontSize: 13 }}
          />
          <Bar
            dataKey="total"
            radius={[3, 3, 0, 0]}
            className="cursor-pointer"
            onClick={(d) => onEscolher(String((d as unknown as { mes: string }).mes))}
          >
            {dados.map((d) => (
              <Cell key={d.mes} fill={d.mes === selecionado ? SELECIONADO : OUTROS} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
