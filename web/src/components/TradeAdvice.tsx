import { FormEvent, useEffect, useState } from "react";
import { api, Frequency, FREQUENCY_LABELS, InstrumentSummary, PlanAction, put, TradeAdvice, TradePlanRow } from "../api";
import { euros } from "../lib/projection";
import Card from "./Card";

const KIND: Record<PlanAction["kind"], [string, string]> = {
  keep: ["Garder", "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"],
  update: ["Modifier", "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"],
  create: ["Créer", "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"],
  delete: ["Supprimer", "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300"],
};

/** The plans Trade Republic can run (whole shares, frequencies) and what to change from yours. */
export function TradeAdviceView({ advice }: { advice: Partial<TradeAdvice> }) {
  if (!advice.trade_plans) return null;
  const changes = advice.actions?.filter((a) => a.kind !== "keep") ?? [];
  return (
    <div className="space-y-3">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-slate-500">
            <th className="font-medium">Plan Trade Republic</th>
            <th className="text-right font-medium">Montant</th>
            <th className="pl-3 font-medium">Fréquence</th>
            <th className="text-right font-medium">Par mois</th>
          </tr>
        </thead>
        <tbody>
          {advice.trade_plans.map((p) => {
            const action = advice.actions?.find((a) => a.isin === p.isin);
            return (
              <tr key={p.isin} className="border-t border-slate-100 dark:border-slate-800">
                <td className="py-2">
                  <span className="font-medium">{p.name}</span>
                  {action && <span className={`ml-2 rounded px-1.5 py-0.5 text-[10px] font-medium ${KIND[action.kind][1]}`}>{KIND[action.kind][0]}</span>}
                  <div className="text-xs text-slate-500">
                    <span className="font-mono">{p.isin}</span>
                    {p.share_price != null && ` · 1 part ≈ ${euros(p.share_price)}`}
                  </div>
                </td>
                <td className="text-right font-semibold tabular-nums">{euros(p.amount)}</td>
                <td className="pl-3">{p.frequency_label}</td>
                <td className="text-right tabular-nums text-slate-500">{euros(p.monthly)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {advice.actions
        ?.filter((a) => a.kind === "delete")
        .map((a) => (
          <p key={a.isin} className="text-sm">
            <span className={`mr-2 rounded px-1.5 py-0.5 text-[10px] font-medium ${KIND.delete[1]}`}>Supprimer</span>
            {a.text}
          </p>
        ))}
      {advice.actions && advice.actions.length > 0 && changes.length === 0 && (
        <p className="rounded-md bg-emerald-50 p-2 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
          Rien à changer dans Trade Republic : tes plans en cours correspondent.
        </p>
      )}
      {advice.plan_notes && advice.plan_notes.length > 0 && (
        <ul className="space-y-1 text-xs text-slate-500">
          {advice.plan_notes.map((n) => (
            <li key={n}>• {n}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

type Row = { isin: string; amount: number; frequency: Frequency };

/** The savings plans running today on Trade Republic, as you set them there. */
export function TradePlansCard({ universe, onChange }: { universe: InstrumentSummary[]; onChange: () => void }) {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [message, setMessage] = useState("");

  const load = () => api<TradePlanRow[]>("/portfolio/trade-plans").then((plans) => setRows(plans.map(({ isin, amount, frequency }) => ({ isin, amount, frequency }))));
  useEffect(() => {
    load();
  }, []);
  if (!rows) return null;

  const update = (i: number, patch: Partial<Row>) => {
    setRows(rows.map((r, k) => (k === i ? { ...r, ...patch } : r)));
    setMessage("");
  };
  const save = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await put("/portfolio/trade-plans", rows.filter((r) => r.isin && r.amount > 0));
      setMessage("Plans enregistrés.");
      load();
      onChange();
    } catch (err) {
      setMessage((err as Error).message);
    }
  };
  const total = rows.reduce((s, r) => s + r.amount * { weekly: 52 / 12, twice_monthly: 2, monthly: 1, quarterly: 1 / 3 }[r.frequency], 0);
  const field = "rounded-md border border-slate-300 bg-transparent px-2 py-1.5 text-sm dark:border-slate-700";

  return (
    <Card title="Mes plans Trade Republic">
      <p className="mb-3 text-sm text-slate-500">
        Recopie ici tes plans d'investissement tels qu'ils tournent dans Trade Republic. Chaque mois, l'outil part de ces plans et ne
        te dit que ce qui doit changer.
      </p>
      <form onSubmit={save} className="space-y-2">
        {rows.map((r, i) => (
          <div key={i} className="flex flex-wrap items-center gap-2">
            <select value={r.isin} onChange={(e) => update(i, { isin: e.target.value })} className={`${field} min-w-0 flex-1`}>
              <option value="">Choisir un titre…</option>
              {universe.map((u) => (
                <option key={u.isin} value={u.isin}>
                  {u.name}
                </option>
              ))}
            </select>
            <input type="number" min={1} step={1} value={r.amount} onChange={(e) => update(i, { amount: +e.target.value })} className={`${field} w-24`} aria-label="Montant" />
            <span className="text-sm">€</span>
            <select value={r.frequency} onChange={(e) => update(i, { frequency: e.target.value as Frequency })} className={field}>
              {Object.entries(FREQUENCY_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
            <button type="button" onClick={() => setRows(rows.filter((_, k) => k !== i))} className="px-2 text-sm text-red-600" aria-label="Retirer">
              ✕
            </button>
          </div>
        ))}
        <div className="flex flex-wrap items-center gap-3 pt-1">
          <button type="button" onClick={() => setRows([...rows, { isin: "", amount: 10, frequency: "monthly" }])} className="rounded-md border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-700">
            + Ajouter un plan
          </button>
          <button className="rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-white">Enregistrer</button>
          <span className="text-sm text-slate-500">≈ {euros(total)} par mois</span>
          {message && <span className="text-sm">{message}</span>}
        </div>
      </form>
    </Card>
  );
}
