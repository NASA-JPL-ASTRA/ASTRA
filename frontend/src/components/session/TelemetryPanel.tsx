import { useState } from 'react';
import { Activity, Maximize2, Minimize2 } from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  ReferenceLine,
} from 'recharts';
import { useStore } from '../../store/useStore';
import type { TelemetryStream } from '../../types';

function TelemetryMini({ stream }: { stream: TelemetryStream }) {
  const [expanded, setExpanded] = useState(false);
  const recentData = stream.data.slice(-60);

  const statusColor = {
    nominal: 'text-accent-green',
    warning: 'text-accent-amber',
    critical: 'text-accent-red',
  };

  const statusBg = {
    nominal: 'bg-accent-green/10 border-accent-green/20',
    warning: 'bg-accent-amber/10 border-accent-amber/20',
    critical: 'bg-accent-red/10 border-accent-red/20',
  };

  const lineColor = {
    nominal: '#00e676',
    warning: '#ffab00',
    critical: '#ff5252',
  };

  return (
    <div
      className={`rounded-lg border ${statusBg[stream.status]} p-3 transition-all ${
        expanded ? 'col-span-2 row-span-2' : ''
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={`w-1.5 h-1.5 rounded-full ${statusColor[stream.status].replace('text-', 'bg-')}`} />
          <span className="text-xs font-medium text-text-primary">{stream.name}</span>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="p-0.5 rounded text-text-muted hover:text-text-primary transition-colors"
        >
          {expanded ? <Minimize2 className="w-3 h-3" /> : <Maximize2 className="w-3 h-3" />}
        </button>
      </div>

      {/* Value */}
      <div className="flex items-baseline gap-1 mb-2">
        <span className={`text-lg font-bold font-mono ${statusColor[stream.status]}`}>
          {stream.currentValue.toFixed(1)}
        </span>
        <span className="text-[10px] text-text-muted">{stream.unit}</span>
      </div>

      {/* Mini Chart */}
      <div className={expanded ? 'h-40' : 'h-16'}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={recentData}>
            <Line
              type="monotone"
              dataKey="value"
              stroke={lineColor[stream.status]}
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
            {stream.threshold && (
              <>
                <ReferenceLine
                  y={stream.threshold.warning}
                  stroke="#ffab00"
                  strokeDasharray="3 3"
                  strokeWidth={0.5}
                />
                <ReferenceLine
                  y={stream.threshold.critical}
                  stroke="#ff5252"
                  strokeDasharray="3 3"
                  strokeWidth={0.5}
                />
              </>
            )}
            {expanded && (
              <>
                <XAxis dataKey="timestamp" hide />
                <YAxis domain={[stream.min, stream.max]} hide />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#131d2a',
                    border: '1px solid #1e3348',
                    borderRadius: '8px',
                    fontSize: '11px',
                    color: '#e8edf3',
                  }}
                  formatter={(value: number | undefined) => [`${(value ?? 0).toFixed(2)} ${stream.unit}`, stream.name]}
                  labelFormatter={() => ''}
                />
              </>
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Range */}
      <div className="flex items-center justify-between text-[10px] text-text-muted mt-1 font-mono">
        <span>
          {stream.min} – {stream.max} {stream.unit}
        </span>
        <span className={`font-medium ${statusColor[stream.status]}`}>{stream.status}</span>
      </div>
    </div>
  );
}

export default function TelemetryPanel() {
  const { telemetryStreams } = useStore();

  return (
    <div className="flex flex-col h-full rounded-xl border border-space-border bg-space-panel overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-space-border shrink-0">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-accent-cyan" />
          <h2 className="text-sm font-semibold text-text-primary">Telemetry</h2>
        </div>
        <span className="text-[10px] text-text-muted font-mono">
          {telemetryStreams.length} streams
        </span>
      </div>

      {/* Telemetry Grid */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="grid grid-cols-2 gap-3">
          {telemetryStreams.map((stream) => (
            <TelemetryMini key={stream.id} stream={stream} />
          ))}
        </div>
      </div>
    </div>
  );
}
