"""DukaanAI demo frontend — Phase 7 redesign.

Three tabs:
  1. Customer chat  - WhatsApp-style sales demo (talks to the Phase 2 agent).
  2. Owner dashboard - KPIs, escalation inbox, conversation log, eval proof.
  3. Catalog         - Spreadsheet / photo onboarding with preview + import.

Design: the app calls run_agent() DIRECTLY (in-process), so the demo runs
with a single `streamlit run app.py`. The FastAPI backend (Phase 4) remains
the integration surface for WhatsApp later.

Redesign notes (Phase 7):
  - Branded header + trust badges, sidebar with business card and
    "how it works" so a first-time visitor understands the product
    in seconds.
  - Chat shows a verification line under every answer ("X claims
    verified from catalog") — the trust proof is the product.
  - Dashboard KPIs as styled cards; catalog tab as a 3-step flow
    with a downloadable template.
  - No agent/db/onboarding behaviour changed — presentation only.

Run:  streamlit run app.py        (from the repo root)
"""

import html
import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from dukaanai import db, onboarding
from dukaanai.agent import run_agent
from dukaanai.index import retrieve

REPO_ROOT = Path(__file__).resolve().parent
BUSINESS_ID = 1  # demo business: Chenab Cloth House

# Suggested openers: cited answer + Roman Urdu + the abstention moment,
# all inside ~30 seconds of clicking.
STARTER_CHIPS = [
    ("💬 Price in Roman Urdu", "lawn ka 3 piece suit kitne ka hai?"),
    ("🕐 Timings in English", "What are your timings?"),
    ("🚫 The abstention test", "do you sell shoes?"),
]

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

_CSS = """
<style>
/* --- brand header --- */
.brand {
    background: linear-gradient(135deg, #075e54 0%, #128c7e 55%, #25d366 130%);
    border-radius: 16px;
    padding: 22px 26px 18px 26px;
    color: #ffffff;
    margin-bottom: 6px;
}
.brand h1 {
    font-size: 30px;
    margin: 0 0 4px 0;
    letter-spacing: -0.5px;
}
.brand p {
    margin: 0;
    font-size: 15px;
    opacity: 0.92;
}
.badges { margin-top: 12px; }
.badge {
    display: inline-block;
    background: rgba(255,255,255,0.16);
    border: 1px solid rgba(255,255,255,0.35);
    border-radius: 999px;
    padding: 3px 11px;
    font-size: 12.5px;
    margin-right: 6px;
    margin-bottom: 4px;
}
/* --- KPI cards --- */
.kpi {
    background: #ffffff;
    border: 1px solid #e6e6e6;
    border-left: 4px solid #128c7e;
    border-radius: 12px;
    padding: 14px 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.kpi .kpi-label {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: #667085;
    margin-bottom: 2px;
}
.kpi .kpi-value {
    font-size: 26px;
    font-weight: 700;
    color: #101828;
    line-height: 1.1;
}
.kpi.warn { border-left-color: #f79009; }
.kpi.warn .kpi-value { color: #b54708; }
/* --- phone (WhatsApp-style chat) --- */
.phone {
    max-width: 460px;
    margin: 0 auto;
    border: 1px solid #d1d7db;
    border-radius: 20px;
    overflow: hidden;
    background: #ece5dd;
    box-shadow: 0 8px 28px rgba(0,0,0,0.14);
}
.phone-header {
    background: #075e54;
    color: #fff;
    padding: 13px 16px;
    display: flex;
    align-items: center;
    gap: 11px;
}
.avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #25d366;
    color: #075e54;
    font-size: 19px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.phone-header .who { font-weight: 600; font-size: 15.5px; line-height: 1.25; }
.phone-header .online { font-weight: 400; font-size: 12px; opacity: 0.85; }
.chat-body { padding: 14px 12px 10px 12px; min-height: 120px; }
.bubble {
    max-width: 84%;
    padding: 8px 12px;
    border-radius: 10px;
    margin: 6px 0;
    font-size: 14.5px;
    line-height: 1.5;
    word-wrap: break-word;
}
.bubble.user {
    background: #dcf8c6;
    margin-left: auto;
    border-top-right-radius: 2px;
}
.bubble.assistant {
    background: #ffffff;
    margin-right: auto;
    border-top-left-radius: 2px;
    box-shadow: 0 1px 1px rgba(0,0,0,0.08);
}
.bubble.abstained {
    background: #fff3cd;
    border: 1px solid #f0c36d;
}
.proof {
    font-size: 11.5px;
    color: #067647;
    margin-top: 4px;
}
.abstain-note {
    font-size: 12px;
    color: #8a6d1b;
    margin-top: 4px;
}
.empty-chat {
    text-align: center;
    color: #667085;
    font-size: 13.5px;
    padding: 26px 10px;
}
/* --- misc --- */
.step {
    background: #f9fafb;
    border: 1px solid #eaecf0;
    border-radius: 12px;
    padding: 12px 14px;
    margin-bottom: 8px;
    font-size: 14px;
}
.step b { color: #075e54; }
.footer {
    text-align: center;
    color: #98a2b3;
    font-size: 12.5px;
    margin-top: 28px;
}
</style>
"""


