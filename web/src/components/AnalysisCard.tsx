import { useEffect, useState } from "react";
import { AnalysisData, api } from "../api";
import { metricValue, pct } from "../lib/format";
import Card from "./Card";
import { Bar, ScoreBadge } from "./Score";

const YEARLY_LABELS: Record<string, [string, string]> = {
  roic: ["ROIC", "pct"],
  roe: ["ROE", "pct"],
  operating_margin: ["Marge opérationnelle", "pct"],
  net_margin: ["Marge nette", "pct"],
  fcf_margin: ["Marge de cash disponible", "pct"],
  cash_conversion: ["Conversion en cash", "pct"],
  net_debt_to_ebitda: ["Dette nette / EBITDA", "x"],
  interest_coverage: ["Couverture des intérêts", "x"],
  payout_ratio: ["Taux de distribution", "pct"],
};

export default function AnalysisCard({ isin }: { isin: string }) {
  const [data, setData] = useState<AnalysisData | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setData(null);
    api<AnalysisData>(`/instruments/${isin}/analysis`).then(setData).catch((e) => setError(e.message));
  }, [isin]);

  if (error) return <Card title="Analyse"><p className="text-sm text-red-600">{error}</p></Card>;
  if (!data) return <Card title="Analyse"><p className="text-sm text-slate-500">Calcul en cours…</p></Card>;

  const info = Object.entries(data.info ?? {}).filter(([, v]) => v != null);

  return (
    <Card title="Analyse">
      <div className="flex flex-wrap items-center gap-4">
        <ScoreBadge score={data.score} size="lg" />
        <div className="min-w-0 flex-1">
          <p className="font-medium">{data.verdict}</p>
          {data.strengths && data.strengths.length > 0 && (
            <p className="text-sm text-emerald-700 dark:text-emerald-400">Points forts : {data.strengths.join(", ")}</p>
          )}
          {data.weaknesses && data.weaknesses.length > 0 && (
            <p className="text-sm text-red-700 dark:text-red-400">Points faibles : {data.weaknesses.join(", ")}</p>
          )}
        </div>
      </div>

      {data.warnings.length > 0 && (
        <ul className="mt-4 space-y-1 rounded-md bg-amber-50 p-3 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-300">
          {data.warnings.map((w) => (
            <li key={w}>⚠ {w}</li>
          ))}
        </ul>
      )}

      {data.pillars && (
        <div className="mt-5 space-y-3">
          {Object.entries(data.pillars).map(([key, p]) => (
            <div key={key} className="rounded-lg border border-slate-100 dark:border-slate-800">
              <button onClick={() => setOpen(open === key ? null : key)} className="flex w-full items-center gap-3 p-3 text-left">
                <span className="w-32 shrink-0 text-sm font-medium">{p.label}</span>
                <Bar score={p.score} />
                <span className="w-8 text-right text-sm tabular-nums">{p.score ?? "-"}</span>
                <span className="text-slate-400">{open === key ? "▴" : "▾"}</span>
              </button>
              {open === key && (
                <div className="border-t border-slate-100 px-3 pb-3 dark:border-slate-800">
                  <p className="py-2 text-xs italic text-slate-500">{p.question}</p>
                  {p.metrics.map((m) => (
                    <details key={m.key} className="border-t border-slate-50 py-2 dark:border-slate-800/50">
                      <summary className="flex cursor-pointer items-center gap-3 text-sm">
                        <span className="flex-1">{m.label}</span>
                        <span className="tabular-nums font-medium">{metricValue(m.value, m.fmt)}</span>
                        <span className="w-16">
                          <Bar score={m.score} />
                        </span>
                      </summary>
                      <div className="mt-2 space-y-1 pl-1 text-xs text-slate-600 dark:text-slate-400">
                        <p>{m.help}</p>
                        <p>
                          Note 0 à {metricValue(m.bad, m.fmt)}, 100 à {metricValue(m.good, m.fmt)}.
                          {m.value != null && ` Ici : ${metricValue(m.value, m.fmt)}, note ${m.score}.`}
                          {data.sector_medians[m.key] != null && ` Médiane du secteur dans l'univers : ${metricValue(data.sector_medians[m.key], m.fmt)}.`}
                        </p>
                        {m.detail && <p className="text-slate-400">Calcul : {m.detail}</p>}
                        {m.value == null && <p className="text-slate-400">Donnée indisponible pour cette entreprise.</p>}
                      </div>
                    </details>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {data.kind === "etf" && (
        <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
          <div>Volatilité : {metricValue(data.risk.volatility, "pct")}</div>
          <div>Pire baisse 5 ans : {metricValue(data.risk.max_drawdown, "pct")}</div>
          <div>Bêta : {metricValue(data.risk.beta, "num")}</div>
        </div>
      )}

      {info.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-500">
          {info.map(([k, v]) => (
            <span key={k}>
              {data.info_labels?.[k]?.[0] ?? k} : <span className="tabular-nums">{pct(v)}</span>
            </span>
          ))}
        </div>
      )}

      {data.yearly && Object.keys(data.yearly.rows).length > 0 && (
        <details className="mt-4">
          <summary className="cursor-pointer text-sm font-medium">Ratios année par année</summary>
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-slate-500">
                  <th />
                  {data.yearly.years.map((y) => (
                    <th key={y} className="px-2 text-right font-medium">
                      {y.slice(0, 4)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.yearly.rows).map(([k, cells]) => (
                  <tr key={k} className="border-t border-slate-100 dark:border-slate-800">
                    <td className="py-1 pr-2">{YEARLY_LABELS[k]?.[0] ?? k}</td>
                    {cells.map((c, i) => (
                      <td key={i} className="px-2 text-right tabular-nums" title={c ? (c.source === "esef" ? "rapport officiel" : "Yahoo") : ""}>
                        {c ? metricValue(c.value, YEARLY_LABELS[k]?.[1] ?? "num") : "-"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
      <p className="mt-3 text-xs text-slate-400">Calculé le {new Date(data.computed_at).toLocaleString("fr-FR")}.</p>
    </Card>
  );
}
