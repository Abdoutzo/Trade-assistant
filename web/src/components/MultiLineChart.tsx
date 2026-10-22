import { useState } from "react";

export type Line = { label: string; color: string; values: number[]; dashed?: boolean };

/** Several series over the same dates, with a hover readout of every series. */
export default function MultiLineChart({ days, lines, format }: { days: string[]; lines: Line[]; format: (y: number) => string }) {
  const [hover, setHover] = useState<number | null>(null);
  if (days.length < 2) return null;
  const W = 640, H = 260, P = 10;
  const max = Math.max(...lines.flatMap((l) => l.values));
  const X = (i: number) => P + (i / (days.length - 1)) * (W - 2 * P);
  const Y = (y: number) => H - P - (y / max) * (H - 2 * P);
  const shown = hover ?? days.length - 1;

  return (
    <div>
      <div className="mb-1 flex flex-wrap gap-x-4 gap-y-1 text-xs">
        <span className="text-slate-500">{new Date(days[shown]).toLocaleDateString("fr-FR", { month: "short", year: "numeric" })}</span>
        {lines.map((l) => (
          <span key={l.label}>
            <span className="mr-1 inline-block h-2 w-3 rounded-sm align-middle" style={{ background: l.color }} />
            {l.label} : <strong className="tabular-nums">{format(l.values[shown])}</strong>
          </span>
        ))}
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full touch-none"
        onMouseMove={(e) => {
          const box = e.currentTarget.getBoundingClientRect();
          setHover(Math.max(0, Math.min(days.length - 1, Math.round(((e.clientX - box.left) / box.width) * (days.length - 1)))));
        }}
        onMouseLeave={() => setHover(null)}
      >
        {lines.map((l) => (
          <path
            key={l.label}
            d={l.values.map((v, i) => `${i ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(" ")}
            fill="none"
            stroke={l.color}
            strokeWidth={l.dashed ? 1.5 : 2}
            strokeDasharray={l.dashed ? "4 4" : undefined}
          />
        ))}
        {hover != null && <line x1={X(hover)} x2={X(hover)} y1={P} y2={H - P} stroke="#94a3b8" strokeDasharray="3 3" />}
      </svg>
      <div className="flex justify-between text-xs text-slate-500">
        <span>{new Date(days[0]).toLocaleDateString("fr-FR", { month: "short", year: "numeric" })}</span>
        <span>{new Date(days[days.length - 1]).toLocaleDateString("fr-FR", { month: "short", year: "numeric" })}</span>
      </div>
    </div>
  );
}
