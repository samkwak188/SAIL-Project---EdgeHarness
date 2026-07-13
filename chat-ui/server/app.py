"""FastAPI SSE bridge for the sail chat UI.

Run from chat-ui/server/ (sail-platform venv active, .env loaded):
    uvicorn app:app --reload --port 8800
"""
from __future__ import annotations

import asyncio
import json
import queue
import threading

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import bridge
import sessions

app = FastAPI(title="sail chat bridge")


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/api/chat")
async def chat(req: ChatRequest):
    session = sessions.get(req.session_id) if req.session_id else None
    if session is None:
        session = sessions.create(title=req.message[:60])
    sid = session["id"]

    q: queue.Queue = queue.Queue()
    threading.Thread(target=bridge.run_chat, args=(req.message, q), daemon=True).start()

    async def gen():
        yield _sse("session", {"id": sid})
        events = []
        while True:
            ev = await asyncio.to_thread(q.get)
            if ev is None:
                break
            events.append(ev)
            yield _sse(ev["type"], ev["data"])
        sessions.append(sid, {"role": "user", "content": req.message})
        sessions.append(sid, {"role": "assistant", "events": events})

    return StreamingResponse(gen(), media_type="text/event-stream")


class SelectRequest(BaseModel):
    file: str


class KeyRequest(BaseModel):
    api_key: str


@app.get("/api/models")
def list_models():
    return bridge.list_configs()


@app.post("/api/models/select")
def select_model(req: SelectRequest):
    return {"ok": bridge.select_config(req.file)}


@app.post("/api/keys")
def add_key(req: KeyRequest):
    return bridge.add_key(req.api_key)


@app.get("/api/sessions")
def list_sessions():
    return sessions.list_sessions()


@app.get("/api/sessions/{sid}")
def get_session(sid: str):
    return sessions.get(sid) or {}
