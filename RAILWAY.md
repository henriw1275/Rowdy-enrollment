# Testing Rowdy on Railway

Standalone POC — no Canvas yet. You're putting the chat at a public Railway
URL so you can poke at Rowdy from any browser.

## 1. Push to GitHub

In the project directory:

```bash
git init
git add .
git commit -m "Rowdy POC"
gh repo create rowdy-tutor --private --source=. --push
```

`.gitignore` already excludes `.env`, so your API key stays on your laptop.
The `static/rowdy.png` mascot image is committed intentionally.

## 2. Create the Railway service

1. Go to railway.app → **New Project → Deploy from GitHub repo** → pick `rowdy-tutor`.
2. Railway auto-detects Python from `requirements.txt` and uses the `Procfile`.
3. First build will fail to start because env vars are missing — that's expected.

## 3. Set Railway environment variables

In the Railway dashboard, open the **Variables** tab and add:

| Variable | Value |
|---|---|
| `SESSION_SECRET` | Output of `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ANTHROPIC_API_KEY` | Your key from console.anthropic.com |
| `CLAUDE_MODEL` | `claude-haiku-4-5-20251001` |

Railway will redeploy.

## 4. Generate a public URL

In Railway: **Settings → Networking → Generate Domain.** You'll get something
like `rowdy-tutor-production.up.railway.app`.

Quick sanity check: hit `https://YOUR-URL/healthz` in a browser. Should return `{"ok": true}`.

## 5. Test it

Open `https://YOUR-URL/` in any browser. The chat UI loads with Rowdy's
mascot in the header. Type "hi" — he should respond with his Crowder
greeting and start the diagnostic flow.

## What to actually test (suggested checklist)

| Test | What to look for |
|---|---|
| Say "hi" | Opening greeting (only once per session), then asks about instructor's AI policy |
| Answer the policy question | Asks what you're working on |
| Say "I need help with my essay" | Asks about your thesis or what part you're stuck on |
| Ask for a direct answer like "just write my intro paragraph" | Should refuse and redirect to guided thinking |
| Ask something unrelated like "what's the weather" | Redirect message about schoolwork |
| Upload a screenshot of a math problem | Rowdy reads it and asks one targeted question |
| Refresh the page | Same conversation continues (session cookie persists) |
| Open in incognito | Fresh conversation (different session) |
| Restart the Railway service | All conversations lost (RAM-only, expected) |

## Common things that go wrong

| Symptom | Likely cause |
|---|---|
| Build fails: "no module named anthropic" | `requirements.txt` didn't get committed. Confirm `git ls-files \| grep requirements` |
| Page loads but chat returns 500 | Open Railway logs. Usually a missing or wrong `ANTHROPIC_API_KEY` |
| Rowdy responds but breaks character (gives direct answers) | The system prompt isn't being sent. Confirm `claude_service.py` is the one with `ROWDY_SYSTEM_PROMPT` and prompt caching enabled |
| Avatar shows "R" instead of the mule | `static/rowdy.png` didn't get pushed. Check `git ls-files \| grep rowdy` |

## Iterating on Rowdy

The prompt is in `claude_service.py` as `ROWDY_SYSTEM_PROMPT`. Edit, commit,
push — Railway redeploys automatically in ~30 seconds.

**Tip**: when iterating on the prompt, the in-memory conversation history
gets wiped on every redeploy, which means you'll re-greet from a clean slate
each time. That's useful for testing the opening flow but annoying if you
were mid-conversation.

## Tearing it down later

Railway → project → **Settings → Delete Project.**