def _esc(text: str) -> str:
    """HTML-escape chat text so messages can't break the layout."""
    return html.escape(text or "").replace("\n", "<br>")


def _brand_header() -> None:
    st.markdown(
        '<div class="brand">'
        "<h1>🛍️ DukaanAI</h1>"
        "<p>Your shop's WhatsApp, answered in seconds — day and night, "
        "strictly from your verified catalog.</p>"
        '<div class="badges">'
        '<span class="badge">✅ 100% grounded — never invents a price</span>'
        '<span class="badge">🗣️ Roman Urdu + English</span>'
        '<span class="badge">🛡️ 2 verification gates</span>'
        '<span class="badge">💸 $0-cost stack</span>'
        "</div></div>",
        unsafe_allow_html=True,
    )


def _eval_metrics() -> dict | None:
    p = REPO_ROOT / "eval" / "last_run.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))["metrics"]
    except (json.JSONDecodeError, KeyError):
        return None


def _sidebar(business_name: str) -> None:
    with st.sidebar:
        st.markdown("### 🏪 Demo shop")
        st.markdown(
            f"**{business_name}**  \n"
            "Cloth house · Faisalabad  \n"
            "40 catalog items · 6 shop policies"
        )
        st.divider()
        st.markdown("### ⚙️ How it answers")
        st.markdown(
            "1. **Retrieve** — finds the matching catalog chunks\n"
            "2. **Gate 1** — no evidence? It abstains, never guesses\n"
            "3. **Answer** — replies with a `[n]` citation on every fact\n"
            "4. **Gate 2** — an independent checker verifies each claim\n"
            "5. **Escalate** — anything unverified goes to the owner"
        )
        st.divider()
        st.markdown("### 🛡️ Trust proof — latest eval")
        metrics = _eval_metrics()
        if metrics is None:
            st.info("No eval run yet — run `python eval/run_eval.py`.")
        else:
            st.markdown(
                f"- **Grounding:** {metrics['grounding']:.1f}%\n"
                f"- **Abstention precision:** "
                f"{metrics['abstention_precision']:.0f}%\n"
                f"- **Adversarial traps:** {metrics['adversarial']:.0f}%\n"
                f"- **Overall:** {metrics['overall']}"
            )
        st.divider()
        st.caption(
            "Built by Muhammad Hanzla · "
            "[GitHub](https://github.com/hanzlikhan/customerAgent)"
        )


# ---------------------------------------------------------------------------
# Tab 1: customer chat (the sales demo)
# ---------------------------------------------------------------------------

def _render_chat(messages: list[dict], business_name: str) -> None:
    """Render the phone-like WhatsApp container."""
    initial = business_name[:1].upper() if business_name else "D"
    parts = [
        '<div class="phone">',
        '<div class="phone-header">'
        f'<div class="avatar">{_esc(initial)}</div>'
        f'<div><div class="who">{_esc(business_name)}</div>'
        '<div class="online">online · replies instantly</div></div>'
        "</div>",
        '<div class="chat-body">',
    ]
    if not messages:
        parts.append(
            '<div class="empty-chat">👋 Try a suggestion above, or type '
            "your own question — in English or Roman Urdu.</div>"
        )
    for m in messages:
        if m["role"] == "user":
            parts.append(f'<div class="bubble user">{_esc(m["text"])}</div>')
        else:
            cls = ("bubble assistant abstained" if m.get("abstained")
                   else "bubble assistant")
            if m.get("abstained"):
                note = ('<div class="abstain-note">⏳ Owner notified — '
                        "they will confirm shortly.</div>")
            elif m.get("verified") is not None:
                note = (f'<div class="proof">✓ {m["verified"]} claim(s) '
                        "verified against the catalog</div>")
            else:
                note = ""
            parts.append(f'<div class="{cls}">{_esc(m["text"])}{note}</div>')
    parts += ["</div>", "</div>"]
    st.markdown("\n".join(parts), unsafe_allow_html=True)


