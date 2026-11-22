# DukaanAI frontend (React)

Real React frontend for DukaanAI — Vite + React 19 + Tailwind CSS v4 +
lucide-react icons (no emojis). Talks to the FastAPI backend
(`../dukaanai/api.py`).

## Run locally

```bash
npm install
npm run dev        # http://127.0.0.1:5173
```

The API must be running too (repo root):

```bash
python -m dukaanai.api   # http://127.0.0.1:8000
```

## Configuration

Copy `.env.example` to `.env` and adjust:

| Variable | Default | Meaning |
|----------|---------|---------|
| `VITE_API_URL` | `http://127.0.0.1:8000` | FastAPI backend base URL |
| `VITE_BUSINESS_ID` | `1` | Demo business id (Chenab Cloth House) |

## What is in here

- `src/components/Chat.jsx` — customer chat + live agent trace.
  Chat runs over Server-Sent Events (`GET /chat/stream`): each agent
  step (understand → language → retrieve → answer → verify) streams
  in real time, then the cited reply arrives with its claim verdicts.
- `src/components/Dashboard.jsx` — owner dashboard: KPIs, top
  questions, escalation inbox (resolve), recent conversations.
  Auto-refreshes every 15 seconds.
- `src/components/Catalog.jsx` — catalog onboarding: upload a
  spreadsheet (.xlsx/.csv) or a photo of a printed rate list (.png/.jpg),
  preview the parsed rows, import. Uses `POST /catalog/upload` +
  `POST /catalog/import`.
- `src/components/Sidebar.jsx` — brand, nav, demo-shop card,
  "How it answers", latest eval metrics.
- `src/lib/api.js` — API client + SSE stream helper.

## Build / deploy

```bash
npm run build    # outputs dist/ (Vercel: Root Directory = frontend)
```

Full live-deploy guide (Vercel + Hugging Face Spaces backend):
`../DEPLOY.md`.
