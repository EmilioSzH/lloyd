"""Classify input type to determine processing approach."""

import re
from enum import Enum
from dataclasses import dataclass


class InputType(str, Enum):
    """Type of input received."""

    IDEA = "idea"  # Concise description, let Lloyd decompose
    SPEC = "spec"  # Structured document with requirements


@dataclass
class InputAnalysis:
    """Result of input analysis."""

    input_type: InputType
    confidence: float
    reason: str
    sections_found: list[str]
    requirement_count: int


class InputClassifier:
    """Detect whether input is a concise idea or a structured spec document."""

    # Patterns that indicate a spec document
    SPEC_PATTERNS = [
        # Numbered requirements: 1.1, 1.2.3, REQ-001, etc.
        r"^\s*\d+\.\d+",  # 1.1, 2.3, etc.
        r"^\s*\d+\.\d+\.\d+",  # 1.1.1, 2.3.4, etc.
        r"^\s*REQ[-_]?\d+",  # REQ-001, REQ_123
        r"^\s*R\d+",  # R1, R23
        r"^\s*FR[-_]?\d+",  # FR-001 (functional requirement)
        r"^\s*NFR[-_]?\d+",  # NFR-001 (non-functional)
        # User story format
        r"^\s*as\s+a\s+",  # As a user...
        r"^\s*given\s+.+when\s+.+then",  # BDD format
        # Acceptance criteria markers
        r"^\s*acceptance\s+criteria",
        r"^\s*ac\s*[\d:.]",
        # Section markers
        r"^#+\s*(requirements?|features?|specifications?|scope|overview|goals?)",
        r"^#+\s*(functional|non-functional|technical|user\s+stories)",
        r"^\*\*requirements?\*\*",
        r"^requirements?\s*:",
    ]

    # Markdown structure patterns
    MARKDOWN_SECTION_PATTERN = r"^#{1,4}\s+(.+)$"
    NUMBERED_LIST_PATTERN = r"^\s*(\d+[\.\)]\s+|\d+\.\d+[\.\)]*\s+)"
    BULLET_LIST_PATTERN = r"^\s*[-*+]\s+"

    def classify(self, text: str) -> InputAnalysis:
        """
        Classify input as idea or spec.

        Args:
            text: Raw input text

        Returns:
            InputAnalysis with type, confidence, and details
        """
        lines = text.strip().split("\n")
        total_lines = len(lines)

        # Quick checks
        if total_lines < 5:
            return InputAnalysis(
                input_type=InputType.IDEA,
                confidence=0.9,
                reason="Very short input, treating as idea",
                sections_found=[],
                requirement_count=0,
            )

        # Count indicators
        spec_signals = 0
        sections_found = []
        numbered_items = 0
        bullet_items = 0

        for line in lines:
            line_lower = line.lower()

            # Check spec patterns
            for pattern in self.SPEC_PATTERNS:
                if re.search(pattern, line_lower, re.IGNORECASE | re.MULTILINE):
                    spec_signals += 2
                    break

            # Check for markdown sections
            section_match = re.match(self.MARKDOWN_SECTION_PATTERN, line)
            if section_match:
                sections_found.append(section_match.group(1))
                spec_signals += 1

            # Count structured list items
            if re.match(self.NUMBERED_LIST_PATTERN, line):
                numbered_items += 1
            elif re.match(self.BULLET_LIST_PATTERN, line):
                bullet_items += 1

        # Calculate spec likelihood
        structure_score = (
            (len(sections_found) * 2)
            + (numbered_items * 1.5)
            + (bullet_items * 0.5)
            + spec_signals
        )

        # Normalize by document length
        normalized_score = structure_score / max(total_lines, 1)

        # Thresholds
        if normalized_score > 0.3 or spec_signals >= 5:
            return InputAnalysis(
                input_type=InputType.SPEC,
                confidence=min(0.95, 0.6 + normalized_score),
                reason=f"Detected {len(sections_found)} sections, {numbered_items} numbered items",
                sections_found=sections_found,
                requirement_count=numbered_items + bullet_items,
            )

        # Check for multiple paragraphs without structure (idea)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) <= 4 and numbered_items < 3:
            return InputAnalysis(
                input_type=InputType.IDEA,
                confidence=0.85,
                reason=f"Prose format with {len(paragraphs)} paragraphs",
                sections_found=sections_found,
                requirement_count=0,
            )

        # Borderline - lean toward spec if there's any structure
        if sections_found or numbered_items > 2:
            return InputAnalysis(
                input_type=InputType.SPEC,
                confidence=0.6,
                reason="Some structure detected, treating as spec",
                sections_found=sections_found,
                requirement_count=numbered_items,
            )

        return InputAnalysis(
            input_type=InputType.IDEA,
            confidence=0.7,
            reason="No clear structure, treating as idea",
            sections_found=[],
            requirement_count=0,
        )

    def is_spec(self, text: str) -> bool:
        """Quick check if input looks like a spec document."""
        return self.classify(text).input_type == InputType.SPEC
