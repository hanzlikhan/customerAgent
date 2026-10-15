"""Seed the DukaanAI demo: wipes and rebuilds everything end-to-end.

    python scripts/seed_demo.py        (run from repo root, venv active)

Repeatable: safe to run any number of times.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dukaanai import db, demo_data, index


def main() -> None:
    # 1. Wipe previous demo state.
    if db.DB_PATH.exists():
        db.DB_PATH.unlink()
        print(f"removed {db.DB_PATH}")
    index.wipe_index()
    print(f"wiped {index.CHROMA_DIR}")

    # 2. Schema + business.
    db.init_db()
    b = demo_data.BUSINESS
    business_id = db.add_business(
        name=b["name"],
        whatsapp_number=b["whatsapp_number"],
        location=b["location"],
        after_hours_text_en=b["after_hours_text_en"],
        after_hours_text_ur=b["after_hours_text_ur"],
        tier=b["tier"],
    )
    print(f"business: {b['name']} (id={business_id})")

    # 3. Catalog items.
    for (name_en, name_ur, price, unit, colors_en, colors_ur, category) in demo_data.ITEMS:
        db.add_catalog_item(
            business_id,
            name_en=name_en,
            name_ur_roman=name_ur,
            price=price,
            unit=unit,
            variants={"en": colors_en, "ur": colors_ur},
            category=category,
            source_doc="demo_catalog_v1",
        )
    n_items = db.count_rows("catalog_item", business_id)
    print(f"catalog items: {n_items}")

    # 4. Policies.
    for type_, text_en, text_ur in demo_data.POLICIES:
        db.add_policy(business_id, type_, text_en, text_ur)
    n_policies = db.count_rows("policy", business_id)
    print(f"policies: {n_policies}")

    # 5. Vector index.
    n_chunks = index.build_index(business_id)
    expected = 2 * (n_items + n_policies)
    print(f"index chunks: {n_chunks} (expected {expected})")
    assert n_chunks == expected, "chunk count mismatch!"

    print("\nSeed complete: 1 business, "
          f"{n_items} items, {n_policies} policies, {n_chunks} chunks.")


if __name__ == "__main__":
    main()
