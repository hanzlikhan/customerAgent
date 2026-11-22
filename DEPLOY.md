# Deploying DukaanAI Live (free)

Two parts, both free:

| Part | Host | What it runs |
|------|------|--------------|
| Backend API (FastAPI + LangGraph agent) | **Hugging Face Spaces** (Docker) | `dukaanai/api.py` — chat, SSE live stream, dashboard, catalog upload |
| Frontend (React + Vite + Tailwind) | **Vercel** | `frontend/` — chat UI, live agent trace, dashboard, catalog |

HF Spaces is the backend pick because the embedding model (~470 MB) and
torch need real RAM — the free CPU Space (2 vCPU, 16 GB RAM) handles it;
Render's free tier (512 MB) does not.

## 1. Push this code to GitHub

```bash
git add -A
git commit -m "Phase 7: React frontend + live SSE chat + deploy files"
git push origin main
```

(If you cloned fresh: `git clone https://github.com/hanzlikhan/customerAgent.git`,
copy the changed files in, then commit + push.)

## 2. Backend — Hugging Face Spaces (Docker)

1. Get a free Groq key (no card): https://console.groq.com → API Keys → Create.
2. Go to **https://huggingface.co/new-space** and sign in (free account).
3. Name it `dukaanai-api`, pick SDK **Docker**, visibility **Public**, Create.
4. In the Space: **Settings → Repository secrets → New secret**:
   name `GROQ_API_KEY`, value your `gsk_...` key.
5. Push the repo into the Space (HF gives you the git remote on the
   Space page — it is a normal git repo):
   ```bash
   git remote add hf https://huggingface.co/spaces/<your-username>/dukaanai-api
   git push hf main
   ```
   The Space builds the Docker image (`Dockerfile` + `start_api.sh`),
   seeds the demo shop (Chenab Cloth House, 40 items) on first boot,
   and serves the API. **First build takes 10–20 minutes** (torch +
   the embedding model download). Later restarts are fast.
6. Check it: open `https://<your-username>-dukaanai-api.hf.space/health`
   — you should see `{"status":"ok","model":"openai/gpt-oss-120b"}`.
   Your API base URL is `https://<your-username>-dukaanai-api.hf.space`.

Notes:
- The Space sleeps after a period of inactivity on the free tier and
  wakes on the next visit (~1–2 minutes to wake).
- The demo database lives on the Space's disk, so conversations and
  escalations persist across restarts.
- The Streamlit app (`app.py`) still exists in the repo but is no
  longer the frontend — the React app is. `app.py` is ignored by the
  Docker build's startup (only the API runs).

## 3. Frontend — Vercel

1. Go to **https://vercel.com/new** and sign in with GitHub.
2. **Import** repository `hanzlikhan/customerAgent`.
3. Set **Root Directory** to `frontend` (Framework Preset: Vite).
4. **Environment Variables** → add:
   - `VITE_API_URL` = your Space URL from step 2
     (e.g. `https://hanzlikhan-dukaanai-api.hf.space`)
   - `VITE_BUSINESS_ID` = `1`
5. Click **Deploy**. Your live link will be like
   `https://dukaanai.vercel.app`.

## 4. Verify the live app

1. Open the Vercel link — you should see the DukaanAI chat with
   "API connected" in the top bar.
2. Tap **Price in Roman Urdu** — watch the live agent trace complete
   step by step, then the cited answer with "2 claim(s) verified".
3. Open **Owner dashboard** — KPIs, escalation inbox, conversations.
4. Open **Catalog** — upload the template to test import
   (the template link downloads `data/catalog_template.xlsx`).

## 5. Make it yours (after the demo works)

- **Real shop catalog:** use the Catalog tab to upload a real
  spreadsheet, or edit `dukaanai/demo_data.py` and re-seed.
- **WhatsApp:** the FastAPI backend (`dukaanai/api.py`) is the
  integration surface — a WhatsApp Cloud API webhook is the next
  build step, not part of this deployment.
- **Custom domain:** Vercel supports custom domains on the free plan.
