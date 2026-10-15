# PHASE 0 REPORT — Environment Setup

**Date:** 2026-10-14 · **Status:** ✅ COMPLETE (all verifications passed)
**Repo:** `~/workspace/dukaanai/` · **Stack:** Groq free tier (LLM) + local embeddings — $0 total

## What was installed

All inside a project virtualenv (`venv/`) — mirrors the Windows setup in README.

| Package | Version | Role |
|---|---|---|
| langchain | 1.4.5 | RAG orchestration |
| langchain-groq | 1.1.3 | Groq LLM connector |
| langchain-community | 0.4.2 | Community integrations |
| langgraph | 1.2.15 | Agentic state machine |
| sentence-transformers | 6.1.0 | Local multilingual embeddings |
| chromadb | 1.5.9 | Local vector store |
| streamlit | 1.65.0 | Chat UI + owner dashboard |
| fastapi | 0.143.0 | Backend API |
| uvicorn | 0.54.0 | ASGI server |
| python-dotenv | 1.2.4 | Env config |
| pandas | 3.0.6 | Catalog import |
| openpyxl | 3.1.5 | Excel catalog import |
| torch | 2.14.1+cpu | Embeddings backend (**CPU-only**) |
| groq | 0.37.1 | Groq SDK (via langchain-groq) |

## Verification results (all run, all real)

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Core imports | `python -c "import langchain, langgraph, chromadb, streamlit, fastapi"` | ✅ `imports ok` |
| 2 | Config loads, no key | `from dukaanai import config` | ✅ `config ok, key present: False` (expected — no key here) |
| 3 | Groq check script, no key | `python scripts/check_groq.py` | ✅ prints setup guidance, exit 0, no crash |
| 4 | Missing-key error path | `config.require_groq_key()` | ✅ raises `MissingGroqKeyError` with 4-step fix instructions |
| 5 | Syntax | `python -m py_compile` on all 3 `.py` files | ✅ ok |

## PENDING — Groq API key (Hanzla's action)

The LLM calls need a free Groq key. Nothing else is blocked.

1. Get a free key at **https://console.groq.com** (sign up → API Keys → Create). Free tier, no card.
2. Copy `.env.example` to `.env` — Windows: `copy .env.example .env`
3. Open `.env` in Notepad, paste the key after `GROQ_API_KEY=`
4. Run `python scripts/check_groq.py` → expect `Groq connectivity OK`

## Honest build notes

- **Disk-full detour:** the first `pip install` failed with `No space left on device` while downloading the 554 MB CUDA torch wheel (a pipeline-masked exit code hid it at first — verified the real error on re-run). Fixed by installing the **CPU-only torch** (~190 MB) from the PyTorch CPU index first. Recommendation for Windows: `pip install torch --index-url https://download.pytorch.org/whl/cpu` before `requirements.txt` — faster and sufficient, since embeddings don't need a GPU.
- **System pip conflict:** the VM's debian-installed `urllib3` couldn't be uninstalled by pip. Fixed by using a project `venv/` instead of `--break-system-packages` — which is also what the Windows instructions prescribe. The system Python was left untouched.
- **No API keys** exist anywhere in this repo. `.env.example` contains only a placeholder.
- **Phase 1 (data layer) NOT started** — awaiting approval, per instructions.
