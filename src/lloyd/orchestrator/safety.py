"""LLM-based safety detection for self-modification intent.

Replaces simple keyword-based detection with an LLM intent classifier
that can better understand context and nuance.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable
import json
import re


class SelfModRisk(str, Enum):
    """Risk levels for self-modification detection."""

    SAFE = "safe"  # 0-2 risk score
    MODERATE = "moderate"  # 3-5 risk score
    RISKY = "risky"  # 6-8 risk score
    BLOCKED = "blocked"  # 9-10 risk score


# Protected categories that should be flagged
PROTECTED_CATEGORIES = {
    "orchestration": [
        "flow.py",
        "orchestrator",
        "router.py",
        "state.py",
        "parallel_executor",
    ],
    "safety_code": [
        "safety.py",
        "selfmod",
        "classifier",
        "validation",
    ],
    "agent_definitions": [
        "agents.yaml",
        "crews",
        "agent",
    ],
    "prompts": [
        "tasks.yaml",
        "prompt",
        "backstory",
    ],
}


@dataclass
class SelfModDetectionResult:
    """Result of self-modification intent detection.

    Attributes:
        risk_score: Risk score from 0-10.
        risk_level: Categorized risk level.
        category: Detected category (orchestration, safety, etc).
        reason: Explanation of the detection.
        affected_files: List of potentially affected protected files.
        is_self_modification: Whether this is definitely self-modification.
    """

    risk_score: int
    risk_level: SelfModRisk
    category: str
    reason: str
    affected_files: list[str]
    is_self_modification: bool


def _score_to_risk_level(score: int) -> SelfModRisk:
    """Convert numeric score to risk level.

    Args:
        score: Risk score 0-10.

    Returns:
        Corresponding SelfModRisk level.
    """
    if score <= 2:
        return SelfModRisk.SAFE
    elif score <= 5:
        return SelfModRisk.MODERATE
    elif score <= 8:
        return SelfModRisk.RISKY
    else:
        return SelfModRisk.BLOCKED


def _detect_protected_files(
    idea: str, files: list[str] | None = None
) -> tuple[list[str], str]:
    """Detect if any protected files/categories are mentioned.

    Args:
        idea: The idea description.
        files: Optional list of files being modified.

    Returns:
        Tuple of (affected_files, category).
    """
    affected = []
    detected_category = ""
    combined = (idea + " " + " ".join(files or [])).lower()

    for category, patterns in PROTECTED_CATEGORIES.items():
        for pattern in patterns:
            if pattern.lower() in combined:
                affected.append(pattern)
                if not detected_category:
                    detected_category = category

    return affected, detected_category


def _build_classification_prompt(idea: str, files: list[str] | None = None) -> str:
    """Build prompt for LLM classification.

    Args:
        idea: The idea description.
        files: Optional list of files being modified.

    Returns:
        Formatted prompt for LLM.
    """
    files_str = "\n".join(f"- {f}" for f in (files or [])) if files else "None specified"

    return f"""Analyze whether this task involves self-modification of an AI system.

Task description: {idea}

Files potentially affected:
{files_str}

Self-modification includes:
- Changes to the AI's own code or logic
- Modifications to orchestration or agent behavior
- Changes to safety systems or validation
- Alterations to prompts or agent definitions

Respond with JSON only:
{{
  "risk": <0-10>,
  "category": "<orchestration|safety_code|agent_definitions|prompts|none>",
  "reason": "<brief explanation>"
}}

