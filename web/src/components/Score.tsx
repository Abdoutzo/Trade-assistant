import { barColor, scoreColor } from "../lib/format";

export function ScoreBadge({ score, size = "sm" }: { score: number | null; size?: "sm" | "lg" }) {
  const dims = size === "lg" ? "h-16 w-16 text-2xl" : "h-8 w-10 text-sm";
  return (
    <span className={`inline-flex items-center justify-center rounded-lg font-semibold tabular-nums ${dims} ${scoreColor(score)}`}>
      {score ?? "-"}
    </span>
  );
}

export function Bar({ score, title }: { score: number | null; title?: string }) {
  return (
    <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800" title={title}>
      {score != null && <div className={`h-2 rounded-full ${barColor(score)}`} style={{ width: `${Math.max(score, 3)}%` }} />}
    </div>
  );
}
