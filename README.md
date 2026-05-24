# Rowdy, Your Crowder Guide

POC "Get Started" assistant for Crowder College. FastAPI + Claude (with web search restricted to crowder.edu).

## Folder layout

```
rowdy-enrollment/
├── main.py
├── claude_service.py
├── knowledge.py          ← catalog retrieval
├── requirements.txt
├── Procfile
├── .gitignore
├── .env.example
├── README.md
├── data/
│   ├── catalog.txt       ← extracted 2026-27 catalog text (required at runtime)
│   ├── 2026-27-Crowder-Catalog-Final-V1_03.pdf   ← source, for re-extraction
│   └── Fall-2026.pdf     ← source calendar, for reference
├── templates/
│   └── chat.html
└── static/
    └── rowdy.png         ← graduation-cap mascot
```

## How Rowdy knows things

Four sources, highest-priority first:

1. **Calendars + verified contacts** — baked into the system prompt in `claude_service.py`. Authoritative, no lookup needed. Three terms loaded: Summer 2026, Fall 2026, Spring 2027.
2. **Catalog excerpts** — `knowledge.py` loads `data/catalog.txt`, splits it into pages, and injects the few most relevant pages into each turn. The full 206-page catalog is never sent at once.
3. **Web search** — restricted to crowder.edu, for anything current or not in the catalog.
4. **Honest "ask Admissions"** when nothing covers it.

To refresh the catalog for a new year: replace the PDF in `data/`, then re-extract with
`pdftotext -layout data/<catalog>.pdf data/catalog.txt`. To add or update a calendar, edit the
dated lists in `claude_service.py` (currently Summer 2026, Fall 2026, and Spring 2027).

## Local setup

```bash
pip install -r requirements.txt
cp .env.example .env       # then fill in real values
uvicorn main:app --reload
```

Visit http://localhost:8000.

## Deploy to Railway

1. Push this folder to a new GitHub repo.
2. In Railway, create a new project from the repo.
3. Under **Variables**, set:
   - `ANTHROPIC_API_KEY`
   - `SESSION_SECRET` — generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Use a fresh value, don't share with the tutor bot.
   - `CLAUDE_MODEL` (optional)
4. **Important:** in the Anthropic Console, make sure **web search is enabled** for your organization — the bot will error otherwise.

Railway auto-detects Python via `requirements.txt` and uses the `Procfile` to start the app.