Risk scale:
0-2: Clearly not self-modification
3-5: Possibly touches AI systems but not core logic
6-8: Likely modifies AI behavior or safety
9-10: Definitely modifies core AI systems (should be blocked)
"""


def _parse_llm_response(response: str) -> dict[str, Any]:
    """Parse LLM JSON response.

    Args:
        response: Raw LLM response string.

    Returns:
        Parsed dict with risk, category, reason.
    """
    # Try to extract JSON from response
    try:
        # Handle markdown code blocks
        if "```" in response:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
            if match:
                response = match.group(1)

        return json.loads(response)
    except json.JSONDecodeError:
        # Fallback: try to extract risk number
        risk_match = re.search(r'"risk":\s*(\d+)', response)
        if risk_match:
            return {
                "risk": int(risk_match.group(1)),
                "category": "unknown",
                "reason": "Could not parse full response",
            }
        return {"risk": 5, "category": "unknown", "reason": "Failed to parse response"}


def detect_self_modification_intent(
    idea: str,
    files: list[str] | None = None,
    llm_func: Callable[[str], str] | None = None,
) -> SelfModDetectionResult:
    """Detect self-modification intent using LLM classification.

    Args:
        idea: The idea/task description.
        files: Optional list of files being modified.
        llm_func: Callable that takes a prompt and returns LLM response.
                  If None, falls back to rule-based detection.

    Returns:
        SelfModDetectionResult with risk assessment.
    """
    # First, do a quick keyword check for protected files
    affected_files, detected_category = _detect_protected_files(idea, files)

    # If we have an LLM function, use it for classification
    if llm_func:
        prompt = _build_classification_prompt(idea, files)
        try:
            response = llm_func(prompt)
            parsed = _parse_llm_response(response)

            risk_score = min(10, max(0, parsed.get("risk", 5)))
            category = parsed.get("category", detected_category or "none")
            reason = parsed.get("reason", "LLM classification")

            # Boost risk if protected files detected
            if affected_files:
                risk_score = min(10, risk_score + 2)
                if category == "none":
                    category = detected_category

            risk_level = _score_to_risk_level(risk_score)

            return SelfModDetectionResult(
                risk_score=risk_score,
                risk_level=risk_level,
                category=category,
                reason=reason,
                affected_files=affected_files,
                is_self_modification=risk_score >= 6,
            )

        except Exception as e:
            # LLM failed, fall back to rule-based
            pass

    # Rule-based fallback (enhanced keyword detection)
    return _rule_based_detection(idea, files, affected_files, detected_category)


def _rule_based_detection(
    idea: str,
    files: list[str] | None,
    affected_files: list[str],
    detected_category: str,
) -> SelfModDetectionResult:
    """Rule-based self-modification detection (fallback).

    Args:
        idea: The idea description.
        files: Optional list of files.
        affected_files: Already detected protected files.
        detected_category: Already detected category.

    Returns:
        SelfModDetectionResult from rule-based analysis.
    """
    idea_lower = idea.lower()

    # Strong self-modification signals
    strong_signals = [
        "lloyd",
        "yourself",
        "your own",
        "modify yourself",
        "upgrade yourself",
        "change your",
        "improve your",
        "fix your code",
        "modify the ai",
        "change the agent",
    ]

    # Moderate signals
    moderate_signals = [
        "orchestrat",
        "agent definition",
        "crew config",
        "backstory",
        "system prompt",
    ]

    risk_score = 0
    reasons = []

    # Check strong signals
    for signal in strong_signals:
        if signal in idea_lower:
            risk_score += 6
            reasons.append(f"Strong signal: '{signal}'")
            break

    # Check moderate signals
    for signal in moderate_signals:
        if signal in idea_lower:
            risk_score += 2
            reasons.append(f"Moderate signal: '{signal}'")

    # Check protected files
    if affected_files:
        risk_score += 3
        reasons.append(f"Protected files affected: {affected_files}")

    # Cap at 10
    risk_score = min(10, risk_score)
    risk_level = _score_to_risk_level(risk_score)

    reason = "; ".join(reasons) if reasons else "No self-modification signals detected"

    return SelfModDetectionResult(
        risk_score=risk_score,
        risk_level=risk_level,
        category=detected_category or "none",
        reason=reason,
        affected_files=affected_files,
        is_self_modification=risk_score >= 6,
    )


def is_self_modification(idea: str) -> bool:
    """Quick check if an idea involves self-modification.

    DEPRECATED: Use detect_self_modification_intent for more detailed analysis.

    Args:
        idea: The idea description.

    Returns:
        True if likely self-modification.
    """
    result = detect_self_modification_intent(idea)
    return result.is_self_modification


class SafetyGuard:
    """Safety guard for validating operations against protected resources.

    Provides a higher-level API for safety checks.
    """

    def __init__(self, llm_func: Callable[[str], str] | None = None) -> None:
        """Initialize the safety guard.

        Args:
            llm_func: Optional LLM callable for enhanced detection.
        """
        self.llm_func = llm_func

    def check_idea(
        self, idea: str, files: list[str] | None = None
    ) -> SelfModDetectionResult:
        """Check an idea for self-modification intent.

        Args:
            idea: The idea description.
            files: Optional list of files.

        Returns:
            SelfModDetectionResult.
        """
        return detect_self_modification_intent(idea, files, self.llm_func)

    def should_block(self, idea: str, files: list[str] | None = None) -> bool:
        """Check if an idea should be blocked.

        Args:
            idea: The idea description.
            files: Optional list of files.

        Returns:
            True if should be blocked.
        """
        result = self.check_idea(idea, files)
        return result.risk_level == SelfModRisk.BLOCKED

    def should_require_approval(
        self, idea: str, files: list[str] | None = None
    ) -> bool:
        """Check if an idea requires human approval.

        Args:
            idea: The idea description.
            files: Optional list of files.

        Returns:
            True if requires approval.
        """
        result = self.check_idea(idea, files)
        return result.risk_level in [SelfModRisk.RISKY, SelfModRisk.BLOCKED]

    def validate_files(self, files: list[str]) -> tuple[bool, list[str]]:
        """Validate a list of files against protected resources.

        Args:
            files: List of file paths.

        Returns:
            Tuple of (is_safe, list of protected files found).
        """
        protected_found = []
        for category, patterns in PROTECTED_CATEGORIES.items():
            for pattern in patterns:
                for file in files:
                    if pattern.lower() in file.lower():
                        protected_found.append(f"{file} ({category})")

        return len(protected_found) == 0, protected_found