def _send(text: str) -> None:
    """One chat turn: user message -> agent -> assistant message."""
    text = (text or "").strip()
    if not text:
        return
    st.session_state.chat.append({"role": "user", "text": text})
    with st.spinner("DukaanAI is checking the catalog…"):
        state = run_agent(BUSINESS_ID, text, customer_ref="streamlit-demo")
    verdicts = state.get("verdicts") or []
    verified = sum(1 for v in verdicts if v.get("verdict") == "SUPPORTED")
    st.session_state.chat.append({
        "role": "assistant",
        "text": state.get("final_reply", "…"),
        "abstained": bool(state.get("abstained")),
        "verified": verified if not state.get("abstained") else None,
    })


def tab_chat() -> None:
    biz = db.get_business(BUSINESS_ID)
    business_name = biz["name"] if biz else "DukaanAI demo"

    if "chat" not in st.session_state:
        st.session_state.chat = []

    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown(
        "Tap a suggestion to see it work — price in Roman Urdu, timings in "
        "English, and the moment it refuses to guess."
    )
    cols = st.columns(3)
    for i, (label, question) in enumerate(STARTER_CHIPS):
        if cols[i].button(label, key=f"chip_{i}",
                          help=question, use_container_width=True):
            _send(question)
            st.rerun()

    _render_chat(st.session_state.chat, business_name)

    typed = st.chat_input("Type a message… (English ya Roman Urdu)")
    if typed:
        _send(typed)
        st.rerun()

    if st.session_state.chat:
        if st.button("🧹 Clear chat", key="clear_chat"):
            st.session_state.chat = []
            st.rerun()

    st.caption("Demo talks to the agent in-process. "
               "Abstentions notify the owner (see Dashboard).")


# ---------------------------------------------------------------------------
# Tab 2: owner dashboard
# ---------------------------------------------------------------------------

def _kpi_card(label: str, value, warn: bool = False) -> str:
    cls = "kpi warn" if warn else "kpi"
    return (
        f'<div class="{cls}"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div></div>'
    )


def tab_dashboard() -> None:
    st.subheader("Owner dashboard")
    st.caption("Everything the shop owner needs — no AI knowledge required.")

    summary = db.dashboard_summary(BUSINESS_ID)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(_kpi_card("Conversations",
                              summary["total_conversations"]),
                    unsafe_allow_html=True)
    with k2:
        st.markdown(_kpi_card("Messages", summary["total_messages"]),
                    unsafe_allow_html=True)
    with k3:
        st.markdown(_kpi_card("Abstentions", summary["abstention_count"],
                              warn=summary["abstention_count"] > 0),
                    unsafe_allow_html=True)
    with k4:
        st.markdown(_kpi_card("Open escalations",
                              summary["open_escalations"],
                              warn=summary["open_escalations"] > 0),
                    unsafe_allow_html=True)

    if summary.get("top_questions"):
        st.divider()
        st.subheader("Top customer inquiries")
        for q in summary["top_questions"]:
            st.write(f"- **{q['question']}** ({q['times']} times)")

    st.divider()
    st.subheader("Escalation inbox")
    st.caption("Questions the AI could not verify — the owner answers "
               "these personally.")
    open_esc = db.get_escalations(BUSINESS_ID, status="open")
    if not open_esc:
        st.success("Inbox zero — nothing waiting on the owner.")
    for e in open_esc:
        with st.container(border=True):
            st.write(f"**#{e['id']}** — {e['question']}")
            st.caption(f"asked {e['created_at']}")
            if st.button("Mark resolved", key=f"resolve_{e['id']}"):
                db.resolve_escalation(e["id"], "Resolved from dashboard")
                st.rerun()

    resolved = db.get_escalations(BUSINESS_ID, status="resolved")
    if resolved:
        with st.expander(f"Resolved ({len(resolved)})"):
            for e in resolved[:10]:
                st.write(f"#{e['id']} — {e['question']}")

    st.divider()
    st.subheader("Recent conversations")
    for conv in db.list_conversations(BUSINESS_ID, limit=10):
        label = (f"#{conv['id']} · {conv['message_count']} messages · "
                 f"{conv['language'] or '?'} · {conv['started_at']}")
        with st.expander(label):
            for m in db.get_messages(conv["id"]):
                who = "🧑 Customer" if m["direction"] == "in" else "🤖 Assistant"
                extra = (f" _(verdict: {m['verdict']})_"
                         if m["direction"] == "out" and m["verdict"] else "")
                st.write(f"{who}: {m['text']}{extra}")

    st.divider()
    st.subheader("Trust proof — latest eval")
    metrics = _eval_metrics()
    if metrics is None:
        st.info("No eval run yet — run `python eval/run_eval.py` "
                "to generate metrics.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Grounding", f"{metrics['grounding']:.1f}%")
        c2.metric("Abstention precision",
                  f"{metrics['abstention_precision']:.0f}%")
        c3.metric("Adversarial", f"{metrics['adversarial']:.0f}%")
        c4.metric("Overall", metrics["overall"])
        st.caption("Every factual claim cited · never invents · "
                   "abstains when unsure.")


