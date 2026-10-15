"""DukaanAI demo frontend (Phase 5).

Two tabs:
  1. Customer chat  - WhatsApp-style sales demo (talks to the Phase 2 agent).
  2. Owner dashboard - KPIs, escalation inbox, conversation log, eval proof.

Design decision: the app calls run_agent() DIRECTLY (in-process), so the
demo runs with a single `streamlit run app.py`. The FastAPI backend
(Phase 4) remains the integration surface for WhatsApp later.

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
    "lawn ka 3 piece suit kitne ka hai?",
    "What are your timings?",
    "do you sell shoes?",
]

# ---------------------------------------------------------------------------
# Styling (WhatsApp-like)
# ---------------------------------------------------------------------------

_CSS = """
<style>
.phone {
    max-width: 430px;
    margin: 0 auto;
    border: 1px solid #d1d7db;
    border-radius: 18px;
    overflow: hidden;
    background: #ece5dd;
    box-shadow: 0 4px 18px rgba(0,0,0,0.12);
}
.phone-header {
    background: #075e54;
    color: #fff;
    padding: 12px 16px;
    font-weight: 600;
    font-size: 16px;
}
.phone-header .online { font-weight: 400; font-size: 12px; opacity: 0.85; }
.chat-body { padding: 14px 12px 8px 12px; }
.bubble {
    max-width: 82%;
    padding: 8px 12px;
    border-radius: 10px;
    margin: 6px 0;
    font-size: 14px;
    line-height: 1.45;
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
.abstain-note {
    font-size: 12px;
    color: #8a6d1b;
    margin-top: 4px;
}
</style>
"""


def _esc(text: str) -> str:
    """HTML-escape chat text so messages can't break the layout."""
    return html.escape(text or "").replace("\n", "<br>")


def _render_chat(messages: list[dict], business_name: str) -> None:
    """Render the phone-like WhatsApp container."""
    parts = [
        '<div class="phone">',
        f'<div class="phone-header">{_esc(business_name)}'
        '<br><span class="online">online</span></div>',
        '<div class="chat-body">',
    ]
    for m in messages:
        if m["role"] == "user":
            parts.append(
                f'<div class="bubble user">{_esc(m["text"])}</div>')
        else:
            cls = "bubble assistant abstained" if m.get("abstained") \
                else "bubble assistant"
            note = ('<div class="abstain-note">⏳ Owner notified — '
                    'they will confirm shortly.</div>'
                    if m.get("abstained") else "")
            parts.append(
                f'<div class="{cls}">{_esc(m["text"])}{note}</div>')
    parts += ["</div>", "</div>"]
    st.markdown("\n".join(parts), unsafe_allow_html=True)


def _send(text: str) -> None:
    """One chat turn: user message -> agent -> assistant message."""
    text = (text or "").strip()
    if not text:
        return
    st.session_state.chat.append({"role": "user", "text": text})
    with st.spinner("typing…"):
        state = run_agent(BUSINESS_ID, text, customer_ref="streamlit-demo")
    st.session_state.chat.append({
        "role": "assistant",
        "text": state.get("final_reply", "…"),
        "abstained": bool(state.get("abstained")),
    })


# ---------------------------------------------------------------------------
# Tab 1: customer chat (the sales demo)
# ---------------------------------------------------------------------------

def tab_chat() -> None:
    biz = db.get_business(BUSINESS_ID)
    business_name = biz["name"] if biz else "DukaanAI demo"

    if "chat" not in st.session_state:
        st.session_state.chat = []

    st.markdown(_CSS, unsafe_allow_html=True)

    cols = st.columns(3)
    for i, chip in enumerate(STARTER_CHIPS):
        # Short label, full question sent on click.
        label = chip[:28] + ("…" if len(chip) > 28 else "")
        if cols[i].button(label, key=f"chip_{i}",
                          help=chip, use_container_width=True):
            _send(chip)

    _render_chat(st.session_state.chat, business_name)

    typed = st.chat_input("Type a message…")
    if typed:
        _send(typed)
        st.rerun()

    st.caption("Demo talks to the Phase 2 agent in-process. "
               "Abstentions notify the owner (see Dashboard).")


# ---------------------------------------------------------------------------
# Tab 2: owner dashboard
# ---------------------------------------------------------------------------

def _eval_metrics() -> dict | None:
    p = REPO_ROOT / "eval" / "last_run.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))["metrics"]
    except (json.JSONDecodeError, KeyError):
        return None


def tab_dashboard() -> None:
    st.subheader("Owner dashboard")

    summary = db.dashboard_summary(BUSINESS_ID)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Conversations", summary["total_conversations"])
    k2.metric("Messages", summary["total_messages"])
    k3.metric("Abstentions", summary["abstention_count"])
    k4.metric("Open escalations", summary["open_escalations"])

    if summary.get("top_questions"):
        st.divider()
        st.subheader("Top customer inquiries")
        for q in summary["top_questions"]:
            st.write(f"- **{q['question']}** ({q['times']} times)")

    st.divider()
    st.subheader("Escalation inbox")
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
    st.caption("Upload a spreadsheet (.xlsx / .csv) or a photo of a printed "
               "rate list (.png / .jpg). Review the parsed preview, then "
               "import. Handwriting is not reliably readable — printed "
               "lists only.")

    uploaded = st.file_uploader(
        "Catalog file", type=["xlsx", "csv", "png", "jpg", "jpeg"])
    if not uploaded:
        st.info("No file yet. See `data/catalog_template.xlsx` for the "
                "spreadsheet format.")
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

    st.session_state["catalog_preview"] = rows
    st.session_state["catalog_errors"] = errors

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
        st.session_state.pop("catalog_preview", None)


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def main() -> None:
    db.init_db()  # idempotent; safe if the DB already exists
    st.set_page_config(page_title="DukaanAI demo", layout="centered")
    st.title("DukaanAI — AI receptionist demo")
    chat_tab, dash_tab, catalog_tab = st.tabs(
        ["💬 Customer chat", "📊 Owner dashboard", "📦 Catalog"])
    with chat_tab:
        tab_chat()
    with dash_tab:
        tab_dashboard()
    with catalog_tab:
        tab_catalog()


# Guard: `import app` (tests) must not boot Streamlit or call the agent.
# `streamlit run app.py` executes the script as __main__, so the UI runs.
if __name__ == "__main__":
    main()
