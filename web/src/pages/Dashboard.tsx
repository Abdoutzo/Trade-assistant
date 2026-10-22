import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertRow, api, Profile } from "../api";
import Card from "../components/Card";
import { euros, project } from "../lib/projection";

const SCENARIOS = [
  { label: "Prudent", rate: 0.04, color: "#94a3b8" },
  { label: "Historique indice monde", rate: 0.07, color: "#0f766e" },
  { label: "Optimiste", rate: 0.1, color: "#6366f1" },
];

export default function Dashboard() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [years, setYears] = useState(15);
  const [alerts, setAlerts] = useState<AlertRow[]>([]);

  useEffect(() => {
    api<Profile>("/profile").then((p) => {
      setProfile(p);
      setYears(p.horizon_years);
    });
    api<AlertRow[]>("/alerts?unread=true").then(setAlerts).catch(() => setAlerts([]));
  }, []);

  const series = useMemo(
    () =>
      profile
        ? SCENARIOS.map((s) => ({ ...s, points: project(profile.initial_amount_eur, profile.monthly_amount_eur, s.rate, years) }))
        : [],
    [profile, years],
  );

  if (!profile) return <p className="text-slate-500">Chargement…</p>;
  const invested = series[0].points.at(-1)!.invested;
  const core = profile.monthly_amount_eur * profile.core_share;

  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Tableau de bord</h1>
        <Link to="/reglages" className="text-sm text-brand hover:underline">
          Modifier mon profil
        </Link>
      </div>

      {alerts.length > 0 && (
        <Link to="/actualites" className="block rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
          <strong>{alerts.length} alerte(s) non lue(s)</strong> : {alerts.slice(0, 2).map((a) => `${a.company} · ${a.title}`).join(" ; ")}
          {alerts.length > 2 ? "…" : ""}
        </Link>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <Card title="Enveloppe">
          <p className="text-2xl font-semibold">{profile.account_type}</p>
          <p className="text-sm text-slate-500">
            {profile.account_type === "PEA"
              ? "Trade Republic, plans programmés sans frais"
              : "Compte-titres : tout est accessible, mais 31,4 % d'impôt sur les gains (2026)"}
          </p>
        </Card>
        <Card title="Versements">
          <p className="text-2xl font-semibold">{euros(profile.monthly_amount_eur)} / mois</p>
          <p className="text-sm text-slate-500">après un départ de {euros(profile.initial_amount_eur)}</p>
        </Card>
        <Card title="Répartition">
          <p className="text-2xl font-semibold">
            {Math.round(profile.core_share * 100)} / {Math.round(profile.satellite_share * 100)}
          </p>
          <p className="text-sm text-slate-500">
            {euros(core)} ETF monde, {euros(profile.monthly_amount_eur - core)} actions choisies
          </p>
        </Card>
      </div>

      <Card title="Projection de ton épargne">
        <label className="mb-4 flex items-center gap-3 text-sm">
          Horizon : <strong>{years} ans</strong>
          <input type="range" min={1} max={30} value={years} onChange={(e) => setYears(+e.target.value)} className="flex-1" />
        </label>
        <Chart series={series} />
        <table className="mt-4 w-full text-sm">
          <tbody>
            <tr className="border-b border-slate-200 dark:border-slate-800">
              <td className="py-1">Total versé</td>
              <td className="text-right font-medium">{euros(invested)}</td>
            </tr>
            {series.map((s) => (
              <tr key={s.label}>
                <td className="py-1">
                  <span className="mr-2 inline-block h-2 w-2 rounded-full" style={{ background: s.color }} />
                  {s.label} ({Math.round(s.rate * 100)} %/an)
                </td>
                <td className="text-right font-medium">{euros(s.points.at(-1)!.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-xs text-slate-500">
          Illustration à taux constant. En réalité le marché monte et baisse : des années à -20 % ou -30 % arrivent, et
          c'est en continuant d'investir pendant ces baisses que l'on achète moins cher.
        </p>
      </Card>
    </div>
  );
}

type Series = { label: string; color: string; points: { month: number; invested: number; value: number }[] };

function Chart({ series }: { series: Series[] }) {
  const W = 600, H = 220, P = 8;
  const last = series[series.length - 1].points;
  const maxY = last[last.length - 1].value;
  const maxX = last.length - 1;
  const path = (values: number[]) =>
    values
      .map((v, i) => `${i ? "L" : "M"}${P + (i / maxX) * (W - 2 * P)},${H - P - (v / maxY) * (H - 2 * P)}`)
      .join(" ");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Projection de l'épargne">
      <path d={path(series[0].points.map((p) => p.invested))} fill="none" stroke="#cbd5e1" strokeDasharray="4 4" />
      {series.map((s) => (
        <path key={s.label} d={path(s.points.map((p) => p.value))} fill="none" stroke={s.color} strokeWidth={2} />
      ))}
    </svg>
  );
}
