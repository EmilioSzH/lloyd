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
                "  [green]lloyd run[/green]          - Run the full workflow\n",
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
def idea(description: str, max_iterations: int, max_parallel: int, sequential: bool, dry_run: bool) -> None:
    """Submit a new product idea for Lloyd to execute."""
    console.print(f"[bold green]Received idea:[/bold green] {description}")

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
