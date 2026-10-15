# PHASE 4 REPORT — FastAPI Backend

**Date:** 2026-10-14 · **Status:** ✅ COMPLETE (all verifications passed)
**Repo:** `~/workspace/dukaanai/` · **Run:** `python -m dukaanai.api` → http://127.0.0.1:8000 (docs at `/docs`)

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + active model |
| POST | `/chat` | Run one customer message through the agent |
| GET | `/escalations?business_id=&status=open` | Owner's escalation inbox, newest first |
| POST | `/escalations/{id}/resolve` | Mark resolved (+ optional resolution note) |
| GET | `/conversations?business_id=&limit=20` | Recent conversations with message counts |
| GET | `/dashboard/summary?business_id=` | Aggregates: conversations, messages, abstentions, open escalations, top-5 questions |

Supporting changes: `db.py` gained `resolve_escalation()`, `get_escalations()`,
`get_escalation()`, `list_conversations()`, `dashboard_summary()` plus an
idempotent `resolution TEXT` migration on `escalation`. `agent.py` gained
`conversation_id` in terminal state and `customer_ref` threading through
`run_agent()` (default keeps Phase 2 behavior). CORS open for v1 demo —
production must restrict origins (commented in code).

## Verification transcripts (real curl runs)

**1. Health**
`GET /health` → `{"status":"ok","model":"openai/gpt-oss-120b"}` ✅

**2. Answerable chat**
`POST /chat {"business_id":1,"user_text":"What is the price of a cotton suit?"}`
→ 200, `abstained:false`, `conversation_id:57`, 5 citations, reply:
"Premium Cotton 3-Piece Suit: 3,250 PKR per suit [1], Cambric Cotton
3-Piece: 2,750 PKR per suit [2], …" ✅

**3. Unanswerable chat**
`POST /chat {"business_id":1,"user_text":"do you sell shoes?"}`
→ 200, `abstained:true`, `escalation_id:14`, honest abstention text ✅

**4. Escalation lifecycle**
`GET /escalations?business_id=1&status=open` → id 14 ("do you sell
shoes?") present ✅ → `POST /escalations/14/resolve
{"resolution":"We only sell fabrics, no shoes."}` → `{"id":14,
"status":"resolved"}` ✅ → open list re-queried: 14 gone ✅

**5. Dashboard summary**
`GET /dashboard/summary?business_id=1` →
`{total_conversations:58, total_messages:116, abstention_count:14,
open_escalations:13, top_questions:[…]}` — counts consistent with the
Phase 2/3 eval history plus the two test chats ✅

**6. Conversations**
`GET /conversations?business_id=1&limit=3` → newest first, correct
`customer_ref` values (`curl-test-2`, `curl-test-1` — proves the
customer_ref threading works), message counts ✅

**7. Negatives**
`POST /chat` business_id=999 → **404** ✅ · empty user_text → **422** ✅ ·
`POST /escalations/99999/resolve` → **404** ✅ ·
`GET /escalations?business_id=999` → **404** ✅

## Verification summary

| # | Check | Result |
|---|---|---|
| 1 | Server starts, /health ok | ✅ |
| 2 | /chat answerable → cited reply, abstained=false | ✅ |
| 3 | /chat unanswerable → abstained=true + escalation_id | ✅ |
| 4 | Escalation resolve lifecycle | ✅ |
| 5 | /dashboard/summary sensible counts | ✅ |
| 6 | /conversations newest-first + counts | ✅ |
| 7 | 404/422 negatives | ✅ |
| 8 | `py_compile` on api.py, db.py, agent.py | ✅ |
| 9 | Test server killed after verification | ✅ |

## Honest build notes

- The `escalation` table needed a `resolution` column for the resolve
  endpoint; added via idempotent `ALTER TABLE` migration in `init_db()`
  (SQLite has no `ADD COLUMN IF NOT EXISTS`).
- `agent.py` previously hardcoded `customer_ref="phase2-test"` and never
  returned `conversation_id`; both fixed with minimal edits, defaults
  preserve Phase 2 behavior.
- Only 2 Groq calls were made in this phase (the two /chat tests); the
  shoes abstention spent $0 (GATE1, no LLM call).
- Pre-existing open escalations (ids 10–13) are leftovers from the Phase 3
  eval run, not test pollution — the resolve test used the fresh id 14.

## Not started
Phase 5 (Streamlit frontend) and later — awaiting approval.
