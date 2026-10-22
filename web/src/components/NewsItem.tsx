import { Link } from "react-router-dom";
import { NewsRow } from "../api";

const TONE: Record<number, [string, string]> = {
  [-2]: ["très négatif", "bg-red-600"],
  [-1]: ["négatif", "bg-red-400"],
  0: ["neutre", "bg-slate-300 dark:bg-slate-600"],
  1: ["positif", "bg-emerald-400"],
  2: ["très positif", "bg-emerald-600"],
};

export default function NewsItem({ item, showCompany = true }: { item: NewsRow; showCompany?: boolean }) {
  const [toneLabel, toneColor] = TONE[item.sentiment ?? 0] ?? TONE[0];
  return (
    <li className="flex gap-3 border-t border-slate-100 py-2.5 dark:border-slate-800">
      <span title={`Ton ${toneLabel}`} className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${toneColor}`} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 text-xs text-slate-500">
          <span>{new Date(item.published_at).toLocaleDateString("fr-FR")}</span>
          {showCompany && item.isin && (
            <Link to={`/analyses/${item.isin}`} className="font-medium text-slate-700 hover:text-brand dark:text-slate-300">
              {item.company}
            </Link>
          )}
          <span className="rounded bg-slate-100 px-1.5 dark:bg-slate-800">{item.category_label}</span>
          <span title="Importance pour un actionnaire de long terme">{"●".repeat(item.importance ?? 0)}</span>
        </div>
        <a href={item.url} target="_blank" rel="noreferrer" className="text-sm hover:text-brand">
          {item.summary ?? item.title}
        </a>
        <div className="text-xs text-slate-400">
          {item.source}
          {item.triaged_by === "mots-clés" && " · tri par mots-clés"}
        </div>
      </div>
    </li>
  );
}
