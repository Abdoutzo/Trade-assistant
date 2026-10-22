import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, Ranking } from "../api";
import Card from "../components/Card";
import { Bar, ScoreBadge } from "../components/Score";
import { changeColor, metricValue, pct } from "../lib/format";

type SortKey = "score" | "quality" | "solidity" | "growth" | "valuation" | "risk" | "pe" | "fcf_yield" | "dividend_yield" | "return_1y";

export default function RankingPage() {
  const [data, setData] = useState<Ranking | null>(null);
  const [sector, setSector] = useState("");
  const [sort, setSort] = useState<SortKey>("score");
  const [error, setError] = useState("");

  useEffect(() => {
    api<Ranking>("/ranking").then(setData).catch((e) => setError(e.message));
  }, []);

  const sectors = useMemo(() => [...new Set((data?.rows ?? []).map((r) => r.sector).filter(Boolean))].sort() as string[], [data]);

  const rows = useMemo(() => {
    const value = (r: Ranking["rows"][number]) =>
      sort === "score" ? r.score : sort in (data?.pillars ?? {}) ? r.pillars[sort] : sort === "return_1y" ? r.return_1y : r.metrics[sort];
    const lowerIsBetter = sort === "pe";
    return (data?.rows ?? [])
      .filter((r) => !sector || r.sector === sector)
      .sort((a, b) => {
        const va = value(a), vb = value(b);
        if (va == null) return 1;
        if (vb == null) return -1;
        return lowerIsBetter ? va - vb : vb - va;
      });
  }, [data, sector, sort]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="text-slate-500">Calcul du classement… (la première fois peut prendre quelques secondes)</p>;

  const header = (key: SortKey, label: string, cls = "") => (
    <th className={`cursor-pointer whitespace-nowrap px-1 py-2 font-medium ${sort === key ? "text-brand" : ""} ${cls}`} onClick={() => setSort(key)}>
      {label}
      {sort === key ? " ↓" : ""}
    </th>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Classement</h1>
        <p className="mt-1 text-sm text-slate-500">
          Note sur 100 calculée à partir des comptes et des cours : qualité 30 %, solidité 20 %, croissance 20 %, valorisation
          20 %, risque 10 %. Clique sur un en-tête pour trier, sur une entreprise pour le détail de sa note.
        </p>
      </div>
      <Card>
        <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
          <select value={sector} onChange={(e) => setSector(e.target.value)} className="rounded-md border border-slate-300 bg-transparent px-2 py-1 dark:border-slate-700">
            <option value="">Tous les secteurs</option>
            {sectors.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <span className="text-slate-500">{rows.length} entreprises</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-slate-500">
              <tr>
                {header("score", "Note")}
                <th className="px-1 py-2 font-medium">Entreprise</th>
                {Object.entries(data.pillars).map(([k, label]) => header(k as SortKey, label.split(" ")[0], "hidden w-20 md:table-cell"))}
                {header("pe", "PER", "text-right")}
                {header("fcf_yield", "Rdt cash", "hidden text-right sm:table-cell")}
                {header("dividend_yield", "Dividende", "hidden text-right sm:table-cell")}
                {header("return_1y", "1 an", "text-right")}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.isin} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="px-1 py-2">
                    <ScoreBadge score={r.score} />
                  </td>
                  <td className="px-1">
                    <Link to={`/analyses/${r.isin}`} className="font-medium hover:text-brand">
                      {r.name}
                    </Link>
                    <div className="text-xs text-slate-500">{r.sector}</div>
                  </td>
                  {Object.keys(data.pillars).map((k) => (
                    <td key={k} className="hidden px-1 md:table-cell">
                      <Bar score={r.pillars[k]} title={`${data.pillars[k]} : ${r.pillars[k] ?? "-"}`} />
                    </td>
                  ))}
                  <td className="whitespace-nowrap px-1 text-right tabular-nums">{metricValue(r.metrics.pe, "x")}</td>
                  <td className="hidden whitespace-nowrap px-1 text-right tabular-nums sm:table-cell">{metricValue(r.metrics.fcf_yield, "pct")}</td>
                  <td className="hidden whitespace-nowrap px-1 text-right tabular-nums sm:table-cell">{metricValue(r.metrics.dividend_yield, "pct")}</td>
                  <td className={`whitespace-nowrap px-1 text-right tabular-nums ${changeColor(r.return_1y)}`}>{pct(r.return_1y, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Une bonne note n'est pas un ordre d'achat : elle dit qu'un dossier mérite d'être étudié. Le plan du mois (brique 5)
          croisera ces notes avec l'actualité, ton portefeuille et la diversification.
        </p>
      </Card>
    </div>
  );
}
