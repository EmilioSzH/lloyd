"""Tests for Lloyd state management."""

from lloyd.orchestrator.state import LloydState


def test_initial_state() -> None:
    """Test initial state values."""
    state = LloydState()

    assert state.idea == ""
    assert state.status == "idle"
    assert state.iteration == 0
    assert state.max_iterations == 50


def test_is_complete() -> None:
    """Test is_complete check."""
    state = LloydState()
    assert state.is_complete() is False

    state.status = "complete"
    assert state.is_complete() is True


def test_is_blocked() -> None:
    """Test is_blocked check."""
    state = LloydState()
    assert state.is_blocked() is False

    state.status = "blocked"
    assert state.is_blocked() is True

    # Also blocked when max iterations reached
    state.status = "executing"
    state.iteration = 50
    assert state.is_blocked() is True


def test_can_continue() -> None:
    """Test can_continue check."""
    state = LloydState()
    state.status = "executing"
    assert state.can_continue() is True

    state.status = "complete"
    assert state.can_continue() is False

    state.status = "executing"
    state.iteration = 50
    assert state.can_continue() is False
