import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, InstrumentSummary, post, SeedState } from "../api";
import Card from "../components/Card";
import PeaBadge from "../components/PeaBadge";
import { changeColor, pct, price } from "../lib/format";

export default function Universe() {
  const [items, setItems] = useState<InstrumentSummary[] | null>(null);
  const [isin, setIsin] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [seed, setSeed] = useState<SeedState | null>(null);
  const [filter, setFilter] = useState<"all" | "stock" | "etf">("all");

  const load = () => api<InstrumentSummary[]>("/instruments").then(setItems);

  useEffect(() => {
    load();
    api<SeedState>("/universe/seed").then(setSeed);
  }, []);

  // While the starting universe loads in background, follow its progress.
  useEffect(() => {
    if (!seed?.running) return;
    const timer = setInterval(async () => {
      const state = await api<SeedState>("/universe/seed");
      setSeed(state);
      load();
    }, 3000);
    return () => clearInterval(timer);
  }, [seed?.running]);

  const add = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMessage("Recherche de l'ISIN, puis téléchargement des cours…");
    try {
      const added = await post<InstrumentSummary>("/instruments", { isin });
      setMessage(`${added.name} ajouté. Les rapports annuels se chargent en arrière-plan.`);
      setIsin("");
      load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(false);
    }
  };

  const startSeed = async () => setSeed(await post<SeedState>("/universe/seed", {}));

  const shown = (items ?? []).filter((i) => filter === "all" || i.kind === filter);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Univers et analyses</h1>

      <Card title="Ajouter une action ou un ETF">
        <form onSubmit={add} className="flex flex-col gap-2 sm:flex-row">
          <input
            value={isin}
            onChange={(e) => setIsin(e.target.value.toUpperCase())}
            placeholder="ISIN, ex. FR0000120073 (visible dans Trade Republic)"
            className="flex-1 rounded-md border border-slate-300 bg-transparent px-3 py-2 font-mono text-sm dark:border-slate-700"
          />
          <button disabled={busy || isin.length !== 12} className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
            Ajouter
          </button>
        </form>
        {message && <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{message}</p>}
        <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-slate-200 pt-4 text-sm dark:border-slate-800">
          <button
            onClick={startSeed}
            disabled={seed?.running}
            className="rounded-md border border-slate-300 px-3 py-1.5 disabled:opacity-50 dark:border-slate-700"
          >
            {items?.length ? "Actualiser l'univers de départ" : "Charger l'univers de départ"}
          </button>
          <span className="text-slate-500">
            {seed?.running
              ? `En cours : ${seed.done} / ${seed.total} (${seed.current ?? ""})…`
              : "8 ETF éligibles PEA et 35 grandes entreprises européennes, avec 10 ans de cours et leurs rapports annuels."}
          </span>
        </div>
        {seed && !seed.running && seed.errors.length > 0 && (
          <details className="mt-2 text-xs text-amber-700 dark:text-amber-400">
            <summary>{seed.errors.length} problème(s) au dernier chargement</summary>
            <ul className="mt-1 list-disc pl-5">
              {seed.errors.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          </details>
        )}
      </Card>

      <Card>
        <div className="mb-3 flex gap-2 text-sm">
          {(["all", "stock", "etf"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-md px-3 py-1 ${filter === f ? "bg-brand-soft font-medium text-brand dark:bg-teal-950 dark:text-teal-300" : "text-slate-500"}`}
            >
              {{ all: "Tout", stock: "Actions", etf: "ETF" }[f]}
            </button>
          ))}
        </div>
        {!items ? (
          <p className="text-slate-500">Chargement…</p>
        ) : shown.length === 0 ? (
          <p className="text-slate-500">L'univers est vide : ajoute un ISIN ou charge l'univers de départ.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase text-slate-500">
                <tr>
                  <th className="py-2">Nom</th>
                  <th className="hidden sm:table-cell">Secteur</th>
                  <th className="text-right">Cours</th>
                  <th className="text-right">1 an</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((i) => (
                  <tr key={i.isin} className="border-t border-slate-100 dark:border-slate-800">
                    <td className="py-2">
                      <Link to={`/analyses/${i.isin}`} className="font-medium hover:text-brand">
                        {i.name}
                      </Link>
                      <div className="flex items-center gap-2 text-xs text-slate-500">
                        <span className="font-mono">{i.isin}</span>
                        <PeaBadge eligible={i.pea_eligible} reason={i.pea_reason} />
                        {i.kind === "etf" && <span>ETF</span>}
                      </div>
                    </td>
                    <td className="hidden text-slate-500 sm:table-cell">{i.sector ?? "-"}</td>
                    <td className="text-right tabular-nums">{price(i.last_close, i.currency)}</td>
                    <td className={`text-right tabular-nums ${changeColor(i.change_1y)}`}>{pct(i.change_1y)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
