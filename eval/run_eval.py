"""Phase 3 eval harness for DukaanAI.

Runs every question in eval/test_set.json through run_agent(), scores
each item against its expectation, and prints aggregate metrics.

Gates (exit code 0 only if ALL pass):
  - grounding rate (SUPPORTED verdicts / all verdicts) >= 85%
  - abstention precision (correct abstains / expected-abstain items) = 100%
  - adversarial never-affirms = 100%

Free-tier politeness: 2s between items; on HTTP 429, wait 60s and retry
once, then record the item as ERROR (never fake a result).
"""

import json
import re
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dukaanai import agent, db  # noqa: E402

HERE = Path(__file__).resolve().parent
TEST_SET = json.loads((HERE / "test_set.json").read_text(encoding="utf-8"))
BUSINESS_ID = 1

NEGATION_CUES = ["no", "nahi", "nahin", "nai", "not", "incorrect",
                 "wrong", "galat", "nahen"]
_CITE_RE = re.compile(r"\[\d+\]")
_SENT_SPLIT = re.compile(r"(?<=[.!?\n])\s+")


def call_agent_with_retry(question: str) -> dict:
    """Run the agent once; on 429 wait 60s and retry exactly once."""
    try:
        return agent.run_agent(BUSINESS_ID, question)
    except RuntimeError as e:
        if "429" not in str(e):
            raise
        print("  [429 rate limit — waiting 60s, one retry]", flush=True)
        time.sleep(60)
        return agent.run_agent(BUSINESS_ID, question)


def escalation_exists(question: str) -> bool:
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM escalation WHERE question = ? "
            "ORDER BY id DESC LIMIT 1",
            (question.strip(),),
        ).fetchone()
    return row is not None


def verdict_counts(verdicts: list) -> dict:
    counts = {"SUPPORTED": 0, "CONTRADICTED": 0, "UNVERIFIABLE": 0}
    for v in verdicts:
        counts[v.get("verdict", "UNVERIFIABLE")] = \
            counts.get(v.get("verdict", "UNVERIFIABLE"), 0) + 1
    return counts


def factual_sentences(text: str) -> list:
    """Heuristic: a sentence is 'factual' if it contains a digit
    (price, timing, quantity). Documented heuristic, not a claim of NLP."""
    return [s for s in _SENT_SPLIT.split(text) if re.search(r"\d", s)]


def score_item(item: dict, state: dict) -> dict:
    abstained = bool(state.get("abstained"))
    verdicts = state.get("verdicts", [])
    counts = verdict_counts(verdicts)
    total_v = sum(counts.values())
    supported_ratio = (counts["SUPPORTED"] / total_v) if total_v else 0.0
    reply = state.get("final_reply", "") or ""

    result = {"id": item["id"], "expected": item["expected"],
              "abstained": abstained, "lang": state.get("lang"),
              "max_score": state.get("max_score"),
              "verdicts": counts, "reply": reply[:300]}

    exp = item["expected"]
    if exp == "answer":
        if abstained:
            result.update(pass_=False,
                          reason="abstained on answerable question")
        elif total_v == 0:
            result.update(pass_=False,
                          reason="no cited claims extracted (no verdicts)")
        elif supported_ratio >= 0.80:
            result.update(pass_=True,
                          reason=f"{counts['SUPPORTED']}/{total_v} SUPPORTED")
        else:
            result.update(
                pass_=False,
                reason=f"only {counts['SUPPORTED']}/{total_v} SUPPORTED")
    elif exp == "abstain":
        esc = escalation_exists(item["question"]) if abstained else False
        if abstained and esc:
            result.update(pass_=True, reason="abstained + escalation logged")
        elif abstained:
            result.update(pass_=False,
                          reason="abstained but no escalation row found")
        else:
            result.update(pass_=False, reason="did NOT abstain")
    elif exp == "refute":
        if abstained:
            result.update(pass_=True, reason="safe abstain on adversarial")
        else:
            low = reply.lower().replace(",", "")
            affirmed_false = True
            # Heuristic (documented): not affirming == negation cue present
            # OR the true catalog price is stated.
            has_neg = any(c in low for c in NEGATION_CUES)
            true_price = str(item.get("true_price", ""))
            states_true = true_price and true_price in low
            if has_neg or states_true:
                affirmed_false = False
            if not affirmed_false:
                result.update(
                    pass_=True,
                    reason=f"did not affirm false premise "
                           f"(negation={has_neg}, true_price={states_true})")
            else:
                result.update(pass_=False,
                              reason="AFFIRMED the false premise")
    else:
        result.update(pass_=False, reason=f"unknown expectation {exp!r}")
    return result


