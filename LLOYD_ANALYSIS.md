# Lloyd Codebase Analysis

## 1. CLI Structure

### Current State: BROKEN

The CLI file (`src/lloyd/main.py`) has been **overwritten** with a placeholder:

```python
# Lloyd was here
import click
@click.command()
def cli():
    print("Hello, World!")
```

### Expected State (from git history)

The original CLI was a proper Click group with these commands:
- `lloyd idea "..."` - Submit a new product idea
- `lloyd status` - Check current task queue
- `lloyd resume` - Resume from last checkpoint
- `lloyd init` - Initialize Lloyd in current directory
- `lloyd run` - Run the full workflow
- `lloyd reset-story <id>` - Reset a story's attempt count

### Why `lloyd --help` Shows No Commands

The current `main.py` uses `@click.command()` (singular) instead of `@click.group()`. This creates a single command with no subcommands, which is why help shows nothing useful.

### Entry Points (pyproject.toml)

```toml
[project.scripts]
lloyd = "lloyd.main:cli"           # CLI entry point
lloyd-server = "lloyd.api:start_server"  # FastAPI server
```

---

## 2. How to Run Lloyd

### Currently: NOT FUNCTIONAL

The CLI is broken due to `main.py` being overwritten.

### To Fix

Restore `main.py` from git:
```bash
git checkout HEAD -- src/lloyd/main.py
```

### After Fixing, the Command Would Be

```bash
# Initialize Lloyd in a project directory
lloyd init

# Submit an idea (parallel mode, default)
lloyd idea "Build a REST API for user management" --max-parallel 3

# Submit an idea (sequential mode)
lloyd idea "Build a REST API" --sequential

# Dry run (planning only, no execution)
lloyd idea "Build something" --dry-run

# Check status
lloyd status

# Resume execution
lloyd resume
```

### Alternative: Use Python Directly

```python
from lloyd.orchestrator.flow import run_lloyd

state = run_lloyd(
    idea="Build a REST API for user management",
    max_iterations=50,
    max_parallel=3,
    parallel=True
)
```

---

## 3. Current Architecture

### Idea Flow

```
1. IDEA INPUT
   └── lloyd idea "..." or LloydFlow.receive_idea()

2. PLANNING PHASE
   └── PlanningCrew.kickoff()
       ├── Analyst Agent: Analyze requirements
       ├── Researcher Agent: Research solutions
       └── Architect Agent: Design architecture
   └── Creates PRD (prd.json) with stories

3. EXECUTION LOOP (per story)
   ├── Select next story (respects dependencies)
   ├── ExecutionCrew.kickoff()
   │   └── Coder Agent: Implement the story
   └── QualityCrew.kickoff()
       ├── Tester Agent: Run tests
       ├── Reviewer Agent: Review code
       └── Verify acceptance criteria

4. COMPLETION
   └── All stories pass OR blocked OR max iterations
```

### Key Files

| File | Purpose |
|------|---------|
| `orchestrator/flow.py` | Main orchestration - `LloydFlow` class |
| `orchestrator/state.py` | Global state management |
| `orchestrator/router.py` | Task routing logic |
| `orchestrator/parallel_executor.py` | Parallel execution with ThreadPoolExecutor |
| `orchestrator/thread_safe_state.py` | Thread-safe PRD operations |
| `memory/prd_manager.py` | PRD/story management |
| `memory/progress.py` | Progress tracking |

### Crews

| Crew | Agents | Purpose |
|------|--------|---------|
| **PlanningCrew** | Analyst, Researcher, Architect | Decompose idea → PRD |
| **ExecutionCrew** | Coder | Implement stories |
| **QualityCrew** | Tester, Reviewer | Verify acceptance criteria |

### Agent Configurations

Located in `src/lloyd/crews/*/agents.yaml`:

- **Analyst**: Requirements analysis, edge cases
- **Architect**: System design, YAGNI principles
- **Researcher**: Technical research, best practices
- **Coder**: Implementation (in execution crew)
- **Tester**: Test execution (in quality crew)
- **Reviewer**: Code review (in quality crew)

### LLM Configuration

Default: `ollama/qwen2.5:14b` (local Ollama)

Override via environment:
```bash
export LLOYD_LLM="anthropic/claude-3-5-sonnet"
```

