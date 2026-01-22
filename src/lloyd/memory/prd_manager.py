"""PRD (Product Requirements Document) management for AEGIS."""

import json
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class StoryStatus(str, Enum):
    """Status of a story in the execution pipeline."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class Story(BaseModel):
    """A single story/task in the PRD."""

    id: str
    title: str
    description: str
    priority: int = 1
    dependencies: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list, alias="acceptanceCriteria")
    passes: bool = False
    attempts: int = 0
    last_attempt_at: str | None = Field(default=None, alias="lastAttemptAt")
    notes: str = ""
    status: StoryStatus = Field(default=StoryStatus.PENDING)
    worker_id: str | None = Field(default=None, alias="workerId")
    started_at: str | None = Field(default=None, alias="startedAt")
    completed_at: str | None = Field(default=None, alias="completedAt")

    class Config:
        """Pydantic configuration."""

        populate_by_name = True


class PRDMetadata(BaseModel):
    """Metadata for a PRD."""

    total_stories: int = Field(default=0, alias="totalStories")
    completed_stories: int = Field(default=0, alias="completedStories")
    in_progress_stories: int = Field(default=0, alias="inProgressStories")
    current_story: str | None = Field(default=None, alias="currentStory")
    estimated_iterations: int = Field(default=0, alias="estimatedIterations")
    actual_iterations: int = Field(default=0, alias="actualIterations")

    class Config:
        """Pydantic configuration."""

        populate_by_name = True


class PRD(BaseModel):
    """Product Requirements Document structure."""

    project_name: str = Field(alias="projectName")
    description: str = ""
    branch_name: str = Field(default="main", alias="branchName")
    created_at: str = Field(default="", alias="createdAt")
    updated_at: str = Field(default="", alias="updatedAt")
    status: str = "idle"  # idle, in_progress, complete, blocked
    stories: list[Story] = Field(default_factory=list)
    metadata: PRDMetadata = Field(default_factory=PRDMetadata)

    class Config:
        """Pydantic configuration."""

        populate_by_name = True


class PRDManager:
    """Manages PRD files and story state."""

    def __init__(self, prd_path: str | Path = ".aegis/prd.json") -> None:
        """Initialize PRD manager.

        Args:
            prd_path: Path to the PRD JSON file.
        """
        self.prd_path = Path(prd_path)

    def load(self) -> PRD | None:
        """Load PRD from disk.

        Returns:
            PRD object or None if file doesn't exist.
        """
        if not self.prd_path.exists():
            return None

        try:
            with open(self.prd_path) as f:
                data = json.load(f)
            return PRD(**data)
        except Exception as e:
            print(f"Error loading PRD: {e}")
            return None

    def save(self, prd: PRD) -> bool:
        """Save PRD to disk.

        Args:
            prd: PRD object to save.

        Returns:
            True if saved successfully, False otherwise.
        """
        try:
            self.prd_path.parent.mkdir(parents=True, exist_ok=True)
            prd.updated_at = datetime.now(UTC).isoformat()

            # Update metadata
            prd.metadata.total_stories = len(prd.stories)
            prd.metadata.completed_stories = sum(1 for s in prd.stories if s.passes)
            prd.metadata.in_progress_stories = sum(
                1 for s in prd.stories if s.status == StoryStatus.IN_PROGRESS
            )

            with open(self.prd_path, "w") as f:
                json.dump(prd.model_dump(by_alias=True), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving PRD: {e}")
            return False

    def create_new(
        self,
        project_name: str,
        description: str = "",
        stories: list[dict[str, Any]] | None = None,
    ) -> PRD:
        """Create a new PRD.

        Args:
            project_name: Name of the project.
            description: Project description.
            stories: Optional list of story dictionaries.

        Returns:
            New PRD object.
        """
        now = datetime.now(UTC).isoformat()

        prd = PRD(
            projectName=project_name,
            description=description,
            createdAt=now,
            updatedAt=now,
            status="idle",
            stories=[Story(**s) for s in (stories or [])],
        )

        prd.metadata.total_stories = len(prd.stories)
        return prd

    def create_from_planning(self, planning_result: Any) -> PRD:
        """Create a PRD from planning crew output.

        Args:
            planning_result: Output from the planning crew.

        Returns:
            New PRD object.
        """
        # Parse planning result - this may be a CrewOutput or string
        result_str = str(planning_result)

        # Try to extract structured data from the result
        # This is a simplified implementation - in practice, you'd want
        # more robust parsing of the planning output
        return self.create_new(
            project_name="Planned Project",
            description=result_str[:500] if len(result_str) > 500 else result_str,
        )

    def get_next_story(self, prd: PRD) -> Story | None:
        """Get the next story to work on.

        Returns the highest priority incomplete story whose dependencies are met.

        Args:
            prd: PRD to search in.

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

    def update_story(
        self,
        prd: PRD,
        story_id: str,
        passes: bool | None = None,
        attempts: int | None = None,
        notes: str | None = None,
    ) -> bool:
        """Update a story in the PRD.

        Args:
            prd: PRD containing the story.
            story_id: ID of the story to update.
            passes: Whether the story passes (optional).
            attempts: Number of attempts (optional).
            notes: Notes to append (optional).

        Returns:
            True if story was found and updated, False otherwise.
        """
        for story in prd.stories:
            if story.id == story_id:
                if passes is not None:
                    story.passes = passes
                if attempts is not None:
                    story.attempts = attempts
                if notes is not None:
                    if story.notes:
                        story.notes += f"\n{notes}"
                    else:
                        story.notes = notes
                story.last_attempt_at = datetime.now(UTC).isoformat()
                return True
        return False

    def add_story(
        self,
        prd: PRD,
        title: str,
        description: str,
        acceptance_criteria: list[str],
        priority: int = 1,
        dependencies: list[str] | None = None,
    ) -> Story:
        """Add a new story to the PRD.

        Args:
            prd: PRD to add story to.
            title: Story title.
            description: Story description.
            acceptance_criteria: List of acceptance criteria.
            priority: Story priority (lower = higher priority).
            dependencies: List of story IDs this depends on.

        Returns:
            The created Story.
        """
        # Generate story ID
        story_id = f"story-{len(prd.stories) + 1:03d}"

        story = Story(
            id=story_id,
            title=title,
            description=description,
            priority=priority,
            dependencies=dependencies or [],
            acceptanceCriteria=acceptance_criteria,
        )

        prd.stories.append(story)
        prd.metadata.total_stories = len(prd.stories)

        return story

    def get_story_by_id(self, prd: PRD, story_id: str) -> Story | None:
        """Get a story by its ID.

        Args:
            prd: PRD to search in.
            story_id: ID of the story to find.

        Returns:
            Story if found, None otherwise.
        """
        for story in prd.stories:
            if story.id == story_id:
                return story
        return None

    def get_status_summary(self, prd: PRD) -> dict[str, Any]:
        """Get a summary of PRD status.

        Args:
            prd: PRD to summarize.

        Returns:
            Dictionary with status information.
        """
        total = len(prd.stories)
        completed = sum(1 for s in prd.stories if s.passes)
        in_progress = sum(1 for s in prd.stories if s.status == StoryStatus.IN_PROGRESS)
        failed = sum(1 for s in prd.stories if s.status == StoryStatus.FAILED)
        blocked = sum(1 for s in prd.stories if s.status == StoryStatus.BLOCKED)

        return {
            "project_name": prd.project_name,
            "status": prd.status,
            "total_stories": total,
            "completed": completed,
            "in_progress": in_progress,
            "failed": failed,
            "blocked": blocked,
            "pending": total - completed - in_progress - blocked - failed,
            "completion_percentage": (completed / total * 100) if total > 0 else 0,
        }
