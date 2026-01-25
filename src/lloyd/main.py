"""CLI entry point for Lloyd."""

import json
import logging
import sys
from pathlib import Path

# Configure logging early
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger(__name__)

# Reduce noise from third-party libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("litellm").setLevel(logging.WARNING)

# Fix Windows console encoding for emoji/unicode characters
from lloyd.utils.windows import configure_console

configure_console()

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lloyd import __version__

# Use force_terminal=True to ensure Rich works properly, and use safe encoding
console = Console(force_terminal=True, safe_box=True)


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="lloyd")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Lloyd - AI Executive Assistant.

    An AI-powered executive assistant that takes high-level product ideas
    and autonomously executes them to completion.
    """
    if ctx.invoked_subcommand is None:
        console.print(
            Panel.fit(
                "[bold blue]Lloyd[/bold blue] initialized\n\n"
                "[dim]AI Executive Assistant[/dim]\n\n"
                f"Version: {__version__}\n\n"
                "Commands:\n"
                "  [green]lloyd idea[/green] \"...\"  - Submit a new product idea\n"
                "  [green]lloyd status[/green]       - Check current task queue\n"
                "  [green]lloyd resume[/green]       - Resume from last checkpoint\n"
                "  [green]lloyd init[/green]         - Initialize Lloyd in current directory\n"
                "  [green]lloyd run[/green]          - Run the full workflow\n"
                "  [green]lloyd metrics[/green]      - Show execution metrics\n",
                title="Welcome to Lloyd",
                border_style="blue",
            )
        )


@cli.command()
@click.argument("description")
@click.option("--max-iterations", "-m", default=50, help="Maximum iterations")
@click.option("--max-parallel", "-p", default=3, help="Maximum parallel workers")
@click.option("--sequential", "-s", is_flag=True, help="Run in sequential mode (disable parallel)")
@click.option("--dry-run", is_flag=True, help="Plan only, don't execute")
@click.option("--branch", "-b", is_flag=True, help="Create a git branch for this task")
@click.option("--auto-pr", is_flag=True, help="Create PR when complete")
@click.option("--draft-pr", is_flag=True, help="Create draft PR when complete")
@click.option("--legacy", is_flag=True, help="Use legacy crew-based execution (not TDD)")
def idea(
    description: str,
    max_iterations: int,
    max_parallel: int,
    sequential: bool,
    dry_run: bool,
    branch: bool,
    auto_pr: bool,
    draft_pr: bool,
    legacy: bool,
) -> None:
    """Submit a new product idea for Lloyd to execute."""
    import uuid

    console.print(f"[bold green]Received idea:[/bold green] {description}")

    task_id = str(uuid.uuid4())[:8]
    branch_name = None

    # Create branch if requested
    if branch:
        from lloyd.memory.git_memory import GitMemory

        git = GitMemory()
        if not git.is_git_repo():
            console.print("[yellow]Not a git repository. Skipping branch creation.[/yellow]")
        else:
            branch_name = git.create_story_branch(task_id)
            if branch_name:
                console.print(f"[cyan]Created branch:[/cyan] {branch_name}")
            else:
                console.print("[yellow]Failed to create branch.[/yellow]")

    if dry_run:
        console.print("[yellow]Dry run mode - planning only.[/yellow]")
        from lloyd.orchestrator.flow import LloydFlow

        flow = LloydFlow()
        flow.receive_idea(description)
        flow.decompose_idea()
        console.print("[green]PRD created. Run 'lloyd status' to see tasks.[/green]")
    else:
        parallel = not sequential
        use_iterative = not legacy
        mode_str = "sequential" if sequential else f"parallel (max {max_parallel} workers)"
        exec_str = "TDD iterative" if use_iterative else "legacy crew"
        console.print(f"[cyan]Starting autonomous execution ({mode_str}, {exec_str}, max {max_iterations} iterations)...[/cyan]")
        from lloyd.orchestrator.flow import run_lloyd

        state = run_lloyd(
            description,
            max_iterations=max_iterations,
            max_parallel=max_parallel,
            parallel=parallel,
            use_iterative_executor=use_iterative,
        )
        console.print(f"\n[bold]Final status:[/bold] {state.status}")
        console.print(f"[bold]Iterations:[/bold] {state.iteration}")

        # Create PR if requested and task completed
        if (auto_pr or draft_pr) and state.status == "complete":
            from lloyd.memory.git_memory import GitMemory

            git = GitMemory()
            if git.is_git_repo():
                # Commit any remaining changes
                if git.has_uncommitted_changes():
                    git.commit_all(f"Lloyd: {description[:50]}")

                pr_url = git.create_pull_request(
                    title=f"Lloyd: {description[:50]}",
                    body=f"Automated PR for task: {description}\n\nTask ID: {task_id}",
                    draft=draft_pr,
                )
                if pr_url:
                    console.print(f"[green]Created PR:[/green] {pr_url}")


@cli.command()
def status() -> None:
    """Check the current task queue status."""
    prd_path = Path(".lloyd/prd.json")
    if not prd_path.exists():
        console.print("[yellow]No PRD found. Submit an idea first.[/yellow]")
        return

    with open(prd_path) as f:
        prd = json.load(f)

    console.print(f"\n[bold]Project:[/bold] {prd.get('projectName', 'Unknown')}")
    console.print(f"[bold]Status:[/bold] {prd.get('status', 'Unknown')}")

    stories = prd.get("stories", [])
    if not stories:
        console.print("[dim]No stories defined yet.[/dim]")
        return

    completed = sum(1 for s in stories if s.get("passes", False))
    in_progress = sum(1 for s in stories if s.get("status") == "in_progress")
    progress_str = f"[bold]Progress:[/bold] {completed}/{len(stories)} tasks complete"
    if in_progress > 0:
        progress_str += f" ({in_progress} running)"
    console.print(progress_str + "\n")

    # Create a table of stories
    table = Table(title="Task Queue")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Priority", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Attempts", justify="center")

    for story in sorted(stories, key=lambda s: s.get("priority", 999)):
        story_status = story.get("status", "pending")
        if story.get("passes"):
            status_str = "[green]PASS[/green]"
        elif story_status == "in_progress":
            status_str = "[blue]RUNNING[/blue]"
        elif story_status == "blocked" or story.get("attempts", 0) >= 3:
            status_str = "[red]BLOCKED[/red]"
        elif story_status == "failed":
            status_str = "[red]FAILED[/red]"
        else:
            status_str = "[yellow]PENDING[/yellow]"
        table.add_row(
            story.get("id", "?"),
            story.get("title", "Untitled")[:40],
            str(story.get("priority", "-")),
            status_str,
            str(story.get("attempts", 0)),
        )

    console.print(table)


@cli.command()
@click.option("--max-iterations", "-m", default=50, help="Maximum iterations")
@click.option("--max-parallel", "-p", default=3, help="Maximum parallel workers")
@click.option("--sequential", "-s", is_flag=True, help="Run in sequential mode (disable parallel)")
def resume(max_iterations: int, max_parallel: int, sequential: bool) -> None:
    """Resume execution from the last checkpoint."""
    prd_path = Path(".lloyd/prd.json")
    if not prd_path.exists():
        console.print("[yellow]No PRD found. Submit an idea first.[/yellow]")
        return

    parallel = not sequential
    mode_str = "sequential" if sequential else f"parallel (max {max_parallel} workers)"
    console.print(f"[cyan]Resuming from last checkpoint ({mode_str})...[/cyan]")

    from lloyd.orchestrator.flow import LloydFlow

    flow = LloydFlow(max_parallel=max_parallel)
    flow.state.max_iterations = max_iterations
    flow.state.parallel_mode = parallel

    # Load existing PRD
    prd = flow.prd
    if not prd:
        console.print("[red]Failed to load PRD.[/red]")
        return

    flow.state.idea = prd.description or "Resumed project"
    flow.state.status = "executing"

    # Run the workflow
    state = flow.run(parallel=parallel)

    console.print(f"\n[bold]Final status:[/bold] {state.status}")
    console.print(f"[bold]Iterations:[/bold] {state.iteration}")


@cli.command()
def init() -> None:
    """Initialize a new Lloyd project in the current directory."""
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
            "createdAt": "",
            "updatedAt": "",
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

    console.print("[bold green]Lloyd initialized successfully![/bold green]")
    console.print(f"Created: {lloyd_dir}/")


@cli.command()
@click.option("--max-iterations", "-m", default=50, help="Maximum iterations")
@click.option("--max-parallel", "-p", default=3, help="Maximum parallel workers")
@click.option("--sequential", "-s", is_flag=True, help="Run in sequential mode (disable parallel)")
def run(max_iterations: int, max_parallel: int, sequential: bool) -> None:
    """Run the Lloyd workflow (requires existing PRD)."""
    prd_path = Path(".lloyd/prd.json")
    if not prd_path.exists():
        console.print("[yellow]No PRD found. Use 'lloyd idea' to create one.[/yellow]")
        return

    from lloyd.orchestrator.flow import LloydFlow

    parallel = not sequential
    flow = LloydFlow(max_parallel=max_parallel)
    flow.state.max_iterations = max_iterations
    flow.state.parallel_mode = parallel

    # Load existing PRD
    prd = flow.prd
    if not prd:
        console.print("[red]Failed to load PRD.[/red]")
        return

    if not prd.stories:
        console.print("[yellow]No stories in PRD. Use 'lloyd idea' to create tasks.[/yellow]")
        return

    flow.state.idea = prd.description or "Running existing project"
    flow.state.status = "executing"

    mode_str = "sequential" if sequential else f"parallel (max {max_parallel} workers)"
    console.print(f"[cyan]Running workflow for: {prd.project_name} ({mode_str})[/cyan]")
    state = flow.run(parallel=parallel)

    console.print(f"\n[bold]Final status:[/bold] {state.status}")


@cli.command()
@click.argument("idea")
@click.option("--continue-session", "-c", help="Continue existing session by ID")
def brainstorm(idea: str, continue_session: str | None) -> None:
    """Start or continue a brainstorming session to refine ideas."""
    from lloyd.brainstorm.session import BrainstormSession, BrainstormStore

    store = BrainstormStore()

    if continue_session:
        session = store.get(continue_session)
        if not session:
            console.print(f"[red]Session {continue_session} not found.[/red]")
            return
        console.print(f"[cyan]Continuing session:[/cyan] {session.session_id}")
    else:
        session = BrainstormSession(initial_idea=idea)
        store.save(session)
        console.print(f"[green]Started brainstorm session:[/green] {session.session_id}")

    console.print(f"\n[bold]Initial idea:[/bold] {session.initial_idea}")

    if session.clarifications:
        console.print("\n[bold]Clarifications so far:[/bold]")
        for i, c in enumerate(session.clarifications, 1):
            console.print(f"  Q{i}: {c['question']}")
            console.print(f"  A{i}: {c['answer']}")

    if session.spec:
        console.print(f"\n[bold]Generated spec:[/bold]\n{session.spec}")
    else:
        console.print("\n[dim]To develop this idea, Lloyd would ask clarifying questions.[/dim]")
        console.print("[dim]This feature integrates with the LLM/crew infrastructure.[/dim]")

    console.print(f"\n[bold]Status:[/bold] {session.status}")
    console.print(f"\nContinue with: [cyan]lloyd brainstorm \"\" --continue-session {session.session_id}[/cyan]")


@cli.command()
@click.option("--category", "-c", help="Filter by category")
@click.option("--limit", "-n", default=10, help="Number of entries to show")
def knowledge(category: str | None, limit: int) -> None:
    """View knowledge base entries."""
    from lloyd.knowledge.store import KnowledgeStore

    store = KnowledgeStore()
    entries = store.query(category=category)[:limit]

    if not entries:
        console.print("[dim]Knowledge base is empty.[/dim]")
        return

    table = Table(title="Knowledge Base")
    table.add_column("ID", style="cyan")
    table.add_column("Category", style="white")
    table.add_column("Conf", justify="right")
    table.add_column("Freq", justify="right")
    table.add_column("Title", style="white")

    for e in entries:
        table.add_row(
            e.id,
            e.category,
            f"{e.confidence:.2f}",
            str(e.frequency),
            e.title[:40],
        )

    console.print(table)


@cli.command()
def metrics() -> None:
    """Show task execution metrics and statistics."""
    from lloyd.orchestrator.metrics import MetricsStore

    store = MetricsStore()
    stats = store.get_stats()

    if stats.get("total", 0) == 0:
        console.print("[yellow]No metrics recorded yet. Run some tasks first.[/yellow]")
        return

    console.print("\n[bold]Task Execution Metrics[/bold]\n")

    # Summary stats
    console.print(f"Total tasks: {stats['total']}")
    console.print(f"Successful: {stats['successful']} ({stats['success_rate']:.1f}%)")
    console.print(f"Avg duration: {stats['avg_duration']:.1f}s")

    # By complexity
    by_complexity = stats.get("by_complexity", {})
    if by_complexity:
        console.print("\n[bold]By Complexity:[/bold]")
        for complexity, data in by_complexity.items():
            console.print(f"  {complexity}: {data['count']} tasks, avg {data['avg_duration']:.1f}s")

    # Recent tasks
    recent = store.get_recent(5)
    if recent:
        console.print("\n[bold]Recent Tasks:[/bold]")
        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Idea", style="white")
        table.add_column("Complexity", justify="center")
        table.add_column("Duration", justify="right")
        table.add_column("Outcome", justify="center")

        for task in reversed(recent):
            outcome = task.get("outcome", "?")
            outcome_style = "[green]" if outcome == "success" else "[red]"
            table.add_row(
                task.get("task_id", "?"),
                task.get("idea", "?")[:35] + "..." if len(task.get("idea", "")) > 35 else task.get("idea", "?"),
                task.get("complexity", "?"),
                task.get("duration_human", "?"),
                f"{outcome_style}{outcome}[/]",
            )

        console.print(table)


@cli.command()
@click.option("--all", "-a", "show_all", is_flag=True, help="Show all items including resolved")
def inbox(show_all: bool) -> None:
    """Show inbox items needing attention."""
    from lloyd.inbox.store import InboxStore

    store = InboxStore()
    items = store.list_all() if show_all else store.list_unresolved()

    if not items:
        console.print("[dim]Inbox is empty.[/dim]")
        return

    table = Table(title="Inbox")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="white")
    table.add_column("Priority", justify="center")
    table.add_column("Title", style="white")
    table.add_column("Status", justify="center")

    for item in items:
        status_str = "[green]resolved[/green]" if item.resolved else "[yellow]pending[/yellow]"
        priority_style = {"high": "[red]", "normal": "[white]", "low": "[dim]"}.get(item.priority, "[white]")
        table.add_row(
            item.id,
            item.type,
            f"{priority_style}{item.priority}[/]",
            item.title[:40],
            status_str,
        )

    console.print(table)


@cli.command("inbox-view")
@click.argument("item_id")
def inbox_view(item_id: str) -> None:
    """View details of an inbox item."""
    from lloyd.inbox.store import InboxStore

    store = InboxStore()
    item = store.get(item_id)

    if not item:
        console.print(f"[red]Item {item_id} not found.[/red]")
        return

    console.print(f"\n[bold]ID:[/bold] {item.id}")
    console.print(f"[bold]Type:[/bold] {item.type}")
    console.print(f"[bold]Title:[/bold] {item.title}")
    console.print(f"[bold]Priority:[/bold] {item.priority}")
    console.print(f"[bold]Created:[/bold] {item.created_at}")
    console.print(f"[bold]Project:[/bold] {item.project_id}")
    console.print(f"[bold]Resolved:[/bold] {item.resolved}")
    if item.resolved:
        console.print(f"[bold]Resolution:[/bold] {item.resolution}")
        console.print(f"[bold]Resolved at:[/bold] {item.resolved_at}")
    console.print(f"\n[bold]Context:[/bold] {json.dumps(item.context, indent=2)}")
    console.print(f"\n[bold]Available actions:[/bold] {', '.join(item.actions) if item.actions else 'none'}")


@cli.command("inbox-resolve")
@click.argument("item_id")
@click.argument("action")
def inbox_resolve(item_id: str, action: str) -> None:
    """Resolve an inbox item with an action."""
    from lloyd.inbox.store import InboxStore

    store = InboxStore()
    item = store.resolve(item_id, action)

    if item:
        console.print(f"[green]Resolved {item_id} with action: {action}[/green]")
    else:
        console.print(f"[red]Item {item_id} not found.[/red]")


@cli.command()
@click.argument("story_id")
def reset_story(story_id: str) -> None:
    """Reset a story's attempt count and status."""
    prd_path = Path(".lloyd/prd.json")
    if not prd_path.exists():
        console.print("[yellow]No PRD found.[/yellow]")
        return

    with open(prd_path) as f:
        prd = json.load(f)

    for story in prd.get("stories", []):
        if story.get("id") == story_id:
            story["passes"] = False
            story["attempts"] = 0
            story["notes"] = ""
            with open(prd_path, "w") as f:
                json.dump(prd, f, indent=2)
            console.print(f"[green]Reset story: {story_id}[/green]")
            return

    console.print(f"[red]Story not found: {story_id}[/red]")


