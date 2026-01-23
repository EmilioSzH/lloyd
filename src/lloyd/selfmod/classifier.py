"""Classify self-modification risk levels."""

import re
from enum import Enum


class ModificationRisk(str, Enum):
    SAFE = "safe"
    MODERATE = "moderate"
    RISKY = "risky"


class ProtectedFileError(Exception):
    """Raised when trying to modify a protected file."""

    pass


class SelfModificationClassifier:
    """Classify the risk level of self-modifications."""

    PROTECTED_FILES = ["lloyd-recovery.bat", "lloyd-recovery.sh", "src/lloyd/selfmod/recovery.py"]

    GPU_REQUIRED_PATTERNS = [
        r"orchestrator/flow\.py$",
        r"crews/.*/crew\.py$",
        r"crews/.*/agents\.yaml$",
        r"crews/.*/tasks\.yaml$",
    ]

    NO_GPU_PATTERNS = [
        r"\.md$",
        r"\.css$",
        r"\.html$",
        r"static/",
        r"themes/",
        r"gui/",
        r"inbox/",
        r"metrics",
        r"knowledge/",
        r"config",
        r"tests/",
        r"selfmod/",
        r"extensions/",
        r"frontend/",
    ]

    GPU_KEYWORDS = ["crew", "agent", "llm", "model", "inference", "flow", "orchestrat"]
    SAFE_KEYWORDS = [
        "ui",
        "theme",
        "style",
        "inbox",
        "metric",
        "knowledge",
        "config",
        "cli",
        "gui",
        "color",
        "display",
        "frontend",
    ]

    def classify(
        self, description: str, affected_files: list[str] | None = None
    ) -> ModificationRisk:
        """
        Classify the risk level of a modification.

        Args:
            description: Description of the modification
            affected_files: List of files that will be affected

        Returns:
            ModificationRisk level

        Raises:
            ProtectedFileError: If modification targets protected files
        """
        if affected_files:
            for f in affected_files:
                for p in self.PROTECTED_FILES:
                    if p in f:
                        raise ProtectedFileError(f"Cannot modify protected file: {f}")

        desc = description.lower()
        safe = sum(1 for k in self.SAFE_KEYWORDS if k in desc)
        gpu = sum(1 for k in self.GPU_KEYWORDS if k in desc)

        if safe >= 2 and gpu == 0:
            return ModificationRisk.SAFE

        if affected_files:
            for f in affected_files:
                for p in self.GPU_REQUIRED_PATTERNS:
                    if re.search(p, f):
                        return ModificationRisk.RISKY
            if all(any(re.search(p, f) for p in self.NO_GPU_PATTERNS) for f in affected_files):
                return ModificationRisk.SAFE

        return ModificationRisk.RISKY if gpu >= 2 else ModificationRisk.MODERATE

    def can_test_immediately(self, risk: ModificationRisk) -> bool:
        """Check if modification can be tested without GPU."""
        return risk != ModificationRisk.RISKY
