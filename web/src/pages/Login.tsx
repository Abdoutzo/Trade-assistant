import { FormEvent, useState } from "react";
import { post } from "../api";

export default function Login({ onLogin }: { onLogin: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await post("/auth/login", { password });
      onLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-xl bg-white p-6 shadow dark:bg-slate-900">
        <h1 className="text-xl font-semibold text-brand">Trade Assistant</h1>
        <input
          type="password"
          autoFocus
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Mot de passe"
          className="w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button className="w-full rounded-md bg-brand px-3 py-2 font-medium text-white hover:opacity-90">Entrer</button>
      </form>
    </div>
  );
}
