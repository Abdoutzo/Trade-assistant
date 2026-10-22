import { NavLink, Outlet } from "react-router-dom";
import { post } from "../api";

const NAV = [
  ["/", "Tableau de bord"],
  ["/plan", "Plan du mois"],
  ["/portefeuille", "Portefeuille"],
  ["/analyses", "Univers et analyses"],
  ["/actualites", "Actualités"],
  ["/guide", "Guide"],
  ["/journal", "Journal"],
  ["/reglages", "Réglages"],
] as const;

export default function Layout({ loginEnabled, onLogout }: { loginEnabled: boolean; onLogout: () => void }) {
  const logout = async () => {
    await post("/auth/logout", {});
    onLogout();
  };

  return (
    <div className="min-h-screen md:flex">
      <aside className="border-b border-slate-200 bg-white p-4 md:w-56 md:border-b-0 md:border-r dark:border-slate-800 dark:bg-slate-900">
        <p className="mb-4 text-lg font-semibold text-brand">Trade Assistant</p>
        <nav className="flex flex-wrap gap-1 md:flex-col">
          {NAV.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm ${
                  isActive
                    ? "bg-brand-soft font-medium text-brand dark:bg-teal-950 dark:text-teal-300"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        {loginEnabled && (
          <button onClick={logout} className="mt-6 text-sm text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">
            Se déconnecter
          </button>
        )}
      </aside>
      <main className="mx-auto w-full max-w-5xl p-4 md:p-8">
        <Outlet />
        <p className="mt-12 text-xs text-slate-400">
          Outil personnel d'aide à la décision. Ce n'est pas un conseil en investissement : tu restes seul décideur, et
          tout investissement en actions comporte un risque de perte en capital.
        </p>
      </main>
    </div>
  );
}
