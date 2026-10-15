# PHASE 5 REPORT — Streamlit Frontend

**Date:** 2026-10-14 · **Status:** ✅ COMPLETE (all verifications passed)
**Repo:** `~/workspace/dukaanai/` · **App:** `app.py`
**Run:** `streamlit run app.py` (from the repo root)

## Design decision

The Streamlit app calls `run_agent()` **directly, in-process** — not via
HTTP. The demo therefore runs with a single `streamlit run app.py`
command and no second server. The FastAPI backend (Phase 4) remains the
integration surface for the WhatsApp Cloud API later; it was not
duplicated or bypassed, just not needed for the demo.

## What was built

**Tab 1 — 💬 Customer chat (the sales demo)**
- WhatsApp-style phone container: business header
  ("Chenab Cloth House · online"), user bubbles right (green),
  assistant bubbles left (white), WhatsApp palette CSS.
- Three starter chips: a Roman Urdu price question, an English timing
  question, and "do you sell shoes?" — cited answer + Urdu + the
  abstention moment inside ~30 seconds of clicking.
- `st.chat_input` for free typing; "typing…" spinner while the agent runs.
- Abstentions render in a distinct amber style with a
  "⏳ Owner notified" note — the demo's key moment, made visible.

**Tab 2 — 📊 Owner dashboard**
- KPI row from `db.dashboard_summary(1)`: conversations, messages,
  abstentions, open escalations.
- Escalation inbox: open items newest-first, each with a working
  Resolve button; resolved items collapsed in an expander.
- Conversation log: 10 most recent conversations as expanders with
  full message threads and per-message verdicts.
- Trust-proof eval panel: reads `eval/last_run.json` and shows
  grounding / abstention / adversarial / overall; graceful message if
  the file is absent.

**Supporting change:** added `db.get_messages(conversation_id)` (the one
read helper the dashboard needed); `py_compile` clean.

## Verification results (all real runs)

| # | Check | Result |
|---|---|---|
| 1 | `python -m py_compile app.py` (+ db.py) | ✅ clean |
| 2 | `python -c "import app"` — no server boot, no Groq calls | ✅ import ok, `main()` not executed (guarded by `if __name__ == "__main__"`) |
| 3 | Headless boot: `streamlit run app.py --server.headless true`, curl `/_stcore/health` | ✅ HTTP 200, server killed afterwards |
| 4 | Logic test (no Streamlit): `run_agent(1, "What are your timings?")` | ✅ `final_reply` str with `[1]` citation, `abstained=False`, verdicts `['SUPPORTED']`, `conversation_id=59` — exactly the shape the UI renders |

No screenshot taken (no display on this VM); the health check plus the
logic test are stated as the evidence instead.

## How to run (Windows)

```
copy .env.example .env   (paste Groq key — not needed for the demo UI boot,
                          only when sending a chat message)
venv\Scripts\activate
streamlit run app.py
```
Then open the printed localhost URL. The demo business is pre-seeded;
clicking the three starter chips runs the full 30-second sales story.

## Honest build notes

- Groq calls happen **only** when a chat message is sent (chip or typed).
  Booting the app, opening the dashboard, and resolving escalations are
  all local/DB operations — $0.
- Chat text is HTML-escaped before rendering so customer messages can't
  break the bubble layout.
- The `NO_PROXY=[::1]` VM quirk from Phases 1–3 applies to the
  HuggingFace client here too; worked around with
  `env -u no_proxy -u NO_PROXY` on this VM only. Windows unaffected.
- One earlier edit accidentally dropped a docstring in db.py; caught and
  restored immediately, verified by re-read.

## Not started
Phase 6 (catalog onboarding: Excel/CSV upload + photo OCR) and later —
awaiting approval, per instructions.
