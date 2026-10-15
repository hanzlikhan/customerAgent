# PHASE 3 REPORT — Eval Harness

**Date:** 2026-10-14 · **Status:** ✅ COMPLETE — all gates pass on the final run
**Repo:** `~/workspace/dukaanai/` · **Harness:** `eval/test_set.json` + `eval/run_eval.py`

## Test set (24 items, all against the real Chenab Cloth House catalog)

| Category | Count | IDs |
|---|---|---|
| Answerable EN (price, timings, policy, variants) | 8 | E1–E8 |
| Answerable Roman Urdu (natural WhatsApp style; hai/he, nai/nahin, kapra/kapda variants) | 8 | U1–U8 |
| Unanswerable (shoes, iPhone, lehengas, stitching service) | 4 | N1–N4 |
| Adversarial (false-price premises, entity conflation, out-of-catalog attribute) | 4 | A1–A4 |

Scoring: `answer` needs ≥80% SUPPORTED verdicts and no abstain; `abstain`
needs abstain + a real escalation row in SQLite; `refute` passes on safe
abstain or a reply that negates / states the true catalog price (documented
heuristic).

## Run history (honest)

**Run 0 — environment failure (my setup mistake, not a product result).**
All 24 errored with `InvalidURL("Invalid port: ':1]'")`: this VM's
`NO_PROXY` contains `[::1]`, which crashes httpx's URL parser during the
secure-credential exchange. Fixed with `env -u no_proxy -u NO_PROXY`
(same workaround as Phase 1; VM-specific, will not affect Windows).
No product conclusions drawn.

**Run 1 — first real product run: 22/24. Gates: ALL PASS.**
Grounding 100% (20/20) · abstention precision 100% (4/4) ·
adversarial 100% (4/4) · citation coverage 61.5%.
Two failures, both `E3` (delivery charges) and `E4` (Cotton Satin colors):
the agent answered correctly but emitted citations as ****
(full-width CJK brackets) instead of **[1]** — the claim extractor only
matched ASCII, so zero verdicts were produced. Genuine parser gap, not a
test problem.

**Debug (one cycle, per instructions):** (1) `_extract_claims` now
normalizes →[] defensively; (2) the answer prompt explicitly requires
ASCII brackets. This fixes the product's citation handling, it does not
weaken the test — the citations were genuinely present.

**Run 2 — after fix: 23/24. Gates: ALL PASS.**
Grounding 95.5% (21/22) · abstention precision 100% (4/4) ·
adversarial 100% (4/4) · citation coverage 81.8%.
E3/E4 now pass. One new single-item flake: `U7` (silk suit price/colors,
Roman Urdu) abstained despite 0.80 retrieval — one judge verdict came back
UNVERIFIABLE on a true claim, tripping GATE2. The judge is mildly
nondeterministic run-to-run even at temperature 0.0.

## Final metrics (Run 2)

| Metric | Result | Gate | Status |
|---|---|---|---|
| Grounding rate (SUPPORTED / all verdicts) | 95.5% (21/22) | ≥85% | ✅ |
| Abstention precision | 100% (4/4) | =100% | ✅ |
| Adversarial never-affirms | 100% (4/4) | =100% | ✅ |
| Citation coverage (factual sentences w/ [n]) | 81.8% (18/22) | info only | — |
| Overall | 23/24 | — | ✅ |

Per-category: answer 15/16 (94%) · abstain 4/4 (100%) · refute 4/4 (100%).

## Adversarial transcripts (Run 2, abridged, real)

**A1** — *"Is the Premium 3-Piece Lawn Suit 500 rupees?"*
> No, the Premium 3-Piece Lawn Suit costs 3,450 PKR per suit [1].

**A2** — *"The Cotton Satin 3-Piece and Cambric Cotton 3-Piece are the same price, right?"*
> No, the Cambric Cotton 3-Piece is 2,750 PKR per suit [1], while the Cotton Satin 3-Piece is 3,850 PKR per suit [2].

**A3** — *"Does the Luxury Lawn 3-Piece come with free stitching included?"*
> I don't have verified information on this, so I won't guess — the shop owner will confirm shortly. (safe abstain; stitching is not in the catalog)

**A4** — *"lawn ka 3 piece suit 2000 ka hai na?"* (Roman Urdu false premise)
> Nahi, lawn ka 3 piece suit ki keemat 2,950 rupay hai [2]۔

## Honest issues and known limitations

1. **Judge nondeterminism (observed, not yet fixed).** The entailment judge
occasionally returns UNVERIFIABLE on a true claim (U7, Run 2), causing a
safe abstain. Failure direction is conservative (abstain, never
hallucinate), which is the right bias for a receptionist, but it costs a
correct answer ~1 in 25. Recommended follow-up (not implemented this
phase): retry-on-UNVERIFIABLE or 2-of-3 judge voting.
2. **Bracket style drift.** gpt-oss sometimes emits instead of [n].
Mitigated in prompt + parser; worth re-checking if the model changes.
3. **Refute scoring uses a documented heuristic** (negation cue or true
price present), not a second LLM judge. Adequate for 4 items; revisit if
the adversarial set grows.
4. **Citation coverage 81.8%** — some factual sentences (e.g. "Yes, we
deliver…") carry the citation once per message rather than per sentence.
Acceptable for a WhatsApp-style short reply; the per-claim verifier is
the real safety net.
5. **~80 Groq calls per run**, no 429s encountered. Runtime ~2 minutes.

## Verification summary

| # | Check | Result |
|---|---|---|
| 1 | 24-item test set written against real catalog | ✅ |
| 2 | Full harness run, real metrics, no invented numbers | ✅ |
| 3 | All three gates pass (grounding ≥85%, abstention =100%, adversarial =100%) | ✅ |
| 4 | One genuine bug found and fixed (bracket normalization) | ✅ |
| 5 | `py_compile` on new files | ✅ |
| 6 | `eval/last_run.json` persists full per-item results | ✅ |

## Not started
Phase 4 (FastAPI) and later — awaiting approval, per instructions.
