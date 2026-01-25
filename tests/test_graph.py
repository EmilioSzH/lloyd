"""Tests for graph utilities."""

import pytest

from lloyd.utils.graph import (
    DependencyStatus,
    DependencyType,
    check_dependencies_ready,
    detect_cycles,
    get_dependency_warnings,
    topological_sort,
    validate_dependencies,
)


class TestDetectCycles:
    """Tests for cycle detection."""

    def test_no_cycles(self):
        """No cycles in valid DAG."""
        stories = [
            {"id": "s1", "dependencies": []},
            {"id": "s2", "dependencies": ["s1"]},
            {"id": "s3", "dependencies": ["s1", "s2"]},
        ]

        cycles = detect_cycles(stories)
        assert len(cycles) == 0

    def test_simple_cycle(self):
        """Detects simple A -> B -> A cycle."""
        stories = [
            {"id": "s1", "dependencies": ["s2"]},
            {"id": "s2", "dependencies": ["s1"]},
        ]

        cycles = detect_cycles(stories)
        assert len(cycles) >= 1

    def test_longer_cycle(self):
        """Detects longer A -> B -> C -> A cycle."""
        stories = [
            {"id": "s1", "dependencies": ["s3"]},
            {"id": "s2", "dependencies": ["s1"]},
            {"id": "s3", "dependencies": ["s2"]},
        ]

        cycles = detect_cycles(stories)
        assert len(cycles) >= 1

    def test_self_cycle(self):
        """Detects self-referential cycle."""
        stories = [
            {"id": "s1", "dependencies": ["s1"]},
        ]

        cycles = detect_cycles(stories)
        assert len(cycles) >= 1


class TestTopologicalSort:
    """Tests for topological sorting."""

    def test_valid_order(self):
        """Returns valid order for DAG."""
        stories = [
            {"id": "s1", "dependencies": []},
            {"id": "s2", "dependencies": ["s1"]},
            {"id": "s3", "dependencies": ["s2"]},
        ]

        order, success = topological_sort(stories)

        assert success is True
        assert order.index("s1") < order.index("s2")
        assert order.index("s2") < order.index("s3")

    def test_multiple_valid_orders(self):
        """Handles multiple valid orderings."""
        stories = [
            {"id": "s1", "dependencies": []},
            {"id": "s2", "dependencies": []},
            {"id": "s3", "dependencies": ["s1", "s2"]},
        ]

        order, success = topological_sort(stories)

        assert success is True
        assert "s3" in order
        # s3 should come after both s1 and s2
        assert order.index("s1") < order.index("s3")
        assert order.index("s2") < order.index("s3")

    def test_fails_with_cycle(self):
        """Returns False for graphs with cycles."""
        stories = [
            {"id": "s1", "dependencies": ["s2"]},
            {"id": "s2", "dependencies": ["s1"]},
        ]

        _, success = topological_sort(stories)
        assert success is False


class TestValidateDependencies:
    """Tests for comprehensive validation."""

    def test_valid_graph(self):
        """Valid graph passes validation."""
        stories = [
            {"id": "s1", "dependencies": []},
            {"id": "s2", "dependencies": ["s1"]},
        ]

        result = validate_dependencies(stories)

        assert result["is_valid"] is True
        assert len(result["cycles"]) == 0
        assert len(result["missing_deps"]) == 0
        assert len(result["errors"]) == 0

    def test_detects_missing_deps(self):
        """Detects references to nonexistent stories."""
        stories = [
            {"id": "s1", "dependencies": ["nonexistent"]},
        ]

        result = validate_dependencies(stories)

        assert result["is_valid"] is False
        assert len(result["missing_deps"]) == 1
        assert result["missing_deps"][0]["missing_dep"] == "nonexistent"

    def test_detects_cycles(self):
        """Includes cycles in validation."""
        stories = [
            {"id": "s1", "dependencies": ["s2"]},
            {"id": "s2", "dependencies": ["s1"]},
        ]

        result = validate_dependencies(stories)

        assert result["is_valid"] is False
        assert len(result["cycles"]) >= 1

    def test_provides_execution_order(self):
        """Provides execution order in result."""
        stories = [
            {"id": "s1", "dependencies": []},
            {"id": "s2", "dependencies": ["s1"]},
        ]

        result = validate_dependencies(stories)

        assert "execution_order" in result
        assert len(result["execution_order"]) == 2

    def test_clear_error_messages(self):
        """Provides clear error messages."""
        stories = [
            {"id": "s1", "dependencies": ["s2"]},
            {"id": "s2", "dependencies": ["s1"]},
        ]

        result = validate_dependencies(stories)

        assert len(result["errors"]) > 0
        assert "cycle" in result["errors"][0].lower()


