"""Handler for self-modification requests."""

import subprocess
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from .classifier import ModificationRisk, ProtectedFileError, SelfModificationClassifier
from .clone_manager import LloydCloneManager
from .queue import SelfModQueue, SelfModTask
from .test_runner import SelfModTestRunner


def create_safety_snapshot() -> str:
    """Create a safety snapshot before modifications.

    Returns:
        Tag name of the snapshot
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    tag = f"pre-selfmod-{timestamp}"

    # Stage any uncommitted changes
    subprocess.run(["git", "add", "-A"], capture_output=True)
    subprocess.run(["git", "commit", "-m", "snapshot", "--allow-empty"], capture_output=True)

    # Create tags
    subprocess.run(["git", "tag", tag], capture_output=True)
    subprocess.run(["git", "tag", "-f", "lloyd-stable"], capture_output=True)

    return tag


def handle_self_modification(
    idea: str, work_func: Callable[[Path], None] | None = None
) -> SelfModTask | None:
    """Handle a self-modification request.

    Args:
        idea: Description of the modification
        work_func: Optional function to make changes in the clone

    Returns:
        SelfModTask with the result
    """
    # Create safety snapshot
    snap = create_safety_snapshot()
    print(f"  Snapshot: {snap}")

    # Classify risk
    classifier = SelfModificationClassifier()
    try:
        risk = classifier.classify(idea)
    except ProtectedFileError as e:
        print(f"  BLOCKED: {e}")
        return None

    can_test = classifier.can_test_immediately(risk)
    print(f"  Risk: {risk.value} | Test now: {can_test}")

    # Create clone
    mgr = LloydCloneManager()
    task_id = str(uuid.uuid4())[:8]
    clone = mgr.create_clone(task_id)
    print(f"  Clone: {clone}")

    # Create task
    task = SelfModTask(
        task_id=task_id,
        description=idea,
        risk_level=risk.value,
        status="in_progress",
        clone_path=str(clone),
    )
    queue = SelfModQueue()
    queue.add(task)

    # Run work function if provided
    if work_func:
        try:
            work_func(clone)
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            queue.update(task)
            print(f"  ERROR: {e}")
            return task

    # Run safe tests
    runner = SelfModTestRunner(clone)
    safe_results = runner.run_safe_tests()
    task.test_results.update(safe_results)

    if not runner.all_passed(safe_results):
        task.status = "failed"
        task.error_message = "Tests failed"
        queue.update(task)
        print("  Safe tests failed")
        return task

    print("  Safe tests passed")

    # Handle based on risk level
    if risk == ModificationRisk.SAFE:
        if mgr.merge_clone(task_id):
            task.status = "merged"
            mgr.cleanup_clone(task_id)
            print("  Auto-merged!")
        else:
            task.status = "failed"
            task.error_message = "Merge failed"
    elif risk == ModificationRisk.MODERATE:
        task.status = "awaiting_approval"
        print(f"  Approve: lloyd selfmod approve {task_id}")
    else:
        task.status = "awaiting_gpu"
        print("  GPU test: lloyd selfmod test-now")

    queue.update(task)
    return task


def is_self_modification(idea: str) -> bool:
    """Check if an idea is about self-modification.

    Args:
        idea: The idea description

    Returns:
        True if this is a self-modification request
    """
    signals = [
        "lloyd",
        "yourself",
        "your own",
        "upgrade lloyd",
        "modify lloyd",
        "change lloyd",
        "improve lloyd",
        "fix lloyd",
    ]
    return any(s in idea.lower() for s in signals)
