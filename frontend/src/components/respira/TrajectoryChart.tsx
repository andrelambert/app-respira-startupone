import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import type { Estrategia, Metodo } from '@/lib/api';
import { COR_METODO } from '@/lib/cores';
import { metodoNome } from '@/lib/copy';
import { brl, centavos, type Centavos } from '@/lib/money';

/**
 * Trajetória do saldo (§10): a linha caindo até zero, com as três estratégias
 * sobrepostas. Uma escala só (R$). As três linhas terminam juntas no zero, então
 * rótulo direto na ponta colidiria: a identidade vem da legenda + tabela.
 */
const ORDEM: Metodo[] = ['AVALANCHE', 'EQUILIBRADO', 'SNOWBALL'];

export default function TrajectoryChart({
  estrategias,
  selecionado,
}: {
  estrategias: Estrategia[];
  selecionado: Metodo;
}) {
  const por = Object.fromEntries(estrategias.map((e) => [e.metodo, e])) as Record<Metodo, Estrategia>;
  const tamanho = Math.max(...estrategias.map((e) => e.trajetoria.length));
  // Coordenadas do gráfico em reais (só desenho; nenhuma conta de dinheiro aqui).
  const dados = Array.from({ length: tamanho }, (_, mes) => {
    const linha: Record<string, number | null> = { mes };
    for (const m of ORDEM) {
      const t = por[m]?.trajetoria;
      linha[m] = t && mes < t.length ? t[mes]! / 100 : null;
    }
    return linha;
  });

  return (
    <div className="flex flex-col gap-2">
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm" aria-label="Legenda">
        {ORDEM.map((m) => (
          <li key={m} className="flex items-center gap-2 text-ink">
            <span aria-hidden="true" className="h-0.5 w-5 rounded" style={{ background: COR_METODO[m], height: m === selecionado ? 3 : 2 }} />
            {metodoNome[m].titulo}
          </li>
        ))}
      </ul>
      <div className="h-56 w-full" role="img" aria-label="Gráfico do saldo total caindo até zero em cada caminho">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={dados} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#E2E8F0" vertical={false} />
            <XAxis
              dataKey="mes"
              tickLine={false}
              axisLine={{ stroke: '#E2E8F0' }}
              tick={{ fill: '#64748B', fontSize: 12 }}
              tickFormatter={(m: number) => (m === 0 ? 'hoje' : `${m}`)}
              interval="preserveStartEnd"
              minTickGap={24}
            />
            <YAxis
              width={56}
              tickLine={false}
              axisLine={false}
              tick={{ fill: '#64748B', fontSize: 12 }}
              tickFormatter={(v: number) => (v === 0 ? '0' : `${Math.round(v / 1000)} mil`)}
            />
            <Tooltip
              formatter={(v, nome) => [
                brl(centavos(Math.round(Number(v) * 100)) as Centavos, { semCentavos: true }),
                metodoNome[nome as Metodo]?.titulo ?? String(nome),
              ]}
              labelFormatter={(m) => (m === 0 ? 'Hoje' : `${m}º mês`)}
              contentStyle={{ borderRadius: 12, borderColor: '#E2E8F0', fontSize: 13 }}
            />
            {ORDEM.map((m) => (
              <Line
                key={m}
                dataKey={m}
                type="monotone"
                stroke={COR_METODO[m]}
                strokeWidth={m === selecionado ? 3 : 2}
                strokeOpacity={m === selecionado ? 1 : 0.7}
                dot={false}
                activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }}
                connectNulls={false}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <details className="text-sm">
        <summary className="min-h-toque cursor-pointer py-2 font-semibold text-blue">Ver em tabela</summary>
        <div className="max-h-64 overflow-auto">
          <table className="w-full text-left tabular">
            <thead>
              <tr className="text-slate">
                <th className="py-1 pr-2 font-medium">Mês</th>
                {ORDEM.map((m) => (
                  <th key={m} className="py-1 pr-2 font-medium">
                    {metodoNome[m].titulo}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: tamanho }, (_, mes) => (
                <tr key={mes} className="border-t border-line">
                  <td className="py-1 pr-2">{mes === 0 ? 'Hoje' : mes}</td>
                  {ORDEM.map((m) => {
                    const t = por[m]?.trajetoria;
                    return (
                      <td key={m} className="py-1 pr-2">
                        {t && mes < t.length ? brl(t[mes]!, { semCentavos: true }) : '—'}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
