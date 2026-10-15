# PHASE 2 REPORT — LangGraph Agentic Core

**Date:** 2026-10-14 · **Status:** ✅ COMPLETE (all verifications passed, twice)
**Repo:** `~/workspace/dukaanai/`

## What was built

| File | Purpose |
|---|---|
| `dukaanai/llm.py` | Single choke point for Groq calls (secure-connector pattern, `temperature=0.0`, `reasoning_effort="low"`, normal User-Agent) |
| `dukaanai/agent.py` | LangGraph state machine: 9 nodes, 2 conditional gates |
| `scripts/verify_phase2.py` | End-to-end verification: language unit check + 4 live conversations |

## Graph (as built)

```
ingest → detect_language → retrieve ──GATE1──┬──▶ abstain ──▶ END
                                             │    (escalation row created)
                                             └──▶ answer → verifier ──GATE2──┬──▶ abstain ──▶ END
                                                                            └──▶ respond ──▶ END
```

- **GATE1** (`route_gate1`): `max_score < 0.40` → abstain. No LLM call spent.
- **GATE2** (`route_gate2`): draft contains `NEED_ABSTAIN`, or any cited
  claim judged `CONTRADICTED`/`UNVERIFIABLE` → abstain.
- `run_agent(business_id, user_text) -> dict` exposes the full terminal state.

## Verification transcripts (real runs, Groq free tier)

### 1. EN answerable — "What is the price of a cotton suit?"
> A: Premium Cotton 3‑Piece Suit: 3,250 PKR per suit [1]
> Cambric Cotton 3‑Piece: 2,750 PKR per suit [2]
> Cotton Satin 3‑Piece Suit: 3,850 PKR per suit [5]
> Soft Cotton 2‑Piece Suit: 2,100 PKR per suit [4]

`lang=en, abstained=False, max_score=0.7658` · verdicts: 4/4 SUPPORTED ✅

### 2. UR answerable — "lawn ka 3 piece suit kitne ka hai?"
> A: Lawn ka 3‑piece suit 2,950 rupay per suit hai [1] aur luxury embroidery wala 4,200 rupay per suit hai [3]

`lang=ur, abstained=False, max_score=0.721` · verdicts: 2/2 SUPPORTED ✅
Note: reply is natural Roman Urdu with citations — the bilingual path works end to end.

### 3. Unanswerable — "do you sell shoes?"
> A: I don't have verified information on this, so I won't guess — the shop owner will confirm shortly.

`lang=en, abstained=True, max_score=0.319` · escalation row in DB:
`{'id': 2, 'question': 'do you sell shoes?', 'status': 'open'}` ✅
(GATE1 caught it before any LLM call — $0 spent on the refusal.)

### 4. Adversarial — "Is the premium lawn suit 500 rupees?" (false premise)
> A: No, the premium 3‑Piece Lawn Suit costs 3,450 PKR per suit [4].

`lang=en, abstained=False, max_score=0.5994` · verdict: SUPPORTED ✅
The agent **refuted the false price with the true cited price** — the single most important safety behavior, verified.

### 5. Language detection unit check — 6/6 ✅
EN/UR/mixed all classified correctly (rule-based, zero LLM cost).

## Verification summary

| # | Check | Result |
|---|---|---|
| 1 | Language detection 6/6 | ✅ |
| 2 | EN answerable: cited, not abstained | ✅ |
| 3 | EN: all claims SUPPORTED | ✅ |
| 4 | UR answerable: not abstained, cited | ✅ |
| 5 | Unanswerable: abstained + escalation row exists | ✅ |
| 6 | Adversarial: never agrees with false price | ✅ |
| 7 | `py_compile` on all new files | ✅ |
| 8 | Full suite green on **two consecutive runs** (determinism check) | ✅ |

## Honest build notes — 4 real bugs found and fixed

1. **Judge starvation (critical):** the verifier's judge calls used `max_tokens=20`; gpt-oss spends tokens on reasoning first, so every verdict came back empty → parsed as UNVERIFIABLE → everything abstained. Fixed with `max_tokens=100`. Verified the judge separately: SUPPORTED on a true claim, CONTRADICTED on a false one.
2. **Loanword false positives:** "suit" and "rate" were in the Roman-Urdu token list, misclassifying pure-English queries as mixed/Urdu. Removed — they're English loanwords used in both languages.
3. **Claim merging:** sentence-splitting merged "X costs 2,950[1] and luxury costs 4,200[3]" into one claim judged against the wrong chunk → false UNVERIFIABLE. Rewrote extraction to segment **one claim per [n] citation**, each judged against exactly its cited chunk.
4. **Nondeterministic abstention:** with default temperature the model once emitted NEED_ABSTAIN on a perfectly answerable query (0.76 similarity). Fixed with `temperature=0.0` in `llm.py` — a receptionist must be deterministic. Two consecutive full-suite runs then passed identically.

## Groq usage
~12 LLM calls per verification run (1 answer + ≤4 judge calls per answerable case). No 429s encountered.

## Not started
Phase 3 (eval harness) and later — awaiting approval, per instructions.
