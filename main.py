"""
Rowdy the Homework Helper — standalone web POC.

A simple chat UI backed by Claude. No authentication, no Canvas LTI; this
exists to validate the tutor's behavior, prompt, and UX before wrestling
with LMS integration.

Each browser session gets its own conversation, scoped by a session cookie.
Conversations live in RAM and disappear on server restart.

Endpoints:
  GET   /          — chat UI
  POST  /api/chat  — chat with Rowdy (multipart: message + optional files)
  GET   /healthz   — health check
"""
import base64
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from claude_service import ClaudeTutor

load_dotenv()
BASE_DIR = Path(__file__).parent

app = FastAPI(title="Rowdy — Homework Helper (POC)")

# Signed session cookies identify each browser. Lax SameSite is fine since
# we're not iframed; HTTPS-only is off here so local `uvicorn` works without
# TLS. Railway terminates TLS in front of the app.
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ["SESSION_SECRET"],
    https_only=False,
    same_site="lax",
)

(BASE_DIR / "static").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

tutor = ClaudeTutor(model=os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001"))

# In-RAM conversation store, keyed by browser session id.
CONVERSATIONS: dict[str, list[dict]] = {}

HISTORY_TURN_CAP = 12
MAX_FILE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
ALLOWED_DOCUMENT_TYPES = {"application/pdf"}


def _ensure_session_id(request: Request) -> str:
    """Assign a stable random id to this browser if it doesn't have one yet."""
    sid = request.session.get("sid")
    if not sid:
        sid = secrets.token_urlsafe(16)
        request.session["sid"] = sid
    return sid


@app.get("/")
async def index(request: Request):
    _ensure_session_id(request)
    return templates.TemplateResponse(request, "chat.html")


@app.post("/api/chat")
async def chat(
    request: Request,
    message: str = Form(""),
    files: list[UploadFile] = File(default=[]),
):
    sid = _ensure_session_id(request)

    if not message.strip() and not files:
        raise HTTPException(400, "Send a message or attach a file")

    content_blocks: list[dict] = []
    for f in files:
        data = await f.read()
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(413, f"{f.filename} exceeds 5 MB limit")
        media_type = (f.content_type or "").lower()
        b64 = base64.standard_b64encode(data).decode("ascii")
        if media_type in ALLOWED_DOCUMENT_TYPES:
            content_blocks.append({
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
            })
        elif media_type in ALLOWED_IMAGE_TYPES:
            content_blocks.append({
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": b64},
            })
        else:
            raise HTTPException(415, f"Unsupported file type: {media_type or 'unknown'}")
    if message.strip():
        content_blocks.append({"type": "text", "text": message})

    history = CONVERSATIONS.setdefault(sid, [])
    history.append({"role": "user", "content": content_blocks})

    trimmed = _strip_old_attachments(history[-HISTORY_TURN_CAP:])
    reply = await tutor.reply(history=trimmed)
    history.append({"role": "assistant", "content": reply})
    return {"reply": reply}


def _strip_old_attachments(history: list[dict]) -> list[dict]:
    """Keep image/document blocks only on the most recent message.

    Documents are expensive — a 5-page PDF is ~10–15k tokens. Re-sending
    one across 12 turns of history would cost 6× more than necessary.
    Older messages get a small text placeholder instead.
    """
    if not history:
        return history
    last_idx = len(history) - 1
    cleaned = []
    for i, msg in enumerate(history):
        if i == last_idx or isinstance(msg["content"], str):
            cleaned.append(msg)
            continue
        new_blocks = []
        attachment_count = 0
        for block in msg["content"]:
            t = block.get("type") if isinstance(block, dict) else None
            if t in ("image", "document"):
                attachment_count += 1
            else:
                new_blocks.append(block)
        if attachment_count:
            new_blocks.append({
                "type": "text",
                "text": f"[{attachment_count} earlier attachment(s) — not re-sent]",
            })
        cleaned.append({"role": msg["role"], "content": new_blocks or msg["content"]})
    return cleaned


@app.get("/healthz")
async def healthz():
    return {"ok": True}
