import { useEffect, useRef, useState } from "react";
import {
  Bell,
  Brain,
  Check,
  ChevronDown,
  CircleAlert,
  Clock,
  FileText,
  Languages,
  Loader2,
  Search,
  Send,
  ShieldAlert,
  ShieldCheck,
  Tag,
  Trash2,
} from "lucide-react";
import { streamChat } from "../lib/api";

const STEPS = [
  { id: "understand", label: "Understanding your message", Icon: Brain },
  { id: "language", label: "Detecting language", Icon: Languages },
  { id: "retrieve", label: "Searching the catalog", Icon: Search },
  { id: "answer", label: "Drafting your answer", Icon: FileText },
  { id: "verify", label: "Verifying every claim", Icon: ShieldCheck },
];

const SUGGESTIONS = [
  {
    label: "Price in Roman Urdu",
    text: "lawn ka 3 piece suit kitne ka hai?",
    Icon: Tag,
  },
  { label: "Timings in English", text: "What are your timings?", Icon: Clock },
  { label: "The abstention test", text: "do you sell shoes?", Icon: ShieldAlert },
];

function StepRow({ step, state }) {
  const { Icon } = step;
  return (
    <li className="flex items-center gap-2.5 text-sm">
      <span
        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
          state === "done"
            ? "bg-emerald-100 text-emerald-700"
            : state === "active"
              ? "bg-emerald-600 text-white"
              : "bg-slate-100 text-slate-400"
        }`}
      >
        {state === "done" ? (
          <Check className="h-3.5 w-3.5" />
        ) : state === "active" ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Icon className="h-3.5 w-3.5" />
        )}
      </span>
      <span
        className={
          state === "pending" ? "text-slate-400" : "text-slate-700"
        }
      >
        {step.label}
      </span>
    </li>
  );
}

export default function Chat({ business }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [doneSteps, setDoneSteps] = useState([]);
  const [currentStep, setCurrentStep] = useState(null);
  const [trace, setTrace] = useState(null);
  const [error, setError] = useState(null);
  const [showSources, setShowSources] = useState({});
  const esRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    return () => {
      if (esRef.current) esRef.current.close();
    };
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, streaming, currentStep]);

  function send(text) {
    const q = (text ?? input).trim();
    if (!q || streaming) return;
    setInput("");
    setError(null);
    setMessages((m) => [...m, { role: "user", text: q }]);
    setStreaming(true);
    setDoneSteps([]);
    setCurrentStep("understand");
    setTrace(null);

    esRef.current = streamChat(q, {
      onStep: (s) => {
        setDoneSteps((prev) => (prev.includes(s.id) ? prev : [...prev, s.id]));
        const idx = STEPS.findIndex((st) => st.id === s.id);
        setCurrentStep(
          idx >= 0 && idx + 1 < STEPS.length ? STEPS[idx + 1].id : null,
        );
        if (s.id === "retrieve") {
          setTrace((t) => ({
            ...(t ?? {}),
            maxScore: s.max_score,
            chunksFound: s.chunks,
          }));
        }
      },
      onResult: (r) => {
        setMessages((m) => [
          ...m,
          {
            role: "assistant",
            text: r.reply,
            abstained: r.abstained,
            verified: r.verified,
            verdicts: r.verdicts ?? [],
            citations: r.citations ?? [],
            lang: r.lang,
          },
        ]);
        setTrace((t) => ({
          ...(t ?? {}),
          verdicts: r.verdicts ?? [],
          citations: r.citations ?? [],
          abstained: r.abstained,
        }));
        setDoneSteps(STEPS.map((s) => s.id));
        setCurrentStep(null);
        setStreaming(false);
      },
      onError: (e) => {
        setError(e.detail || "Something went wrong. Please try again.");
        setStreaming(false);
        setCurrentStep(null);
      },
    });
  }

  const businessName = business?.name ?? "DukaanAI demo";
  const initial = businessName.charAt(0).toUpperCase();

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
      {/* Chat panel */}
      <div className="flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {/* Chat header */}
        <div className="flex items-center gap-3 border-b border-slate-200 bg-emerald-800 px-4 py-3 text-white">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500 text-lg font-bold">
            {initial}
          </div>
          <div className="min-w-0">
            <div className="truncate font-semibold">{businessName}</div>
            <div className="flex items-center gap-1.5 text-xs text-emerald-100">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              online · replies instantly
            </div>
          </div>
          {messages.length > 0 && (
            <button
              onClick={() => {
                setMessages([]);
                setTrace(null);
                setError(null);
              }}
              className="ml-auto flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-emerald-100 hover:bg-emerald-700"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Clear chat
            </button>
          )}
        </div>

        {/* Suggestions */}
        <div className="flex flex-wrap gap-2 border-b border-slate-200 bg-slate-50 px-4 py-3">
          {SUGGESTIONS.map(({ label, text, Icon }) => (
            <button
              key={label}
              onClick={() => send(text)}
              disabled={streaming}
              className="flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition-colors hover:border-emerald-500 hover:text-emerald-700 disabled:opacity-50"
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </button>
          ))}
        </div>

        {/* Messages */}
        <div
          ref={scrollRef}
          className="scroll-slim h-[440px] overflow-y-auto bg-[#ece5dd] px-4 py-4"
        >
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center text-center text-sm text-slate-500">
              <p className="max-w-xs">
                Tap a suggestion above, or type your own question — in
                English or Roman Urdu.
              </p>
              <p className="mt-2 max-w-xs text-xs text-slate-400">
                Every answer comes from the shop&apos;s verified catalog,
                with citations. If it can&apos;t verify, it says so.
              </p>
            </div>
          )}
          <div className="flex flex-col gap-2.5">
            {messages.map((m, i) =>
              m.role === "user" ? (
                <div
                  key={i}
                  className="animate-fade-up ml-auto max-w-[85%] rounded-xl rounded-tr-sm bg-[#dcf8c6] px-3.5 py-2.5 text-sm leading-relaxed text-slate-900 shadow-sm"
                >
                  {m.text}
                </div>
              ) : (
                <div
                  key={i}
                  className={`animate-fade-up mr-auto max-w-[88%] rounded-xl rounded-tl-sm px-3.5 py-2.5 text-sm leading-relaxed shadow-sm ${
                    m.abstained
                      ? "border border-amber-300 bg-amber-50 text-slate-900"
                      : "bg-white text-slate-900"
                  }`}
                >
                  <div>{m.text}</div>
                  {m.abstained ? (
                    <div className="mt-1.5 flex items-center gap-1.5 text-xs text-amber-800">
                      <Bell className="h-3.5 w-3.5" />
                      Owner notified — they will confirm shortly.
                    </div>
                  ) : (
                    <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
                      <span className="flex items-center gap-1 text-xs font-medium text-emerald-700">
                        <ShieldCheck className="h-3.5 w-3.5" />
                        {m.verified} claim(s) verified against the catalog
                      </span>
                      {m.citations?.length > 0 && (
                        <button
                          onClick={() =>
                            setShowSources((s) => ({ ...s, [i]: !s[i] }))
                          }
                          className="flex items-center gap-0.5 text-xs text-slate-500 hover:text-slate-700"
                        >
                          View sources ({m.citations.length})
                          <ChevronDown
                            className={`h-3.5 w-3.5 transition-transform ${
                              showSources[i] ? "rotate-180" : ""
                            }`}
                          />
                        </button>
                      )}
                    </div>
                  )}
                  {showSources[i] && m.citations?.length > 0 && (
                    <div className="mt-2 space-y-1.5 border-t border-slate-100 pt-2">
                      {m.citations.map((c, j) => (
                        <div
                          key={j}
                          className="rounded-lg bg-slate-50 px-2.5 py-2 text-xs leading-relaxed text-slate-600"
                        >
                          <span className="font-semibold text-slate-700">
                            [{j + 1}] · {(c.similarity * 100).toFixed(0)}%
                            match
                          </span>{" "}
                          — {c.text}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ),
            )}
            {streaming && (
              <div className="animate-fade-up mr-auto flex items-center gap-2 rounded-xl rounded-tl-sm bg-white px-3.5 py-3 text-sm text-slate-500 shadow-sm">
                <span className="flex gap-1">
                  <span className="typing-dot h-2 w-2 rounded-full bg-slate-400" />
                  <span className="typing-dot h-2 w-2 rounded-full bg-slate-400" />
                  <span className="typing-dot h-2 w-2 rounded-full bg-slate-400" />
                </span>
                {currentStep &&
                  STEPS.find((s) => s.id === currentStep)?.label}
              </div>
            )}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 border-t border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">
            <CircleAlert className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        {/* Input */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
          className="flex items-center gap-2 border-t border-slate-200 bg-white px-3 py-3"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={streaming}
            placeholder="Type a message… (English ya Roman Urdu)"
            className="min-w-0 flex-1 rounded-full border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 disabled:bg-slate-50"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-700 text-white transition-colors hover:bg-emerald-800 disabled:opacity-40"
            aria-label="Send message"
          >
            {streaming ? (
              <Loader2 className="h-4.5 w-4.5 animate-spin" />
            ) : (
              <Send className="h-4.5 w-4.5" />
            )}
          </button>
        </form>
      </div>

      {/* Live agent trace */}
      <div className="flex flex-col gap-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-1 flex items-center gap-2 font-semibold text-slate-900">
            <Brain className="h-4.5 w-4.5 text-emerald-700" />
            Live agent trace
          </div>
          <p className="mb-3 text-xs text-slate-500">
            Watch each step complete in real time as the agent works.
          </p>
          <ul className="flex flex-col gap-2.5">
            {STEPS.map((s) => (
              <StepRow
                key={s.id}
                step={s}
                state={
                  doneSteps.includes(s.id)
                    ? "done"
                    : currentStep === s.id
                      ? "active"
                      : "pending"
                }
              />
            ))}
          </ul>
          {trace?.maxScore != null && (
            <div className="mt-4 border-t border-slate-100 pt-3">
              <div className="flex justify-between text-xs text-slate-500">
                <span>Best catalog match</span>
                <span className="font-semibold text-slate-700">
                  {(trace.maxScore * 100).toFixed(0)}%
                </span>
              </div>
              <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-full rounded-full ${
                    trace.maxScore >= 0.4 ? "bg-emerald-600" : "bg-amber-500"
                  }`}
                  style={{ width: `${Math.min(100, trace.maxScore * 100)}%` }}
                />
              </div>
              <p className="mt-1.5 text-xs text-slate-400">
                {trace.chunksFound} chunks retrieved · below 40% the agent
                abstains instead of guessing.
              </p>
            </div>
          )}
          {trace?.verdicts?.length > 0 && (
            <div className="mt-4 border-t border-slate-100 pt-3">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Claim verdicts
              </div>
              <ul className="flex flex-col gap-2">
                {trace.verdicts.map((v, i) => (
                  <li key={i} className="text-xs leading-relaxed text-slate-600">
                    <span
                      className={`mr-1.5 inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-semibold ${
                        v.verdict === "SUPPORTED"
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-red-50 text-red-700"
                      }`}
                    >
                      {v.verdict === "SUPPORTED" ? (
                        <Check className="h-3 w-3" />
                      ) : (
                        <CircleAlert className="h-3 w-3" />
                      )}
                      {v.verdict}
                    </span>
                    {v.claim}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {!trace && !streaming && (
            <p className="mt-3 border-t border-slate-100 pt-3 text-xs leading-relaxed text-slate-400">
              Send a message to see the agent retrieve, answer and verify —
              live.
            </p>
          )}
        </div>

        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
          <div className="flex items-center gap-2 font-semibold text-emerald-900">
            <ShieldCheck className="h-4.5 w-4.5" />
            The promise
          </div>
          <p className="mt-1.5 text-sm leading-relaxed text-emerald-800">
            Every factual claim carries a citation to the exact catalog
            chunk it came from. No citation, no answer — the question goes
            to the owner instead.
          </p>
        </div>
      </div>
    </div>
  );
}
