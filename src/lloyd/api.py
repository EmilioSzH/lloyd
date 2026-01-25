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
from lloyd.brainstorm.session import BrainstormSession, BrainstormStore
from lloyd.extensions.manager import ExtensionManager
from lloyd.extensions.scaffold import create_extension_scaffold
from lloyd.inbox.store import InboxStore
from lloyd.knowledge.store import KnowledgeStore
from lloyd.selfmod.queue import SelfModQueue

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
    queue_only: bool = False  # Add to queue without running


class QueueIdeaRequest(BaseModel):
    description: str
    priority: int = 1


class BatchIdeaRequest(BaseModel):
    ideas: list[str]
    priority: int = 1


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
    try:
        # Validate description
        if not request.description or not request.description.strip():
            raise HTTPException(status_code=400, detail="Description cannot be empty")

        # If queue_only, just add to queue
        if request.queue_only:
            from lloyd.orchestrator.idea_queue import IdeaQueue

            q = IdeaQueue()
            idea = q.add(request.description)

            await manager.broadcast({
                "type": "queue_updated",
                "action": "added",
                "idea_id": idea.id,
            })

            return {
                "success": True,
                "message": f"Added to queue: {idea.id}",
                "idea_id": idea.id,
                "queued": True,
            }

        from lloyd.orchestrator.flow import LloydFlow

        parallel = not request.sequential
        flow = LloydFlow(max_parallel=request.max_parallel)
        flow.state.parallel_mode = parallel
        flow.receive_idea(request.description)

        # Broadcast status update
        desc_preview = request.description[:200] + "..." if len(request.description) > 200 else request.description
        await manager.broadcast({"type": "status", "message": f"Received idea: {desc_preview}"})

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

    except HTTPException:
        raise
    except Exception as e:
        # Log the error and return a helpful message
        error_msg = str(e)
        await manager.broadcast({
            "type": "error",
            "message": f"Failed to submit idea: {error_msg}",
        })
        raise HTTPException(status_code=500, detail=f"Failed to submit idea: {error_msg}")


async def run_workflow_async(flow: Any, max_iterations: int, parallel: bool = True) -> None:
    """Run workflow asynchronously with status updates."""
    flow.state.max_iterations = max_iterations

    try:
        # Planning phase
        await manager.broadcast({"type": "phase", "phase": "planning"})
        flow.decompose_idea()
        await manager.broadcast(
            {"type": "prd_created", "stories": len(flow.prd.stories) if flow.prd else 0}
        )

        # Execution loop
        while flow.state.can_continue():
            await manager.broadcast(
                {
                    "type": "iteration",
                    "iteration": flow.state.iteration + 1,
                    "status": flow.state.status,
                    "parallel": parallel,
                }
            )

            if parallel:
                should_continue = flow.run_parallel_iteration()
            else:
                should_continue = flow.run_iteration()

            # Send updated status
            prd_path = Path(".lloyd/prd.json")
            if prd_path.exists():
                with open(prd_path) as f:
                    prd = json.load(f)
                in_progress = sum(
                    1 for s in prd.get("stories", []) if s.get("status") == "in_progress"
                )
                await manager.broadcast(
                    {
                        "type": "status_update",
                        "stories": prd.get("stories", []),
                        "iteration": flow.state.iteration,
                        "in_progress": in_progress,
                    }
                )

            if not should_continue:
                break

            # Small delay to prevent overwhelming
            await asyncio.sleep(0.1)

        # Final status
        await manager.broadcast(
            {
                "type": "complete",
                "status": flow.state.status,
                "iterations": flow.state.iteration,
            }
        )

    except Exception as e:
        await manager.broadcast(
            {
                "type": "error",
                "message": str(e),
            }
        )


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
async def get_knowledge(
    category: str | None = None, min_confidence: float = 0.0
) -> list[dict[str, Any]]:
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


# ============== Self-Modification API ==============


@app.get("/api/selfmod/queue")
async def get_selfmod_queue() -> list[dict[str, Any]]:
    """Get all self-modification tasks."""
    queue = SelfModQueue()
    return [
        {
            "task_id": t.task_id,
            "description": t.description,
            "risk_level": t.risk_level,
            "status": t.status,
            "clone_path": t.clone_path,
            "created_at": t.created_at,
            "test_results": t.test_results,
            "error_message": t.error_message,
        }
        for t in queue.list_all()
    ]


@app.get("/api/selfmod/{task_id}")
async def get_selfmod_task(task_id: str) -> dict[str, Any]:
    """Get a specific self-modification task."""
    queue = SelfModQueue()
    task = queue.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return {
        "task_id": task.task_id,
        "description": task.description,
        "risk_level": task.risk_level,
        "status": task.status,
        "clone_path": task.clone_path,
        "created_at": task.created_at,
        "test_results": task.test_results,
        "error_message": task.error_message,
    }


