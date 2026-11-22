#!/usr/bin/env bash
# Boot the DukaanAI API: init the DB, seed the demo shop on first boot,
# then serve with uvicorn. GROQ_API_KEY must be set (HF Spaces secret).
set -e

python -c "from dukaanai import db; db.init_db()"

BUSINESSES=$(python -c "import sqlite3; print(sqlite3.connect('data/dukaanai.db').execute('SELECT COUNT(*) FROM business').fetchone()[0])")
if [ "$BUSINESSES" = "0" ]; then
  echo "No businesses found — seeding the demo shop (Chenab Cloth House)..."
  python scripts/seed_demo.py
fi

exec uvicorn dukaanai.api:app --host 0.0.0.0 --port "${PORT:-7860}"