# ============== SELF-MODIFICATION COMMANDS ==============


@cli.group()
def selfmod() -> None:
    """Self-modification commands."""
    pass


@selfmod.command("queue")
def selfmod_queue() -> None:
    """Show self-modification task queue."""
    from lloyd.selfmod.queue import SelfModQueue

    tasks = SelfModQueue().list_all()
    if not tasks:
        console.print("[dim]No self-modification tasks.[/dim]")
        return

    table = Table(title="Self-Modification Queue")
    table.add_column("ID", style="cyan")
    table.add_column("Risk", justify="center")
    table.add_column("Status", style="white")
    table.add_column("Description", style="dim")

    for task in tasks:
        risk_icon = {"safe": "[green]SAFE[/green]", "moderate": "[yellow]MODERATE[/yellow]", "risky": "[red]RISKY[/red]"}.get(
            task.risk_level, "[dim]?[/dim]"
        )
        table.add_row(task.task_id, risk_icon, task.status, task.description[:40])

    console.print(table)


@selfmod.command("preview")
@click.argument("task_id")
def selfmod_preview(task_id: str) -> None:
    """Preview a self-modification task."""
    import os
    import subprocess

    from lloyd.selfmod.queue import SelfModQueue

    task = SelfModQueue().get(task_id)
    if not task:
        console.print(f"[red]Task {task_id} not found.[/red]")
        return

    console.print(f"\n[bold]Task:[/bold] {task.task_id}")
    console.print(f"[bold]Description:[/bold] {task.description}")
    console.print(f"[bold]Risk:[/bold] {task.risk_level}")
    console.print(f"[bold]Status:[/bold] {task.status}")
    console.print(f"[bold]Clone:[/bold] {task.clone_path}")
    console.print(f"\n[cyan]Approve:[/cyan] lloyd selfmod approve {task_id}")
    console.print(f"[cyan]Reject:[/cyan] lloyd selfmod reject {task_id}")

    # Open file explorer / terminal at clone
    if task.clone_path:
        if os.name == "nt":
            subprocess.Popen(f'explorer "{task.clone_path}"', shell=True)
        else:
            subprocess.Popen(f'xdg-open "{task.clone_path}"', shell=True)


