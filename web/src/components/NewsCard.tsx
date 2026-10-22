import { useEffect, useState } from "react";
import { api, DigestData, DigestPoint, NewsRow, post } from "../api";
import Card from "./Card";
import NewsItem from "./NewsItem";

type Data = { items: NewsRow[]; digest: DigestData | null };

export default function NewsCard({ isin }: { isin: string }) {
  const [data, setData] = useState<Data | null>(null);
  const [state, setState] = useState("");
  const [all, setAll] = useState(false);

  const load = () => api<Data>(`/instruments/${isin}/news`).then(setData);
  useEffect(() => {
    load();
  }, [isin]);

  const refresh = async () => {
    setState("Collecte et tri des articles…");
    try {
      const r = await post<{ new: number; errors: string[] }>(`/instruments/${isin}/news/refresh`, {});
      setState(`${r.new} nouvel(s) article(s).${r.errors.length ? " Sources en erreur : " + r.errors.join(" ; ") : ""}`);
      load();
    } catch (e) {
      setState(e instanceof Error ? e.message : "Erreur");
    }
  };

  const summarize = async () => {
    setState("L'IA rédige la synthèse (jusqu'à une minute)…");
    try {
      await post(`/instruments/${isin}/digest`, {});
      setState("");
      load();
    } catch (e) {
      setState(e instanceof Error ? e.message : "Erreur");
    }
  };

  if (!data) return <Card title="Actualités"><p className="text-sm text-slate-500">Chargement…</p></Card>;
  const items = all ? data.items : data.items.filter((i) => (i.importance ?? 0) >= 1).slice(0, 10);
  const d = data.digest;

  const cite = (p: DigestPoint) =>
    p.sources.map((n) => {
      const s = d?.sources.find((x) => x.n === n);
      return (
        <a key={n} href={s?.url} target="_blank" rel="noreferrer" title={s ? `${s.source} : ${s.title}` : ""} className="ml-0.5 text-xs text-brand">
          [{n}]
        </a>
      );
    });

  return (
    <Card title="Actualités">
      <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
        <button onClick={refresh} className="rounded-md border border-slate-300 px-3 py-1.5 dark:border-slate-700">
          Collecter
        </button>
        <button onClick={summarize} className="rounded-md bg-brand px-3 py-1.5 font-medium text-white">
          {d ? "Refaire la synthèse IA" : "Synthèse IA"}
        </button>
        <span className="text-slate-500">{state}</span>
      </div>

      {d && (
        <div className="mb-4 rounded-lg bg-slate-50 p-4 text-sm dark:bg-slate-800/50">
          <p className="mb-2 font-medium">Ce qu'il faut retenir</p>
          <ul className="list-disc space-y-1 pl-5">
            {d.points.map((p, i) => (
              <li key={i}>
                {p.text}
                {cite(p)}
              </li>
            ))}
          </ul>
          {d.watch.length > 0 && (
            <>
              <p className="mb-1 mt-3 font-medium">À surveiller</p>
              <ul className="list-disc space-y-1 pl-5">
                {d.watch.map((p, i) => (
                  <li key={i}>
                    {p.text}
                    {cite(p)}
                  </li>
                ))}
              </ul>
            </>
          )}
          <p className="mt-3 text-xs text-slate-500">
            Rédigé le {new Date(d.created_at).toLocaleString("fr-FR")} par {d.model}, uniquement à partir des {d.sources.length} articles
            numérotés (survole un numéro pour voir l'article). Une phrase sans source vérifiable est supprimée automatiquement.
          </p>
        </div>
      )}

      {items.length === 0 ? (
        <p className="text-sm text-slate-500">Pas d'actualité significative en base : clique sur Collecter.</p>
      ) : (
        <ul>
          {items.map((item) => (
            <NewsItem key={item.id} item={item} showCompany={false} />
          ))}
        </ul>
      )}
      {data.items.length > items.length && !all && (
        <button onClick={() => setAll(true)} className="mt-2 text-sm text-brand hover:underline">
          Voir les {data.items.length} articles, bruit compris
        </button>
      )}
    </Card>
  );
}
