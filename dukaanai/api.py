"""FastAPI backend for DukaanAI (Phase 4).

Exposes the LangGraph agent over HTTP for the Streamlit frontend (Phase 5)
and future WhatsApp integration.

Run:  python -m dukaanai.api   (from the repo root)
Docs: http://127.0.0.1:8000/docs
"""

from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import agent, config, db

app = FastAPI(
    title="DukaanAI API",
    description="Grounded bilingual AI receptionist — HTTP API",
    version="0.4.0",
)

# v1 demo: allow all origins. PRODUCTION MUST restrict this to the
# dashboard's origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    business_id: int = Field(..., gt=0)
    user_text: str = Field(..., min_length=1)
    customer_ref: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    abstained: bool
    lang: str
    citations: list
    escalation_id: Optional[int] = None
    conversation_id: Optional[int] = None


class ResolveRequest(BaseModel):
    resolution: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "model": config.GROQ_MODEL}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if db.get_business(req.business_id) is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown business_id={req.business_id}",
        )
    text = req.user_text.strip()
    if not text:
        raise HTTPException(
            status_code=422, detail="user_text must not be empty"
        )
    try:
        state = agent.run_agent(
            req.business_id, text, customer_ref=req.customer_ref
        )
    except ValueError as e:  # e.g. unknown business raised mid-graph
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:  # e.g. Groq failure
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")
    citations = [
        {
            "ref_id": c["metadata"].get("ref_id"),
            "similarity": round(c.get("similarity", 0.0), 4),
            "text": c["text"][:300],
        }
        for c in state.get("chunks", [])
    ]
    return ChatResponse(
        reply=state.get("final_reply", ""),
        abstained=bool(state.get("abstained", False)),
        lang=state.get("lang", "en"),
        citations=citations,
        escalation_id=state.get("escalation_id"),
        conversation_id=state.get("conversation_id"),
    )


@app.get("/escalations")
def list_escalations(business_id: int, status: str = "open"):
    if db.get_business(business_id) is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown business_id={business_id}"
        )
    rows = db.get_escalations(business_id, status=status)
    return [
        {
            "id": r["id"],
            "question": r["question"],
            "status": r["status"],
            "created_at": r["created_at"],
            "resolved_at": r["resolved_at"],
            "resolution": r["resolution"] if "resolution" in r.keys() else None,
        }
        for r in rows
    ]


@app.post("/escalations/{escalation_id}/resolve")
def resolve_escalation(escalation_id: int, req: ResolveRequest):
    if db.get_escalation(escalation_id) is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown escalation_id={escalation_id}",
        )
    db.resolve_escalation(escalation_id, req.resolution)
    return {"id": escalation_id, "status": "resolved"}


@app.get("/conversations")
def list_conversations(business_id: int, limit: int = 20):
    if db.get_business(business_id) is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown business_id={business_id}"
        )
    rows = db.list_conversations(business_id, limit=min(limit, 100))
    return [
        {
            "id": r["id"],
            "customer_ref": r["customer_ref"],
            "language": r["language"],
            "started_at": r["started_at"],
            "message_count": r["message_count"],
        }
        for r in rows
    ]


@app.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(conversation_id: int):
    rows = db.get_messages(conversation_id)
    return [
        {
            "id": r["id"],
            "direction": r["direction"],
            "text": r["text"],
            "retrieved_chunk_ids": r["retrieved_chunk_ids"],
            "verdict": r["verdict"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@app.get("/dashboard/summary")
def dashboard_summary(business_id: int):
    if db.get_business(business_id) is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown business_id={business_id}"
        )
    return db.dashboard_summary(business_id)


if __name__ == "__main__":
    db.init_db()
    uvicorn.run(app, host="127.0.0.1", port=8000)
