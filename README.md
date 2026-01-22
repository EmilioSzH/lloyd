# Lloyd - AI Executive Assistant

An AI-powered executive assistant that takes high-level product ideas and autonomously executes them to completion.

## Quick Start

### CLI Usage

```bash
# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Install dependencies
pip install -e .

# Initialize Lloyd
lloyd init

# Submit your first idea
lloyd idea "Build a simple todo API with FastAPI"

# Check status
lloyd status
```

### Web GUI Usage

```bash
# Start the Lloyd server
lloyd-server

# Open in browser
# GUI: http://localhost:8000
# API: http://localhost:8000/api
```

The web GUI provides:
- **Dashboard** - Overview of project status and progress
- **New Idea** - Submit product ideas with configurable options
- **Task Queue** - View and manage all tasks with expandable details
- **Progress Log** - View session history and learnings
- **Settings** - Initialize projects and resume execution
- **Real-time updates** - Live WebSocket notifications during execution

## Features

- **Multi-agent orchestration** with CrewAI
- **Tool integrations** via Composio (GitHub, APIs, etc.)
- **Secure code execution** with E2B sandboxes
- **State persistence** via Git and JSON files
- **Beautiful CLI** with Rich
- **Modern Web GUI** with React, Tailwind CSS, and real-time updates

## CLI Commands

```bash
lloyd              # Show welcome message
lloyd init         # Initialize a new Lloyd project
lloyd idea "..."   # Submit a new product idea
lloyd status       # Check current task queue
lloyd resume       # Resume from last checkpoint
lloyd run          # Run the full workflow
lloyd reset-story  # Reset a story's status
lloyd-server       # Start the web GUI server
```

## Development

```bash
# Run tests
pytest

# Linting
ruff check .

# Type checking
mypy src/

# Build frontend (if needed)
cd src/lloyd/frontend && npm install && npm run build
```

## License

MIT