@selfmod.command("diff")
@click.argument("task_id")
def selfmod_diff(task_id: str) -> None:
    """Show diff for a self-modification task."""
    from lloyd.selfmod.clone_manager import LloydCloneManager
    from lloyd.selfmod.queue import SelfModQueue

    task = SelfModQueue().get(task_id)
    if not task:
        console.print(f"[red]Task {task_id} not found.[/red]")
        return

    diff = LloydCloneManager().get_diff(task_id)
    console.print(diff if diff else "[dim]No changes.[/dim]")


@selfmod.command("test-now")
def selfmod_test_now() -> None:
    """Run GPU tests on awaiting tasks."""
    from lloyd.selfmod.queue import SelfModQueue
    from lloyd.selfmod.test_runner import SelfModTestRunner

    queue = SelfModQueue()
    tasks = queue.get_by_status("awaiting_gpu")

    if not tasks:
        console.print("[dim]No tasks awaiting GPU tests.[/dim]")
        return

    for task in tasks:
        console.print(f"[cyan]Testing {task.task_id}...[/cyan]")
        results = SelfModTestRunner(Path(task.clone_path)).run_gpu_tests()
        task.test_results.update(results)

        all_passed = all(r[0] for r in results.values())
        if all_passed:
            task.status = "awaiting_approval"
            console.print(f"  [green]Passed! Approve: lloyd selfmod approve {task.task_id}[/green]")
        else:
            task.status = "failed"
            console.print(f"  [red]Failed.[/red]")

        queue.update(task)


