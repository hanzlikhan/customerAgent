# PHASE 1 REPORT — Data Layer

**Date:** 2026-10-14 · **Status:** ✅ COMPLETE (all verifications passed)
**Repo:** `~/workspace/dukaanai/`

## What was built

| File | Purpose |
|---|---|
| `dukaanai/db.py` | SQLite layer: 6 tables, idempotent `init_db()`, CRUD helpers |
| `dukaanai/demo_data.py` | Demo dataset: 1 business, 40 items, 6 policies (bilingual) |
| `dukaanai/index.py` | Chroma per-business collections, multilingual embeddings, `build_index()` + `retrieve()` |
| `scripts/seed_demo.py` | Wipe-and-rebuild end to end (repeatable) |
| `scripts/verify_phase1.py` | Price-consistency + retrieval-quality checks |

## Schema (text diagram)

```
business 1──┬──< catalog_item   (name_en, name_ur_roman, price, unit,
             │                   variants_json{en,ur}, category, source_doc)
             ├──< policy         (type, text_en, text_ur_roman)
             ├──< conversation 1──< message (direction, text,
             │                              retrieved_chunk_ids, verdict)
             └──< escalation    (question, status)
```

DB file: `data/dukaanai.db`. Vector store: `data/chroma/` (collection `business_1`).

## Seed results (real run)

| Entity | Count |
|---|---|
| Business ("Chenab Cloth House", Chenab Market, Faisalabad) | 1 |
| Catalog items (Lawn/Cotton/Khaddar/Wash-n-Wear/Linen/Fancy/Velvet/Winter/Kids/Gents/Denim/Home/Premium) | 40 |
| Policies (timing, delivery, return, payment, location, discount) | 6 |
| Chroma chunks (2 per item/policy: EN + Roman Urdu) | 92 (expected 92) |

## Price consistency (real run)

| Item | EN chunk | UR chunk | DB | Result |
|---|---|---|---|---|
| Premium 3-Piece Lawn Suit - Floral Print | 3,450 | 3,450 | 3,450 | OK |
| Premium Wash-n-Wear - Per Meter | 850 | 850 | 850 | OK |
| Jacquard Suiting - Per Meter | 1,100 | 1,100 | 1,100 | OK |

Prices extracted from the actual indexed chunk texts via regex — identical across languages. **PASS.**

## Retrieval tests (real run, threshold = 0.40)

| # | Query | Top-1 chunk | Similarity | Note |
|---|---|---|---|---|
| 1 | "What is the price of a cotton suit?" (EN) | Premium Cotton 3-Piece Suit (EN item) | 0.7658 | correct product |
| 2 | "What are your shop timings?" (EN) | SHOP POLICY (timing) (EN) | 0.7911 | correct policy |
| 3 | "lawn ka 3 piece suit kitne ka hai?" (UR) | Lawn 3-piece, geometric (UR item) | 0.7210 | correct + UR chunk |
| 4 | "timing kya hai apki dukan ki?" (UR) | DUKAN POLICY (timing) (UR) | 0.7367 | correct + UR chunk |
| 5 | "khaddar suit price per meter batao" (mixed) | Heavy Khaddar - Per Meter (EN item) | 0.6828 | correct product |
| 6 | "do you sell shoes?" (unanswerable) | discount policy (EN) | 0.3190 | **below threshold → abstain path. PASS** |

Language routing works: Urdu queries retrieve Urdu chunks, English queries retrieve English chunks. The unanswerable query scores 0.3190 < 0.40, so Phase 2's Gate 1 will correctly abstain.

## Verification summary

| # | Check | Result |
|---|---|---|
| 1 | `seed_demo.py` runs clean, counts as expected | ✅ 1 / 40 / 6 / 92 |
| 2 | Price identical in EN chunk, UR chunk, DB (3 items) | ✅ PASS |
| 3 | 6 retrieval queries, correct top-1 + language match | ✅ PASS |
| 4 | Unanswerable query below 0.40 threshold | ✅ 0.3190 PASS |
| 5 | `py_compile` on all 5 new files | ✅ OK |

## Honest build notes

- **httpx vs. no_proxy:** this VM's `NO_PROXY` env var contains `[::1]`, which crashes httpx's URL parser (`Invalid port: ':1]'`) whenever huggingface_hub builds an HTTP client. Workaround used: `env -u no_proxy -u NO_PROXY` for seed/verify runs. **This is VM-specific — Hanzla's Windows machine will not hit it.** Noted here so the workaround isn't mistaken for a code bug.
- **Model download:** `paraphrase-multilingual-MiniLM-L12-v2` (458 MB) downloaded once to the HF cache; subsequent runs load locally.
- **No API keys** anywhere in the repo. No Groq calls were made in this phase (embeddings + Chroma are fully local).
- **Phase 2 (LangGraph agent) NOT started** — awaiting approval.
