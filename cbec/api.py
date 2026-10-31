from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from cbec.engine import MODELS, TARGETS, Store

DATA_PATH = Path(os.getenv("CBEC_DATA_PATH", "data/processed/demo.json"))
app = FastAPI(title="CBEC Recommendation & Operations API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CBEC_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
store: Store | None = None


def envelope(data=None, error=None):
    return {"data": data, "meta": {"request_id": str(uuid.uuid4()), "generated_at": datetime.now(timezone.utc).isoformat()}, "error": error}


def get_store() -> Store:
    global store
    if store is None or store.path != DATA_PATH or store.path.stat().st_mtime != getattr(store, "mtime", None):
        if not DATA_PATH.exists():
            raise HTTPException(503, "Dataset not prepared. Run python -m cbec.pipeline first.")
        store = Store(DATA_PATH)
        store.mtime = DATA_PATH.stat().st_mtime
    return store


@app.exception_handler(HTTPException)
async def http_error(_request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content=envelope(error={"code": exc.status_code, "message": exc.detail}))


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content=envelope(error={"code": 422, "message": "Invalid request parameters", "details": exc.errors()}))


@app.get("/api/v1/health")
def health():
    return envelope({"status": "ok", "data_ready": DATA_PATH.exists()})


@app.get("/api/v1/overview")
def overview():
    return envelope(get_store().overview())


@app.get("/api/v1/sessions")
def sessions(limit: int = Query(10, ge=1, le=100)):
    s = get_store()
    return envelope([{"session_id": row["session"], "events": len(row["events"]), "split": "validation"}
                     for row in s.visible[:limit]])


@app.get("/api/v1/sessions/{session_id}")
def session(session_id: int):
    s = get_store()
    if session_id not in s.sessions:
        raise HTTPException(404, "Session not found")
    return envelope({"session_id": session_id, "events": s.sessions[session_id],
                     "split": "validation" if any(r["session"] == session_id for r in s.visible) else "train"})


@app.get("/api/v1/recommendations/{session_id}")
def recommendations(session_id: int, k: int = Query(10, ge=1, le=20), target: str = Query("order"), model: str = Query("hybrid")):
    if target not in TARGETS or model not in MODELS:
        raise HTTPException(422, "target or model is invalid")
    try:
        results = get_store().recommend(session_id, k, target, model)
    except KeyError:
        raise HTTPException(404, "Session not found") from None
    return envelope({"session_id": session_id, "results": results})


@app.get("/api/v1/items/top")
def top_items(metric: str = Query("order"), limit: int = Query(10, ge=1, le=100)):
    if metric not in TARGETS:
        raise HTTPException(422, "metric is invalid")
    return envelope(get_store().top_items(metric, limit))


@app.get("/api/v1/items/{item_id}/stats")
def item_stats(item_id: int):
    try:
        return envelope(get_store().item_stats(item_id))
    except KeyError:
        raise HTTPException(404, "Item not found") from None


@app.get("/api/v1/items/{item_id}/related")
def item_related(item_id: int, limit: int = Query(10, ge=1, le=50)):
    try:
        return envelope(get_store().related(item_id, limit))
    except KeyError:
        raise HTTPException(404, "Item not found") from None


@app.get("/api/v1/metrics/evaluation")
def evaluation():
    return envelope({"results": get_store().metrics, "split": get_store().data["split"],
                     "note": "Local last-event-window evaluation; not comparable with the official OTTO leaderboard."})


class ChatInput(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@app.post("/api/v1/agent/chat")
def chat(payload: ChatInput):
    return envelope(get_store().answer(payload.question))


@app.post("/api/v1/reports/operations")
def report():
    return envelope(get_store().report())
