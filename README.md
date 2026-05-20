# Rowdy the Homework Helper — Standalone POC

A web chat that runs the Rowdy Homework Helper persona, backed by Claude Haiku.
This is the **pre-Canvas** version: a plain web page at `/` you can hit from
any browser. Canvas LTI integration is deferred until the tutor behavior is
where you want it.

**Deploying to Railway?** Skip ahead to [`RAILWAY.md`](./RAILWAY.md).

## POC scope

| In | Out (for now) |
|---|---|
| Rowdy persona as the verbatim system prompt | Canvas LTI 1.3 integration |
| Per-browser conversation memory (cookie-based session) | Authentication / user identity |
| Prompt caching for the ~1,500-token system prompt | Postgres / Redis / any DB |
| Last 12 messages sent to Claude per call | Logging of student prompts/responses |
| PDF + image upload (homework, screenshots) | Document **production** |
| Aggressive attachment trimming (see below) | Streaming responses |
| Crowder-blue chat UI with Rowdy's mascot | |

Conversations live in RAM. Restart the server and they're gone. That's a
deliberate POC choice — you can validate behavior without worrying about
database migrations or FERPA logs yet.

## Files

- `main.py` — FastAPI app: chat UI at `/`, chat API at `/api/chat`
- `claude_service.py` — Anthropic SDK wrapper, Rowdy system prompt, prompt caching
- `templates/chat.html` — chat UI
- `static/rowdy.png` — mascot avatar (already in place)
- `Procfile` — start command for Railway
- `RAILWAY.md` — deployment steps

## Local quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                       # fill in SESSION_SECRET, ANTHROPIC_API_KEY
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` and say hi to Rowdy.

`SESSION_SECRET` can be generated with:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## How document support behaves

Students can attach PDFs and images (PNG, JPEG, GIF, WebP), 5 MB per file.
**Each attachment is sent to Claude exactly once**, on the turn it's uploaded.
On every later turn it's replaced with a placeholder in history. That keeps a
single 5-page PDF from being re-sent across 12 history turns and costing 6×
more than necessary.

The Socratic flow in the Rowdy prompt makes this work: Rowdy looks at the
homework on turn N, asks a guiding question, and operates on the student's
text answers from turn N+1 onward.

## Token economics (Haiku + caching, rough per-session)

For a 30-turn text-only session: **~$0.01–$0.03 per student.**
Add a 5-page PDF: **+$0.01–$0.02.** Add one screenshot: **+~$0.003.**

Tuning levers in order of impact:

1. Lower `HISTORY_TURN_CAP` in `main.py` (currently 12 → try 8)
2. Trim the Rowdy system prompt itself
3. Tighten `max_tokens` in `claude_service.py` (currently 512)

## When you're ready to add Canvas

The Canvas LTI 1.3 work from earlier still applies — `main.py` just gains four
endpoints (`/lti/login`, `/lti/launch`, `/lti/jwks`, plus the OIDC bits),
identity comes from the launch JWT instead of an anonymous session cookie,
and the chat UI gets served inside a Canvas iframe instead of at `/`.
Everything below the chat handler (claude service, system prompt, attachment
handling) stays the same.

## When you're ready to leave POC entirely

1. Conversation store → Postgres (keyed on `(user_id, course_id, turn_index)`)
2. Streaming via `client.messages.stream(...)` and SSE on `/api/chat`
3. Per-user/course token budgets + usage logging
4. FERPA review of any content logging
5. Request Zero Data Retention from Anthropic for the API key
