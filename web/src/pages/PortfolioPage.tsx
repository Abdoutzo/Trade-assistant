import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, InstrumentSummary, PlanData, PortfolioData, post, Projection, put, SimStats, SimulationData } from "../api";
import Card from "../components/Card";
import MultiLineChart from "../components/MultiLineChart";
import { changeColor, pct, unitEuros } from "../lib/format";
import { euros } from "../lib/projection";

const input = "rounded-md border border-slate-300 bg-transparent px-2 py-1.5 text-sm dark:border-slate-700";

export default function PortfolioPage() {
  const [pf, setPf] = useState<PortfolioData | null>(null);
  const [plan, setPlan] = useState<PlanData | null>(null);
  const [universe, setUniverse] = useState<InstrumentSummary[]>([]);

  const load = () => {
    api<PortfolioData>("/portfolio").then(setPf);
    api<PlanData>("/portfolio/plan").then(setPlan);
  };
  useEffect(() => {
    load();
    api<InstrumentSummary[]>("/instruments").then(setUniverse);
  }, []);

  if (!pf || !plan) return <p className="text-slate-500">Chargement…</p>;
  const names = Object.fromEntries(universe.map((i) => [i.isin, i.name]));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Portefeuille</h1>

      <div className="grid gap-4 sm:grid-cols-4">
        <Card title="Valeur">
          <p className="text-2xl font-semibold tabular-nums">{euros(pf.total_value)}</p>
        </Card>
        <Card title="Versé">
          <p className="text-2xl font-semibold tabular-nums">{euros(pf.contributions)}</p>
        </Card>
        <Card title="Gain">
          <p className={`text-2xl font-semibold tabular-nums ${changeColor(pf.gain)}`}>{euros(pf.gain)}</p>
          <p className="text-sm text-slate-500">{pf.contributions ? pct(pf.gain / pf.contributions) : "-"}</p>
        </Card>
        <Card title="Cœur ETF">
          <p className="text-2xl font-semibold tabular-nums">{pf.core_weight == null ? "-" : `${Math.round(pf.core_weight * 100)} %`}</p>
          <p className="text-sm text-slate-500">cible {Math.round(pf.core_target * 100)} %</p>
        </Card>
      </div>

      {pf.warnings.length > 0 && (
        <ul className="space-y-1 rounded-md bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-300">
          {pf.warnings.map((w) => (
            <li key={w}>⚠ {w}</li>
          ))}
        </ul>
      )}

      <PlanCard plan={plan} onChange={load} />
      <PositionsCard pf={pf} />
      <TransactionsCard pf={pf} universe={universe} names={names} onChange={load} />
      <SimulationCard />
    </div>
  );
}