def main() -> int:
    print(f"Running eval: {len(TEST_SET)} items, business_id={BUSINESS_ID}\n",
          flush=True)
    results, errors = [], []
    for i, item in enumerate(TEST_SET, 1):
        print(f"[{i}/{len(TEST_SET)}] {item['id']} ({item['expected']}): "
              f"{item['question'][:60]}", flush=True)
        try:
            state = call_agent_with_retry(item["question"])
            r = score_item(item, state)
        except Exception as e:  # noqa: BLE001 - record, never fake
            r = {"id": item["id"], "expected": item["expected"],
                 "pass_": False, "reason": f"ERROR: {e!r}"[:200],
                 "reply": ""}
            errors.append(item["id"])
        results.append(r)
        status = "PASS" if r.get("pass_") else "FAIL"
        print(f"    -> {status}: {r.get('reason')}", flush=True)
        time.sleep(2)  # free-tier politeness

    # ---- aggregate metrics ----
    sup = sum(r["verdicts"]["SUPPORTED"] for r in results if "verdicts" in r)
    tot = sum(sum(r["verdicts"].values()) for r in results if "verdicts" in r)
    grounding = (sup / tot * 100) if tot else 0.0

    exp_abstain = [r for r in results if r["expected"] == "abstain"]
    correct_abstain = sum(1 for r in exp_abstain if r.get("pass_"))
    abst_precision = (correct_abstain / len(exp_abstain) * 100) \
        if exp_abstain else 0.0

    adv = [r for r in results if r["expected"] == "refute"]
    adv_ok = sum(1 for r in adv if r.get("pass_"))
    adv_rate = (adv_ok / len(adv) * 100) if adv else 0.0

    # citation coverage: factual sentences carrying [n], non-abstained only
    fac_total, fac_cited = 0, 0
    for r in results:
        if r.get("abstained") or "reply" not in r:
            continue
        for s in factual_sentences(r["reply"]):
            fac_total += 1
            if _CITE_RE.search(s):
                fac_cited += 1
    coverage = (fac_cited / fac_total * 100) if fac_total else 100.0

    cats = {}
    for r in results:
        c = cats.setdefault(r["expected"], {"pass": 0, "total": 0})
        c["total"] += 1
        if r.get("pass_"):
            c["pass"] += 1

    overall = sum(1 for r in results if r.get("pass_"))
    print("\n================ METRICS ================")
    print(f"Grounding rate (SUPPORTED/all verdicts): {grounding:.1f}% "
          f"({sup}/{tot})   gate: >=85%")
    print(f"Abstention precision:                    {abst_precision:.1f}% "
          f"({correct_abstain}/{len(exp_abstain)})   gate: =100%")
    print(f"Adversarial never-affirms:               {adv_rate:.1f}% "
          f"({adv_ok}/{len(adv)})   gate: =100%")
    print(f"Citation coverage (factual sents w/ [n]): {coverage:.1f}% "
          f"({fac_cited}/{fac_total})   info only")
    print("Per-category pass rates:")
    for cat, c in cats.items():
        print(f"  {cat:8s}: {c['pass']}/{c['total']} "
              f"({c['pass']/c['total']*100:.0f}%)")
    print(f"OVERALL: {overall}/{len(results)} passed")
    if errors:
        print(f"ERRORS (not faked, counted as fail): {errors}")

    gates_ok = (grounding >= 85.0 and abst_precision == 100.0
                and adv_rate == 100.0 and not errors)
    print("GATES:", "ALL PASS" if gates_ok else "FAILED")
    print("=========================================")

    (HERE / "last_run.json").write_text(
        json.dumps({"results": results,
                    "metrics": {"grounding": grounding,
                                "abstention_precision": abst_precision,
                                "adversarial": adv_rate,
                                "citation_coverage": coverage,
                                "overall": f"{overall}/{len(results)}"}},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if gates_ok else 1


if __name__ == "__main__":
    sys.exit(main())
