# Ralph to Ralphy Migration Analysis

## Executive Summary

After analyzing Lloyd's codebase and researching Ralphy's capabilities, **I recommend NOT migrating Lloyd to use Ralphy**. Lloyd and Ralphy solve different problems at different layers of abstraction, and attempting to merge them would require dismantling Lloyd's core value proposition.

---

## Current Architecture

### Lloyd's Orchestration Model

Lloyd uses **CrewAI** for multi-agent orchestration with three specialized crews:

```
┌─────────────────────────────────────────────────────────────────┐
│                        LloydFlow                                │
│  (src/lloyd/orchestrator/flow.py)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│   │   Planning   │───▶│  Execution   │───▶│   Quality    │     │
│   │    Crew      │    │    Crew      │    │    Crew      │     │
│   └──────────────┘    └──────────────┘    └──────────────┘     │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│   ┌──────────┐        ┌──────────┐        ┌──────────┐         │
│   │ Analyst  │        │  Coder   │        │  Tester  │         │
│   │ Architect│        │          │        │ Reviewer │         │
│   └──────────┘        └──────────┘        └──────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   .lloyd/       │
                    │   prd.json      │
                    │   progress.txt  │
                    └─────────────────┘
```

**Key Components:**
- `LloydFlow.run()` - Main orchestration loop with `while self.state.can_continue()`
- `LloydFlow.run_iteration()` - Single iteration: plan → execute → verify
- `LloydState` - Tracks iteration count, max_iterations, completion status
- YAML-configured agents with specialized roles (Analyst, Architect, Coder, Tester, Reviewer)
- File-based state persistence (.lloyd/prd.json, progress.txt)

### Iteration Control (flow.py:178-238)

```python
def run(self) -> dict[str, Any]:
    """Run the full Lloyd flow."""
    while self.state.can_continue():
        self.run_iteration()
        if self.state.completed:
            break
    return self.state.to_dict()
```

Lloyd already has a complete iteration loop - it's not using the external Ralph plugin at all.

---

## Ralphy's Architecture

Ralphy is a **task orchestration layer** that wraps AI coding tools:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Ralphy                                  │
│  (External bash/npm CLI)                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────────────────────────────────────────────────┐ │
│   │                  Task Orchestrator                        │ │
│   │  - PRD/YAML/GitHub Issue parsing                         │ │
│   │  - Parallel execution with isolated worktrees            │ │
│   │  - Branch management (ralphy/<task-slug>)                │ │
│   │  - Auto-PR creation and merge conflict resolution        │ │
│   └──────────────────────────────────────────────────────────┘ │
│                              │                                  │
│                              ▼                                  │
│   ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐     │
│   │Claude Code│ │ OpenCode  │ │  Cursor   │ │  Codex    │     │
│   └───────────┘ └───────────┘ └───────────┘ └───────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Wraps existing AI coding tools (Claude Code, OpenCode, Cursor, etc.)
- Parallel execution with `--max-parallel N`
- Git worktree isolation per task
- Automatic branch creation and PR management
- Task sources: PRD markdown, YAML, GitHub Issues
- AI-assisted merge conflict resolution

---

## Integration Points

### Where They Overlap

| Aspect | Lloyd | Ralphy |
|--------|-------|--------|
| Task queue | `.lloyd/prd.json` | PRD.md / YAML / GitHub Issues |
| Iteration loop | `LloydFlow.run()` | `ralphy.sh` while loop |
| Progress tracking | `.lloyd/progress.txt` | Git history + task checkboxes |
| Completion signal | `state.completed = True` | `<promise>COMPLETE</promise>` |

### Where They Differ

| Aspect | Lloyd | Ralphy |
|--------|-------|--------|
| Agent orchestration | Built-in (CrewAI) | None (wraps external tools) |
| Parallel execution | Single-threaded | Multi-agent parallel |
| AI engine | Ollama/LiteLLM | Claude Code, OpenCode, Cursor, etc. |
| Branch management | Basic (GitMemory) | Full automation |
| Specialized agents | Yes (7 agent types) | No (generic prompts) |
| Task decomposition | AI-driven (Planning Crew) | Manual PRD authoring |

---

## Feature Gap Analysis

### What Lloyd Has That Ralphy Doesn't

1. **Specialized Agent Roles**
   - Analyst: Decomposes ideas into requirements
   - Architect: Designs system structure
   - Coder: Implements features
   - Tester: Writes and runs tests
   - Reviewer: Code quality checks

2. **AI-Driven Planning**
   - Lloyd's Planning Crew automatically decomposes ideas into stories
   - Ralphy requires pre-written PRD files

3. **Quality Verification Loop**
   - Lloyd runs a Quality Crew that verifies acceptance criteria
   - Ralphy relies on external test commands

4. **LLM Flexibility**
   - Lloyd uses LiteLLM for provider abstraction (Ollama, OpenAI, Anthropic)
   - Ralphy is tied to specific CLI tools

### What Ralphy Has That Lloyd Doesn't

1. **Parallel Execution**
   - Ralphy can run multiple agents simultaneously
   - Lloyd is single-threaded

2. **Git Workflow Automation**
   - Automatic branch creation per task
   - PR creation and auto-merge
   - AI-assisted conflict resolution

3. **Multi-Tool Support**
   - Can use Claude Code, OpenCode, Cursor, Codex, etc.
   - Switch tools mid-project

4. **Browser Automation**
   - UI testing and verification
   - Screenshot capture

---

## Migration Complexity

### Option A: Replace Lloyd with Ralphy

**Effort: HIGH (Complete Rewrite)**

