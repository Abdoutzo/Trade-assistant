import { useEffect, useState } from "react";
import { api, LlmStatus, LlmTest, post } from "../api";
import Card from "../components/Card";
import ProfileForm from "../components/ProfileForm";

const ROLE_LABELS: Record<string, string> = {
  reasoning: "Analyse approfondie",
  long_context: "Lecture de rapports longs",
  fast: "Tri rapide des actualités",
};

export default function Settings() {
  const [status, setStatus] = useState<LlmStatus | null>(null);
  const [results, setResults] = useState<Record<string, string>>({});

  useEffect(() => {
    api<LlmStatus>("/llm/status").then(setStatus);
  }, []);

  const test = async (role: string) => {
    setResults((r) => ({ ...r, [role]: "Test en cours…" }));
    try {
      const t = await post<LlmTest>("/llm/test", { role });
      setResults((r) => ({ ...r, [role]: `OK : ${t.provider} / ${t.model}` }));
    } catch (e) {
      setResults((r) => ({ ...r, [role]: e instanceof Error ? e.message : "Erreur" }));
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Réglages</h1>
      <Card title="Mon profil d'investissement">
        <ProfileForm />
      </Card>
      <Card title="Modèles d'IA (offres gratuites)">
        {!status ? (
          <p className="text-slate-500">Chargement…</p>
        ) : (
          <div className="space-y-4">
            {Object.entries(status).map(([role, chain]) => (
              <div key={role}>
                <div className="flex items-center justify-between">
                  <p className="font-medium">{ROLE_LABELS[role] ?? role}</p>
                  <button onClick={() => test(role)} className="rounded-md border border-slate-300 px-2 py-1 text-xs dark:border-slate-700">
                    Tester
                  </button>
                </div>
                {chain.length === 0 ? (
                  <p className="text-sm text-amber-600">Aucune clé API configurée pour ce rôle.</p>
                ) : (
                  <ol className="list-decimal pl-5 text-sm text-slate-600 dark:text-slate-300">
                    {chain.map((c) => (
                      <li key={c.provider + c.model}>
                        {c.provider} : <code>{c.model}</code>
                      </li>
                    ))}
                  </ol>
                )}
                {results[role] && <p className="mt-1 text-xs text-slate-500">{results[role]}</p>}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
