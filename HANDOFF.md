# Lloyd Project Handoff Document

## Project Overview

**Lloyd** is an AI Executive Assistant that takes high-level product ideas and autonomously executes them to completion. You describe what you want ("Build a CLI calculator"), and Lloyd decomposes it into tasks, writes the code, runs tests, and iterates until done.

**Problem it solves**: Automating the entire software development lifecycle from idea to working code, without manual intervention between steps.

**Target users**: Developers who want to prototype ideas quickly, or automate repetitive development tasks.

**Tech stack**:
- Python 3.11+ with `uv` package manager
- CrewAI for multi-agent orchestration
- LiteLLM for LLM provider abstraction (currently using Ollama)
- FastAPI + React (Vite/TypeScript) for web GUI
- Tailwind CSS with custom glassmorphism styling

---

## Current State

### What's Working
- **CLI commands**: `lloyd idea "..."`, `lloyd status`, `lloyd resume`, `lloyd init`, `lloyd reset-story`
- **Web GUI**: Running at `http://localhost:8000` with futuristic glassmorphism design
  - Dashboard with Live Preview (real-time WebSocket activity feed)
  - Idea submission form
  - Task queue viewer
  - Progress log
  - Settings page
  - "How to Use" guide
- **LLM Integration**: Successfully using **Ollama with qwen2.5:14b** locally (no API key needed)
- **Agent system**: Planning, Execution, and Quality crews with YAML-configured agents
- **Test run completed**: Calculator idea was successfully executed and created working `calculator.py`

### What's Broken/Warnings (Non-blocking)
- **LiteLLM proxy warnings**: `apscheduler` missing - shows noisy error logs but doesn't block execution
- **Emoji encoding on Windows**: `charmap` codec errors in CrewAI event logs (cosmetic only)
- **Some tools fail gracefully**: DuckDuckGo search, GitHub CLI not installed - agents work around these

### In-Progress
- Nothing actively in-progress at handoff

---

## Architecture & Key Decisions

### Why CrewAI?
Chose CrewAI over alternatives (LangGraph, AutoGen) because it provides:
- YAML-based agent/task configuration (easy to modify without code changes)
- Built-in delegation between agents
- Sequential and hierarchical process support

### Why Ollama instead of OpenAI/Anthropic?
Switched from Anthropic to **Ollama** because:
- User didn't have Anthropic API key configured
- Local LLM = no API costs, no rate limits, works offline
- `ollama/qwen2.5:14b` is capable enough for code generation tasks

**Config location**: `src/lloyd/config.py` - change `DEFAULT_LLM` to switch models

### Why LiteLLM?
CrewAI uses LiteLLM under the hood for Ollama support. It's a required dependency.

### Frontend Architecture
- React SPA served by FastAPI (not a separate server)
- Built frontend lives in `src/lloyd/frontend/dist/`
- FastAPI catches all routes and serves `index.html` for SPA routing
- WebSocket at `/ws` for real-time updates during execution

### State Persistence
- `.lloyd/prd.json` - Task queue (stories, status, acceptance criteria)
- `.lloyd/progress.txt` - Session logs and learnings
- No database - everything is file-based for simplicity

---

## File Structure

```
lloyd/
├── src/lloyd/
│   ├── main.py              # CLI entry point (click commands)
│   ├── api.py               # FastAPI server + WebSocket
│   ├── config.py            # LLM config (DEFAULT_LLM = "ollama/qwen2.5:14b")
│   ├── orchestrator/
│   │   ├── flow.py          # Main LloydFlow class - orchestrates everything
│   │   ├── state.py         # LloydState dataclass
│   │   └── router.py        # Story selection logic
│   ├── crews/
│   │   ├── planning/        # Decomposes idea into PRD
│   │   ├── execution/       # Implements stories
│   │   └── quality/         # Runs tests, reviews code
│   ├── agents/              # BaseAgent + specialized agents (unused directly)
│   ├── tools/               # filesystem, shell, github, web_search, code_exec
│   ├── memory/
│   │   ├── prd_manager.py   # PRD CRUD operations
│   │   ├── progress.py      # Progress log operations
│   │   └── git_memory.py    # Git integration (basic)
│   └── frontend/
│       ├── src/             # React source (TypeScript)
│       └── dist/            # Built frontend (served by FastAPI)
├── .lloyd/                  # Project-specific state
│   ├── prd.json
│   └── progress.txt
├── tests/                   # pytest tests
├── pyproject.toml           # Dependencies and build config
└── CLAUDE.md                # AI assistant instructions
```