Would require:
- Abandoning CrewAI and all agent configurations
- Rewriting Lloyd as a Ralphy task definition
- Losing specialized agent roles
- Losing AI-driven task decomposition
- Converting `.lloyd/prd.json` format to Ralphy PRD format

**Result:** Lloyd would no longer be Lloyd - it would just be Ralphy with a different name.

### Option B: Use Ralphy to Orchestrate Lloyd

**Effort: MEDIUM (Integration Layer)**

Would require:
- Creating a CLI wrapper that Ralphy can invoke
- Mapping Ralphy task format to Lloyd stories
- Handling state sync between `.lloyd/` and Ralphy's tracking
- Losing Lloyd's internal iteration (Ralphy would control the loop)

**Challenges:**
- Lloyd already has its own iteration loop
- Ralphy expects to run tools like `claude "task description"`
- Lloyd expects to receive an idea and plan/execute/verify autonomously

### Option C: Cherry-Pick Ralphy Features into Lloyd

**Effort: MEDIUM-LOW (Feature Additions)**

Could add:
- Parallel story execution (requires CrewAI parallel process mode)
- Better git workflow (enhance GitMemory)
- Branch-per-story with auto-PR

**Preserves:** All of Lloyd's existing architecture and value

---

## Recommendation

### Do NOT Migrate to Ralphy

**Rationale:**

1. **Different Abstraction Levels**
   - Ralphy: Task orchestrator for AI coding tools
   - Lloyd: AI coding tool with built-in orchestration

   Ralphy is designed to wrap tools like Claude Code. Lloyd IS the equivalent of Claude Code (but with multi-agent capabilities).

2. **Lloyd's Value Proposition Would Be Lost**
   - Specialized agents (Analyst, Architect, Coder, Tester, Reviewer)
   - AI-driven planning and decomposition
   - Quality verification loops

   These are what make Lloyd unique. Migrating to Ralphy would reduce it to a dumb prompt executor.

3. **Redundant Orchestration**
   - Lloyd already has `LloydFlow` for iteration control
   - Adding Ralphy would create two competing orchestration layers

4. **LLM Provider Lock-in**
   - Lloyd uses LiteLLM (works with Ollama, any provider)
   - Ralphy is tied to specific CLI tools that require API keys

### Instead, Consider These Enhancements

If you want Ralphy-like features, add them natively to Lloyd:

1. **Parallel Story Execution**
   ```python
   # In flow.py, use CrewAI's parallel process
   crew = Crew(
       agents=agents,
       tasks=tasks,
       process=Process.parallel  # Instead of sequential
   )
   ```

2. **Branch-Per-Story**
   ```python
   # Enhance GitMemory
   def create_story_branch(self, story_id: str):
       branch_name = f"lloyd/{story_id}"
       subprocess.run(["git", "checkout", "-b", branch_name])
   ```

3. **Auto-PR Creation**
   ```python
   # Add to GitMemory
   def create_pull_request(self, story_id: str, title: str):
       subprocess.run(["gh", "pr", "create", "--title", title, "--body", "..."])
   ```

These changes preserve Lloyd's architecture while adding the most valuable Ralphy features.

---

## If Migrating Anyway

If you still want to proceed with migration, here's what would need to change:

### Required Changes

1. **Create Ralphy-compatible CLI entry point**
   ```bash
   # lloyd/bin/lloyd-task
   # Single-task executor that Ralphy can call
   lloyd execute-story "$1"
   ```

2. **Convert prd.json to Ralphy PRD format**
   ```markdown
   # PRD.md
   - [ ] Story 001: Initial Implementation
   - [ ] Story 002: Add tests
   ```

3. **Modify LloydFlow to be single-iteration**
   - Remove the `while self.state.can_continue()` loop
   - Let Ralphy control iteration externally

4. **Add completion promise output**
   ```python
   if all_stories_complete:
       print("<promise>COMPLETE</promise>")
   ```

5. **Install and configure Ralphy**
   ```bash
   npm install -g ralphy-cli
   ralphy init
   # Configure .ralphy/config.yaml
   ```

6. **Run via Ralphy**
   ```bash
   ralphy --tool lloyd-task PRD.md --max-parallel 1
   ```

### Files to Modify

| File | Change |
|------|--------|
| `src/lloyd/main.py` | Add `execute-story` command |
| `src/lloyd/orchestrator/flow.py` | Remove outer iteration loop |
| `src/lloyd/memory/prd_manager.py` | Add Ralphy format export |
| `pyproject.toml` | Add `lloyd-task` script entry |
| New: `.ralphy/config.yaml` | Ralphy configuration |
| New: `PRD.md` | Ralphy-format task list |

---

## Conclusion

Lloyd and Ralphy are complementary, not competing tools:

- **Ralphy** = "Run any AI coder in a loop on a task list"
- **Lloyd** = "An AI coder with specialized agents and planning capabilities"

The right integration would be using Ralphy to orchestrate multiple Lloyd instances for parallel execution, not replacing Lloyd's internals with Ralphy's simpler task model.

**My recommendation: Keep Lloyd's architecture, cherry-pick useful features (parallel execution, git automation) as native enhancements.**

---

## Sources

- [Ralphy GitHub Repository](https://github.com/michaelshimeles/ralphy)
- [Ralph Wiggum Plugin](https://github.com/anthropics/claude-code/blob/main/plugins/ralph-wiggum/README.md)
- [Ralph Orchestrator](https://github.com/mikeyobrien/ralph-orchestrator)
- [Original Ralph Technique](https://ghuntley.com/ralph/)
- [Ralphy Overview on daily.dev](https://app.daily.dev/posts/ralphy-opencode-claude-code-this-is-ralph-loops-on-steroids--5hyjoecow)

---

*Analysis completed: 2026-01-22*
