import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AlertRow, api, NewsRow, post } from "../api";
import Card from "../components/Card";
import NewsItem from "../components/NewsItem";

type Feed = { categories: Record<string, string>; watched: string[]; items: NewsRow[] };
type Job = { running: boolean; done: number; new: number; alerts: number; errors: string[] };

export default function NewsPage() {
  const [scope, setScope] = useState<"mine" | "all">("mine");
  const [category, setCategory] = useState("");
  const [minImportance, setMinImportance] = useState(1);
  const [feed, setFeed] = useState<Feed | null>(null);
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [job, setJob] = useState<Job | null>(null);

  const request = useRef(0);

  const load = () => {
    const q = new URLSearchParams({ scope, min_importance: String(minImportance), ...(category ? { category } : {}) });
    const id = ++request.current;
    // Only the latest request may update the page: a slower earlier one must not overwrite it.
    api<Feed>(`/news?${q}`).then((f) => id === request.current && setFeed(f));
    api<AlertRow[]>("/alerts").then(setAlerts);
  };
  useEffect(load, [scope, category, minImportance]);
  useEffect(() => {
    api<Job>("/news/collect").then(setJob);
  }, []);
  useEffect(() => {
    if (!job?.running) return;
    const t = setInterval(async () => {
      const state = await api<Job>("/news/collect");
      setJob(state);
      if (!state.running) load();
    }, 4000);
    return () => clearInterval(t);
  }, [job?.running]);

  const readAll = async () => {
    await post("/alerts/read", {});
    load();
  };
  const unread = alerts.filter((a) => !a.read);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-2xl font-semibold">Actualités</h1>
        <button
          onClick={async () => setJob(await post<Job>("/news/collect", {}))}
          disabled={job?.running}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm disabled:opacity-50 dark:border-slate-700"
        >
          {job?.running ? "Collecte en cours (1 à 3 minutes)…" : "Collecter maintenant"}
        </button>
      </div>
      {job && !job.running && job.done > 0 && (
        <p className="text-sm text-slate-500">
          Dernière collecte : {job.new} nouveaux articles sur {job.done} entreprises, {job.alerts} alerte(s).
        </p>
      )}

      <Card title={`Alertes${unread.length ? ` (${unread.length} non lues)` : ""}`}>
        {alerts.length === 0 ? (
          <p className="text-sm text-slate-500">
            Aucune alerte. Elles apparaissent pour une nouvelle majeure, une nouvelle négative notable (prévisions, justice,
            dirigeants…) ou une variation de cours de 5 % ou plus sur tes valeurs.
          </p>
        ) : (
          <>
            <ul>
              {alerts.slice(0, 15).map((a) => (
                <li key={a.id} className={`border-t border-slate-100 py-2 text-sm dark:border-slate-800 ${a.read ? "opacity-60" : ""}`}>
                  <span className={`mr-2 font-bold ${a.severity >= 3 ? "text-red-600" : a.severity === 2 ? "text-amber-600" : "text-slate-500"}`}>
                    {"!".repeat(a.severity)}
                  </span>
                  <Link to={`/analyses/${a.isin}`} className="font-medium hover:text-brand">
                    {a.company}
                  </Link>{" "}
                  · {a.url ? <a href={a.url} target="_blank" rel="noreferrer" className="hover:text-brand">{a.title}</a> : a.title}
                  <div className="text-xs text-slate-500">
                    {new Date(a.created_at).toLocaleDateString("fr-FR")} · {a.detail}
                  </div>
                </li>
              ))}
            </ul>
            {unread.length > 0 && (
              <button onClick={readAll} className="mt-2 text-sm text-brand hover:underline">
                Tout marquer comme lu
              </button>
            )}
          </>
        )}
      </Card>

      <Card>
        <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
          {(["mine", "all"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setScope(s)}
              className={`rounded-md px-3 py-1 ${scope === s ? "bg-brand-soft font-medium text-brand dark:bg-teal-950 dark:text-teal-300" : "text-slate-500"}`}
            >
              {s === "mine" ? "Mes valeurs" : "Tout l'univers"}
            </button>
          ))}
          <select value={category} onChange={(e) => setCategory(e.target.value)} className="rounded-md border border-slate-300 bg-transparent px-2 py-1 dark:border-slate-700">
            <option value="">Toutes catégories</option>
            {Object.entries(feed?.categories ?? {}).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
          <select value={minImportance} onChange={(e) => setMinImportance(+e.target.value)} className="rounded-md border border-slate-300 bg-transparent px-2 py-1 dark:border-slate-700">
            <option value={0}>Tout, même le bruit</option>
            <option value={1}>Importance ● et plus</option>
            <option value={2}>Notable ●● et plus</option>
            <option value={3}>Majeur ●●● seulement</option>
          </select>
        </div>
        {scope === "mine" && (
          <p className="text-xs text-slate-500">
            Mes valeurs : tes positions et les actions sélectionnées pour tes plans ({feed?.watched.length ?? 0}).
          </p>
        )}
        {!feed ? (
          <p className="text-slate-500">Chargement…</p>
        ) : feed.items.length === 0 ? (
          <p className="py-4 text-sm text-slate-500">Rien sur 30 jours avec ces filtres. Lance une collecte si c'est la première fois.</p>
        ) : (
          <ul className="mt-2">
            {feed.items.map((item) => (
              <NewsItem key={item.id} item={item} />
            ))}
          </ul>
        )}
        <p className="mt-3 text-xs text-slate-500">
          Chaque article est trié par l'IA (catégorie, ton, importance, résumé) ou, si aucun modèle ne répond, par mots-clés.
          Le lien ouvre l'article d'origine : vérifie toujours à la source avant de décider.
        </p>
      </Card>
    </div>
  );
}