@selfmod.command("approve")
@click.argument("task_id")
def selfmod_approve(task_id: str) -> None:
    """Approve and merge a self-modification."""
    from lloyd.selfmod.clone_manager import LloydCloneManager
    from lloyd.selfmod.queue import SelfModQueue

    queue = SelfModQueue()
    manager = LloydCloneManager()
    task = queue.get(task_id)

    if not task:
        console.print(f"[red]Task {task_id} not found.[/red]")
        return

    if manager.merge_clone(task_id):
        task.status = "merged"
        queue.update(task)
        manager.cleanup_clone(task_id)
        console.print(f"[green]Merged {task_id}![/green]")
    else:
        console.print(f"[red]Merge failed for {task_id}.[/red]")


@selfmod.command("reject")
@click.argument("task_id")
def selfmod_reject(task_id: str) -> None:
    """Reject a self-modification."""
    from lloyd.selfmod.clone_manager import LloydCloneManager
    from lloyd.selfmod.queue import SelfModQueue

    queue = SelfModQueue()
    task = queue.get(task_id)

    if task:
        task.status = "rejected"
        queue.update(task)

    LloydCloneManager().cleanup_clone(task_id)
    console.print(f"[yellow]Rejected {task_id}.[/yellow]")


# ============== EXTENSION COMMANDS ==============


