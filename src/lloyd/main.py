"""CLI entry point for Lloyd."""

import json
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lloyd import __version__

console = Console()


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
def idea(
    description: str,
    max_iterations: int,
    max_parallel: int,
    sequential: bool,
    dry_run: bool,
    branch: bool,
    auto_pr: bool,
    draft_pr: bool,
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
        mode_str = "sequential" if sequential else f"parallel (max {max_parallel} workers)"
        console.print(f"[cyan]Starting autonomous execution ({mode_str}, max {max_iterations} iterations)...[/cyan]")
        from lloyd.orchestrator.flow import run_lloyd

        state = run_lloyd(
            description,
            max_iterations=max_iterations,
            max_parallel=max_parallel,
            parallel=parallel,
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


if __name__ == "__main__":
    cli()
