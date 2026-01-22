"""FastAPI server for Lloyd GUI."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from lloyd import __version__
from lloyd.inbox.store import InboxStore
from lloyd.inbox.models import InboxItem
from lloyd.brainstorm.session import BrainstormSession, BrainstormStore
from lloyd.knowledge.store import KnowledgeStore

# Frontend path
FRONTEND_DIR = Path(__file__).parent / "frontend" / "dist"

app = FastAPI(
    title="Lloyd API",
    description="AI Executive Assistant API",
    version=__version__,
)

# CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static assets if frontend exists
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")


# WebSocket connections for real-time updates
class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


# Pydantic models
class IdeaRequest(BaseModel):
    description: str
    max_iterations: int = 50
    max_parallel: int = 3
    sequential: bool = False
    dry_run: bool = False


class StoryReset(BaseModel):
    story_id: str


class StatusResponse(BaseModel):
    project_name: str
    description: str
    status: str
    total_stories: int
    completed_stories: int
    in_progress_stories: int = 0
    stories: list[dict[str, Any]]


class ProgressResponse(BaseModel):
    content: str
    lines: list[str]


# API Routes
@app.get("/api/status")
async def get_status() -> StatusResponse:
    """Get current project status."""
    prd_path = Path(".lloyd/prd.json")
    if not prd_path.exists():
        return StatusResponse(
            project_name="No Project",
            description="No PRD found. Submit an idea to get started.",
            status="idle",
            total_stories=0,
            completed_stories=0,
            stories=[],
        )

    with open(prd_path) as f:
        prd = json.load(f)

    stories = prd.get("stories", [])
    completed = sum(1 for s in stories if s.get("passes", False))
    in_progress = sum(1 for s in stories if s.get("status") == "in_progress")

    return StatusResponse(
        project_name=prd.get("projectName", "Unknown"),
        description=prd.get("description", ""),
        status=prd.get("status", "idle"),
        total_stories=len(stories),
        completed_stories=completed,
        in_progress_stories=in_progress,
        stories=sorted(stories, key=lambda s: s.get("priority", 999)),
    )


@app.get("/api/progress")
async def get_progress() -> ProgressResponse:
    """Get progress log."""
    progress_path = Path(".lloyd/progress.txt")
    if not progress_path.exists():
        return ProgressResponse(content="", lines=[])

    content = progress_path.read_text()
    return ProgressResponse(content=content, lines=content.strip().split("\n"))


@app.post("/api/idea")
async def submit_idea(request: IdeaRequest) -> dict[str, Any]:
    """Submit a new product idea."""
    from lloyd.orchestrator.flow import LloydFlow

    parallel = not request.sequential
    flow = LloydFlow(max_parallel=request.max_parallel)
    flow.state.parallel_mode = parallel
    flow.receive_idea(request.description)

    # Broadcast status update
    await manager.broadcast({"type": "status", "message": f"Received idea: {request.description}"})

    if request.dry_run:
        # Just create the PRD
        prd = flow.decompose_idea()
        await manager.broadcast({"type": "prd_created", "stories": len(prd.stories)})
        return {
            "success": True,
            "message": "PRD created (dry run)",
            "stories": len(prd.stories),
        }

    # Start execution in background
    asyncio.create_task(run_workflow_async(flow, request.max_iterations, parallel))

    return {
        "success": True,
        "message": "Execution started",
        "max_iterations": request.max_iterations,
        "max_parallel": request.max_parallel,
        "parallel": parallel,
    }


async def run_workflow_async(flow: Any, max_iterations: int, parallel: bool = True) -> None:
    """Run workflow asynchronously with status updates."""
    flow.state.max_iterations = max_iterations

    try:
        # Planning phase
        await manager.broadcast({"type": "phase", "phase": "planning"})
        flow.decompose_idea()
        await manager.broadcast({"type": "prd_created", "stories": len(flow.prd.stories) if flow.prd else 0})

        # Execution loop
        while flow.state.can_continue():
            await manager.broadcast({
                "type": "iteration",
                "iteration": flow.state.iteration + 1,
                "status": flow.state.status,
                "parallel": parallel,
            })

            if parallel:
                should_continue = flow.run_parallel_iteration()
            else:
                should_continue = flow.run_iteration()

            # Send updated status
            prd_path = Path(".lloyd/prd.json")
            if prd_path.exists():
                with open(prd_path) as f:
                    prd = json.load(f)
                in_progress = sum(1 for s in prd.get("stories", []) if s.get("status") == "in_progress")
                await manager.broadcast({
                    "type": "status_update",
                    "stories": prd.get("stories", []),
                    "iteration": flow.state.iteration,
                    "in_progress": in_progress,
                })

            if not should_continue:
                break

            # Small delay to prevent overwhelming
            await asyncio.sleep(0.1)

        # Final status
        await manager.broadcast({
            "type": "complete",
            "status": flow.state.status,
            "iterations": flow.state.iteration,
        })

    except Exception as e:
        await manager.broadcast({
            "type": "error",
            "message": str(e),
        })


@app.post("/api/init")
async def initialize_project() -> dict[str, str]:
    """Initialize a new Lloyd project."""
    lloyd_dir = Path(".lloyd")
    lloyd_dir.mkdir(exist_ok=True)
    (lloyd_dir / "checkpoints").mkdir(exist_ok=True)
    (lloyd_dir / "logs").mkdir(exist_ok=True)

    prd_path = lloyd_dir / "prd.json"
    if not prd_path.exists():
        prd = {
            "projectName": "New Project",
            "description": "",
            "branchName": "main",
            "createdAt": datetime.now(UTC).isoformat(),
            "updatedAt": datetime.now(UTC).isoformat(),
            "status": "idle",
            "stories": [],
            "metadata": {
                "totalStories": 0,
                "completedStories": 0,
                "currentStory": None,
                "estimatedIterations": 0,
                "actualIterations": 0,
            },
        }
        with open(prd_path, "w") as f:
            json.dump(prd, f, indent=2)

    progress_path = lloyd_dir / "progress.txt"
    if not progress_path.exists():
        progress_path.write_text("# Lloyd Progress Log\n\n")

    return {"message": "Lloyd initialized successfully"}


@app.post("/api/reset-story")
async def reset_story(request: StoryReset) -> dict[str, str]:
    """Reset a story's attempt count and status."""
    prd_path = Path(".lloyd/prd.json")
    if not prd_path.exists():
        raise HTTPException(status_code=404, detail="No PRD found")

    with open(prd_path) as f:
        prd = json.load(f)

    for story in prd.get("stories", []):
        if story.get("id") == request.story_id:
            story["passes"] = False
            story["attempts"] = 0
            story["notes"] = ""
            with open(prd_path, "w") as f:
                json.dump(prd, f, indent=2)
            return {"message": f"Reset story: {request.story_id}"}

    raise HTTPException(status_code=404, detail=f"Story not found: {request.story_id}")


