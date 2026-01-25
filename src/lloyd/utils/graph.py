"""Graph utilities for story dependency validation.

Provides cycle detection, topological sorting, and dependency validation
for story dependencies.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DependencyType(str, Enum):
    """Types of dependencies between stories."""

    HARD = "hard"  # Must be completely satisfied
    SOFT = "soft"  # Can proceed if partially satisfied (>= threshold)
    INTERFACE = "interface"  # Can proceed if interface defined, even if impl incomplete


@dataclass
class DependencyStatus:
    """Status of a dependency.

    Attributes:
        story_id: The dependent story ID.
        dep_type: Type of dependency.
        status: Current status (pending, in_progress, completed).
        completion_percentage: How complete the dependency is (0.0-1.0).
        interface_ready: Whether the interface is defined.
    """

    story_id: str
    dep_type: DependencyType
    status: str
    completion_percentage: float
    interface_ready: bool


def detect_cycles(stories: list[dict[str, Any]]) -> list[list[str]]:
    """Detect cycles in story dependencies using DFS.

    Args:
        stories: List of story dicts with 'id' and 'dependencies' keys.

    Returns:
        List of cycles found, where each cycle is a list of story IDs.
    """
    # Build adjacency list
    graph: dict[str, list[str]] = {}
    for story in stories:
        story_id = story.get("id", "")
        deps = story.get("dependencies", [])
        graph[story_id] = deps

    cycles: list[list[str]] = []
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                # Found cycle - extract it from path
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)

        path.pop()
        rec_stack.remove(node)

    # Run DFS from all nodes
    for story_id in graph:
        if story_id not in visited:
            dfs(story_id)

    return cycles


def topological_sort(stories: list[dict[str, Any]]) -> tuple[list[str], bool]:
    """Perform topological sort on stories.

    Args:
        stories: List of story dicts with 'id' and 'dependencies' keys.

    Returns:
        Tuple of (sorted story IDs, success). If cycles exist, returns
        partial ordering and False.
    """
    # Build adjacency list and in-degree count
    graph: dict[str, list[str]] = {}
    in_degree: dict[str, int] = {}
    all_ids: set[str] = set()

    for story in stories:
        story_id = story.get("id", "")
        deps = story.get("dependencies", [])
        all_ids.add(story_id)
        graph[story_id] = []
        in_degree[story_id] = len(deps)

        for dep in deps:
            all_ids.add(dep)
            if dep not in graph:
                graph[dep] = []
            graph[dep].append(story_id)

    # Ensure all nodes have in_degree entry
    for node in all_ids:
        if node not in in_degree:
            in_degree[node] = 0

    # Find all nodes with no incoming edges
    queue = [node for node in all_ids if in_degree[node] == 0]
    result: list[str] = []

    while queue:
        node = queue.pop(0)
        result.append(node)

        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # If result doesn't include all nodes, there's a cycle
    success = len(result) == len(all_ids)
    return result, success


def validate_dependencies(
    stories: list[dict[str, Any]]
) -> dict[str, Any]:
    """Validate story dependencies comprehensively.

    Args:
        stories: List of story dicts.

    Returns:
        Dict with:
        - cycles: List of detected cycles
        - missing_deps: List of dependencies that reference nonexistent stories
        - execution_order: Topological order if valid
        - is_valid: Whether the dependency graph is valid
        - errors: List of error messages
    """
    result = {
        "cycles": [],
        "missing_deps": [],
        "execution_order": [],
        "is_valid": True,
        "errors": [],
    }

    # Get all story IDs
    story_ids = {story.get("id", "") for story in stories}

    # Check for missing dependencies
    for story in stories:
        story_id = story.get("id", "")
        deps = story.get("dependencies", [])

        for dep in deps:
            if dep not in story_ids:
                result["missing_deps"].append({
                    "story": story_id,
                    "missing_dep": dep,
                })
                result["errors"].append(
                    f"Story '{story_id}' depends on non-existent story '{dep}'"
                )

    # Detect cycles
    cycles = detect_cycles(stories)
    result["cycles"] = cycles

    if cycles:
        result["is_valid"] = False
        for cycle in cycles:
            cycle_str = " -> ".join(cycle)
            result["errors"].append(f"Dependency cycle detected: {cycle_str}")

    # Get execution order
    order, success = topological_sort(stories)
    result["execution_order"] = order

    if not success and not cycles:
        # Topological sort failed but no cycles detected
        # This can happen with missing dependencies
        result["is_valid"] = False
        result["errors"].append(
            "Could not determine valid execution order due to dependency issues"
        )

    if result["missing_deps"]:
        result["is_valid"] = False

    return result


def check_dependencies_ready(
    story: dict[str, Any],
    all_stories: list[dict[str, Any]],
    threshold: float = 0.8,
) -> tuple[bool, list[DependencyStatus]]:
    """Check if a story's dependencies are ready.

    Supports different dependency types:
    - HARD: Must be completely satisfied
    - SOFT: Proceed if completion >= threshold
    - INTERFACE: Proceed if interface defined

    Args:
        story: The story to check.
        all_stories: All stories in the project.
        threshold: Completion threshold for SOFT dependencies.

    Returns:
        Tuple of (is_ready, list of DependencyStatus).
    """
    deps = story.get("dependencies", [])
    if not deps:
        return True, []

    # Build lookup for stories
    story_map = {s.get("id", ""): s for s in all_stories}

    statuses: list[DependencyStatus] = []
    all_ready = True

    for dep_spec in deps:
        # Parse dependency spec - could be "story-001" or "story-001:soft"
        if ":" in str(dep_spec):
            dep_id, dep_type_str = dep_spec.split(":", 1)
            dep_type = DependencyType(dep_type_str.lower())
        else:
            dep_id = dep_spec
            dep_type = DependencyType.HARD

        dep_story = story_map.get(dep_id)

        if not dep_story:
            # Missing dependency - treat as not ready
            statuses.append(
                DependencyStatus(
                    story_id=dep_id,
                    dep_type=dep_type,
                    status="missing",
                    completion_percentage=0.0,
                    interface_ready=False,
                )
            )
            all_ready = False
            continue

        # Calculate completion percentage
        status = dep_story.get("status", "pending")
        passes = dep_story.get("passes", False)

        if passes:
            completion = 1.0
        elif status == "in_progress":
            # Estimate progress from attempts
            attempts = dep_story.get("attempts", 0)
            completion = min(0.8, attempts * 0.2)  # Cap at 80%
        else:
            completion = 0.0

        # Check if interface is ready (simplified check)
        interface_ready = status in ["in_progress", "completed"] or passes

        dep_status = DependencyStatus(
            story_id=dep_id,
            dep_type=dep_type,
            status=status,
            completion_percentage=completion,
            interface_ready=interface_ready,
        )
        statuses.append(dep_status)

        # Check if this dependency is satisfied
        if dep_type == DependencyType.HARD:
            if not passes:
                all_ready = False
        elif dep_type == DependencyType.SOFT:
            if completion < threshold:
                all_ready = False
        elif dep_type == DependencyType.INTERFACE:
            if not interface_ready:
                all_ready = False

    return all_ready, statuses


def get_dependency_warnings(
    statuses: list[DependencyStatus], threshold: float = 0.8
) -> list[str]:
    """Get warnings for partially satisfied dependencies.

    Args:
        statuses: List of dependency statuses.
        threshold: Soft dependency threshold.

    Returns:
        List of warning messages.
    """
    warnings = []

    for status in statuses:
        if status.dep_type == DependencyType.SOFT:
            if status.completion_percentage >= threshold and status.completion_percentage < 1.0:
                warnings.append(
                    f"Soft dependency '{status.story_id}' is {status.completion_percentage:.0%} "
                    f"complete (threshold: {threshold:.0%})"
                )

        if status.dep_type == DependencyType.INTERFACE:
            if status.interface_ready and status.completion_percentage < 1.0:
                warnings.append(
                    f"Interface dependency '{status.story_id}' has interface ready "
                    f"but implementation is {status.completion_percentage:.0%} complete"
                )

    return warnings