@app.post("/api/selfmod/{task_id}/approve")
async def approve_selfmod_task(task_id: str) -> dict[str, str]:
    """Approve and merge a self-modification task."""
    from lloyd.selfmod.clone_manager import LloydCloneManager

    queue = SelfModQueue()
    task = queue.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    if task.status not in ("awaiting_approval", "awaiting_gpu"):
        raise HTTPException(status_code=400, detail=f"Task not awaiting approval: {task.status}")

    # Merge the changes
    clone_mgr = LloydCloneManager()
    if clone_mgr.merge_clone(task_id):
        task.status = "merged"
        queue.update(task)
        clone_mgr.cleanup_clone(task_id)
        return {"message": f"Approved and merged task: {task_id}"}
    else:
        task.status = "failed"
        task.error_message = "Merge failed"
        queue.update(task)
        raise HTTPException(status_code=500, detail="Merge failed")


@app.post("/api/selfmod/{task_id}/reject")
async def reject_selfmod_task(task_id: str) -> dict[str, str]:
    """Reject a self-modification task."""
    from lloyd.selfmod.clone_manager import LloydCloneManager

    queue = SelfModQueue()
    task = queue.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    task.status = "rejected"
    queue.update(task)

    # Clean up the clone
    clone_mgr = LloydCloneManager()
    clone_mgr.cleanup_clone(task_id)

    return {"message": f"Rejected task: {task_id}"}


# ============== Extensions API ==============


@app.get("/api/extensions")
async def get_extensions() -> list[dict[str, Any]]:
    """Get all extensions."""
    manager = ExtensionManager()
    extensions = manager.discover()
    return [
        {
            "name": ext.name,
            "display_name": ext.display_name,
            "version": ext.version,
            "description": ext.description,
            "path": str(ext.path),
            "enabled": ext.enabled,
            "error": ext.error,
            "has_tool": ext.tool_instance is not None,
        }
        for ext in extensions
    ]


class CreateExtensionRequest(BaseModel):
    name: str
    description: str = ""


@app.post("/api/extensions")
async def create_extension(request: CreateExtensionRequest) -> dict[str, Any]:
    """Create a new extension scaffold."""
    try:
        ext_path = create_extension_scaffold(request.name, request.description or None)
        return {
            "success": True,
            "name": request.name,
            "path": str(ext_path),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/extensions/{name}/enable")
async def enable_extension(name: str) -> dict[str, str]:
    """Enable an extension."""
    manager = ExtensionManager()
    if manager.enable_extension(name):
        return {"message": f"Enabled extension: {name}"}
    raise HTTPException(status_code=404, detail=f"Extension not found: {name}")


@app.post("/api/extensions/{name}/disable")
async def disable_extension(name: str) -> dict[str, str]:
    """Disable an extension."""
    manager = ExtensionManager()
    if manager.disable_extension(name):
        return {"message": f"Disabled extension: {name}"}
    raise HTTPException(status_code=404, detail=f"Extension not found: {name}")


@app.delete("/api/extensions/{name}")
async def delete_extension(name: str) -> dict[str, str]:
    """Remove an extension."""
    import shutil

    ext_path = Path(".lloyd") / "extensions" / name
    if not ext_path.exists():
        raise HTTPException(status_code=404, detail=f"Extension not found: {name}")
    shutil.rmtree(ext_path)
    return {"message": f"Removed extension: {name}"}


# ============== Idea Queue API ==============


@app.get("/api/queue")
async def get_idea_queue(show_all: bool = False) -> list[dict[str, Any]]:
    """Get ideas in the queue."""
    from lloyd.orchestrator.idea_queue import IdeaQueue

    q = IdeaQueue()
    ideas = q.list_all() if show_all else q.list_pending()
    return [idea.to_dict() for idea in ideas]


@app.get("/api/queue/stats")
async def get_queue_stats() -> dict[str, int]:
    """Get queue statistics."""
    from lloyd.orchestrator.idea_queue import IdeaQueue

    q = IdeaQueue()
    return q.count()


@app.get("/api/queue/{idea_id}")
async def get_queue_idea(idea_id: str) -> dict[str, Any]:
    """Get a specific queued idea."""
    from lloyd.orchestrator.idea_queue import IdeaQueue

    q = IdeaQueue()
    idea = q.get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail=f"Idea not found: {idea_id}")
    return idea.to_dict()


