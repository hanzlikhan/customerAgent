import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  Loader2,
  MessageSquare,
  Package,
  Store,
  Wifi,
  WifiOff,
} from "lucide-react";
import { API_URL, api } from "./lib/api";
import Sidebar from "./components/Sidebar";
import Chat from "./components/Chat";
import Dashboard from "./components/Dashboard";
import Catalog from "./components/Catalog";

const NAV = [
  { id: "chat", label: "Chat", Icon: MessageSquare },
  { id: "dashboard", label: "Dashboard", Icon: LayoutDashboard },
  { id: "catalog", label: "Catalog", Icon: Package },
];

export default function App() {
  const [tab, setTab] = useState("chat");
  const [business, setBusiness] = useState(null);
  const [evalMetrics, setEvalMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState(null);

  async function load() {
    setLoading(true);
    setApiError(null);
    try {
      const [b, e] = await Promise.all([api.business(), api.evalLatest()]);
      setBusiness(b);
      setEvalMetrics(e.metrics);
    } catch (err) {
      setApiError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 text-slate-500">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        Connecting to DukaanAI…
      </div>
    );
  }

  if (apiError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
        <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-600">
            <WifiOff className="h-6 w-6" />
          </div>
          <h1 className="mt-4 text-lg font-bold text-slate-900">
            Cannot reach the DukaanAI API
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-slate-500">
            The frontend is running, but the backend did not answer at{" "}
            <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-700">
              {API_URL}
            </code>
            . Start it from the repo root with{" "}
            <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-700">
              python -m dukaanai.api
            </code>{" "}
            (or set VITE_API_URL to your deployed API) and try again.
          </p>
          <p className="mt-2 text-xs text-slate-400">{apiError}</p>
          <button
            onClick={load}
            className="mt-4 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
          >
            Retry connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-slate-100 font-sans text-slate-900 antialiased">
      {/* Sidebar (desktop) */}
      <aside className="sticky top-0 hidden h-screen w-72 shrink-0 border-r border-slate-200 bg-white lg:block">
        <Sidebar
          business={business}
          evalMetrics={evalMetrics}
          tab={tab}
          onTab={setTab}
        />
      </aside>

      <div className="min-w-0 flex-1">
        {/* Top bar */}
        <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
            {/* Mobile brand */}
            <div className="flex items-center gap-2 lg:hidden">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-700 text-white">
                <Store className="h-4.5 w-4.5" />
              </div>
              <span className="font-bold">DukaanAI</span>
            </div>
            {/* Mobile nav */}
            <nav className="flex gap-1 lg:hidden">
              {NAV.map(({ id, label, Icon }) => (
                <button
                  key={id}
                  onClick={() => setTab(id)}
                  className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium ${
                    tab === id
                      ? "bg-emerald-700 text-white"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </button>
              ))}
            </nav>
            {/* Desktop status */}
            <div className="ml-auto hidden items-center gap-2 text-xs text-slate-500 lg:flex">
              <span className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 font-medium text-emerald-700">
                <Wifi className="h-3.5 w-3.5" />
                API connected
              </span>
              <span className="rounded-full bg-slate-100 px-2.5 py-1">
                {business?.name}
              </span>
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="mx-auto max-w-6xl px-4 py-5">
          {tab === "chat" && <Chat business={business} />}
          {tab === "dashboard" && <Dashboard evalMetrics={evalMetrics} />}
          {tab === "catalog" && <Catalog />}
          <footer className="mt-8 text-center text-xs text-slate-400">
            DukaanAI · Grounded bilingual AI receptionist · Every answer
            cited, nothing invented.
          </footer>
        </main>
      </div>
    </div>
  );
}
