"""Task routing logic for AEGIS."""

from typing import Any

from lloyd.memory.prd_manager import PRD, Story, StoryStatus


def should_plan(state: Any) -> bool:
    """Determine if planning is needed.

    Args:
        state: Current AEGIS state.

    Returns:
        True if planning should be performed.
    """
    return state.status == "idle" and state.idea and not state.prd


def should_execute(state: Any) -> bool:
    """Determine if execution should proceed.

    Args:
        state: Current AEGIS state.

    Returns:
        True if execution should proceed.
    """
    return state.status in ("planning", "executing", "testing") and state.current_story is not None


def get_next_story(prd: PRD) -> Story | None:
    """Get the next story to work on.

    Returns the highest priority incomplete story whose dependencies are met.

    Args:
        prd: PRD containing stories.

    Returns:
        Next Story to work on, or None if all complete.
    """
    completed_ids = {s.id for s in prd.stories if s.passes}

    # Sort by priority (lower = higher priority)
    for story in sorted(prd.stories, key=lambda s: s.priority):
        if story.passes:
            continue

        # Check dependencies
        deps_met = all(dep in completed_ids for dep in story.dependencies)
        if deps_met:
            return story

    return None


def get_ready_stories(prd: PRD, max_count: int = 10) -> list[Story]:
    """Get all stories that are ready to execute in parallel.

    A story is ready if:
    - It has not passed (passes=False)
    - It is not currently in progress (status != IN_PROGRESS)
    - It is not blocked (status != BLOCKED)
    - All its dependencies have passed

    Args:
        prd: PRD containing stories.
        max_count: Maximum number of stories to return.

    Returns:
        List of stories ready for execution, sorted by priority.
    """
    completed_ids = {s.id for s in prd.stories if s.passes}
    ready_stories: list[Story] = []

    # Sort by priority (lower = higher priority)
    for story in sorted(prd.stories, key=lambda s: s.priority):
        if len(ready_stories) >= max_count:
            break

        # Skip completed stories
        if story.passes:
            continue

        # Skip in-progress stories
        if story.status == StoryStatus.IN_PROGRESS:
            continue

        # Skip blocked stories
        if story.status == StoryStatus.BLOCKED:
            continue

        # Check dependencies
        deps_met = all(dep in completed_ids for dep in story.dependencies)
        if deps_met:
            ready_stories.append(story)

    return ready_stories


def check_all_complete(prd: PRD) -> bool:
    """Check if all stories are complete.

    Args:
        prd: PRD to check.

    Returns:
        True if all stories pass.
    """
    return all(s.passes for s in prd.stories)


def check_blocked(prd: PRD, max_attempts: int = 3) -> list[Story]:
    """Find stories that are blocked (failed multiple times).

    Args:
        prd: PRD to check.
        max_attempts: Number of attempts before considering blocked.

    Returns:
        List of blocked stories.
    """
    blocked = []
    completed_ids = {s.id for s in prd.stories if s.passes}

    for story in prd.stories:
        if story.passes:
            continue

        # Check if dependencies are met
        deps_met = all(dep in completed_ids for dep in story.dependencies)
        if not deps_met:
            continue

        # Check if exceeded max attempts
        if story.attempts >= max_attempts:
            blocked.append(story)

    return blocked


def determine_next_action(state: Any, prd: PRD | None) -> str:
    """Determine the next action to take.

    Args:
        state: Current AEGIS state.
        prd: Current PRD (may be None).

    Returns:
        Action string: "plan", "execute", "test", "complete", "blocked", "idle"
    """
    if state.is_blocked():
        return "blocked"

    if not state.idea:
        return "idle"

    if not prd or not prd.stories:
        return "plan"

    if check_all_complete(prd):
        return "complete"

    blocked_stories = check_blocked(prd)
    if blocked_stories and len(blocked_stories) == len([s for s in prd.stories if not s.passes]):
        return "blocked"

    next_story = get_next_story(prd)
    if next_story:
        if state.status == "executing":
            return "test"
        return "execute"

    return "blocked"