---

## Unfinished Work / Next Steps

1. **Story decomposition is simplistic**: Currently creates ONE story from any idea. Should parse LLM output to create multiple granular stories.

2. **No real dependency tracking**: Stories have a `dependencies` field but it's not used for ordering.

3. **Quality crew verification is basic**: Just checks for "passes: true" or "all criteria met" in text output.

4. **Missing tools**:
   - `duckduckgo-search` package not installed (web search fails)
   - GitHub CLI (`gh`) not installed (GitHub operations fail)

5. **GUI improvements possible**:
   - File tree viewer showing generated code
   - Diff viewer for changes
   - Stop/cancel button for running tasks

---

## Gotchas & Landmines

### Critical
- **Don't delete `.lloyd/` directory** during execution - it contains live state
- **Ollama must be running** before using Lloyd: `ollama serve`
- **Frontend must be rebuilt** after changes: `cd src/lloyd/frontend && npm run build`

### Windows-Specific
- Division operator `/` in CLI gets interpreted as path by Git Bash. Use Python import to test:
  ```python
  python -c "from calculator import perform_operation; print(perform_operation(20, 4, '/'))"
  ```

### CrewAI Quirks
- Agents need explicit `llm=get_llm()` parameter or they default to OpenAI
- Tool errors are logged but execution continues (fail gracefully)
- Verbose output includes emojis that break on Windows console

### LiteLLM Warnings
The `apscheduler` warnings are harmless:
```
Missing dependency No module named 'apscheduler'. Run `pip install 'litellm[proxy]'`
```
This is only needed for LiteLLM's proxy server feature, not for basic usage.

---

## Dependencies & Environment

### Required
- Python 3.11+
- Ollama installed and running (`ollama serve`)
- Model pulled: `ollama pull qwen2.5:14b`
- Node.js 18+ (for frontend development only)

### Install
```bash
cd lloyd
uv sync  # or: pip install -e ".[dev]"
```

### Run
```bash
# CLI
uv run lloyd idea "Build a REST API..."

# Web GUI
uv run lloyd-server
# or: uv run python -m lloyd.api
# Then open http://localhost:8000
```

### Test
```bash
uv run pytest
```

---

## Open Questions

1. **Should stories be auto-generated or user-editable?**
   Currently auto-generated. Might want manual refinement option.

2. **How to handle long-running tasks?**
   No timeout currently. Should add max execution time per story.

3. **Multi-project support?**
   Currently one `.lloyd/` per directory. No global project registry.

4. **Git integration depth?**
   `git_memory.py` exists but isn't well integrated. Should it auto-commit after each story?

5. **Error recovery strategy?**
   If a story fails 3+ times, it's marked "blocked" but there's no manual intervention flow.

---

## Quick Commands Reference

```bash
# Initialize Lloyd in a directory
uv run lloyd init

# Submit an idea
uv run lloyd idea "Your product idea here"

# Check status
uv run lloyd status

# Resume paused execution
uv run lloyd resume

# Reset a stuck story
uv run lloyd reset-story <story-id>

# Start web GUI
uv run python -m lloyd.api
```

---

*Last updated: 2026-01-22*
*Project renamed from AEGIS to Lloyd in Phase 3*
