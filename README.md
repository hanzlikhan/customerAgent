<div align="center">

# 🛍️ DukaanAI — Grounded Bilingual AI Receptionist
### Instant WhatsApp Sales & Support for Local Commerce · Never Invents a Price

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.38%2B-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2%2B-black.svg)](https://langchain-ai.github.io/langgraph/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5%2B-orange.svg)](https://www.trychroma.com/)
[![Groq](https://img.shields.io/badge/Groq-Free%20Tier-f55036.svg)](https://console.groq.com)
[![Evaluation Gates](https://img.shields.io/badge/Eval%20Gates-100%25%20PASS%20(24%2F24)-brightgreen.svg)](eval/last_run.json)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

*Your shop's WhatsApp answered in seconds — day and night — strictly from your verified catalog. Grounded, cited, bilingual (English + Roman Urdu), and 100% $0-cost stack.*

---

[Key Features](#key-features) •
[Architecture](#architecture) •
[Eval Metrics](#verified-evaluation-metrics) •
[Quickstart](#quickstart) •
[API Reference](#api-reference) •
[Catalog Onboarding](#catalog-onboarding) •
[Sales Demo](#2-minute-walk-in-demo)

</div>

---

## What is DukaanAI?

Small and medium retail businesses across Pakistan and South Asia conduct the majority of their sales conversations on **WhatsApp**. Owners receive dozens or hundreds of repetitive inquiries every day:
> *"Yeh suit kitne ka hai?"* · *"Shop timings kya hain?"* · *"Delivery charges kitne hain?"* · *"Silk party wear available hai?"*

Because owners are busy managing inventory and walk-in customers, inquiries are answered late, inconsistently, or completely missed after hours. Hiring dedicated support staff costs PKR 25,000–35,000/month, while generic AI chatbots hallucinate prices, invent phantom discounts, and fail catastrophically on **Roman Urdu** (the authentic code-mixed dialect customers actually type).

**DukaanAI** solves this with a **local-first, grounded AI receptionist** engineered to guarantee that:
1. **It answers only from the shop's verified catalog.** Every single factual statement cites its exact source chunk `[n]`.
2. **It never guesses.** If an answer cannot be verified with mathematical certainty, it gracefully abstains and logs an escalation for the owner.
3. **It speaks natural Roman Urdu and English.** Code-mixed queries and colloquial spelling variations (`kitne ka hai / kitne ka he`, `kapra / kapda`, `dukan / shop`) are handled natively.
4. **$0 Infrastructure Cost.** Runs on Groq free-tier LLM inference, local CPU sentence-transformers, local Chroma vector store, and SQLite.

---

## Key Features

- ⚡ **Instant Response (Sub-10s)**: Answers customers 24/7, capturing night-time orders and weekend traffic.
- 🛡️ **Dual-Gate Anti-Drift Architecture**:
  - **Gate 1 (Retrieval Confidence)**: Rejects out-of-catalog or irrelevant queries before calling the LLM.
  - **Gate 2 (Entailment Verifier)**: An independent fact-checker LLM inspects each cited claim against its source chunk before customer delivery.
- 🗣️ **Bilingual Roman Urdu + English Detection**: Fast, rule-based language classifier with zero LLM latency or cost overhead.
- 📦 **Automated Catalog Onboarding**:
  - Ingests spreadsheets (`.xlsx` / `.csv`) with row-level validation.
  - Optical Character Recognition (OCR via Tesseract) for digitizing printed rate lists directly from a smartphone photo.
- 📊 **Owner Business Dashboard**:
  - Real-time KPI counters (Conversations, Messages, Abstentions, Open Escalations).
  - Escalation inbox with one-click resolution.
  - Full conversation audit trail with source chunk citations and verification status.
  - Top customer inquiries breakdown.
- 🔒 **Privacy-Focused & Local-First**: Customer conversations and vector embeddings remain completely local on the merchant's machine; no third-party data lock-in.

---

## Architecture

DukaanAI is orchestrated as a **LangGraph state machine** with two fail-safe gates protecting the business reputation:

```
Customer Message (WhatsApp / Web Chat)
         │
         ▼
┌──────────────────┐
│  INGEST (FastAPI)│   Normalize text, validate business identity
└────────┬─────────┘
         ▼
┌──────────────────┐
│  LANGUAGE NODE   │   Instant regex/token detector: English / Roman Urdu / Mixed
└────────┬─────────┘
         ▼
┌──────────────────┐
│    RETRIEVER     │   ChromaDB (per-business collection, multilingual embeddings)
└────────┬─────────┘
         ▼
    ┌────┴─────┐  Max similarity < 0.40?
    │  GATE 1  │─── YES ──▶ ┌──────────────┐
    └────┬─────┘            │ ABSTAIN NODE │ ──▶ Honest "can't verify" reply
         │ NO               │ + ESCALATION │ ──▶ Notification logged in SQLite
         ▼                  └──────────────┘
┌──────────────────┐
│  ANSWER ENGINE   │   Strict prompting: cite every factual claim [n],
│  (LangGraph node)│   never invent, emit NEED_ABSTAIN if unanswerable
└────────┬─────────┘
         ▼
┌──────────────────┐
│  VERIFIER NODE   │   LLM-as-judge entailment check for each cited claim [n]
└────────┬─────────┘   (SUPPORTED / CONTRADICTED / UNVERIFIABLE)
         ▼
    ┌────┴─────┐  NEED_ABSTAIN or any CONTRADICTED / UNVERIFIABLE claim?
    │  GATE 2  │─── YES ──▶ ABSTAIN NODE (logged to owner inbox)
    └────┬─────┘
         │ NO (All claims strictly SUPPORTED)
         ▼
┌──────────────────┐
│  REPLY DELIVERY  │   Bilingual response delivered to customer with audit trace
└────────┬─────────┘
         ▼
┌──────────────────┐
│ OWNER DASHBOARD  │   Streamlit: KPIs, escalations, conversation logs,
│   (Streamlit)    │   catalog uploader, live eval metrics
└──────────────────┘
```

---

## Verified Evaluation Metrics

Tested against a comprehensive 24-question adversarial benchmark (`eval/test_set.json`):
- **8 English answerable** questions (products, timings, delivery policies, locations)
- **8 Roman Urdu answerable** questions (authentic spelling variants, colloquial terms)
- **4 Out-of-catalog unanswerable** questions (shoes, iPhones, bridal lehengas, stitching)
- **4 Adversarial false-premise traps** (false price affirmation bait, price conflation)

| Metric | Result | Target Gate | Status |
|---|---|---|---|
| **Grounding Rate** (Claims entailed by cited catalog) | **100.0%** (22/22) | ≥ 85% | ✅ PASS |
| **Abstention Precision** (Unanswerable queries refused) | **100.0%** (4/4) | = 100% | ✅ PASS |
| **Adversarial Never-Affirms** (False prices refuted) | **100.0%** (4/4) | = 100% | ✅ PASS |
| **Citation Coverage** (Factual sentences carrying `[n]`) | **79.2%** (19/24) | Informational | ✅ PASS |
| **Overall Test Pass Rate** | **24 / 24 (100%)** | ≥ 22/24 | **PERFECT** |

> Re-run the evaluation suite anytime:
> ```powershell
> python eval/run_eval.py
> ```

---

## Technology Stack ($0 Total Cost)

| Component | Technology | Role |
|---|---|---|
| **LLM Inference** | Groq Free Tier (`openai/gpt-oss-120b`) | Deterministic answering & strict claim entailment checking |
| **Embeddings** | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Local, CPU-friendly bilingual vector representations |
| **Vector Index** | ChromaDB (`chromadb`) | Per-business vector similarity storage |
| **Relational Store** | SQLite (`sqlite3`) | Businesses, catalogs, policies, conversations, escalations |
| **State Machine** | LangGraph (`langgraph`) | Cyclical multi-node workflow with conditional gate routing |
| **REST API** | FastAPI + Uvicorn | Production-ready HTTP backend for WhatsApp webhooks |
| **Frontend UI** | Streamlit (`streamlit`) | Mobile-responsive sales demo & merchant management portal |
| **OCR Ingestion** | Tesseract OCR + Pillow | Automatic digitization of printed price sheets from photos |

---

## Quickstart

### Prerequisites
- Python 3.10, 3.11, or 3.12
- Free Groq API Key (Sign up in 30 seconds at [console.groq.com](https://console.groq.com) — no credit card needed)

### Windows Installation (PowerShell)

```powershell
# 1. Clone repository
git clone https://github.com/hanzlikhan/customerAgent.git
cd customerAgent

# 2. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install CPU PyTorch first (skips unnecessary ~2GB CUDA packages)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 4. Install project dependencies
pip install -r requirements.txt

# 5. Set up environment variables
copy .env.example .env
# Open .env and insert your GROQ_API_KEY:
notepad .env

# 6. Verify Groq connectivity
python scripts/check_groq.py
# Expected output: Groq connectivity OK. Model replied: OK

# 7. Seed demo business catalog ("Chenab Cloth House")
python scripts/seed_demo.py
# Expected output: Seed complete: 1 business, 40 items, 6 policies, 92 chunks.

# 8. Launch the Streamlit application
streamlit run app.py
```

### Linux / macOS Installation

```bash
# 1. Clone repository
git clone https://github.com/hanzlikhan/customerAgent.git
cd customerAgent

# 2. Virtual environment setup
python3 -m venv venv
source venv/bin/activate

# 3. Install CPU PyTorch & requirements
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
nano .env  # Add your GROQ_API_KEY

# 5. Verify and seed
python scripts/check_groq.py
python scripts/seed_demo.py

# 6. Run web application
streamlit run app.py
```

---

## API Reference

DukaanAI exposes a clean REST API via FastAPI for WhatsApp Cloud API integration or third-party webhooks.

Start the API server:
```powershell
python -m dukaanai.api
# API available at http://127.0.0.1:8000
# Interactive Swagger documentation: http://127.0.0.1:8000/docs
```

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health status and active model |
| `POST` | `/chat` | Submit a customer message; runs through LangGraph agent |
| `GET` | `/conversations?business_id=1` | List recent conversation sessions and message counts |
| `GET` | `/conversations/{id}/messages` | Retrieve full message thread with verdict audit metadata |
| `GET` | `/escalations?business_id=1&status=open` | List unresolved customer questions needing owner attention |
| `POST` | `/escalations/{id}/resolve` | Mark an escalation as resolved with optional resolution notes |
| `GET` | `/dashboard/summary?business_id=1` | Aggregate metrics (conversations, messages, abstentions, top questions) |

#### Example: Chat Completion Request
```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"business_id": 1, "user_text": "lawn ka 3 piece suit kitne ka hai?"}'
```

#### Example Response
```json
{
  "reply": "Lawn ka 3 piece suit 2,950 rupay per suit hai [1]. Luxury embroidery wala version 4,200 rupay per suit hai [3].",
  "abstained": false,
  "lang": "ur",
  "citations": [
    {
      "ref_id": 2,
      "similarity": 0.721,
      "text": "PRODUCT (Urdu): Lawn ka 3 piece suit, geometric design wala. Keemat: 2,950 rupay per suit..."
    }
  ],
  "escalation_id": null,
  "conversation_id": 1
}
```

---

## Catalog Onboarding

Onboard any local merchant in minutes using the **📦 Catalog** tab in the Streamlit app or `dukaanai/onboarding.py`.

### 1. Spreadsheet Import (`.xlsx` or `.csv`)
Place a `.xlsx` or `.csv` catalog with the following columns (download standard template at `data/catalog_template.xlsx`):

| Column | Required | Allowed Aliases | Description | Example |
|---|---|---|---|---|
| `name_en` | Yes | `name`, `product`, `item` | English product title | `Premium 3-Piece Lawn Suit` |
| `price` | Yes | `rate`, `keemat` | Numeric price (> 0) | `3450` |
| `unit` | Yes | `per` | Sales unit | `per suit`, `per meter`, `per piece` |
| `name_ur_roman` | No | `urdu`, `nameur` | Roman Urdu title (defaults to `name_en`) | `Lawn ka 3 piece suit` |
| `category` | No | `cat` | Product classification | `Lawn`, `Cotton`, `Winter` |
| `variants` | No | `colors`, `rang` | Variant details | `color: red, blue, green` |

*Every row is validated against strict constraints. Invalid rows are flagged with specific row numbers and reasons; valid rows are inserted and indexed immediately into Chroma.*

### 2. Printed Rate List Photo OCR
1. Capture a clear, well-lit photo of the store's printed rate list.
2. Upload via the Streamlit interface.
3. Tesseract OCR parses lines matching `<Item Name> <Price> <Unit>`.
4. The merchant reviews the parsed preview before committing changes.

---

## 2-Minute Walk-In Demo

When pitching DukaanAI to a shop owner, follow the structured script in [DEMO_SCRIPT.md](DEMO_SCRIPT.md):

1. **The Hook (30s)**: *"How many WhatsApp messages do you get daily asking 'yeh kitne ka hai?' ... and how many do you answer late or miss after closing?"*
2. **Chip 1 (Urdu Price)**: Click *"lawn ka 3 piece suit kitne ka hai?"* → Instant answer in Roman Urdu from catalog.
3. **Chip 2 (English Timings)**: Click *"What are your timings?"* → Instant policy reply in English.
4. **Chip 3 (The Abstention Moment)**: Click *"do you sell shoes?"* → Amber alert appears: refuses to guess, notifies the owner in the dashboard.
5. **The Close**: *"Every other chatbot hallucinates prices. DukaanAI never invents a price. Less than PKR 10,000/month — a quarter of an assistant's salary."*

---

## Project Structure

```
dukaanai-v1/
├── app.py                      # Streamlit application: Chat, Dashboard & Catalog tabs
├── requirements.txt            # Minimal open-source dependencies
├── .env.example                # Configuration template (Groq key, model defaults)
├── .gitignore                  # Strict secret and cache exclusions
├── README.md                   # Complete system documentation
├── DEMO_SCRIPT.md              # 2-minute sales walk-in script
├── docs/
│   └── one-pager.md            # Merchant leave-behind sales flyer
├── data/                       # Local data storage
│   ├── catalog_template.xlsx   # Pre-formatted catalog upload template
│   ├── dukaanai.db             # Local SQLite database (auto-generated)
│   └── chroma/                 # Local vector store (auto-generated)
├── dukaanai/                   # Core application package
│   ├── __init__.py
│   ├── config.py               # Central configuration & dynamic credential loader
│   ├── llm.py                  # Single robust choke point for Groq LLM invocations
│   ├── db.py                   # Pure SQLite data access layer
│   ├── index.py                # Chroma indexing, vectorization & retrieval
│   ├── agent.py                # LangGraph state machine & dual verification gates
│   ├── api.py                  # FastAPI REST backend
│   ├── onboarding.py           # Multi-modal catalog parsers (Spreadsheet & OCR)
│   └── demo_data.py            # Fictional "Chenab Cloth House" reference catalog
├── eval/                       # Verification & evaluation harness
│   ├── test_set.json           # 24-question bilingual adversarial test suite
│   ├── run_eval.py             # Automated test evaluator and metric calculator
│   └── last_run.json           # Latest verified test execution results
└── scripts/                    # Automation utilities
    ├── check_groq.py           # Connectivity & API key validation
    ├── seed_demo.py            # Clean-slate database & vector index seeder
    ├── verify_phase1.py        # Data consistency & retrieval quality verifier
    └── verify_phase2.py        # LangGraph agent live execution verifier
```

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
