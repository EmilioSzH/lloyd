# Lloyd - AI Executive Assistant

## TOP PRIORITY RULES (Override Everything)

1. **NEVER leave a task half-finished** - Complete each task fully before moving to the next
2. **NEVER break existing tests** - Run tests before and after every change
3. **NEVER commit without verification** - All commits must pass linting, type checks, and tests
4. **ALWAYS update progress.txt** - Document learnings after each iteration
5. **ALWAYS check prd.json** - This is your task queue, respect priorities and dependencies

## Project Context

Lloyd is a multi-agent AI system that takes product ideas and autonomously executes them.
Built with CrewAI for agent orchestration, Composio for tool integrations, and E2B for code execution.

### Tech Stack
- Python 3.11+ with uv package manager
- CrewAI for multi-agent orchestration
- Composio for GitHub/API integrations
- E2B for sandboxed code execution
- Rich for terminal UI
- pytest for testing

## Available Commands

```bash
# Development
uv run lloyd                    # Start Lloyd CLI
uv run lloyd idea "..."         # Submit a new product idea
uv run lloyd status             # Check current task queue
uv run lloyd resume             # Resume from last checkpoint

# Testing
uv run pytest                   # Run all tests
uv run pytest -x               # Stop on first failure
uv run pytest --cov            # With coverage

# Quality
uv run ruff check .            # Linting
uv run ruff format .           # Formatting
uv run mypy src/               # Type checking

# Build
uv build                       # Build package
```

## Development Workflow

### For Each Task:
1. Read prd.json to find highest priority task where `passes: false`
2. Understand the task requirements and acceptance criteria
3. Implement the solution incrementally
4. Run tests after each significant change
5. If tests pass, mark task as `passes: true` in prd.json
6. Update progress.txt with learnings
7. Commit with descriptive message
8. Move to next task

### When Stuck:
1. Document what you tried in progress.txt
2. If blocked for 3+ iterations, escalate to human checkpoint
3. Never proceed without understanding why something failed

## Key Files to Know

- `src/lloyd/orchestrator/flow.py` - Main orchestration logic
- `src/lloyd/crews/*/agents.yaml` - Agent definitions (role, goal, backstory)
- `src/lloyd/crews/*/tasks.yaml` - Task definitions
- `src/lloyd/tools/` - All available tools
- `.lloyd/prd.json` - Current task queue (SOURCE OF TRUTH)
- `.lloyd/progress.txt` - Accumulated learnings

## Constraints

### MUST Confirm Before:
- Deleting any file
- Modifying pyproject.toml dependencies
- Changing API keys or environment variables
- Making changes to CLAUDE.md itself
- Any action that affects external systems (GitHub push, API calls with side effects)

### NEVER Do:
- Hardcode API keys or secrets
- Skip tests to save time
- Ignore type errors
- Leave print statements in production code
- Create files outside the project directory
- **Modify Lloyd's own source files** (anything in src/lloyd/) - this causes self-destruction

## Safe Test Commands

When testing Lloyd, use these safe ideas that don't modify Lloyd itself:

```bash
# Safe trivial task test
lloyd idea "Create a file called test_output.txt with the text 'Hello from Lloyd'"

# Safe simple task test
lloyd idea "Create a Python script called hello.py that prints Hello World"
```

**NEVER test with ideas that modify src/lloyd/ files!**

## Agent Behavior Guidelines

### Thinking Modes
- Use "think step by step" for complex architectural decisions
- Use "ultrathink" for debugging mysterious failures
- Default to action-oriented execution for straightforward tasks

### Error Handling
- Log all errors with full stack traces
- Retry transient failures up to 3 times with exponential backoff
- For persistent failures, document and escalate

### Code Style
- Use type hints everywhere
- Docstrings for all public functions
- Keep functions under 50 lines
- Prefer composition over inheritance
- Use dependency injection for testability