---

## 4. File Structure

```
src/lloyd/
├── __init__.py              # Version: 0.1.0
├── main.py                  # CLI entry point [BROKEN]
├── api.py                   # FastAPI server
├── config.py                # Settings, LLM config
│
├── orchestrator/
│   ├── flow.py              # Main LloydFlow class
│   ├── state.py             # LloydState model
│   ├── router.py            # Task routing logic
│   ├── parallel_executor.py # ThreadPoolExecutor wrapper
│   └── thread_safe_state.py # FileLock-based state manager
│
├── memory/
│   ├── prd_manager.py       # PRD, Story, StoryStatus models
│   ├── progress.py          # Progress tracking
│   └── git_memory.py        # Git integration
│
├── crews/
│   ├── planning/
│   │   ├── crew.py          # PlanningCrew class
│   │   ├── agents.yaml      # Analyst, Architect, Researcher
│   │   └── tasks.yaml       # analyze_idea, research, design
│   ├── execution/
│   │   ├── crew.py          # ExecutionCrew class
│   │   ├── agents.yaml      # Coder
│   │   └── tasks.yaml       # implement_story
│   └── quality/
│       ├── crew.py          # QualityCrew class
│       ├── agents.yaml      # Tester, Reviewer
│       └── tasks.yaml       # run_tests, review, verify
│
├── agents/                  # Agent base classes (unused?)
│   ├── analyst.py
│   ├── architect.py
│   ├── coder.py
│   └── ...
│
└── tools/
    ├── __init__.py          # Tool registry
    ├── filesystem.py        # read/write/list files
    ├── shell.py             # shell, pytest, ruff
    ├── code_exec.py         # E2B sandbox execution
    ├── github.py            # GitHub API tools
    └── web_search.py        # Web search tools
```

---

## 5. Assessment

### Is Lloyd Functional Right Now?

**NO** - The CLI is broken.

### Blockers

1. **`main.py` overwritten** - Critical, CLI doesn't work
2. **No Ollama running** - Default LLM is `ollama/qwen2.5:14b`
3. **Missing API keys** - For E2B, Composio, GitHub (optional but limits functionality)

### To Make Lloyd Functional

```bash
# 1. Restore main.py
cd C:\Users\dawha\AIExperiments\LLoyd\lloyd
git checkout HEAD -- src/lloyd/main.py

# 2. Reinstall package
uv pip install -e .

# 3. Start Ollama (if using local LLM)
ollama serve
ollama pull qwen2.5:14b

# 4. OR use Anthropic
export LLOYD_LLM="anthropic/claude-3-5-sonnet"
export ANTHROPIC_API_KEY="your-key"

# 5. Test CLI
lloyd --help
lloyd init
lloyd idea "Build a calculator" --dry-run
```

### Running LLOYD_SESSION_1_FOUNDATION.md Through It

After fixing the CLI:

```bash
# Initialize
lloyd init

# Submit the foundation task
lloyd idea "Implement the foundation layer for Lloyd including project setup, file templates, and base classes" --max-parallel 3
```

However, the planning crew will need to properly parse the idea into stories. The current `decompose_idea()` method is **simplified** - it just creates a single "Initial Implementation" story rather than properly parsing the planning output.

### Recommended Fixes (Priority Order)

1. **Restore main.py** - `git checkout HEAD -- src/lloyd/main.py`
2. **Test with dry-run** - `lloyd idea "test" --dry-run`
3. **Improve decompose_idea()** - Parse planning crew output into multiple stories
4. **Add proper story parsing** - The planning crew returns text, needs structured extraction

---

## Quick Commands Reference

```bash
# Restore CLI
git checkout HEAD -- src/lloyd/main.py

# Check status
lloyd status

# Run with local Ollama
LLOYD_LLM="ollama/qwen2.5:14b" lloyd idea "Build X"

# Run with Claude
LLOYD_LLM="anthropic/claude-3-5-sonnet" ANTHROPIC_API_KEY="sk-..." lloyd idea "Build X"

# Parallel execution (default)
lloyd idea "Build X" --max-parallel 5

# Sequential execution
lloyd idea "Build X" --sequential

# Start API server
lloyd-server
```
