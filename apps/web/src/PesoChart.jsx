import { CartesianGrid, Cell, ComposedChart, Line, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from "recharts";
import { capturedLabel, isTestReading, weightValue } from "./readings.js";

const REAL = "#176575";
const TEST = "#b7791f";
const OUTLIER = "#c0392b";

const dateLabel = (value) => new Intl.DateTimeFormat("es-MX", { day: "numeric", month: "short" }).format(value);
const colorOf = (row) => row.isOutlier ? OUTLIER : row.isTest ? TEST : REAL;
function WeightTooltip({ active, payload }) {
  const reading = payload?.[0]?.payload;
  if (!active || !reading) return null;
  return <div className="weight-tooltip" role="status" aria-live="polite">
    <p>{capturedLabel(reading.captured_at)}</p>
    <strong>{weightValue(reading.weight_kg)} <small>kg</small></strong>
    <p>{reading.device_id}</p>
    {reading.isOutlier && <p className="trend-outlier-label">Lectura atípica: revisar</p>}
    {reading.isTest && <p className="dashboard-test">Lectura de prueba</p>}
  </div>;
}

export default function PesoChart({ rows, mode, outliers }) {
  const data = rows.map((row) => {
    const isOutlier = outliers.has(row.event_id);
    return { ...row, timestamp: Date.parse(row.captured_at), isTest: isTestReading(row), isOutlier,
      // La línea sigue la tendencia; el atípico queda como punto suelto.
      trend_kg: isOutlier ? null : row.weight_kg, outlier_kg: isOutlier ? row.weight_kg : null };
  });
  // Una prueba nunca debe parecer peso real: mismo trazo, punto en otro color.
  // El atípico no tiene punto de línea (trend_kg nulo): lo dibuja el Scatter.
  const dot = ({ cx, cy, payload }) => payload.isOutlier ? <g key={payload.event_id} /> :
    <circle key={payload.event_id} cx={cx} cy={cy} r={4} fill="#fff" strokeWidth={2} stroke={colorOf(payload)} />;
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
        {mode === 'points' ? <Scatter name="Peso" dataKey="weight_kg" fill={REAL} isAnimationActive={false}>
          {data.map((row) => <Cell key={row.event_id} fill={colorOf(row)} />)}
        </Scatter> : <>
          <Line name="Peso" type="linear" dataKey="trend_kg" stroke={REAL} strokeWidth={2.5} connectNulls
            dot={dot} activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2 }} isAnimationActive={false} />
          <Scatter name="Atípico" dataKey="outlier_kg" fill={OUTLIER} isAnimationActive={false} />
        </>}
      </ComposedChart>
    </ResponsiveContainer>
  </div>;
}
