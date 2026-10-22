import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, InstrumentDetail, post, PricePoint } from "../api";
import AnalysisCard from "../components/AnalysisCard";
import Card from "../components/Card";
import LineChart from "../components/LineChart";
import NewsCard from "../components/NewsCard";
import PeaBadge from "../components/PeaBadge";
import { amount, changeColor, pct, price } from "../lib/format";
import { METRICS } from "../lib/metrics";

const PERIODS = ["1m", "6m", "1y", "3y", "5y", "10y"] as const;

export default function InstrumentPage() {
  const { isin = "" } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<InstrumentDetail | null>(null);
  const [error, setError] = useState("");
  const [period, setPeriod] = useState<(typeof PERIODS)[number]>("1y");
  const [prices, setPrices] = useState<PricePoint[] | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () =>
    api<InstrumentDetail>(`/instruments/${isin}`)
      .then(setDetail)
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, [isin]);

  useEffect(() => {
    setPrices(null);
    api<PricePoint[]>(`/instruments/${isin}/prices?period=${period}`).then(setPrices);
  }, [isin, period]);

  const refresh = async () => {
    setBusy(true);
    await post(`/instruments/${isin}/refresh`, {}).catch(() => undefined);
    // Annual reports reload in background: look again a bit later.
    setTimeout(load, 8000);
    await load();
    setBusy(false);
  };

  const remove = async () => {
    if (!confirm(`Retirer ${detail?.name} de l'univers ?`)) return;
    await api(`/instruments/${isin}`, { method: "DELETE" });
    navigate("/analyses");
  };

  if (error) return <p className="text-red-600">{error}</p>;
  if (!detail) return <p className="text-slate-500">Chargement…</p>;

  const rows = METRICS.filter((m) => detail.fundamentals[m.key]?.some(Boolean));
  const periodChange = prices && prices.length > 1 ? prices[prices.length - 1].adj_close / prices[0].adj_close - 1 : null;

  return (
    <div className="space-y-6">
      <div>
        <Link to="/analyses" className="text-sm text-slate-500 hover:text-brand">
          ← Univers
        </Link>
        <h1 className="mt-1 text-2xl font-semibold">{detail.name}</h1>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-500">
          <span className="font-mono">{detail.isin}</span>
          <span>{detail.symbol}</span>
          <PeaBadge eligible={detail.pea_eligible} reason={detail.pea_reason} />
          {detail.sector && <span>{detail.sector}{detail.industry ? ` · ${detail.industry}` : ""}</span>}
        </div>
        {detail.pea_reason && <p className="mt-1 text-xs text-slate-500">{detail.pea_reason}</p>}
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card title="Dernier cours">
          <p className="text-2xl font-semibold tabular-nums">{price(detail.last_close, detail.currency)}</p>
          <p className="text-sm text-slate-500">{detail.last_day && new Date(detail.last_day).toLocaleDateString("fr-FR")}</p>
        </Card>
        <Card title="Sur 1 an">
          <p className={`text-2xl font-semibold tabular-nums ${changeColor(detail.change_1y)}`}>{pct(detail.change_1y)}</p>
          <p className="text-sm text-slate-500">dividendes réinvestis</p>
        </Card>
        <Card title="Données">
          <div className="flex flex-wrap gap-2">
            <button onClick={refresh} disabled={busy} className="rounded-md border border-slate-300 px-3 py-1.5 text-sm disabled:opacity-50 dark:border-slate-700">
              {busy ? "Actualisation…" : "Actualiser"}
            </button>
            <button onClick={remove} className="rounded-md px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950">
              Retirer
            </button>
          </div>
        </Card>
      </div>

      <AnalysisCard isin={detail.isin} />

      {detail.kind === "stock" && <NewsCard isin={detail.isin} />}

      <Card title="Cours">
        <div className="mb-3 flex flex-wrap items-center gap-1 text-sm">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`rounded-md px-2.5 py-1 ${period === p ? "bg-brand-soft font-medium text-brand dark:bg-teal-950 dark:text-teal-300" : "text-slate-500"}`}
            >
              {p.replace("m", " mois").replace("y", " an").replace(/(\d+) an$/, (_, n) => (n === "1" ? "1 an" : `${n} ans`))}
            </button>
          ))}
          <span className={`ml-auto tabular-nums ${changeColor(periodChange)}`}>{pct(periodChange)}</span>
        </div>
        {prices ? (
          <LineChart points={prices.map((p) => ({ x: p.day, y: p.close }))} format={(y) => price(y, detail.currency)} />
        ) : (
          <p className="py-10 text-center text-sm text-slate-500">Chargement…</p>
        )}
      </Card>

      {detail.kind === "stock" && (
        <Card title="Comptes annuels">
          {rows.length === 0 ? (
            <p className="text-sm text-slate-500">
              Pas encore de comptes : ils se chargent après l'ajout (quelques secondes à quelques minutes). Clique sur
              Actualiser si besoin.
            </p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-slate-500">
                      <th className="py-2 text-left font-normal">{detail.fundamentals.revenue?.find(Boolean)?.currency ?? ""}</th>
                      {detail.years.map((y) => (
                        <th key={y} className="px-2 text-right font-medium">
                          {y.slice(0, 4)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((m) => (
                      <tr key={m.key} className="border-t border-slate-100 dark:border-slate-800">
                        <td className="py-1.5 pr-2" title={m.help}>
                          {m.label}
                          <span className="ml-1 cursor-help text-slate-400">ⓘ</span>
                        </td>
                        {detail.fundamentals[m.key].map((c, i) => (
                          <td key={i} className="whitespace-nowrap px-2 text-right tabular-nums">
                            {c ? (
                              <span
                                title={
                                  (c.source === "esef" ? "Rapport annuel officiel" : "Yahoo Finance") +
                                  (c.other_value != null ? ` · l'autre source indique ${amount(c.other_value)} (écart ${pct(c.gap, 0)})` : "")
                                }
                                className={c.source === "esef" ? "font-medium" : "text-slate-600 dark:text-slate-300"}
                              >
                                {amount(c.value)}
                                {c.source === "esef" && <sup className="ml-0.5 text-brand">●</sup>}
                                {c.other_value != null && <span className="ml-0.5 text-amber-500">⚠</span>}
                              </span>
                            ) : (
                              <span className="text-slate-300 dark:text-slate-600">-</span>
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 text-xs text-slate-500">
                <span className="text-brand">●</span> chiffre du rapport annuel officiel (audité), sinon Yahoo Finance.{" "}
                <span className="text-amber-500">⚠</span> les deux sources diffèrent de plus de 3 % : survole pour voir.
                Passe la souris sur une ligne pour sa définition.
              </p>
              {detail.reports.length > 0 && (
                <p className="mt-2 text-xs text-slate-500">
                  Rapports officiels lus :{" "}
                  {detail.reports.map((r, i) => (
                    <span key={r.url}>
                      {i > 0 && ", "}
                      <a href={r.url} target="_blank" rel="noreferrer" className="underline hover:text-brand">
                        {r.period_end.slice(0, 4)}
                      </a>
                    </span>
                  ))}
                </p>
              )}
            </>
          )}
        </Card>
      )}
    </div>
  );
}
