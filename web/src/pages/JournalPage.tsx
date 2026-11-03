import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, JournalData } from "../api";
import Card from "../components/Card";
import MultiLineChart from "../components/MultiLineChart";
import { changeColor, pct } from "../lib/format";
import { euros } from "../lib/projection";

const MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
const monthLabel = (m: string) => `${MONTHS[+m.slice(5, 7) - 1]} ${m.slice(0, 4)}`;
const STATUS: Record<string, string> = { approved: "plan validé", rejected: "plan refusé" };

function Signed({ value }: { value: number }) {
  return (
    <span className={`tabular-nums ${changeColor(value)}`}>
      {value > 0 ? "+" : ""}
      {euros(value)}
    </span>
  );
}

export default function JournalPage() {
  const [data, setData] = useState<JournalData | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api<JournalData>("/journal").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="text-slate-500">Chargement…</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Journal et performance</h1>
        <p className="mt-1 text-sm text-slate-500">
          Chaque euro que tu as investi est rejoué, le même jour, sur l'ETF monde seul. La différence dit si tes choix d'actions apportent
          quelque chose.
        </p>
      </div>

      {data.empty ? (
        <Card>
          <p className="text-sm text-slate-500">
            {data.error ?? "Aucun achat enregistré pour l'instant."} Enregistre tes achats dans{" "}
            <Link to="/portefeuille" className="underline">
              Portefeuille &gt; Transactions
            </Link>{" "}
            : le journal se remplit tout seul.
          </p>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-4">
            <Card title="Toi">
              <p className="text-2xl font-semibold tabular-nums">{euros(data.value)}</p>
              {data.xirr != null && <p className="text-sm text-slate-500">{pct(data.xirr)} par an</p>}
            </Card>
            <Card title="Si tout sur l'ETF">
              <p className="text-2xl font-semibold tabular-nums">{euros(data.if_etf)}</p>
              {data.etf_xirr != null && <p className="text-sm text-slate-500">{pct(data.etf_xirr)} par an</p>}
            </Card>
            <Card title="Différence">
              <p className="text-2xl font-semibold">
                <Signed value={data.difference} />
              </p>
            </Card>
            <Card title="Versé">
              <p className="text-2xl font-semibold tabular-nums">{euros(data.invested)}</p>
              <p className="text-sm text-slate-500">depuis le {new Date(data.since).toLocaleDateString("fr-FR")}</p>
            </Card>
          </div>

          <Card title="Verdict">
            <p className="text-sm">{data.verdict}</p>
          </Card>

          {data.chart.days.length > 2 && (
            <Card title="Toi contre l'ETF monde seul">
              <MultiLineChart
                days={data.chart.days}
                format={euros}
                lines={[
                  { label: "Toi", color: "#0f766e", values: data.chart.mine },
                  { label: "Si tout sur l'ETF", color: "#6366f1", values: data.chart.etf },
                  { label: "Versé", color: "#94a3b8", values: data.chart.invested, dashed: true },
                ]}
              />
            </Card>
          )}

          <Card title="Ligne par ligne">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500">
                    <th className="font-medium">Ligne</th>
                    <th className="text-right font-medium">Investi</th>
                    <th className="text-right font-medium">Vaut</th>
                    <th className="text-right font-medium">Sur l'ETF</th>
                    <th className="text-right font-medium">Écart</th>
                  </tr>
                </thead>
                <tbody>
                  {data.lines.map((l) => (
                    <tr key={l.isin} className="border-t border-slate-100 dark:border-slate-800">
                      <td className="py-2">
                        <Link to={`/analyses/${l.isin}`} className="font-medium hover:text-brand">
                          {l.name}
                        </Link>
                        <div className="text-xs text-slate-500">
                          {l.role === "core" ? "cœur" : "action"} · depuis le {new Date(l.since).toLocaleDateString("fr-FR")}
                          {l.return != null && ` · ${pct(l.return)} contre ${pct(l.etf_return)} pour l'ETF`}
                        </div>
                      </td>
                      <td className="text-right tabular-nums">{euros(l.invested)}</td>
                      <td className="text-right tabular-nums">{euros(l.value)}</td>
                      <td className="text-right tabular-nums">{euros(l.if_etf)}</td>
                      <td className="text-right">{l.role === "core" ? <span className="text-slate-400">-</span> : <Signed value={l.difference} />}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-xs text-slate-500">
              Une action en vert a fait mieux que la même somme placée sur l'ETF le même jour ; en rouge, moins bien. Les dividendes versés
              en espèces par les actions ne sont pas comptés (l'ETF réinvestit les siens) : léger avantage à l'ETF.
            </p>
          </Card>

          <Card title="Mois par mois">
            <ul className="space-y-4">
              {data.by_month.map((m) => (
                <li key={m.month} className="border-t border-slate-100 pt-3 first:border-0 first:pt-0 dark:border-slate-800">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <p className="font-medium capitalize">{monthLabel(m.month)}</p>
                    {m.trades.length > 0 && (
                      <p className="text-sm">
                        {euros(m.invested)} investis, valent {euros(m.value)} · écart <Signed value={m.difference} />
                      </p>
                    )}
                  </div>
                  {m.plan && (
                    <p className="text-sm text-slate-600 dark:text-slate-300">
                      <Link to="/plan" className="underline">
                        {STATUS[m.plan.status] ?? m.plan.status}
                      </Link>{" "}
                      : {m.plan.orders.map((o) => `${o.name} ${euros(o.amount)}`).join(", ")}
                      {m.plan.note && <span className="block text-xs text-slate-500">Ton commentaire : « {m.plan.note} »</span>}
                    </p>
                  )}
                  {m.trades.length > 0 ? (
                    <p className="text-xs text-slate-500">
                      Réalisé : {m.trades.map((t) => `${t.side === "buy" ? "achat" : "vente"} ${t.quantity.toLocaleString("fr-FR")} ${t.name} (${euros(t.amount)})`).join(" ; ")}
                    </p>
                  ) : (
                    <p className="text-xs text-slate-500">Aucun achat enregistré ce mois-ci.</p>
                  )}
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-slate-500">
              Relis tes commentaires : comprendre pourquoi tu as validé ou refusé un plan, et ce qui s'est passé ensuite, est la meilleure
              façon de progresser.
            </p>
          </Card>
        </>
      )}
    </div>
  );
}
