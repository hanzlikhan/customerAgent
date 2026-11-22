# DukaanAI backend (FastAPI) — Hugging Face Spaces (Docker SDK) or any
# container host. The React frontend (frontend/) is deployed separately
# (Vercel) and talks to this API over HTTPS.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# tesseract for the OCR catalog path (photo rate lists)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# HF Spaces serves on port 7860; honour $PORT when set.
EXPOSE 7860
CMD ["bash", "start_api.sh"]
