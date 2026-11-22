import {
  ExternalLink,
  FileText,
  Inbox,
  LayoutDashboard,
  MapPin,
  MessageSquare,
  Package,
  Search,
  ShieldAlert,
  ShieldCheck,
  Store,
} from "lucide-react";

const NAV = [
  { id: "chat", label: "Customer chat", Icon: MessageSquare },
  { id: "dashboard", label: "Owner dashboard", Icon: LayoutDashboard },
  { id: "catalog", label: "Catalog", Icon: Package },
];

const HOW_IT_WORKS = [
  { Icon: Search, text: "Retrieve — finds the matching catalog chunks" },
  { Icon: ShieldAlert, text: "Gate 1 — no evidence? It abstains, never guesses" },
  { Icon: FileText, text: "Answer — replies with a [n] citation on every fact" },
  { Icon: ShieldCheck, text: "Gate 2 — an independent checker verifies each claim" },
  { Icon: Inbox, text: "Escalate — anything unverified goes to the owner" },
];

export default function Sidebar({ business, evalMetrics, tab, onTab }) {
  return (
    <div className="flex h-full flex-col gap-6 overflow-y-auto p-5">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-700 text-white shadow-sm">
          <Store className="h-6 w-6" />
        </div>
        <div>
          <div className="text-lg font-bold leading-tight text-slate-900">
            DukaanAI
          </div>
          <div className="text-xs leading-tight text-slate-500">
            Grounded AI receptionist
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-1">
        {NAV.map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => onTab(id)}
            className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
              tab === id
                ? "bg-emerald-700 text-white shadow-sm"
                : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            <Icon className="h-4.5 w-4.5" />
            {label}
          </button>
        ))}
      </nav>

      {/* Demo shop */}
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Demo shop
        </div>
        <div className="font-semibold text-slate-900">
          {business?.name ?? "Loading…"}
        </div>
        {business?.location && (
          <div className="mt-1 flex items-start gap-1.5 text-xs text-slate-500">
            <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>{business.location}</span>
          </div>
        )}
        {business && (
          <div className="mt-3 flex gap-4 text-xs text-slate-600">
            <span className="flex items-center gap-1">
              <Package className="h-3.5 w-3.5" />
              {business.catalog_items} items
            </span>
            <span className="flex items-center gap-1">
              <FileText className="h-3.5 w-3.5" />
              {business.policies} policies
            </span>
          </div>
        )}
      </div>

      {/* How it answers */}
      <div>
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          How it answers
        </div>
        <ol className="flex flex-col gap-2.5">
          {HOW_IT_WORKS.map(({ Icon, text }, i) => (
            <li key={i} className="flex items-start gap-2.5 text-sm text-slate-600">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-emerald-50 text-emerald-700">
                <Icon className="h-3.5 w-3.5" />
              </span>
              <span>{text}</span>
            </li>
          ))}
        </ol>
      </div>

      {/* Trust proof */}
      <div>
        <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
          <ShieldCheck className="h-3.5 w-3.5" />
          Trust proof — latest eval
        </div>
        {evalMetrics ? (
          <ul className="space-y-1 text-sm text-slate-600">
            <li className="flex justify-between">
              <span>Grounding</span>
              <span className="font-semibold text-slate-900">
                {evalMetrics.grounding.toFixed(1)}%
              </span>
            </li>
            <li className="flex justify-between">
              <span>Abstention precision</span>
              <span className="font-semibold text-slate-900">
                {evalMetrics.abstention_precision.toFixed(0)}%
              </span>
            </li>
            <li className="flex justify-between">
              <span>Adversarial traps</span>
              <span className="font-semibold text-slate-900">
                {evalMetrics.adversarial.toFixed(0)}%
              </span>
            </li>
            <li className="flex justify-between">
              <span>Overall</span>
              <span className="font-semibold text-slate-900">
                {evalMetrics.overall}
              </span>
            </li>
          </ul>
        ) : (
          <p className="text-sm text-slate-500">No eval run yet.</p>
        )}
      </div>

      <div className="mt-auto border-t border-slate-200 pt-4 text-xs text-slate-400">
        <a
          href="https://github.com/hanzlikhan/customerAgent"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1.5 hover:text-slate-600"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          hanzlikhan/customerAgent
        </a>
        <p className="mt-1.5">Built by Muhammad Hanzla</p>
      </div>
    </div>
  );
}
