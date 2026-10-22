import { ReactNode, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, MonthlyPlanData, PlanJob, PlanSummary, post } from "../api";
import Card from "../components/Card";
import { euros } from "../lib/projection";

const STATUS: Record<string, [string, string]> = {
  draft: ["Brouillon : à valider", "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"],
  approved: ["Validé", "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"],
  rejected: ["Refusé", "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300"],
  replaced: ["Remplacé", "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"],
};
const STANCE: Record<string, string> = {
  renforcer: "text-emerald-700 dark:text-emerald-400",
  conserver: "text-slate-600 dark:text-slate-300",
  attendre: "text-amber-700 dark:text-amber-400",
};
const ROLE_LABEL: Record<string, string> = { analyst: "Analyste", critic: "Avocat du diable", manager: "Gérant" };

function Facts({ ids, facts }: { ids: string[]; facts: Record<string, string> }) {
  if (!ids.length) return null;
  return (
    <span className="ml-1">
      {ids.map((id) => (
        <span key={id} title={facts[id]} className="mr-0.5 cursor-help rounded bg-slate-100 px-1 text-[10px] text-slate-500 dark:bg-slate-800">
          {id}
        </span>
      ))}
    </span>
  );
}

function Unverified({ values }: { values?: number[] }) {
  if (!values?.length) return null;
  return (
    <span title="Chiffres absents des faits fournis à l'IA : à vérifier, voire à ignorer." className="ml-1 rounded bg-red-50 px-1 text-[10px] text-red-700 dark:bg-red-950 dark:text-red-300">
      chiffre non vérifié : {values.map((v) => v.toLocaleString("fr-FR")).join(", ")}
    </span>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <p className="mb-1 text-sm font-medium">{title}</p>
      <div className="text-sm text-slate-700 dark:text-slate-300">{children}</div>
    </div>
  );
}

