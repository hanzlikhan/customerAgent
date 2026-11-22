"""DukaanAI backend entrypoint for Hugging Face Spaces (Gradio SDK).

Hugging Face runs `python app.py` and proxies HTTP to port 7860. This
launcher initialises the SQLite database, seeds the demo shop (Chenab
Cloth House) only when the database is empty, rebuilds the vector index
when it is missing, then serves the FastAPI API with uvicorn.

Why this exists: Docker SDK Spaces are a paid feature on a free Hugging
Face account, so the API runs here under the free Gradio SDK instead of
the Dockerfile (kept in the repo for local / paid use).

The Streamlit demo UI moved to streamlit_app.py:
    streamlit run streamlit_app.py
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from dukaanai import db, demo_data, index  # noqa: E402


def seed_if_empty() -> int:
    """Seed the demo shop only when no business exists yet.

    Unlike scripts/seed_demo.py (which wipes everything first), this
    never deletes data: on a Space restart with an existing database it
    is a no-op, so live conversations survive restarts. The insert
    steps mirror scripts/seed_demo.py. Returns the business id.
    """
    db.init_db()
    if db.count_rows("business") > 0:
        with db.get_connection() as conn:
            row = conn.execute("SELECT MIN(id) AS id FROM business").fetchone()
        return row["id"]

    b = demo_data.BUSINESS
    business_id = db.add_business(
        name=b["name"],
        whatsapp_number=b["whatsapp_number"],
        location=b["location"],
        after_hours_text_en=b["after_hours_text_en"],
        after_hours_text_ur=b["after_hours_text_ur"],
        tier=b["tier"],
    )
    for (name_en, name_ur, price, unit, colors_en, colors_ur,
         category) in demo_data.ITEMS:
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
    for type_, text_en, text_ur in demo_data.POLICIES:
        db.add_policy(business_id, type_, text_en, text_ur)
    print(
        f"seeded demo business id={business_id}: "
        f"{db.count_rows('catalog_item', business_id)} items, "
        f"{db.count_rows('policy', business_id)} policies",
        flush=True,
    )
    return business_id


def ensure_index(business_id: int) -> None:
    """Rebuild the vector index when it is missing or empty.

    The SQLite file and the Chroma directory can drift apart across
    Space restarts (one persists, the other does not); retrieval fails
    outright when the collection is missing, so check every boot.
    """
    if index.count_chunks(business_id) == 0:
        n = index.build_index(business_id)
        print(f"rebuilt vector index: {n} chunks", flush=True)


def main() -> None:
    business_id = seed_if_empty()
    ensure_index(business_id)
    import uvicorn

    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run("dukaanai.api:app", host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
