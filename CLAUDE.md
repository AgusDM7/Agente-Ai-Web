# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server (auto-reload on file changes)
uvicorn main:app --reload

# Run on a specific port
uvicorn main:app --reload --port 8000
```

The app is served at `http://localhost:8000`.

## Environment Variables

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your_key_here
GITHUB_TOKEN=your_token_here   # optional, increases GitHub API rate limits
```

## Architecture

This is a single-page AI chat app for programming questions. It has two Python files and one HTML template.

**Request flow:**
1. Browser sends `POST /agent` with `{ "prompt": "..." }`
2. `main.py` validates the prompt (max 600 chars, rate limit: 3 req / 120 s per IP)
3. `main.py` calls `run_agent()` from `agent.py`
4. `agent.py` runs a LangGraph ReAct agent (gpt-4o-mini) that can call up to 3 tools in a loop (max 10 recursion steps)
5. The final message from the agent's message list is returned as `{ "response": "..." }`

**`agent.py` — the AI layer:**
- Three `@tool`-decorated functions: `search_wikipedia`, `search_github`, `search_stackoverflow`
- All HTTP calls go through `_get()` (shared httpx client, 10 s timeout)
- The ReAct agent is created once at module import with `create_react_agent` and reused across requests (stateless — no memory between calls)
- Stack Overflow tool makes two API calls: one to find questions, one to fetch the top answer body (strips HTML tags, truncates to 2 000 chars)

**`main.py` — the web layer:**
- FastAPI app with Jinja2 templates and a `/static` mount
- Rate limiting is in-memory (`defaultdict(list)` of timestamps per IP) — resets on server restart, not suitable for multi-process deployments
- `GET /` → renders `templates/index.html`
- `POST /agent` → invokes the agent, returns `AgentResponse`

**`templates/index.html` — the frontend:**
- Single self-contained HTML file with all CSS and JS inline (no build step)
- Chat UI appends bubbles to `#chatLog` via DOM manipulation
- Character counter enforces a soft limit of 300 in the UI (server enforces 600)
- Enter sends, Shift+Enter inserts newline
