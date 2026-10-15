"""SQLite data layer for DukaanAI.

Tables (per project documentation):
  business      - one row per client business
  catalog_item  - products with bilingual names, price, variants
  policy        - timings/delivery/return/payment/location/discount texts
  conversation  - customer chat sessions
  message       - individual messages with retrieval verdicts
  escalation    - questions the AI could not answer -> owner inbox

Design: stdlib sqlite3 only, no ORM. init_db() is idempotent.
DB file lives at <repo>/data/dukaanai.db.
"""

import json
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
DB_PATH = DATA_DIR / "dukaanai.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS business (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    whatsapp_number TEXT,
    location        TEXT,
    language_default TEXT DEFAULT 'auto',
    after_hours_text_en TEXT,
    after_hours_text_ur TEXT,
    tier            TEXT DEFAULT 'starter',
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS catalog_item (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id     INTEGER NOT NULL REFERENCES business(id),
    name_en         TEXT NOT NULL,
    name_ur_roman   TEXT NOT NULL,
    price           REAL NOT NULL,
    unit            TEXT NOT NULL,
    variants_json   TEXT DEFAULT '{}',
    category        TEXT,
    source_doc      TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS policy (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id     INTEGER NOT NULL REFERENCES business(id),
    type            TEXT NOT NULL,
    text_en         TEXT NOT NULL,
    text_ur_roman   TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS conversation (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id     INTEGER NOT NULL REFERENCES business(id),
    customer_ref    TEXT,
    language        TEXT,
    started_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS message (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id     INTEGER NOT NULL REFERENCES conversation(id),
    direction           TEXT NOT NULL,
    text                TEXT NOT NULL,
    retrieved_chunk_ids TEXT DEFAULT '[]',
    verdict             TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS escalation (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id     INTEGER NOT NULL REFERENCES business(id),
    conversation_id INTEGER REFERENCES conversation(id),
    question        TEXT NOT NULL,
    status          TEXT DEFAULT 'open',
    resolution      TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    resolved_at     TEXT
);
"""


def get_connection() -> sqlite3.Connection:
    """Open a connection, creating the data dir if needed."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all tables. Safe to call repeatedly."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        # Migration: resolution column added in Phase 4.
        try:
            conn.execute("ALTER TABLE escalation ADD COLUMN resolution TEXT")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                raise


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

def add_business(name, whatsapp_number=None, location=None,
                 after_hours_text_en=None, after_hours_text_ur=None,
                 tier="starter") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO business
               (name, whatsapp_number, location, after_hours_text_en,
                after_hours_text_ur, tier)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, whatsapp_number, location, after_hours_text_en,
             after_hours_text_ur, tier),
        )
        return cur.lastrowid


def add_catalog_item(business_id, name_en, name_ur_roman, price, unit,
                     variants=None, category=None, source_doc=None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO catalog_item
               (business_id, name_en, name_ur_roman, price, unit,
                variants_json, category, source_doc)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (business_id, name_en, name_ur_roman, price, unit,
             json.dumps(variants or {}, ensure_ascii=False),
             category, source_doc),
        )
        return cur.lastrowid


def add_policy(business_id, type_, text_en, text_ur_roman) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO policy (business_id, type, text_en, text_ur_roman)"
            " VALUES (?, ?, ?, ?)",
            (business_id, type_, text_en, text_ur_roman),
        )
        return cur.lastrowid


def add_conversation(business_id, customer_ref=None, language=None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO conversation (business_id, customer_ref, language)"
            " VALUES (?, ?, ?)",
            (business_id, customer_ref, language),
        )
        return cur.lastrowid


def add_message(conversation_id, direction, text,
                retrieved_chunk_ids=None, verdict=None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO message
               (conversation_id, direction, text, retrieved_chunk_ids, verdict)
               VALUES (?, ?, ?, ?, ?)""",
            (conversation_id, direction, text,
             json.dumps(retrieved_chunk_ids or []), verdict),
        )
        return cur.lastrowid


def add_escalation(business_id, question, conversation_id=None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO escalation (business_id, conversation_id, question)"
            " VALUES (?, ?, ?)",
            (business_id, conversation_id, question),
        )
        return cur.lastrowid


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

def get_business(business_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM business WHERE id = ?", (business_id,)
        ).fetchone()


def list_catalog_items(business_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM catalog_item WHERE business_id = ? ORDER BY id",
            (business_id,),
        ).fetchall()


def list_policies(business_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM policy WHERE business_id = ? ORDER BY id",
            (business_id,),
        ).fetchall()


def count_rows(table: str, business_id: int | None = None) -> int:
    with get_connection() as conn:
        if business_id is None:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        return conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE business_id = ?",
            (business_id,),
        ).fetchone()[0]


# ---------------------------------------------------------------------------
# Phase 4: API-facing helpers
# ---------------------------------------------------------------------------

def get_escalations(business_id: int, status: str | None = None):
    """Escalations for a business, newest first. Optional status filter."""
    with get_connection() as conn:
        if status is None:
            return conn.execute(
                "SELECT * FROM escalation WHERE business_id = ? "
                "ORDER BY id DESC",
                (business_id,),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM escalation WHERE business_id = ? AND status = ? "
            "ORDER BY id DESC",
            (business_id, status),
        ).fetchall()


def get_escalation(escalation_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM escalation WHERE id = ?", (escalation_id,)
        ).fetchone()


def resolve_escalation(escalation_id: int,
                       resolution: str | None = None) -> bool:
    """Mark an escalation resolved. Returns False if it does not exist."""
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE escalation SET status = 'resolved', "
            "resolved_at = datetime('now'), resolution = ? "
            "WHERE id = ?",
            (resolution, escalation_id),
        )
        return cur.rowcount > 0


def list_conversations(business_id: int, limit: int = 20):
    """Recent conversations with message counts, newest first."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT c.*, COUNT(m.id) AS message_count "
            "FROM conversation c LEFT JOIN message m "
            "ON m.conversation_id = c.id "
            "WHERE c.business_id = ? "
            "GROUP BY c.id ORDER BY c.id DESC LIMIT ?",
            (business_id, limit),
        ).fetchall()


def get_messages(conversation_id: int):
    """All messages in one conversation, oldest first."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM message WHERE conversation_id = ? "
            "ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()


def dashboard_summary(business_id: int) -> dict:
    """Owner-dashboard aggregates for one business."""
    with get_connection() as conn:
        total_conversations = conn.execute(
            "SELECT COUNT(*) FROM conversation WHERE business_id = ?",
            (business_id,),
        ).fetchone()[0]
        total_messages = conn.execute(
            "SELECT COUNT(*) FROM message m "
            "JOIN conversation c ON m.conversation_id = c.id "
            "WHERE c.business_id = ?",
            (business_id,),
        ).fetchone()[0]
        abstention_count = conn.execute(
            "SELECT COUNT(*) FROM message m "
            "JOIN conversation c ON m.conversation_id = c.id "
            "WHERE c.business_id = ? AND m.verdict = 'ABSTAINED'",
            (business_id,),
        ).fetchone()[0]
        open_escalations = conn.execute(
            "SELECT COUNT(*) FROM escalation "
            "WHERE business_id = ? AND status = 'open'",
            (business_id,),
        ).fetchone()[0]
        top_questions = conn.execute(
            "SELECT m.text AS question, COUNT(*) AS times "
            "FROM message m JOIN conversation c "
            "ON m.conversation_id = c.id "
            "WHERE c.business_id = ? AND m.direction = 'in' "
            "GROUP BY m.text ORDER BY times DESC LIMIT 5",
            (business_id,),
        ).fetchall()
    return {
        "business_id": business_id,
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "abstention_count": abstention_count,
        "open_escalations": open_escalations,
        "top_questions": [
            {"question": r["question"], "times": r["times"]}
            for r in top_questions
        ],
    }
