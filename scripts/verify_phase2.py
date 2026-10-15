"""Phase 2 verification: real runs through the LangGraph agent.

Prints a structured report and saves transcripts to
/tmp/phase2_results.json for PHASE2_REPORT.md.
"""
import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaanai import agent, db  # noqa: E402

BIZ = 1
OUT = Path(tempfile.gettempdir()) / "phase2_results.json"
results: dict = {"tests": []}


def tprint(*a):
    print(*a, flush=True)


def lang_unit_check():
    cases = [
        ("What is the price of a cotton suit?", "en"),
        ("lawn ka 3 piece suit kitne ka hai?", "ur"),
        ("timing kya hai apki dukan ki?", "ur"),
        ("khaddar suit price per meter batao", "mixed"),
        ("Do you offer home delivery?", "en"),
        ("discount hai kya bulk order par?", "ur"),
    ]
    ok = 0
    for text, expected in cases:
        got = agent.detect_lang(text)
        mark = "OK " if got == expected else "FAIL"
        if got == expected:
            ok += 1
        tprint(f"  [{mark}] {text!r:55} -> {got} (expected {expected})")
    results["tests"].append(
        {"name": "language_detection", "passed": ok == len(cases),
         "detail": f"{ok}/{len(cases)} correct"})
    return ok == len(cases)


def run_case(name, text):
    tprint(f"\n--- {name} ---")
    tprint(f"Q: {text}")
    t0 = time.time()
    try:
        state = agent.run_agent(BIZ, text)
    except Exception as e:  # noqa: BLE001 - report honestly, don't crash the suite
        tprint(f"ERROR: {type(e).__name__}: {e}")
        results["tests"].append({"name": name, "passed": False,
                                 "detail": f"EXCEPTION {type(e).__name__}: {e}"})
        return None
    dt = time.time() - t0
    tprint(f"A: {state['final_reply']}")
    tprint(f"lang={state.get('lang')} abstained={state.get('abstained')} "
           f"max_score={state.get('max_score')} time={dt:.1f}s")
    for v in state.get("verdicts", []):
        tprint(f"  verdict: {v['verdict']:12} [{v['chunk_idx']}] "
               f"{v['claim'][:80]}")
    if state.get("escalation_id"):
        tprint(f"  escalation_id={state['escalation_id']}")
    results["tests"].append({
        "name": name, "question": text,
        "reply": state["final_reply"], "lang": state.get("lang"),
        "abstained": state.get("abstained"),
        "max_score": state.get("max_score"),
        "verdicts": state.get("verdicts", []),
        "escalation_id": state.get("escalation_id"),
        "seconds": round(dt, 1),
    })
    return state


def escalation_proof(esc_id):
    conn = sqlite3.connect(db.DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, question, status FROM escalation WHERE id = ?",
        (esc_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def main():
    tprint("== Phase 2 verification ==\n")
    tprint("[1] language detection unit check")
    lang_ok = lang_unit_check()

    s1 = run_case("en_answerable", "What is the price of a cotton suit?")
    s2 = run_case("ur_answerable", "lawn ka 3 piece suit kitne ka hai?")
    s3 = run_case("unanswerable", "do you sell shoes?")
    s4 = run_case("adversarial_false_price",
                  "Is the premium lawn suit 500 rupees?")

    # --- assertions (honest pass/fail, reported not hidden) ---
    checks = [("lang_unit", lang_ok)]

    def ck(name, cond, note=""):
        checks.append((name, bool(cond)))
        tprint(f"[{'PASS' if cond else 'FAIL'}] {name} {note}")

    if s1:
        ck("en_cited_answer",
           (not s1["abstained"]) and "[1]" in s1["final_reply"],
           f"abstained={s1['abstained']}")
        ck("en_all_supported",
           s1["verdicts"] and all(v["verdict"] == "SUPPORTED"
                                  for v in s1["verdicts"]))
    if s2:
        ck("ur_not_abstained", not s2["abstained"])
        ck("ur_has_citation", "[1]" in s2["final_reply"])
    if s3:
        ck("unanswerable_abstained", s3["abstained"] is True)
        proof = escalation_proof(s3["escalation_id"]) if s3.get("escalation_id") else None
        ck("escalation_row_exists", proof is not None, f"row={proof}")
        results["escalation_proof"] = proof
    if s4:
        reply_nc = s4["final_reply"].replace(",", "")
        # Agreeing with the false price = asserting 500 as the price.
        # Correct behavior: abstain, or refute with the true cited price.
        agreed_false = "500" in reply_nc and "3450" not in reply_nc
        ck("adversarial_never_agrees_false_price",
           bool(s4["abstained"]) or not agreed_false,
           f"abstained={s4['abstained']}")

    results["checks"] = [{"name": n, "passed": p} for n, p in checks]
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    tprint(f"\nSaved transcripts -> {OUT}")
    allok = all(p for _, p in checks)
    tprint(f"\nOVERALL: {'ALL PASS' if allok else 'SOME FAILED'}")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
