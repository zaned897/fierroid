import { CartesianGrid, ComposedChart, Line, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from "recharts";
import { capturedLabel, weightValue } from "./readings.js";

const dateLabel = (value) => new Intl.DateTimeFormat("es-MX", { day: "numeric", month: "short" }).format(value);
function WeightTooltip({ active, payload }) {
  const reading = payload?.[0]?.payload;
  if (!active || !reading) return null;
  return <div className="weight-tooltip" role="status" aria-live="polite">
    <p>{capturedLabel(reading.captured_at)}</p>
    <strong>{weightValue(reading.weight_kg)} <small>kg</small></strong>
    <p>{reading.device_id}</p>
  </div>;
}

export default function PesoChart({ rows, mode }) {
  const data = rows.map((row) => ({ ...row, timestamp: Date.parse(row.captured_at) }));
  return <div className="animal-chart">
    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
      <ComposedChart data={data} margin={{ top: 20, right: 16, bottom: 12, left: 0 }} accessibilityLayer
        aria-label="Evolución del peso. Usa las flechas izquierda y derecha para recorrer los pesajes.">
        <CartesianGrid vertical={false} stroke="var(--line)" strokeDasharray="3 5" />
        <XAxis dataKey="timestamp" type="number" scale="time" domain={['dataMin - 60000', 'dataMax + 60000']}
          tickFormatter={dateLabel} minTickGap={48} tickLine={false} axisLine={false} tick={{ fill: '#617873', fontSize: 12 }} />
        <YAxis width={58} domain={[(min) => Math.max(0, Math.floor(min - 5)), (max) => Math.ceil(max + 5)]}
          tickFormatter={(value) => `${value} kg`} tickLine={false} axisLine={false} tick={{ fill: '#617873', fontSize: 11 }} />
        <Tooltip content={<WeightTooltip />} cursor={{ stroke: '#799b94', strokeDasharray: '4 4' }} />
        {mode === 'points' ? <Scatter name="Peso" dataKey="weight_kg" fill="#176575" isAnimationActive={false} /> :
          <Line name="Peso" type="linear" dataKey="weight_kg" stroke="#176575" strokeWidth={2.5}
            dot={{ r: 4, fill: '#fff', strokeWidth: 2 }} activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2 }} isAnimationActive={false} />}
      </ComposedChart>
    </ResponsiveContainer>
  </div>;
}