@cli.group()
def ext() -> None:
    """Extension commands."""
    pass


@ext.command("list")
def ext_list() -> None:
    """List all extensions."""
    from lloyd.extensions.manager import ExtensionManager

    exts = ExtensionManager().discover()
    if not exts:
        console.print("[dim]No extensions. Create one: lloyd ext create <name>[/dim]")
        return

    table = Table(title="Extensions")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="dim")
    table.add_column("Status", justify="center")
    table.add_column("Description", style="white")

    for e in exts:
        if e.error:
            status = "[red]ERROR[/red]"
        elif e.enabled:
            status = "[green]ON[/green]"
        else:
            status = "[dim]OFF[/dim]"
        table.add_row(e.display_name, e.version, status, e.description[:35])

    console.print(table)


@ext.command("create")
@click.argument("name")
@click.option("-d", "--description", help="Extension description")
def ext_create(name: str, description: str | None) -> None:
    """Create a new extension scaffold."""
    from lloyd.extensions.scaffold import create_extension_scaffold

    path = create_extension_scaffold(name, description)
    console.print(f"[green]Created extension:[/green] {path}")
    console.print(f"Edit: {path}/tool.py")


@ext.command("configure")
@click.argument("name")
def ext_configure(name: str) -> None:
    """Configure an extension."""
    import yaml

    from lloyd.extensions.manager import ExtensionManager

    manager = ExtensionManager()
    manager.discover()
    ext = manager.extensions.get(name)

    if not ext:
        console.print(f"[red]Extension {name} not found.[/red]")
        return

    # Load existing config
    config_path = ext.path / "config.yaml"
    config = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    # Get required config from manifest
    requires = ext.manifest.get("requires", {}).get("config", [])
    if not requires:
        console.print("[dim]No configuration required.[/dim]")
        return

    # Prompt for each config item
    for item in requires:
        key = item.get("key", "")
        desc = item.get("description", key)
        secret = item.get("secret", False)

        current = config.get(key, "")
        value = click.prompt(desc, default=current, hide_input=secret, show_default=not secret)
        if value:
            config[key] = value

    # Save config
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f)

    console.print("[green]Configuration saved.[/green]")


