import { useState } from "react";

type Point = { x: string; y: number };

/** Minimal SVG line chart with a hover readout. Values are shown with the formatter given. */
export default function LineChart({ points, format, color = "#0f766e" }: { points: Point[]; format: (y: number) => string; color?: string }) {
  const [hover, setHover] = useState<number | null>(null);
  if (points.length < 2) return <p className="py-10 text-center text-sm text-slate-500">Pas assez de données.</p>;

  const W = 640, H = 240, P = 10;
  const ys = points.map((p) => p.y);
  const min = Math.min(...ys), max = Math.max(...ys);
  const span = max - min || 1;
  const X = (i: number) => P + (i / (points.length - 1)) * (W - 2 * P);
  const Y = (y: number) => H - P - ((y - min) / span) * (H - 2 * P);
  const d = points.map((p, i) => `${i ? "L" : "M"}${X(i).toFixed(1)},${Y(p.y).toFixed(1)}`).join(" ");
  const shown = hover ?? points.length - 1;

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - box.left) / box.width;
    setHover(Math.max(0, Math.min(points.length - 1, Math.round(ratio * (points.length - 1)))));
  };

  return (
    <div>
      <p className="mb-1 text-sm">
        <span className="font-semibold">{format(points[shown].y)}</span>
        <span className="ml-2 text-slate-500">{new Date(points[shown].x).toLocaleDateString("fr-FR")}</span>
      </p>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full touch-none" onMouseMove={onMove} onMouseLeave={() => setHover(null)} role="img">
        <path d={d} fill="none" stroke={color} strokeWidth={2} />
        {hover != null && (
          <>
            <line x1={X(hover)} x2={X(hover)} y1={P} y2={H - P} stroke="#94a3b8" strokeDasharray="3 3" />
            <circle cx={X(hover)} cy={Y(points[hover].y)} r={4} fill={color} />
          </>
        )}
      </svg>
      <div className="flex justify-between text-xs text-slate-500">
        <span>{new Date(points[0].x).toLocaleDateString("fr-FR")}</span>
        <span>
          min {format(min)} · max {format(max)}
        </span>
        <span>{new Date(points[points.length - 1].x).toLocaleDateString("fr-FR")}</span>
      </div>
    </div>
  );
}
