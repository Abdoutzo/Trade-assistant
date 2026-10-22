import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { api, Me } from "./api";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import GuidePage from "./pages/GuidePage";
import InstrumentPage from "./pages/InstrumentPage";
import Login from "./pages/Login";
import NewsPage from "./pages/NewsPage";
import Placeholder from "./pages/Placeholder";
import PlanPage from "./pages/PlanPage";
import PortfolioPage from "./pages/PortfolioPage";
import RankingPage from "./pages/RankingPage";
import Settings from "./pages/Settings";
import Universe from "./pages/Universe";

export default function App() {
  const [me, setMe] = useState<Me | null>(null);

  const refresh = () =>
    api<Me>("/auth/me")
      .then(setMe)
      .catch(() => setMe({ authenticated: false, login_enabled: true }));

  useEffect(() => {
    refresh();
  }, []);

  if (!me) return <p className="p-8 text-slate-500">Chargement…</p>;
  if (!me.authenticated) return <Login onLogin={refresh} />;

  return (
    <Routes>
      <Route element={<Layout loginEnabled={me.login_enabled} onLogout={refresh} />}>
        <Route index element={<Dashboard />} />
        <Route path="portefeuille" element={<PortfolioPage />} />
        <Route path="analyses" element={<Universe />} />
        <Route path="analyses/:isin" element={<InstrumentPage />} />
        <Route path="classement" element={<RankingPage />} />
        <Route path="actualites" element={<NewsPage />} />
        <Route path="plan" element={<PlanPage />} />
        <Route path="guide" element={<GuidePage />} />
        <Route path="guide/:id" element={<GuidePage />} />
        <Route path="journal" element={<Placeholder title="Journal et performance" brick={8} />} />
        <Route path="reglages" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