class ResumeRequest(BaseModel):
    max_iterations: int = 50
    max_parallel: int = 3
    sequential: bool = False


@app.post("/api/resume")
async def resume_execution(request: ResumeRequest | None = None) -> dict[str, Any]:
    """Resume execution from the last checkpoint."""
    prd_path = Path(".lloyd/prd.json")
    if not prd_path.exists():
        raise HTTPException(status_code=404, detail="No PRD found")

    # Handle optional request body for backwards compatibility
    max_iterations = request.max_iterations if request else 50
    max_parallel = request.max_parallel if request else 3
    parallel = not request.sequential if request else True

    from lloyd.orchestrator.flow import LloydFlow

    flow = LloydFlow(max_parallel=max_parallel)
    flow.state.parallel_mode = parallel
    prd = flow.prd
    if not prd:
        raise HTTPException(status_code=500, detail="Failed to load PRD")

    flow.state.idea = prd.description or "Resumed project"
    flow.state.status = "executing"

    # Start execution in background
    asyncio.create_task(run_workflow_async(flow, max_iterations, parallel))

    return {
        "success": True,
        "message": "Execution resumed",
        "parallel": parallel,
        "max_parallel": max_parallel,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ============== Inbox API ==============

@app.get("/api/inbox")
async def get_inbox(show_resolved: bool = False) -> list[dict[str, Any]]:
    """Get inbox items."""
    store = InboxStore()
    if show_resolved:
        items = store.list_all()
    else:
        items = store.list_unresolved()
    return [item.to_dict() for item in items]


@app.get("/api/inbox/{item_id}")
async def get_inbox_item(item_id: str) -> dict[str, Any]:
    """Get a specific inbox item."""
    store = InboxStore()
    item = store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Inbox item not found: {item_id}")
    return item.to_dict()


class ResolveRequest(BaseModel):
    action: str


@app.post("/api/inbox/{item_id}/resolve")
async def resolve_inbox_item(item_id: str, request: ResolveRequest) -> dict[str, str]:
    """Resolve an inbox item."""
    store = InboxStore()
    item = store.resolve(item_id, request.action)
    if not item:
        raise HTTPException(status_code=404, detail=f"Inbox item not found: {item_id}")
    return {"message": f"Resolved item {item_id} with action: {request.action}"}


@app.delete("/api/inbox/{item_id}")
async def delete_inbox_item(item_id: str) -> dict[str, str]:
    """Delete an inbox item."""
    store = InboxStore()
    if not store.delete(item_id):
        raise HTTPException(status_code=404, detail=f"Inbox item not found: {item_id}")
    return {"message": f"Deleted inbox item: {item_id}"}


# ============== Brainstorm API ==============

@app.get("/api/brainstorm")
async def get_brainstorm_sessions() -> list[dict[str, Any]]:
    """Get all brainstorm sessions."""
    store = BrainstormStore()
    sessions = store.list_all()
    return [s.to_dict() for s in sessions]


@app.get("/api/brainstorm/{session_id}")
async def get_brainstorm_session(session_id: str) -> dict[str, Any]:
    """Get a specific brainstorm session."""
    store = BrainstormStore()
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return session.to_dict()


class BrainstormRequest(BaseModel):
    idea: str


@app.post("/api/brainstorm")
async def create_brainstorm_session(request: BrainstormRequest) -> dict[str, Any]:
    """Create a new brainstorm session."""
    store = BrainstormStore()
    session = BrainstormSession(initial_idea=request.idea)
    store.save(session)
    return session.to_dict()


class ClarificationRequest(BaseModel):
    question: str
    answer: str


@app.post("/api/brainstorm/{session_id}/clarify")
async def add_clarification(session_id: str, request: ClarificationRequest) -> dict[str, Any]:
    """Add a clarification to a brainstorm session."""
    store = BrainstormStore()
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    session.add_clarification(request.question, request.answer)
    store.save(session)
    return session.to_dict()


@app.post("/api/brainstorm/{session_id}/approve")
async def approve_brainstorm_session(session_id: str) -> dict[str, str]:
    """Approve a brainstorm session spec."""
    store = BrainstormStore()
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    session.approve()
    store.save(session)
    return {"message": f"Approved session: {session_id}"}


@app.delete("/api/brainstorm/{session_id}")
async def delete_brainstorm_session(session_id: str) -> dict[str, str]:
    """Delete a brainstorm session."""
    store = BrainstormStore()
    if not store.delete(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return {"message": f"Deleted session: {session_id}"}


# ============== Knowledge API ==============

@app.get("/api/knowledge")
async def get_knowledge(category: str | None = None, min_confidence: float = 0.0) -> list[dict[str, Any]]:
    """Get knowledge entries."""
    store = KnowledgeStore()
    entries = store.query(category=category, min_confidence=min_confidence)
    return [e.to_dict() for e in entries]


@app.get("/api/knowledge/{entry_id}")
async def get_knowledge_entry(entry_id: str) -> dict[str, Any]:
    """Get a specific knowledge entry."""
    store = KnowledgeStore()
    entry = store.get(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Entry not found: {entry_id}")
    return entry.to_dict()


@app.delete("/api/knowledge/{entry_id}")
async def delete_knowledge_entry(entry_id: str) -> dict[str, str]:
    """Delete a knowledge entry."""
    store = KnowledgeStore()
    if not store.delete(entry_id):
        raise HTTPException(status_code=404, detail=f"Entry not found: {entry_id}")
    return {"message": f"Deleted entry: {entry_id}"}


# Serve frontend for all non-API routes (SPA catch-all)
@app.get("/")
async def serve_frontend_root() -> FileResponse:
    """Serve the frontend index.html."""
    if FRONTEND_DIR.exists():
        return FileResponse(FRONTEND_DIR / "index.html")
    return FileResponse(status_code=404)


@app.get("/{path:path}")
async def serve_frontend(path: str) -> FileResponse:
    """Serve frontend assets or index.html for SPA routing."""
    if path.startswith("api/") or path == "ws":
        raise HTTPException(status_code=404, detail="Not found")

    # Check if it's a static file
    file_path = FRONTEND_DIR / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)

    # Return index.html for SPA routing
    if FRONTEND_DIR.exists():
        return FileResponse(FRONTEND_DIR / "index.html")

    raise HTTPException(status_code=404, detail="Frontend not found")


def start_server() -> None:
    """Start the Lloyd API server."""
    print(f"Starting Lloyd Server v{__version__}")
    print("API: http://localhost:8000/api")
    print("GUI: http://localhost:8000")

    if not FRONTEND_DIR.exists():
        print("Warning: Frontend not built. Run 'npm run build' in src/lloyd/frontend/")

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    start_server()