@ext.command("remove")
@click.argument("name")
def ext_remove(name: str) -> None:
    """Remove an extension."""
    import shutil

    from lloyd.extensions.manager import ExtensionManager

    manager = ExtensionManager()
    manager.discover()
    ext = manager.extensions.get(name)

    if not ext:
        console.print(f"[red]Extension {name} not found.[/red]")
        return

    if click.confirm(f"Remove extension {name}?"):
        shutil.rmtree(ext.path)
        console.print(f"[yellow]Removed {name}.[/yellow]")


@ext.command("build")
@click.argument("idea")
def ext_build(idea: str) -> None:
    """Build an extension from a natural language description."""
    from lloyd.extensions.builder import build_extension_from_idea

    result = build_extension_from_idea(idea)
    if result["status"] == "created":
        console.print(f"\n[green]Extension created:[/green] {result['extension']}")
        if result["needs_config"]:
            console.print(f"[cyan]Configure:[/cyan] lloyd ext configure {result['extension']}")


# ============== CLASSIFY COMMAND ==============


@cli.command()
@click.argument("idea")
def classify(idea: str) -> None:
    """Classify an idea to see how Lloyd would handle it."""
    from lloyd.orchestrator.intent_classifier import IntentClassifier

    classifier = IntentClassifier()
    intent, reason, confidence = classifier.classify(idea)
    plan = classifier.get_implementation_plan(intent, idea)

    console.print(f"\n[bold]Idea:[/bold] {idea}")
    console.print(f"[bold]Detected:[/bold] {intent.value} (confidence: {confidence:.0%})")
    console.print(f"[bold]Reason:[/bold] {reason}")
    console.print(f"\n[bold]Approach:[/bold] {plan['approach']}")
    console.print(f"[bold]Description:[/bold] {plan['description']}")
    console.print(f"[bold]Steps:[/bold]")
    for step in plan["steps"]:
        console.print(f"  - {step}")