class TestCheckDependenciesReady:
    """Tests for dependency readiness checking."""

    def test_no_dependencies_ready(self):
        """Story with no dependencies is always ready."""
        story = {"id": "s1", "dependencies": []}
        all_stories = [story]

        ready, statuses = check_dependencies_ready(story, all_stories)

        assert ready is True
        assert len(statuses) == 0

    def test_hard_dependency_requires_complete(self):
        """HARD dependency requires completion."""
        story = {"id": "s2", "dependencies": ["s1"]}
        all_stories = [
            {"id": "s1", "status": "in_progress", "passes": False},
            story,
        ]

        ready, _ = check_dependencies_ready(story, all_stories)
        assert ready is False

    def test_hard_dependency_satisfied_when_passes(self):
        """HARD dependency satisfied when passes=True."""
        story = {"id": "s2", "dependencies": ["s1"]}
        all_stories = [
            {"id": "s1", "status": "completed", "passes": True},
            story,
        ]

        ready, _ = check_dependencies_ready(story, all_stories)
        assert ready is True

    def test_soft_dependency_with_threshold(self):
        """SOFT dependency can proceed at threshold."""
        story = {"id": "s2", "dependencies": ["s1:soft"]}
        all_stories = [
            {"id": "s1", "status": "in_progress", "passes": False, "attempts": 4},
            story,
        ]

        ready, statuses = check_dependencies_ready(story, all_stories, threshold=0.8)
        assert ready is True  # 4 attempts * 0.2 = 0.8

    def test_interface_dependency_ready_when_started(self):
        """INTERFACE dependency ready when started."""
        story = {"id": "s2", "dependencies": ["s1:interface"]}
        all_stories = [
            {"id": "s1", "status": "in_progress", "passes": False},
            story,
        ]

        ready, statuses = check_dependencies_ready(story, all_stories)
        assert ready is True

    def test_missing_dependency_not_ready(self):
        """Missing dependency means not ready."""
        story = {"id": "s2", "dependencies": ["nonexistent"]}
        all_stories = [story]

        ready, statuses = check_dependencies_ready(story, all_stories)

        assert ready is False
        assert statuses[0].status == "missing"


class TestDependencyType:
    """Tests for DependencyType enum."""

    def test_values(self):
        """Enum has expected values."""
        assert DependencyType.HARD.value == "hard"
        assert DependencyType.SOFT.value == "soft"
        assert DependencyType.INTERFACE.value == "interface"


class TestGetDependencyWarnings:
    """Tests for warning generation."""

    def test_soft_dependency_warning(self):
        """Generates warning for partially complete soft dep."""
        statuses = [
            DependencyStatus(
                story_id="s1",
                dep_type=DependencyType.SOFT,
                status="in_progress",
                completion_percentage=0.9,
                interface_ready=True,
            )
        ]

        warnings = get_dependency_warnings(statuses)

        assert len(warnings) == 1
        assert "soft" in warnings[0].lower()

    def test_interface_dependency_warning(self):
        """Generates warning for interface dep with partial impl."""
        statuses = [
            DependencyStatus(
                story_id="s1",
                dep_type=DependencyType.INTERFACE,
                status="in_progress",
                completion_percentage=0.5,
                interface_ready=True,
            )
        ]

        warnings = get_dependency_warnings(statuses)

        assert len(warnings) == 1
        assert "interface" in warnings[0].lower()