@app.post("/api/queue")
async def add_to_queue(request: QueueIdeaRequest) -> dict[str, Any]:
    """Add an idea to the queue."""
    from lloyd.orchestrator.idea_queue import IdeaQueue

    q = IdeaQueue()
    idea = q.add(request.description, priority=request.priority)

    await manager.broadcast({
        "type": "queue_updated",
        "action": "added",
        "idea_id": idea.id,
    })

    return {
        "success": True,
        "idea_id": idea.id,
        "message": f"Added to queue: {idea.id}",
    }


@app.post("/api/queue/batch")
async def add_batch_to_queue(request: BatchIdeaRequest) -> dict[str, Any]:
    """Add multiple ideas to the queue."""
    from lloyd.orchestrator.idea_queue import IdeaQueue

    if not request.ideas:
        raise HTTPException(status_code=400, detail="No ideas provided")

    q = IdeaQueue()
    ideas = q.add_many(request.ideas, priority=request.priority)

    await manager.broadcast({
        "type": "queue_updated",
        "action": "batch_added",
        "count": len(ideas),
    })

    return {
        "success": True,
        "count": len(ideas),
        "idea_ids": [idea.id for idea in ideas],
        "message": f"Added {len(ideas)} ideas to queue",
    }


@app.delete("/api/queue/{idea_id}")
async def remove_from_queue(idea_id: str) -> dict[str, str]:
    """Remove an idea from the queue."""
    from lloyd.orchestrator.idea_queue import IdeaQueue

    q = IdeaQueue()
    if not q.remove(idea_id):
        raise HTTPException(status_code=404, detail=f"Idea not found: {idea_id}")

    await manager.broadcast({
        "type": "queue_updated",
        "action": "removed",
        "idea_id": idea_id,
    })

    return {"message": f"Removed from queue: {idea_id}"}


@app.post("/api/queue/clear")
async def clear_queue(completed_only: bool = True) -> dict[str, Any]:
    """Clear completed ideas from the queue."""
    from lloyd.orchestrator.idea_queue import IdeaQueue

    q = IdeaQueue()
    removed = q.clear_completed()

    await manager.broadcast({
        "type": "queue_updated",
        "action": "cleared",
        "count": removed,
    })

    return {
        "success": True,
        "removed": removed,
        "message": f"Cleared {removed} completed ideas",
    }


@app.post("/api/queue/run")
async def run_queue(
    max_iterations: int = 50,
    max_parallel: int = 3,
    sequential: bool = False,
    limit: int = 0,
) -> dict[str, Any]:
    """Start processing the idea queue."""
    from lloyd.orchestrator.idea_queue import IdeaQueue

    q = IdeaQueue()
    pending = q.list_pending()

    if not pending:
        return {
            "success": False,
            "message": "No pending ideas in queue",
        }

    if limit > 0:
        pending = pending[:limit]

    # Start processing in background
    asyncio.create_task(
        run_queue_async(
            pending,
            max_iterations=max_iterations,
            max_parallel=max_parallel,
            sequential=sequential,
        )
    )

    return {
        "success": True,
        "message": f"Started processing {len(pending)} ideas",
        "count": len(pending),
    }


async def run_queue_async(
    ideas: list[Any],
    max_iterations: int,
    max_parallel: int,
    sequential: bool,
) -> None:
    """Process queued ideas asynchronously."""
    from lloyd.orchestrator.flow import run_lloyd
    from lloyd.orchestrator.idea_queue import IdeaQueue

    q = IdeaQueue()
    parallel = not sequential

    for i, idea in enumerate(ideas, 1):
        await manager.broadcast({
            "type": "queue_progress",
            "current": i,
            "total": len(ideas),
            "idea_id": idea.id,
            "status": "starting",
        })

        # Mark as in progress
        q.start(idea.id)

        try:
            # Run in executor to not block event loop
            import asyncio

            loop = asyncio.get_event_loop()
            state = await loop.run_in_executor(
                None,
                lambda: run_lloyd(
                    idea.description,
                    max_iterations=max_iterations,
                    max_parallel=max_parallel,
                    parallel=parallel,
                ),
            )

            success = state.status == "complete"
            q.complete(
                idea.id,
                success=success,
                iterations=state.iteration,
                prd_path=".lloyd/prd.json" if success else None,
                error=None if success else f"Status: {state.status}",
            )

            await manager.broadcast({
                "type": "queue_progress",
                "current": i,
                "total": len(ideas),
                "idea_id": idea.id,
                "status": "completed" if success else "failed",
            })

        except Exception as e:
            q.complete(idea.id, success=False, error=str(e))
            await manager.broadcast({
                "type": "queue_progress",
                "current": i,
                "total": len(ideas),
                "idea_id": idea.id,
                "status": "error",
                "error": str(e),
            })

    # Final summary
    await manager.broadcast({
        "type": "queue_complete",
        "stats": q.count(),
    })


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
