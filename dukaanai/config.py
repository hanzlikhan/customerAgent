"""Central configuration for DukaanAI.

Loads everything from environment variables (see .env.example) with sane
defaults. Design rule: importing this module must NEVER fail or raise —
the missing-key error is raised only when an LLM call is actually
attempted, so scripts like check_groq.py can give friendly guidance.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the repo root (one level above this package) if present.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()

# Retrieval gate: chunks scoring below this cosine similarity are treated
# as "no usable evidence" and route to the abstention path.
try:
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.40"))
except ValueError:
    SIMILARITY_THRESHOLD = 0.40

# Multilingual embeddings model (runs locally, free).
EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
)


class MissingGroqKeyError(RuntimeError):
    """Raised when an LLM call is attempted without a Groq API key."""


def require_groq_key() -> str:
    """Return the Groq key, or raise a clear, actionable error.

    Call this at the start of any function that talks to Groq —
    never at import time.
    """
    key = os.getenv("GROQ_API_KEY", GROQ_API_KEY).strip()
    if not key or key == "your_key_here":
        raise MissingGroqKeyError(
            "GROQ_API_KEY is not set.\n"
            "  1. Get a FREE key at https://console.groq.com (sign up -> API Keys -> Create)\n"
            "  2. Copy .env.example to .env\n"
            "  3. Paste your key after GROQ_API_KEY= in .env\n"
            "  4. Re-run. Verify with: python scripts/check_groq.py"
        )
    return key