# ============== QUEUE COMMANDS ==============


@cli.group()
def queue() -> None:
    """Idea queue commands for batch processing."""
    pass


@queue.command("add")
@click.argument("description")
@click.option("--priority", "-p", default=1, help="Priority (lower = higher priority)")
def queue_add(description: str, priority: int) -> None:
    """Add an idea to the queue."""
    from lloyd.orchestrator.idea_queue import IdeaQueue

    q = IdeaQueue()
    idea = q.add(description, priority=priority)
    console.print(f"[green]Added to queue:[/green] {idea.id}")
    console.print(f"[dim]{description[:100]}{'...' if len(description) > 100 else ''}[/dim]")


@queue.command("add-file")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--priority", "-p", default=1, help="Priority (lower = higher priority)")
def queue_add_file(file_path: str, priority: int) -> None:
    """Add an idea from a file (spec document or text file)."""
    from pathlib import Path

    from lloyd.orchestrator.idea_queue import IdeaQueue

    content = Path(file_path).read_text(encoding="utf-8")
    q = IdeaQueue()
    idea = q.add(content, priority=priority)
    console.print(f"[green]Added to queue:[/green] {idea.id}")
    console.print(f"[dim]From file: {file_path} ({len(content)} chars)[/dim]")


@queue.command("add-many")
@click.argument("descriptions", nargs=-1)
def queue_add_many(descriptions: tuple[str, ...]) -> None:
    """Add multiple ideas to the queue."""
    from lloyd.orchestrator.idea_queue import IdeaQueue

    if not descriptions:
        console.print("[yellow]No ideas provided.[/yellow]")
        return

    q = IdeaQueue()
    ideas = q.add_many(list(descriptions))
    console.print(f"[green]Added {len(ideas)} ideas to queue:[/green]")
    for idea in ideas:
        console.print(f"  [{idea.id}] {idea.description[:50]}...")


