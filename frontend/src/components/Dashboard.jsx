import { useCallback, useEffect, useState } from "react";
import {
  Check,
  ChevronDown,
  CircleAlert,
  Inbox,
  Loader2,
  MessageCircle,
  MessagesSquare,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { api } from "../lib/api";

function KpiCard({ Icon, label, value, warn }) {
  return (
    <div
      className={`rounded-2xl border bg-white p-4 shadow-sm ${
        warn ? "border-amber-200" : "border-slate-200"
      }`}
    >
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        <Icon className={`h-4 w-4 ${warn ? "text-amber-600" : "text-emerald-700"}`} />
        {label}
      </div>
      <div
        className={`mt-2 text-3xl font-bold ${
          warn ? "text-amber-700" : "text-slate-900"
        }`}
      >
        {value}
      </div>
    </div>
  );
}

export default function Dashboard({ evalMetrics }) {
  const [summary, setSummary] = useState(null);
  const [openEsc, setOpenEsc] = useState([]);
  const [resolvedEsc, setResolvedEsc] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [openConvId, setOpenConvId] = useState(null);
  const [convMessages, setConvMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [resolvingId, setResolvingId] = useState(null);
  const [showResolved, setShowResolved] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async (quiet = false) => {
    if (!quiet) setRefreshing(true);
    try {
      const [s, o, r, c] = await Promise.all([
        api.summary(),
        api.escalations(undefined, "open"),
        api.escalations(undefined, "resolved"),
        api.conversations(undefined, 10),
      ]);
      setSummary(s);
      setOpenEsc(o);
      setResolvedEsc(r);
      setConversations(c);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(() => load(true), 15000);
    return () => clearInterval(t);
  }, [load]);

  async function resolve(id) {
    setResolvingId(id);
    try {
      await api.resolveEscalation(id, "Resolved from dashboard");
      await load(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setResolvingId(null);
    }
  }

  async function toggleConversation(id) {
    if (openConvId === id) {
      setOpenConvId(null);
      return;
    }
    setOpenConvId(id);
    try {
      setConvMessages(await api.messages(id));
    } catch (e) {
      setError(e.message);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-8 text-slate-500 shadow-sm">
        <Loader2 className="h-5 w-5 animate-spin" />
        Loading dashboard…
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Owner dashboard</h2>
          <p className="text-sm text-slate-500">
            Everything the shop owner needs — no AI knowledge required.
            Refreshes automatically.
          </p>
        </div>
        <button
          onClick={() => load()}
          disabled={refreshing}
          className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:border-emerald-500 hover:text-emerald-700 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <CircleAlert className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <KpiCard
          Icon={MessagesSquare}
          label="Conversations"
          value={summary?.total_conversations ?? 0}
        />
        <KpiCard
          Icon={MessageCircle}
          label="Messages"
          value={summary?.total_messages ?? 0}
        />
        <KpiCard
          Icon={ShieldAlert}
          label="Abstentions"
          value={summary?.abstention_count ?? 0}
          warn={(summary?.abstention_count ?? 0) > 0}
        />
        <KpiCard
          Icon={Inbox}
          label="Open escalations"
          value={summary?.open_escalations ?? 0}
          warn={(summary?.open_escalations ?? 0) > 0}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Top questions */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center gap-2 font-semibold text-slate-900">
            <TrendingUp className="h-4.5 w-4.5 text-emerald-700" />
            Top customer inquiries
          </div>
          {summary?.top_questions?.length ? (
            <ul className="flex flex-col gap-2">
              {summary.top_questions.map((q, i) => (
                <li
                  key={i}
                  className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2 text-sm"
                >
                  <span className="text-slate-700">{q.question}</span>
                  <span className="shrink-0 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800">
                    {q.times}×
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">
              No customer questions yet — try the chat tab.
            </p>
          )}
        </div>

        {/* Eval proof */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center gap-2 font-semibold text-slate-900">
            <ShieldCheck className="h-4.5 w-4.5 text-emerald-700" />
            Trust proof — latest eval
          </div>
          {evalMetrics ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: "Grounding", value: `${evalMetrics.grounding.toFixed(1)}%` },
                { label: "Abstention", value: `${evalMetrics.abstention_precision.toFixed(0)}%` },
                { label: "Adversarial", value: `${evalMetrics.adversarial.toFixed(0)}%` },
                { label: "Overall", value: evalMetrics.overall },
              ].map((m) => (
                <div
                  key={m.label}
                  className="rounded-xl bg-slate-50 px-3 py-2.5 text-center"
                >
                  <div className="text-lg font-bold text-slate-900">{m.value}</div>
                  <div className="text-xs text-slate-500">{m.label}</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No eval run yet.</p>
          )}
          <p className="mt-3 text-xs text-slate-400">
            Every factual claim cited · never invents · abstains when unsure.
          </p>
        </div>
      </div>

      {/* Escalation inbox */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-1 flex items-center gap-2 font-semibold text-slate-900">
          <Inbox className="h-4.5 w-4.5 text-emerald-700" />
          Escalation inbox
        </div>
        <p className="mb-3 text-sm text-slate-500">
          Questions the AI could not verify — the owner answers these
          personally.
        </p>
        {openEsc.length === 0 ? (
          <p className="rounded-xl bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
            Inbox zero — nothing waiting on the owner.
          </p>
        ) : (
          <ul className="flex flex-col gap-2.5">
            {openEsc.map((e) => (
              <li
                key={e.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 px-3.5 py-3"
              >
                <div className="min-w-0">
                  <div className="text-sm font-medium text-slate-900">
                    <span className="text-slate-400">#{e.id}</span> {e.question}
                  </div>
                  <div className="text-xs text-slate-400">
                    asked {e.created_at}
                  </div>
                </div>
                <button
                  onClick={() => resolve(e.id)}
                  disabled={resolvingId === e.id}
                  className="flex shrink-0 items-center gap-1.5 rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-800 disabled:opacity-50"
                >
                  {resolvingId === e.id ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Check className="h-3.5 w-3.5" />
                  )}
                  Mark resolved
                </button>
              </li>
            ))}
          </ul>
        )}
        {resolvedEsc.length > 0 && (
          <div className="mt-3">
            <button
              onClick={() => setShowResolved((s) => !s)}
              className="flex items-center gap-1 text-sm font-medium text-slate-600 hover:text-slate-900"
            >
              Resolved ({resolvedEsc.length})
              <ChevronDown
                className={`h-4 w-4 transition-transform ${
                  showResolved ? "rotate-180" : ""
                }`}
              />
            </button>
            {showResolved && (
              <ul className="mt-2 flex flex-col gap-1.5">
                {resolvedEsc.slice(0, 10).map((e) => (
                  <li key={e.id} className="text-sm text-slate-500">
                    <span className="text-slate-400">#{e.id}</span> {e.question}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {/* Recent conversations */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-3 flex items-center gap-2 font-semibold text-slate-900">
          <MessagesSquare className="h-4.5 w-4.5 text-emerald-700" />
          Recent conversations
        </div>
        {conversations.length === 0 ? (
          <p className="text-sm text-slate-500">No conversations yet.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {conversations.map((c) => (
              <li
                key={c.id}
                className="overflow-hidden rounded-xl border border-slate-200"
              >
                <button
                  onClick={() => toggleConversation(c.id)}
                  className="flex w-full items-center justify-between gap-3 px-3.5 py-2.5 text-left text-sm hover:bg-slate-50"
                >
                  <span className="text-slate-700">
                    <span className="font-medium text-slate-900">
                      #{c.id}
                    </span>{" "}
                    · {c.message_count} messages · {c.language ?? "?"} ·{" "}
                    {c.started_at}
                  </span>
                  <ChevronDown
                    className={`h-4 w-4 shrink-0 text-slate-400 transition-transform ${
                      openConvId === c.id ? "rotate-180" : ""
                    }`}
                  />
                </button>
                {openConvId === c.id && (
                  <div className="flex flex-col gap-1.5 border-t border-slate-100 bg-slate-50 px-3.5 py-3">
                    {convMessages.map((m) => (
                      <div key={m.id} className="text-sm">
                        <span className="font-medium text-slate-700">
                          {m.direction === "in" ? "Customer" : "Assistant"}:
                        </span>{" "}
                        <span className="text-slate-600">{m.text}</span>
                        {m.direction === "out" && m.verdict && (
                          <span className="text-xs text-slate-400">
                            {" "}
                            (verdict: {m.verdict})
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