function PlanCard({ plan, onChange }: { plan: PlanData; onChange: () => void }) {
  const choose = async (isin: string, status: "pinned" | "excluded" | null) => {
    await put(`/portfolio/choices/${isin}`, { status });
    onChange();
  };

  return (
    <Card title={`Tes plans d'investissement ce mois-ci (${euros(plan.monthly_amount)})`}>
      <p className="mb-3 text-sm text-slate-500">
        Sur Trade Republic, les <strong>plans d'investissement programmés</strong> sont gratuits ; un ordre manuel coûte 1 €. Crée
        (ou ajuste) un plan mensuel par ligne ci-dessous, puis ne touche à rien tant que la proposition ne change pas.
      </p>
      <table className="w-full text-sm">
        <tbody>
          {plan.orders.map((o) => (
            <tr key={o.isin} className="border-t border-slate-100 dark:border-slate-800">
              <td className="py-2">
                <Link to={`/analyses/${o.isin}`} className="font-medium hover:text-brand">
                  {o.name}
                </Link>
                <div className="text-xs text-slate-500">
                  <span className="font-mono">{o.isin}</span> · {o.role === "core" ? "cœur" : "satellite"} · {o.reason}
                </div>
              </td>
              <td className="whitespace-nowrap text-right text-lg font-semibold tabular-nums">{euros(o.amount)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {plan.first_payment && (
        <div className="mt-4 rounded-md bg-slate-50 p-3 text-sm dark:bg-slate-800/50">
          <p className="font-medium">Premier versement</p>
          <p className="mb-2 text-xs text-slate-500">
            Ordres ponctuels, 1 € de frais chacun. Variante plus économique : tout le premier versement sur l'ETF (1 seul ordre),
            les actions arrivant ensuite par les plans mensuels.
          </p>
          {plan.first_payment.map((o) => (
            <div key={o.isin} className="flex justify-between">
              <span>{o.name}</span>
              <span className="tabular-nums">{euros(o.amount)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mt-5">
        <p className="mb-2 text-sm font-medium">Actions sélectionnées</p>
        <ul className="space-y-1 text-sm">
          {plan.targets.map((t) => (
            <li key={t.isin} className="flex flex-wrap items-center gap-2">
              <span className="w-8 text-right font-semibold tabular-nums">{t.score ?? "-"}</span>
              <Link to={`/analyses/${t.isin}`} className="hover:text-brand">
                {t.name}
              </Link>
              <span className="text-xs text-slate-500">
                {t.sector} · {t.reason}
              </span>
              <span className="ml-auto flex gap-1">
                <button onClick={() => choose(t.isin, t.pinned ? null : "pinned")} className="rounded border border-slate-300 px-2 text-xs dark:border-slate-700">
                  {t.pinned ? "Désépingler" : "Épingler"}
                </button>
                <button onClick={() => choose(t.isin, "excluded")} className="rounded px-2 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-950">
                  Exclure
                </button>
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-slate-500">
          Choix automatique : tes actions détenues, celles que tu épingles, puis les meilleures notes du{" "}
          <Link to="/classement" className="underline">
            classement
          </Link>{" "}
          (60/100 minimum, 2 par secteur au plus). Nombre d'actions, plafond par ligne et montant minimum se règlent dans Réglages.
        </p>
      </div>
    </Card>
  );
}

function PositionsCard({ pf }: { pf: PortfolioData }) {
  return (
    <Card title="Positions">
      {pf.positions.length === 0 ? (
        <p className="text-sm text-slate-500">Aucune position : enregistre tes achats Trade Republic ci-dessous.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-slate-500">
              <tr>
                <th className="py-2">Ligne</th>
                <th className="text-right">Quantité</th>
                <th className="hidden text-right sm:table-cell">Prix moyen</th>
                <th className="text-right">Valeur</th>
                <th className="text-right">Poids</th>
                <th className="text-right">+/- value</th>
              </tr>
            </thead>
            <tbody>
              {pf.positions.map((p) => (
                <tr key={p.isin} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="py-2">
                    <Link to={`/analyses/${p.isin}`} className="font-medium hover:text-brand">
                      {p.name}
                    </Link>
                    <div className="text-xs text-slate-500">{p.role === "core" ? "cœur" : p.sector}</div>
                  </td>
                  <td className="text-right tabular-nums">{p.quantity.toLocaleString("fr-FR", { maximumFractionDigits: 4 })}</td>
                  <td className="hidden text-right tabular-nums sm:table-cell">{p.average_cost == null ? "-" : unitEuros(p.average_cost)}</td>
                  <td className="text-right tabular-nums">{p.value == null ? "-" : euros(p.value)}</td>
                  <td className="text-right tabular-nums">{p.weight == null ? "-" : `${(p.weight * 100).toFixed(1)} %`}</td>
                  <td className={`whitespace-nowrap text-right tabular-nums ${changeColor(p.gain)}`}>
                    {p.gain == null ? "-" : `${euros(p.gain)} (${pct(p.gain_pct, 0)})`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {Object.keys(pf.sectors).length > 0 && (
        <div className="mt-4 text-xs text-slate-500">
          Secteurs des actions :{" "}
          {Object.entries(pf.sectors)
            .map(([s, v]) => `${s} ${euros(v)}`)
            .join(" · ")}
        </div>
      )}
    </Card>
  );
}

function TransactionsCard({
  pf,
  universe,
  names,
  onChange,
}: {
  pf: PortfolioData;
  universe: InstrumentSummary[];
  names: Record<string, string>;
  onChange: () => void;
}) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ day: today, isin: "", side: "buy", quantity: "", price_eur: "", fees_eur: "0" });
  const [message, setMessage] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await post("/portfolio/transactions", {
        ...form,
        quantity: parseFloat(form.quantity.replace(",", ".")),
        price_eur: parseFloat(form.price_eur.replace(",", ".")),
        fees_eur: parseFloat(form.fees_eur.replace(",", ".") || "0"),
      });
      setMessage("Enregistré.");
      setForm({ ...form, quantity: "", price_eur: "" });
      onChange();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erreur");
    }
  };

  const remove = async (id: number) => {
    if (!confirm("Supprimer cette transaction ?")) return;
    await api(`/portfolio/transactions/${id}`, { method: "DELETE" });
    onChange();
  };

  return (
    <Card title="Transactions">
      <form onSubmit={submit} className="grid grid-cols-2 gap-2 sm:grid-cols-6">
        <input type="date" value={form.day} max={today} onChange={(e) => setForm({ ...form, day: e.target.value })} className={input} />
        <select value={form.isin} onChange={(e) => setForm({ ...form, isin: e.target.value })} className={`${input} col-span-2`} required>
          <option value="">Choisir la valeur…</option>
          {universe.map((i) => (
            <option key={i.isin} value={i.isin}>
              {i.name}
            </option>
          ))}
        </select>
        <select value={form.side} onChange={(e) => setForm({ ...form, side: e.target.value })} className={input}>
          <option value="buy">Achat</option>
          <option value="sell">Vente</option>
        </select>
        <input placeholder="Quantité (ex. 0,1523)" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} className={input} required />
        <input placeholder="Prix unitaire €" value={form.price_eur} onChange={(e) => setForm({ ...form, price_eur: e.target.value })} className={input} required />
        <input placeholder="Frais €" value={form.fees_eur} onChange={(e) => setForm({ ...form, fees_eur: e.target.value })} className={input} />
        <button className="rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-white sm:col-span-1">Ajouter</button>
        {message && <span className="col-span-2 self-center text-sm text-slate-600 dark:text-slate-300 sm:col-span-4">{message}</span>}
      </form>
      <p className="mt-2 text-xs text-slate-500">
        Dans Trade Republic : Profil &gt; Transactions, chaque exécution indique la quantité (souvent fractionnée) et le prix. Un plan
        programmé = une transaction par exécution, sans frais.
      </p>
      {pf.transactions.length > 0 && (
        <table className="mt-4 w-full text-sm">
          <tbody>
            {pf.transactions.map((t) => (
              <tr key={t.id} className="border-t border-slate-100 dark:border-slate-800">
                <td className="py-1.5 tabular-nums">{new Date(t.day).toLocaleDateString("fr-FR")}</td>
                <td>{t.side === "buy" ? "Achat" : "Vente"}</td>
                <td>{names[t.isin] ?? t.isin}</td>
                <td className="text-right tabular-nums">
                  {t.quantity.toLocaleString("fr-FR", { maximumFractionDigits: 4 })} × {unitEuros(t.price_eur)}
                </td>
                <td className="text-right">
                  <button onClick={() => remove(t.id)} className="px-2 text-xs text-red-600">
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

function SimulationCard() {
  const [years, setYears] = useState(10);
  const [sim, setSim] = useState<SimulationData | null>(null);
  const [state, setState] = useState("");

  const run = async () => {
    setState("Simulation en cours… (la première fois, téléchargement de 10 ans de MSCI World)");
    try {
      setSim(await post<SimulationData>("/portfolio/simulation", { years }));
      setState("");
    } catch (err) {
      setState(err instanceof Error ? err.message : "Erreur");
    }
  };

  const rate = (x: number | null | undefined) => (x == null ? "-" : pct(x));
  const rows: [string, (s: SimStats) => string][] = [
    ["Valeur finale", (s) => euros(s.final_value)],
    ["Total versé", (s) => euros(s.invested)],
    ["Rendement annuel de ton argent", (s) => rate(s.money_weighted_return)],
    ["Volatilité annuelle", (s) => rate(s.volatility)],
    ["Pire baisse depuis un sommet", (s) => rate(s.max_drawdown)],
    ["Pire période de 12 mois", (s) => rate(s.worst_12_months)],
  ];
  const proj = (p: Projection) => (p ? `${euros(p.p10)} · ${euros(p.p50)} · ${euros(p.p90)}` : "-");

  return (
    <Card title="Simulation : et si j'avais suivi ces règles ?">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <select value={years} onChange={(e) => setYears(+e.target.value)} className={input}>
          {[5, 10, 15].map((y) => (
            <option key={y} value={y}>
              sur {y} ans
            </option>
          ))}
        </select>
        <button onClick={run} className="rounded-md bg-brand px-3 py-1.5 font-medium text-white">
          Lancer la simulation
        </button>
        <span className="text-slate-500">{state}</span>
      </div>
      <p className="mt-2 text-xs text-slate-500">
        Ton profil (départ, versement mensuel, part ETF) et les mêmes règles que ci-dessus, rejoués mois par mois sur les cours
        passés, avec les actions sélectionnées aujourd'hui. Comparé à 100 % ETF monde.
      </p>

      {sim && (
        <div className="mt-4 space-y-4">
          <MultiLineChart
            days={sim.chart.days}
            format={euros}
            lines={[
              { label: "Ta stratégie", color: "#0f766e", values: sim.chart.strategy },
              { label: "100 % ETF monde", color: "#6366f1", values: sim.chart.core_only },
              { label: "Versé", color: "#94a3b8", values: sim.chart.invested, dashed: true },
            ]}
          />
          <table className="w-full text-sm">
            <thead className="text-xs text-slate-500">
              <tr>
                <th />
                <th className="text-right font-medium">Ta stratégie</th>
                <th className="text-right font-medium">100 % ETF monde</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(([label, f]) => (
                <tr key={label} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="py-1.5">{label}</td>
                  <td className="text-right tabular-nums">{f(sim.strategy)}</td>
                  <td className="text-right tabular-nums">{f(sim.core_only)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div>
            <p className="text-sm font-medium">Dans {sim.projection.horizon_years} ans : fourchette (1 chance sur 10 en dessous · médiane · 1 chance sur 10 au-dessus)</p>
            <table className="mt-1 w-full text-sm">
              <tbody>
                <tr className="border-t border-slate-100 dark:border-slate-800">
                  <td className="py-1.5">Si l'avenir ressemble aux {Math.round(sim.years)} dernières années</td>
                  <td className="text-right tabular-nums">{proj(sim.projection.strategy)}</td>
                </tr>
                <tr className="border-t border-slate-100 dark:border-slate-800">
                  <td className="py-1.5">
                    <strong>Prudent</strong> : mêmes secousses, marché à {Math.round(sim.projection.long_run_rate * 100)} %/an en moyenne
                  </td>
                  <td className="text-right font-medium tabular-nums">{proj(sim.projection.strategy_normalized)}</td>
                </tr>
              </tbody>
            </table>
            {sim.projection.strategy_normalized && (
              <p className="mt-1 text-xs text-slate-500">
                Pour {euros(sim.projection.strategy_normalized.invested)} versés. Probabilité de finir sous ce montant (scénario prudent) :{" "}
                {pct(sim.projection.strategy_normalized.loss_probability, 0).replace("+", "")}.
              </p>
            )}
          </div>

          <ul className="space-y-1 rounded-md bg-amber-50 p-3 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-300">
            {sim.warnings.map((w) => (
              <li key={w}>⚠ {w}</li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