# ---------------------------------------------------------------------------
# Tab 3: catalog onboarding
# ---------------------------------------------------------------------------

def tab_catalog() -> None:
    st.subheader("Catalog onboarding")
    st.caption("Get any shop's price list into DukaanAI in minutes.")

    st.markdown(
        '<div class="step"><b>Step 1 —</b> Download the template and fill '
        "in your products, or snap a photo of your printed rate list "
        "(printed lists only — handwriting is not reliably readable).</div>"
        '<div class="step"><b>Step 2 —</b> Upload the file below and review '
        "the parsed preview. Rows with problems are flagged, never "
        "silently imported.</div>"
        '<div class="step"><b>Step 3 —</b> Click Import. The catalog is '
        "indexed immediately and the AI starts answering from it.</div>",
        unsafe_allow_html=True,
    )

    template = REPO_ROOT / "data" / "catalog_template.xlsx"
    if template.exists():
        st.download_button(
            "⬇️ Download spreadsheet template",
            data=template.read_bytes(),
            file_name="catalog_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument."
                 "spreadsheetml.sheet",
        )

    uploaded = st.file_uploader(
        "Catalog file", type=["xlsx", "csv", "png", "jpg", "jpeg"])
    if not uploaded:
        return

    suffix = Path(uploaded.name).suffix.lower()
    with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        tmp_path = tmp.name

    try:
        if suffix in (".xlsx", ".csv"):
            rows, errors = onboarding.parse_spreadsheet(tmp_path)
            raw_text = None
        else:
            rows, errors, raw_text = onboarding.parse_photo(tmp_path)
    except RuntimeError as e:  # e.g. tesseract missing
        st.error(str(e))
        return
    except ValueError as e:
        st.error(str(e))
        return
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if raw_text is not None:
        with st.expander("What the OCR actually read"):
            st.code(raw_text or "(nothing readable)")

    if rows:
        st.write(f"**{len(rows)} valid items** ready to import:")
        st.dataframe(pd.DataFrame([{
            "name_en": r["name_en"],
            "name_ur_roman": r["name_ur_roman"],
            "price": r["price"],
            "unit": r["unit"],
            "category": r["category"],
        } for r in rows]), use_container_width=True)
    if errors:
        st.warning(f"{len(errors)} rows have problems and will be skipped:")
        for e in errors:
            st.write(f"- {e['reason']}")

    if rows and st.button(f"Import {len(rows)} items", type="primary"):
        n = onboarding.commit_rows(
            rows, BUSINESS_ID, source_doc=f"upload:{uploaded.name}")
        st.success(f"Imported {n} items — index rebuilt.")
        # live proof: retrieve the first imported item
        hits = retrieve(BUSINESS_ID, rows[0]["name_en"], k=1)
        if hits:
            st.info(f"Live check — '{rows[0]['name_en']}' now answers from: "
                    f"{hits[0]['text'][:90]}… (similarity "
                    f"{hits[0]['similarity']})")


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="DukaanAI — Grounded AI Receptionist",
        page_icon="🛍️",
        layout="wide",
    )
    db.init_db()  # idempotent; safe if the DB already exists
    biz = db.get_business(BUSINESS_ID)
    business_name = biz["name"] if biz else "DukaanAI demo"
    _brand_header()
    _sidebar(business_name)
    chat_tab, dash_tab, catalog_tab = st.tabs(
        ["💬 Customer chat", "📊 Owner dashboard", "📦 Catalog"])
    with chat_tab:
        tab_chat()
    with dash_tab:
        tab_dashboard()
    with catalog_tab:
        tab_catalog()
    st.markdown(
        '<div class="footer">DukaanAI · Grounded bilingual AI receptionist '
        "· Every answer cited, nothing invented.</div>",
        unsafe_allow_html=True,
    )


# Guard: `import app` (tests) must not boot Streamlit or call the agent.
# `streamlit run app.py` executes the script as __main__, so the UI runs.
if __name__ == "__main__":
    main()