export default function PlanPage() {
  const [plan, setPlan] = useState<MonthlyPlanData | null | undefined>(undefined);
  const [history, setHistory] = useState<PlanSummary[]>([]);
  const [job, setJob] = useState<PlanJob | null>(null);
  const [note, setNote] = useState("");

  const load = (id?: number) => {
    api<MonthlyPlanData | null>(id ? `/plans/${id}` : "/plans/latest").then(setPlan);
    api<PlanSummary[]>("/plans").then(setHistory);
  };
  useEffect(() => {
    load();
    api<PlanJob>("/plans/job").then(setJob);
  }, []);
  useEffect(() => {
    if (!job?.running) return;
    const t = setInterval(async () => {
      const state = await api<PlanJob>("/plans/job");
      setJob(state);
      if (!state.running) load();
    }, 3000);
    return () => clearInterval(t);
  }, [job?.running]);

  const decide = async (status: "approved" | "rejected") => {
    if (!plan) return;
    setPlan(await post<MonthlyPlanData>(`/plans/${plan.id}/decision`, { status, note: note || null }));
    setNote("");
    api<PlanSummary[]>("/plans").then(setHistory);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-2xl font-semibold">Plan du mois</h1>
        <button
          onClick={async () => setJob(await post<PlanJob>("/plans/generate", {}))}
          disabled={job?.running}
          className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {job?.running ? `${job.step ?? "En cours"}…` : "Préparer un nouveau plan"}
        </button>
      </div>
      <p className="text-sm text-slate-500">
        L'agent part des notes, de ton portefeuille et de l'actualité. Un analyste étudie chaque dossier, un avocat du diable cherche
        les failles, un gérant décide. Tous les chiffres viennent des données de l'outil (faits F1, F2… : survole-les). Préparé
        automatiquement le 1er de chaque mois, ou à la demande (1 à 3 minutes). <strong>Rien n'est exécuté sans toi.</strong>
      </p>
      {job?.error && <p className="text-sm text-red-600">Échec : {job.error}</p>}

      {plan === undefined ? (
        <p className="text-slate-500">Chargement…</p>
      ) : plan === null ? (
        <Card>
          <p className="text-sm text-slate-500">Aucun plan pour l'instant : clique sur « Préparer un nouveau plan ».</p>
        </Card>
      ) : (
        <>
          <Card>
            <div className="mb-4 flex flex-wrap items-center gap-2 text-sm">
              <span className={`rounded px-2 py-0.5 font-medium ${STATUS[plan.status][1]}`}>{STATUS[plan.status][0]}</span>
              <span className="text-slate-500">
                {plan.month} · préparé le {new Date(plan.created_at).toLocaleString("fr-FR")} · {plan.source === "agent" ? `par l'agent (${plan.model})` : "par les règles"}
              </span>
            </div>
            {plan.fallback_reason && (
              <p className="mb-4 rounded-md bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-300">⚠ {plan.fallback_reason}</p>
            )}

            <table className="w-full text-sm">
              <tbody>
                {plan.orders.map((o) => (
                  <tr key={o.isin} className="border-t border-slate-100 align-top dark:border-slate-800">
                    <td className="py-2.5 pr-3">
                      <Link to={`/analyses/${o.isin}`} className="font-medium hover:text-brand">
                        {o.name}
                      </Link>
                      <span className="ml-2 text-xs text-slate-400">{o.role === "core" ? "cœur" : "satellite"} · {o.isin}</span>
                      {o.reason && (
                        <div className="text-xs text-slate-600 dark:text-slate-400">
                          {o.reason}
                          <Facts ids={o.facts} facts={plan.facts} />
                          <Unverified values={o.unverified} />
                        </div>
                      )}
                    </td>
                    <td className="whitespace-nowrap py-2.5 text-right text-lg font-semibold tabular-nums">{euros(o.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="mt-5 space-y-4">
              {plan.summary && (
                <Section title="La décision">
                  {plan.summary}
                  <Unverified values={plan.text_unverified} />
                </Section>
              )}
              {plan.changes && <Section title="Par rapport au plan calculé">{plan.changes}</Section>}
              {plan.change_my_mind && <Section title="Ce qui ferait changer ce plan">{plan.change_my_mind}</Section>}
            </div>

            {plan.status === "draft" ? (
              <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
                <input
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Ton commentaire (facultatif) : pourquoi tu valides ou refuses"
                  className="min-w-0 flex-1 rounded-md border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
                />
                <button onClick={() => decide("approved")} className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white">
                  Valider
                </button>
                <button onClick={() => decide("rejected")} className="rounded-md border border-red-300 px-4 py-2 text-sm text-red-700 dark:border-red-800 dark:text-red-400">
                  Refuser
                </button>
              </div>
            ) : (
              plan.note && <p className="mt-4 text-sm text-slate-500">Ton commentaire : {plan.note}</p>
            )}
          </Card>

          {plan.status !== "rejected" && (
            <Card title={plan.status === "approved" ? "À faire dans Trade Republic" : "Ce qu'il faudra faire dans Trade Republic (après validation)"}>
              <ol className="list-decimal space-y-1 pl-5 text-sm">
                {plan.checklist.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ol>
            </Card>
          )}

          {plan.lesson && (
            <Card title={`Leçon du mois : ${plan.lesson.title}`}>
              <p className="text-sm">{plan.lesson.text}</p>
            </Card>
          )}

          {plan.critic.length > 0 && (
            <Card title="L'avocat du diable">
              <ul className="space-y-2 text-sm">
                {[...plan.critic]
                  .sort((a, b) => b.severity - a.severity)
                  .map((o, i) => (
                    <li key={i}>
                      <span className={`mr-2 font-bold ${o.severity >= 3 ? "text-red-600" : o.severity === 2 ? "text-amber-600" : "text-slate-400"}`}>
                        {"!".repeat(o.severity)}
                      </span>
                      <strong>{o.name}</strong> : {o.text}
                      <Facts ids={o.facts} facts={plan.facts} />
                      <Unverified values={o.unverified} />
                    </li>
                  ))}
              </ul>
            </Card>
          )}

          {plan.analyst && (
            <Card title="L'analyste">
              {plan.analyst.overview && (
                <p className="mb-3 text-sm">
                  {plan.analyst.overview}
                  <Unverified values={plan.analyst.overview_unverified} />
                </p>
              )}
              <div className="space-y-3">
                {plan.analyst.companies.map((c) => (
                  <div key={c.isin} className="rounded-lg border border-slate-100 p-3 text-sm dark:border-slate-800">
                    <div className="flex flex-wrap items-center gap-2">
                      <Link to={`/analyses/${c.isin}`} className="font-medium hover:text-brand">
                        {c.name}
                      </Link>
                      <span className="text-xs text-slate-500">
                        {c.role === "alternative" ? "alternative" : c.role === "held" ? "détenue" : "sélectionnée"}
                        {c.score != null && ` · note ${c.score}`}
                      </span>
                      <span className={`ml-auto font-medium ${STANCE[c.stance]}`}>
                        {c.stance} · confiance {c.confidence}/3
                      </span>
                    </div>
                    <p className="mt-1">
                      {c.thesis}
                      <Facts ids={c.facts} facts={plan.facts} />
                    </p>
                    <p className="mt-1 text-slate-600 dark:text-slate-400">
                      Risque : {c.risks}
                      <Unverified values={c.unverified} />
                    </p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card title="Comment l'agent a travaillé">
            <ul className="text-sm">
              {plan.steps.map((s) => (
                <li key={s.role}>
                  {s.ok ? "✓" : "✗"} {ROLE_LABEL[s.role] ?? s.role} : {s.ok ? `${s.model}, ${s.seconds} s` : s.error}
                </li>
              ))}
            </ul>
            <details className="mt-3 text-xs">
              <summary className="cursor-pointer text-sm">Les {Object.keys(plan.facts).length} faits fournis à l'IA</summary>
              <ul className="mt-2 space-y-0.5 text-slate-600 dark:text-slate-400">
                {Object.entries(plan.facts).map(([id, text]) => (
                  <li key={id}>
                    <strong>{id}</strong> {text}
                  </li>
                ))}
              </ul>
            </details>
          </Card>
        </>
      )}

      {history.length > 1 && (
        <Card title="Plans précédents">
          <ul className="text-sm">
            {history.map((h) => (
              <li key={h.id} className="flex flex-wrap gap-2 border-t border-slate-100 py-1.5 dark:border-slate-800">
                <button onClick={() => load(h.id)} className="font-medium hover:text-brand">
                  {h.month} · {new Date(h.created_at).toLocaleDateString("fr-FR")}
                </button>
                <span className={`rounded px-1.5 text-xs ${STATUS[h.status]?.[1] ?? ""}`}>{STATUS[h.status]?.[0] ?? h.status}</span>
                <span className="text-slate-500">{h.orders.map((o) => `${o.name.split(" ")[0]} ${o.amount} €`).join(", ")}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
