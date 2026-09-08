import { useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Card } from '../ui/Card';
import { useFilters } from '../../context/FiltersContext';
import { CHART_AXIS_TICK, CHART_TOOLTIP_STYLE } from '../../lib/palette';

type Mode = 'delegation' | 'imada';

export function AdminDivisionChart() {
  const { filteredEvents, filters, toggleDelegation, toggleImada } = useFilters();
  const [mode, setMode] = useState<Mode>('delegation');

  const activeSet = mode === 'delegation' ? filters.delegations : filters.imadas;
  const toggle = mode === 'delegation' ? toggleDelegation : toggleImada;

  const data = useMemo(() => {
    const counts = new Map<string, number>();
    for (const e of filteredEvents) {
      const value = mode === 'delegation' ? e.parsed.locationDelegation : e.parsed.locationImada;
      if (!value) continue;
      counts.set(value, (counts.get(value) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 12);
  }, [filteredEvents, mode]);

  return (
    <Card
      title={mode === 'delegation' ? 'عدد الحوادث حسب المعتمدية' : 'عدد الحوادث حسب العمادة'}
      subtitle="أعلى 12 · اضغط عمودًا للتصفية"
      action={
        <div className="flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.02] p-0.5 text-xs">
          <button
            onClick={() => setMode('delegation')}
            className={`rounded-full px-2.5 py-1 transition ${
              mode === 'delegation' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            المعتمدية
          </button>
          <button
            onClick={() => setMode('imada')}
            className={`rounded-full px-2.5 py-1 transition ${
              mode === 'imada' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            العمادة
          </button>
        </div>
      }
    >
      {data.length === 0 ? (
        <p className="py-10 text-center text-sm text-slate-500">
          لا توجد بيانات {mode === 'delegation' ? 'معتمدية' : 'عمادة'} مذكورة صراحة في الحوادث الحالية
        </p>
      ) : (
        <ResponsiveContainer width="100%" height="100%" minHeight={280}>
          <BarChart data={data} margin={{ top: 4, right: 8, bottom: 40, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ ...CHART_AXIS_TICK, fontSize: 10 }}
              interval={0}
              angle={-35}
              textAnchor="end"
              height={60}
              axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
              tickLine={false}
            />
            <YAxis tick={CHART_AXIS_TICK} allowDecimals={false} axisLine={false} tickLine={false} />
            <Tooltip
              cursor={{ fill: 'rgba(255,255,255,0.04)' }}
              contentStyle={CHART_TOOLTIP_STYLE}
              labelStyle={{ color: '#e7ecf5' }}
            />
            <Bar
              dataKey="count"
              radius={[8, 8, 0, 0]}
              cursor="pointer"
              maxBarSize={40}
              onClick={(entry) => {
                const name = (entry as unknown as { name: string }).name;
                toggle(name);
              }}
            >
              {data.map((d) => (
                <Cell
                  key={d.name}
                  fill={activeSet.has(d.name) ? '#67e8f9' : '#22d3ee'}
                  opacity={activeSet.size === 0 || activeSet.has(d.name) ? 1 : 0.3}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
