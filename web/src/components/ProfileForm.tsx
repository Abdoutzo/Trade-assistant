import { FormEvent, useEffect, useState } from "react";
import { api, InstrumentSummary, Profile, put } from "../api";
import { euros } from "../lib/projection";

const input = "w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700";

/** The investment settings every part of the tool uses: change them whenever your situation changes. */
export default function ProfileForm() {
  const [form, setForm] = useState<Profile | null>(null);
  const [message, setMessage] = useState("");
  const [etfs, setEtfs] = useState<InstrumentSummary[]>([]);

  useEffect(() => {
    api<Profile>("/profile").then(setForm);
    api<InstrumentSummary[]>("/instruments").then((all) => setEtfs(all.filter((i) => i.kind === "etf" && i.pea_eligible)));
  }, []);

  if (!form) return <p className="text-slate-500">Chargement…</p>;
  const set = <K extends keyof Profile>(key: K, value: Profile[K]) => {
    setForm({ ...form, [key]: value });
    setMessage("");
  };

  const save = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const saved = await put<Profile>("/profile", {
        account_type: form.account_type,
        initial_amount_eur: form.initial_amount_eur,
        monthly_amount_eur: form.monthly_amount_eur,
        core_share: form.core_share,
        horizon_years: form.horizon_years,
        core_isin: form.core_isin,
        satellites_count: form.satellites_count,
        max_position_share: form.max_position_share,
        min_order_eur: form.min_order_eur,
      });
      setForm(saved);
      setMessage("Profil enregistré.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erreur");
    }
  };

  const core = form.monthly_amount_eur * form.core_share;

  return (
    <form onSubmit={save} className="grid gap-4 sm:grid-cols-2">
      <label className="text-sm">
        Enveloppe
        <select value={form.account_type} onChange={(e) => set("account_type", e.target.value as Profile["account_type"])} className={`${input} mt-1`}>
          <option value="PEA">PEA (actions européennes et ETF éligibles)</option>
          <option value="CTO">Compte-titres (tout le marché)</option>
        </select>
      </label>
      <label className="text-sm">
        Horizon de placement (années)
        <input type="number" min={1} max={60} value={form.horizon_years} onChange={(e) => set("horizon_years", +e.target.value)} className={`${input} mt-1`} />
      </label>
      <label className="text-sm">
        Montant de départ (€)
        <input type="number" min={0} step={10} value={form.initial_amount_eur} onChange={(e) => set("initial_amount_eur", +e.target.value)} className={`${input} mt-1`} />
      </label>
      <label className="text-sm">
        Versement mensuel (€)
        <input type="number" min={0} step={10} value={form.monthly_amount_eur} onChange={(e) => set("monthly_amount_eur", +e.target.value)} className={`${input} mt-1`} />
      </label>
      <label className="text-sm sm:col-span-2">
        Part du versement sur l'ETF monde : <strong>{Math.round(form.core_share * 100)} %</strong>
        <input type="range" min={0} max={100} step={5} value={Math.round(form.core_share * 100)} onChange={(e) => set("core_share", +e.target.value / 100)} className="mt-2 w-full" />
        <span className="text-xs text-slate-500">
          Chaque mois : {euros(core)} sur l'ETF monde (le cœur, diversifié) et {euros(form.monthly_amount_eur - core)} sur les
          actions choisies par l'agent (les satellites, plus risqués). Moins de 50 % sur l'ETF, c'est beaucoup de risque
          pour un débutant.
        </span>
      </label>
      {form.horizon_years < 5 && form.account_type === "PEA" && (
        <p className="text-sm text-amber-600 sm:col-span-2">
          Un PEA n'a d'avantage fiscal qu'au-delà de 5 ans, et des actions détenues moins de 5 ans peuvent être en perte au
          moment de vendre.
        </p>
      )}
      <p className="mt-2 text-sm font-medium sm:col-span-2">Règles du portefeuille</p>
      <label className="text-sm">
        ETF du cœur
        <select value={form.core_isin} onChange={(e) => set("core_isin", e.target.value)} className={`${input} mt-1`}>
          {etfs.map((i) => (
            <option key={i.isin} value={i.isin}>
              {i.name}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm">
        Nombre d'actions visé
        <input type="number" min={0} max={15} value={form.satellites_count} onChange={(e) => set("satellites_count", +e.target.value)} className={`${input} mt-1`} />
      </label>
      <label className="text-sm">
        Plafond par action (% du portefeuille)
        <input type="number" min={2} max={50} value={Math.round(form.max_position_share * 100)} onChange={(e) => set("max_position_share", +e.target.value / 100)} className={`${input} mt-1`} />
      </label>
      <label className="text-sm">
        Montant minimum par plan (€)
        <input type="number" min={1} max={1000} value={form.min_order_eur} onChange={(e) => set("min_order_eur", +e.target.value)} className={`${input} mt-1`} />
      </label>
      <p className="text-xs text-slate-500 sm:col-span-2">
        Avec {euros(form.monthly_amount_eur - core)} par mois pour les actions et {euros(form.min_order_eur)} minimum par plan, au plus{" "}
        {Math.floor((form.monthly_amount_eur - core) / Math.max(form.min_order_eur, 1))} action(s) sont alimentées chaque mois ; les
        autres attendent leur tour.
      </p>
      <div className="flex items-center gap-3 sm:col-span-2">
        <button className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:opacity-90">Enregistrer</button>
        {message && <span className="text-sm text-slate-600 dark:text-slate-300">{message}</span>}
      </div>
    </form>
  );
}
