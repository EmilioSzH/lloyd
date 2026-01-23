"""Self-modification framework for Lloyd."""

from .classifier import ModificationRisk, ProtectedFileError, SelfModificationClassifier
from .clone_manager import LloydCloneManager
from .handler import create_safety_snapshot, handle_self_modification
from .queue import SelfModQueue, SelfModTask
from .test_runner import SelfModTestRunner

__all__ = [
    "ModificationRisk",
    "SelfModificationClassifier",
    "ProtectedFileError",
    "LloydCloneManager",
    "SelfModTestRunner",
    "SelfModQueue",
    "SelfModTask",
    "handle_self_modification",
    "create_safety_snapshot",
]