@queue.command("list")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show completed ideas too")
def queue_list(show_all: bool) -> None:
    """List ideas in the queue."""
    from rich.table import Table

    from lloyd.orchestrator.idea_queue import IdeaQueue, IdeaStatus

    q = IdeaQueue()
    ideas = q.list_all() if show_all else q.list_pending()

    if not ideas:
        console.print("[dim]Queue is empty.[/dim]")
        return

    table = Table(title="Idea Queue")
    table.add_column("ID", style="cyan")
    table.add_column("Priority", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Description", style="white")

    status_styles = {
        IdeaStatus.PENDING: "[yellow]PENDING[/yellow]",
        IdeaStatus.IN_PROGRESS: "[blue]RUNNING[/blue]",
        IdeaStatus.COMPLETED: "[green]DONE[/green]",
        IdeaStatus.FAILED: "[red]FAILED[/red]",
        IdeaStatus.SKIPPED: "[dim]SKIPPED[/dim]",
    }

    for idea in ideas:
        table.add_row(
            idea.id,
            str(idea.priority),
            status_styles.get(idea.status, str(idea.status)),
            idea.description[:50] + ("..." if len(idea.description) > 50 else ""),
        )

    console.print(table)

    counts = q.count()
    console.print(
        f"\n[dim]Total: {counts['total']} | "
        f"Pending: {counts['pending']} | "
        f"Running: {counts['in_progress']} | "
        f"Done: {counts['completed']} | "
        f"Failed: {counts['failed']}[/dim]"
    )


@queue.command("remove")
@click.argument("idea_id")
def queue_remove(idea_id: str) -> None:
    """Remove an idea from the queue."""
    from lloyd.orchestrator.idea_queue import IdeaQueue

    q = IdeaQueue()
    if q.remove(idea_id):
        console.print(f"[green]Removed:[/green] {idea_id}")
    else:
        console.print(f"[red]Not found:[/red] {idea_id}")


@queue.command("clear")
@click.option("--completed", "-c", is_flag=True, help="Clear only completed/failed ideas")
def queue_clear(completed: bool) -> None:
    """Clear the idea queue."""
    from lloyd.orchestrator.idea_queue import IdeaQueue

    q = IdeaQueue()
    if completed:
        removed = q.clear_completed()
        console.print(f"[green]Cleared {removed} completed ideas.[/green]")
    else:
        if click.confirm("Clear ALL ideas from queue?"):
            count = len(q.list_all())
            for idea in q.list_all():
                q.remove(idea.id)
            console.print(f"[green]Cleared {count} ideas.[/green]")


@queue.command("run")
@click.option("--max-iterations", "-m", default=50, help="Max iterations per idea")
@click.option("--max-parallel", "-p", default=3, help="Max parallel workers per idea")
@click.option("--sequential", "-s", is_flag=True, help="Run stories sequentially")
@click.option("--limit", "-n", default=0, help="Max ideas to process (0 = all)")
@click.option("--legacy", is_flag=True, help="Use legacy crew-based execution (not TDD)")
def queue_run(max_iterations: int, max_parallel: int, sequential: bool, limit: int, legacy: bool) -> None:
    """Process ideas from the queue."""
    from lloyd.orchestrator.flow import run_lloyd
    from lloyd.orchestrator.idea_queue import IdeaQueue

    q = IdeaQueue()
    pending = q.list_pending()

    if not pending:
        console.print("[yellow]No pending ideas in queue.[/yellow]")
        return

    if limit > 0:
        pending = pending[:limit]

    parallel = not sequential
    use_iterative = not legacy
    mode_str = "sequential" if sequential else f"parallel (max {max_parallel})"
    exec_str = "TDD iterative" if use_iterative else "legacy crew"
    console.print(f"[bold blue]Processing {len(pending)} ideas ({mode_str}, {exec_str})...[/bold blue]")

    for i, idea in enumerate(pending, 1):
        console.print(f"\n[bold cyan]=== Idea {i}/{len(pending)}: {idea.id} ===[/bold cyan]")
        console.print(f"[dim]{idea.description[:200]}{'...' if len(idea.description) > 200 else ''}[/dim]\n")

        # Mark as in progress
        q.start(idea.id)

        try:
            state = run_lloyd(
                idea.description,
                max_iterations=max_iterations,
                max_parallel=max_parallel,
                parallel=parallel,
                use_iterative_executor=use_iterative,
            )

            success = state.status == "complete"
            q.complete(
                idea.id,
                success=success,
                iterations=state.iteration,
                prd_path=".lloyd/prd.json" if success else None,
                error=None if success else f"Status: {state.status}",
            )

            if success:
                console.print(f"[green]Completed:[/green] {idea.id}")
            else:
                console.print(f"[red]Failed:[/red] {idea.id} ({state.status})")

        except Exception as e:
            q.complete(idea.id, success=False, error=str(e))
            console.print(f"[red]Error:[/red] {idea.id} - {e}")

    # Final summary
    counts = q.count()
    console.print(f"\n[bold]Queue Summary:[/bold]")
    console.print(f"  Completed: {counts['completed']}")
    console.print(f"  Failed: {counts['failed']}")
    console.print(f"  Remaining: {counts['pending']}")


@queue.command("view")
@click.argument("idea_id")
def queue_view(idea_id: str) -> None:
    """View details of a queued idea."""
    from lloyd.orchestrator.idea_queue import IdeaQueue

    q = IdeaQueue()
    idea = q.get(idea_id)

    if not idea:
        console.print(f"[red]Not found:[/red] {idea_id}")
        return

    console.print(f"\n[bold]ID:[/bold] {idea.id}")
    console.print(f"[bold]Status:[/bold] {idea.status.value}")
    console.print(f"[bold]Priority:[/bold] {idea.priority}")
    console.print(f"[bold]Created:[/bold] {idea.created_at}")
    if idea.started_at:
        console.print(f"[bold]Started:[/bold] {idea.started_at}")
    if idea.completed_at:
        console.print(f"[bold]Completed:[/bold] {idea.completed_at}")
    if idea.iterations:
        console.print(f"[bold]Iterations:[/bold] {idea.iterations}")
    if idea.prd_path:
        console.print(f"[bold]PRD:[/bold] {idea.prd_path}")
    if idea.error:
        console.print(f"[bold red]Error:[/bold red] {idea.error}")
    console.print(f"\n[bold]Description:[/bold]\n{idea.description}")


if __name__ == "__main__":
    cli()
