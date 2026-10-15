"""Connectivity check for the Groq free-tier key.

- Key present  -> makes one minimal chat call ("reply with OK") and prints the result.
- Key absent   -> prints exactly what the user must do. Exits 0 either way
                 (absence of a key is an expected state, not a crash).

Usage:  python scripts/check_groq.py
"""

import sys
from pathlib import Path

# Allow running from the repo root: python scripts/check_groq.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dukaanai import config  # noqa: E402


def main() -> int:
    if not config.GROQ_API_KEY or config.GROQ_API_KEY == "your_key_here":
        print("Groq API key NOT found. To enable the LLM (free tier):")
        print("  1. Get a free key at https://console.groq.com  (sign up -> API Keys -> Create)")
        print("  2. Copy .env.example to .env")
        print("     Windows:  copy .env.example .env")
        print("     Linux:    cp .env.example .env")
        print("  3. Paste your key after GROQ_API_KEY= inside .env")
        print("  4. Re-run:  python scripts/check_groq.py")
        print()
        print("Everything else in Phase 0 works without the key.")
        return 0

    # Key present: one minimal call to prove connectivity.
    try:
        from dukaanai import llm

        reply = llm.chat("Reply with exactly: OK", max_tokens=20)
        print(f"Groq connectivity OK. Model: {config.GROQ_MODEL}")
        print(f"Model replied: {reply}")
        return 0
    except Exception as exc:  # noqa: BLE001 - we want the raw error visible
        print(f"Groq call FAILED: {type(exc).__name__}: {exc}")
        print("Check that your key is valid at https://console.groq.com")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
