"""Phase 1 verification: price consistency + retrieval quality.

Run:  env -u no_proxy -u NO_PROXY ./venv/bin/python scripts/verify_phase1.py
(The env workaround is needed: httpx chokes on this VM's malformed
no_proxy entry when huggingface_hub builds its HTTP client.)
"""

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dukaanai import config, db, index

PRICE_RE = re.compile(r"([\d,]+)\s*(?:PKR|rupay)")


def extract_price(text: str) -> str | None:
    m = PRICE_RE.search(text)
    return m.group(1) if m else None


def main() -> None:
    business_id = 1
    items = db.list_catalog_items(business_id)
    assert len(items) == 40, f"expected 40 items, got {len(items)}"

    # --- 1. Price consistency: 3 deterministic picks (first/middle/last) ---
    print("== Price consistency (EN vs UR chunk text) ==")
    ok = True
    for item in (items[0], items[19], items[39]):
        chunks = {c["metadata"]["lang"]: c["text"]
                  for c in index.retrieve(business_id, item["name_en"], k=10)
                  if c["metadata"]["kind"] == "item"
                  and c["metadata"]["ref_id"] == item["id"]}
        p_en = extract_price(chunks.get("en", ""))
        p_ur = extract_price(chunks.get("ur", ""))
        match = p_en == p_ur == f"{item['price']:,.0f}"
        ok &= bool(match)
        print(f"  id={item['id']} {item['name_en'][:40]:42} "
              f"EN={p_en} UR={p_ur} db={item['price']:,.0f} -> "
              f"{'OK' if match else 'MISMATCH'}")
    print("price check:", "PASS" if ok else "FAIL")
    assert ok, "price mismatch between language versions!"

    # --- 2. Retrieval quality: 6 queries ---
    print("\n== Retrieval tests (top-1) ==")
    queries = [
        ("en_answerable", "What is the price of a cotton suit?"),
        ("en_answerable", "What are your shop timings?"),
        ("ur_answerable", "lawn ka 3 piece suit kitne ka hai?"),
        ("ur_answerable", "timing kya hai apki dukan ki?"),
        ("mixed", "khaddar suit price per meter batao"),
        ("unanswerable", "do you sell shoes?"),
    ]
    results = []
    for kind, q in queries:
        top = index.retrieve(business_id, q, k=1)[0]
        meta = top["metadata"]
        flag = ""
        if kind == "unanswerable":
            flag = ("BELOW-THRESHOLD (good -> abstain)"
                    if top["similarity"] < config.SIMILARITY_THRESHOLD
                    else "ABOVE-THRESHOLD (bad!)")
        results.append((kind, q, top["similarity"], meta["kind"],
                        meta["lang"], top["text"][:80], flag))
        print(f"  [{kind:14}] q={q!r}")
        print(f"    -> sim={top['similarity']:.4f} kind={meta['kind']} "
              f"lang={meta['lang']} {flag}")
        print(f"    -> {top['text'][:90]}...")

    unanswerable_sim = results[-1][2]
    assert unanswerable_sim < config.SIMILARITY_THRESHOLD, (
        f"unanswerable query scored {unanswerable_sim} >= "
        f"threshold {config.SIMILARITY_THRESHOLD}"
    )
    print("\nunanswerable-query gate check: PASS "
          f"({unanswerable_sim:.4f} < {config.SIMILARITY_THRESHOLD})")
    print("\nALL PHASE 1 CHECKS PASSED")


if __name__ == "__main__":
    main()
