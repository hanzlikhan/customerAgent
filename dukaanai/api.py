"""FastAPI backend for DukaanAI (Phase 4, extended Phase 7).

Exposes the LangGraph agent over HTTP for the React frontend
(frontend/) and future WhatsApp integration.

Run:  python -m dukaanai.api   (from the repo root)
Docs: http://127.0.0.1:8000/docs
"""

import json
import tempfile
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import agent, config, db, onboarding

app = FastAPI(
    title="DukaanAI API",
    description="Grounded bilingual AI receptionist — HTTP API",
    version="0.5.0",
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


class CatalogImportRequest(BaseModel):
    business_id: int = Field(..., gt=0)
    rows: list = Field(..., min_length=1)
    source_doc: str = Field(default="api-upload")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "model": config.GROQ_MODEL}


@app.get("/business/{business_id}")
def get_business(business_id: int):
    """Shop profile + catalog counts for the frontend header/sidebar."""
    row = db.get_business(business_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown business_id={business_id}"
        )
    out = dict(row)
    out["catalog_items"] = db.count_rows("catalog_item", business_id)
    out["policies"] = db.count_rows("policy", business_id)
    return out


@app.get("/eval/latest")
def eval_latest():
    """Latest eval metrics (eval/last_run.json), or null if never run."""
    p = Path(__file__).resolve().parent.parent / "eval" / "last_run.json"
    if not p.exists():
        return {"metrics": None}
    try:
        return {"metrics": json.loads(p.read_text(encoding="utf-8"))["metrics"]}
    except (json.JSONDecodeError, KeyError):
        return {"metrics": None}


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


# Node name -> user-facing live step shown while the agent works.
_STREAM_STEPS = {
    "ingest": ("understand", "Understanding your message"),
    "detect_language": ("language", "Detecting language"),
    "retrieve": ("retrieve", "Searching the catalog"),
    "answer": ("answer", "Drafting your answer"),
    "verifier": ("verify", "Verifying every claim"),
}


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.get("/chat/stream")
def chat_stream(business_id: int, user_text: str,
                customer_ref: Optional[str] = None):
    """Live chat over Server-Sent Events.

    Streams one `step` event per agent node as it completes (real
    progress, not a timer), then a single `result` event with the same
    payload as POST /chat, plus `verdicts`. Emits `error` and ends
    early if the agent fails.
    """
    if db.get_business(business_id) is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown business_id={business_id}"
        )
    text = (user_text or "").strip()
    if not text:
        raise HTTPException(
            status_code=422, detail="user_text must not be empty"
        )

    def generate():
        graph = agent.build_graph()
        state: dict = {}
        try:
            for update in graph.stream({
                "business_id": business_id,
                "user_text": text,
                "customer_ref": customer_ref,
            }):
                for node, patch in update.items():
                    if isinstance(patch, dict):
                        state.update(patch)
                    step = _STREAM_STEPS.get(node)
                    if step is not None:
                        payload = {"id": step[0], "label": step[1]}
                        if node == "retrieve":
                            payload["max_score"] = state.get("max_score")
                            payload["chunks"] = len(state.get("chunks", []))
                        yield _sse("step", payload)
        except RuntimeError as e:  # e.g. Groq failure
            yield _sse("error", {"detail": f"LLM error: {e}"})
            return
        except ValueError as e:
            yield _sse("error", {"detail": str(e)})
            return
        verdicts = state.get("verdicts") or []
        citations = [
            {
                "ref_id": c["metadata"].get("ref_id"),
                "similarity": round(c.get("similarity", 0.0), 4),
                "text": c["text"][:300],
            }
            for c in state.get("chunks", [])
        ]
        yield _sse("result", {
            "reply": state.get("final_reply", ""),
            "abstained": bool(state.get("abstained", False)),
            "lang": state.get("lang", "en"),
            "citations": citations,
            "verdicts": verdicts,
            "verified": sum(1 for v in verdicts
                            if v.get("verdict") == "SUPPORTED"),
            "escalation_id": state.get("escalation_id"),
            "conversation_id": state.get("conversation_id"),
        })

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/catalog/upload")
async def catalog_upload(business_id: int, file: UploadFile = File(...)):
    """Parse a catalog file WITHOUT writing. Returns preview rows + errors.

    Accepts .xlsx / .csv (spreadsheet) or .png / .jpg (printed rate-list
    photo via OCR). The frontend shows the preview, then calls
    POST /catalog/import with the rows to commit.
    """
    if db.get_business(business_id) is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown business_id={business_id}"
        )
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".xlsx", ".csv", ".png", ".jpg", ".jpeg"):
        raise HTTPException(
            status_code=400,
            detail=f"unsupported file type: {suffix or '(none)'} "
                   "(use .xlsx, .csv, .png or .jpg)",
        )
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        if suffix in (".xlsx", ".csv"):
            rows, errors = onboarding.parse_spreadsheet(tmp_path)
            raw_text = None
        else:
            rows, errors, raw_text = onboarding.parse_photo(tmp_path)
    except RuntimeError as e:  # e.g. tesseract missing
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return {
        "filename": file.filename,
        "rows": rows,
        "errors": errors,
        "raw_text": raw_text,
    }


@app.post("/catalog/import")
def catalog_import(req: CatalogImportRequest):
    """Commit previewed rows to the catalog and rebuild the index.

    Rows are re-validated server-side; invalid rows are rejected with
    reasons and never silently imported.
    """
    if db.get_business(req.business_id) is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown business_id={req.business_id}"
        )
    valid, errors = [], []
    for i, raw in enumerate(req.rows, start=1):
        if not isinstance(raw, dict):
            errors.append({"row": i, "reason": "row is not an object"})
            continue
        clean, err = onboarding.validate_row(raw, i)
        if err:
            errors.append({"row": i, "reason": err})
        else:
            valid.append(clean)
    imported = onboarding.commit_rows(
        valid, req.business_id, source_doc=req.source_doc
    ) if valid else 0
    return {"imported": imported, "errors": errors}


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
