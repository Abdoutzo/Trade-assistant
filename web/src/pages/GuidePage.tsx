import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, GlossaryTerm, GuideAnswer, GuideChapter, GuideProgressState, GuideSummary, post, QuizResult } from "../api";
import Card from "../components/Card";

const AI_BADGE = "rounded bg-violet-100 px-1.5 py-0.5 text-[10px] font-medium text-violet-800 dark:bg-violet-950 dark:text-violet-300";

/** The guide's text uses **bold** for the key words; nothing else is interpreted. */
export function Rich({ text }: { text: string }) {
  return (
    <>
      {text.split(/\*\*(.+?)\*\*/g).map((part, i) => (i % 2 ? <strong key={i}>{part}</strong> : part))}
    </>
  );
}

function QuizBadge({ score, total }: { score: number | null; total: number | null }) {
  if (score == null || !total) return null;
  const color = score === total ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300" : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300";
  return <span className={`rounded px-1.5 py-0.5 text-xs tabular-nums ${color}`}>Quiz {score}/{total}</span>;
}

export default function GuidePage() {
  const { id } = useParams();
  return id ? <ChapterView id={id} /> : <Overview />;
}

// --- Overview ------------------------------------------------------------------------------------

function Overview() {
  const [data, setData] = useState<GuideSummary | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api<GuideSummary>("/guide").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="text-slate-500">Chargement…</p>;
  const next = data.chapters.find((c) => c.id === data.next);

  return (
    <>
      <h1 className="mb-2 text-2xl font-semibold">Guide de l'investisseur</h1>
      <p className="mb-6 text-sm text-slate-500">
        Dix chapitres courts pour comprendre ce que fait l'outil et décider par toi-même. Chacun se termine par un quiz.
      </p>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <div className="flex flex-wrap items-center gap-6">
              <div>
                <p className="text-3xl font-semibold tabular-nums">
                  {data.read}/{data.total}
                </p>
                <p className="text-xs text-slate-500">chapitres lus</p>
              </div>
              <div>
                <p className="text-3xl font-semibold tabular-nums">{data.mastered}</p>
                <p className="text-xs text-slate-500">quiz réussis sans faute</p>
              </div>
              <div className="min-w-48 flex-1">
                <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800">
                  <div className="h-2 rounded-full bg-brand" style={{ width: `${(100 * data.read) / data.total}%` }} />
                </div>
              </div>
              {next ? (
                <Link to={`/guide/${next.id}`} className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white">
                  {next.read ? "Refaire le quiz" : "Continuer"} : {next.title}
                </Link>
              ) : (
                <span className="text-sm text-emerald-700 dark:text-emerald-400">Tout est lu et maîtrisé. Bravo !</span>
              )}
            </div>
          </Card>

          <Card title="Chapitres">
            <ol className="divide-y divide-slate-100 dark:divide-slate-800">
              {data.chapters.map((c, i) => (
                <li key={c.id}>
                  <Link to={`/guide/${c.id}`} className="flex flex-wrap items-center gap-3 py-3 hover:text-brand">
                    <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${c.read ? "bg-brand text-white" : "bg-slate-100 text-slate-500 dark:bg-slate-800"}`}>
                      {c.read ? "✓" : i + 1}
                    </span>
                    <span className="min-w-0 flex-1 font-medium">{c.title}</span>
                    <span className="text-xs text-slate-500">
                      {c.level} · {c.minutes} min
                    </span>
                    <QuizBadge score={c.quiz_score} total={c.quiz_total} />
                  </Link>
                </li>
              ))}
            </ol>
          </Card>

          <Lessons lessons={data.lessons} />
        </div>

        <div className="space-y-6">
          <Ask />
          <Glossary />
        </div>
      </div>
    </>
  );
}

function Lessons({ lessons }: { lessons: GuideSummary["lessons"] }) {
  return (
    <Card title="Leçons des plans mensuels">
      {lessons.length === 0 ? (
        <p className="text-sm text-slate-500">Chaque plan du mois contient une leçon ; elles s'accumuleront ici.</p>
      ) : (
        <ul className="space-y-4">
          {lessons.map((l) => (
            <li key={l.plan_id}>
              <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
                {l.title}
                <span className={AI_BADGE}>rédigée par l'IA, peut contenir des erreurs</span>
              </p>
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{l.text}</p>
              <p className="mt-1 text-xs text-slate-400">
                Plan de {l.month} ·{" "}
                <Link to="/plan" className="underline">
                  voir les plans
                </Link>
              </p>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-4 text-xs text-slate-500">
        Exercice : relis chaque leçon d'un œil critique. Le chapitre « Utiliser l'agent » explique pourquoi une IA peut se
        tromper même quand elle paraît sûre d'elle.
      </p>
    </Card>
  );
}

function Ask() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<GuideAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setAnswer(await post<GuideAnswer>("/guide/ask", { question }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Poser une question au guide">
      <form onSubmit={submit} className="space-y-2">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          maxLength={500}
          rows={3}
          placeholder="Ex. : que se passe-t-il si je retire de l'argent de mon PEA avant 5 ans ?"
          className="w-full rounded-md border border-slate-300 bg-transparent p-2 text-sm dark:border-slate-700"
        />
        <button disabled={busy || question.trim().length < 3} className="rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">
          {busy ? "Réflexion…" : "Demander"}
        </button>
      </form>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      {answer && (
        <div className="mt-4 space-y-2 text-sm">
          <span className={AI_BADGE}>réponse de l'IA, appuyée sur le guide</span>
          <p className="whitespace-pre-line">{answer.answer}</p>
          {answer.unverified.length > 0 && (
            <p className="rounded bg-red-50 p-2 text-xs text-red-700 dark:bg-red-950 dark:text-red-300">
              Chiffres absents du guide, à vérifier : {answer.unverified.map((v) => v.toLocaleString("fr-FR")).join(", ")}
            </p>
          )}
          {answer.chapters.length > 0 && (
            <p className="text-xs">
              À lire :{" "}
              {answer.chapters.map((c, i) => (
                <span key={c.id}>
                  {i > 0 && ", "}
                  <Link to={`/guide/${c.id}`} className="text-brand underline">
                    {c.title}
                  </Link>
                </span>
              ))}
            </p>
          )}
          <p className="text-xs text-slate-400">{answer.warning}</p>
        </div>
      )}
    </Card>
  );
}

function Glossary() {
  const [terms, setTerms] = useState<GlossaryTerm[]>([]);
  const [query, setQuery] = useState("");
  useEffect(() => {
    api<GlossaryTerm[]>("/guide/glossary").then(setTerms);
  }, []);
  const q = query.trim().toLowerCase();
  const shown = q ? terms.filter((t) => `${t.label} ${t.definition}`.toLowerCase().includes(q)) : terms;

  return (
    <Card title="Glossaire">
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Chercher un mot : PER, ETF, dividende…"
        className="mb-3 w-full rounded-md border border-slate-300 bg-transparent px-2 py-1.5 text-sm dark:border-slate-700"
      />
      <dl className="max-h-[32rem] space-y-3 overflow-y-auto pr-1 text-sm">
        {shown.map((t) => (
          <div key={t.key}>
            <dt className="font-medium">{t.label}</dt>
            <dd className="text-slate-600 dark:text-slate-400">
              {t.definition}
              {t.chapter && (
                <Link to={`/guide/${t.chapter}`} className="ml-1 text-xs text-brand underline">
                  chapitre
                </Link>
              )}
            </dd>
          </div>
        ))}
        {shown.length === 0 && <p className="text-slate-500">Aucun terme trouvé.</p>}
      </dl>
    </Card>
  );
}

// --- Chapter -------------------------------------------------------------------------------------

function ChapterView({ id }: { id: string }) {
  const [chapter, setChapter] = useState<GuideChapter | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setChapter(null);
    setError("");
    window.scrollTo(0, 0);
    api<GuideChapter>(`/guide/${id}`).then(setChapter).catch((e) => setError(e.message));
  }, [id]);

  if (error)
    return (
      <p className="text-red-600">
        {error}.{" "}
        <Link to="/guide" className="underline">
          Retour au guide
        </Link>
      </p>
    );
  if (!chapter) return <p className="text-slate-500">Chargement…</p>;

  const markRead = async () => {
    const state = await post<GuideProgressState>(`/guide/${id}/read`, {});
    setChapter({ ...chapter, ...state });
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <Link to="/guide" className="text-sm text-slate-500 hover:text-brand">
          ← Guide
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">
          {chapter.number}. {chapter.title}
        </h1>
        <p className="text-sm text-slate-500">
          {chapter.level} · {chapter.minutes} min de lecture {chapter.read && "· lu ✓"}
        </p>
      </div>

      <Card>
        <div className="space-y-5">
          {chapter.sections.map((s) => (
            <section key={s.title}>
              <h2 className="mb-1 font-semibold">{s.title}</h2>
              <p className="leading-relaxed text-slate-700 dark:text-slate-300">
                <Rich text={s.text} />
              </p>
            </section>
          ))}
        </div>
      </Card>

      <Card title="À retenir">
        <ul className="list-disc space-y-1 pl-5 text-sm">
          {chapter.takeaways.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
        {chapter.links.length > 0 && (
          <p className="mt-4 text-sm">
            Dans l'outil :{" "}
            {chapter.links.map((l, i) => (
              <span key={l.path}>
                {i > 0 && " · "}
                <Link to={l.path} className="text-brand underline">
                  {l.label}
                </Link>
              </span>
            ))}
          </p>
        )}
        {!chapter.read && (
          <button onClick={markRead} className="mt-4 rounded-md border border-brand px-3 py-1.5 text-sm text-brand">
            Marquer comme lu
          </button>
        )}
      </Card>

      {chapter.glossary.length > 0 && (
        <Card title="Mots du chapitre">
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            {chapter.glossary.map((t) => (
              <div key={t.key}>
                <dt className="font-medium">{t.label}</dt>
                <dd className="text-slate-600 dark:text-slate-400">{t.definition}</dd>
              </div>
            ))}
          </dl>
        </Card>
      )}

      <Quiz chapter={chapter} onGraded={(best, total) => setChapter({ ...chapter, read: true, quiz_score: best, quiz_total: total })} />

      <div className="flex justify-between text-sm">
        {chapter.previous ? (
          <Link to={`/guide/${chapter.previous}`} className="text-brand underline">
            ← Chapitre précédent
          </Link>
        ) : (
          <span />
        )}
        {chapter.next ? (
          <Link to={`/guide/${chapter.next}`} className="text-brand underline">
            Chapitre suivant →
          </Link>
        ) : (
          <Link to="/guide" className="text-brand underline">
            Retour au guide
          </Link>
        )}
      </div>
    </div>
  );
}

function Quiz({ chapter, onGraded }: { chapter: GuideChapter; onGraded: (best: number, total: number) => void }) {
  const [answers, setAnswers] = useState<(number | null)[]>(() => chapter.quiz.map(() => null));
  const [result, setResult] = useState<QuizResult | null>(null);

  const submit = async () => {
    const r = await post<QuizResult>(`/guide/${chapter.id}/quiz`, { answers });
    setResult(r);
    onGraded(r.best, r.total);
  };
  const retry = () => {
    setResult(null);
    setAnswers(chapter.quiz.map(() => null));
  };

  return (
    <Card title="Quiz">
      <ol className="space-y-5">
        {chapter.quiz.map((q, qi) => {
          const r = result?.results[qi];
          return (
            <li key={q.question}>
              <p className="mb-2 text-sm font-medium">
                {qi + 1}. {q.question}
              </p>
              <div className="space-y-1">
                {q.choices.map((c, ci) => {
                  const right = r && ci === r.answer_index;
                  const wrong = r && ci === r.chosen && !r.correct;
                  return (
                    <label
                      key={c}
                      className={`flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm ${
                        right
                          ? "border-emerald-400 bg-emerald-50 dark:bg-emerald-950"
                          : wrong
                            ? "border-red-400 bg-red-50 dark:bg-red-950"
                            : "border-slate-200 dark:border-slate-700"
                      }`}
                    >
                      <input
                        type="radio"
                        name={`q${qi}`}
                        checked={answers[qi] === ci}
                        disabled={!!result}
                        onChange={() => setAnswers(answers.map((a, i) => (i === qi ? ci : a)))}
                      />
                      {c}
                    </label>
                  );
                })}
              </div>
              {r && (
                <p className={`mt-2 text-sm ${r.correct ? "text-emerald-700 dark:text-emerald-400" : "text-red-700 dark:text-red-400"}`}>
                  {r.correct ? "Juste. " : "Pas tout à fait. "}
                  <span className="text-slate-700 dark:text-slate-300">{r.explanation}</span>
                </p>
              )}
            </li>
          );
        })}
      </ol>
      <div className="mt-5 flex flex-wrap items-center gap-3">
        {result ? (
          <>
            <p className="text-sm font-medium">
              Score : {result.score}/{result.total}
              {result.best > result.score && <span className="font-normal text-slate-500"> (meilleur : {result.best}/{result.total})</span>}
            </p>
            {result.score < result.total && (
              <button onClick={retry} className="rounded-md border border-brand px-3 py-1.5 text-sm text-brand">
                Recommencer
              </button>
            )}
          </>
        ) : (
          <button onClick={submit} disabled={answers.some((a) => a == null)} className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
            Corriger
          </button>
        )}
        {!result && chapter.quiz_score != null && (
          <QuizBadge score={chapter.quiz_score} total={chapter.quiz_total} />
        )}
      </div>
    </Card>
  );
}
