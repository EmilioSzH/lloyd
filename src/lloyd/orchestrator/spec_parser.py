"""Parse structured spec documents into requirements."""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Requirement:
    """A single requirement extracted from a spec."""

    id: str  # e.g., "1.1", "REQ-001", "FR-1"
    title: str
    description: str
    section: str  # Parent section name
    priority: int = 3  # 1=high, 5=low
    acceptance_criteria: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    raw_text: str = ""


@dataclass
class ParsedSpec:
    """Result of parsing a spec document."""

    title: str
    description: str
    requirements: list[Requirement]
    sections: list[str]
    metadata: dict = field(default_factory=dict)


class SpecParser:
    """Parse markdown spec documents into structured requirements."""

    def parse(self, text: str) -> ParsedSpec:
        """
        Parse a spec document and extract requirements.

        Args:
            text: Raw spec document text (markdown format)

        Returns:
            ParsedSpec with extracted requirements
        """
        lines = text.strip().split("\n")

        # Extract title from first H1 or use default
        title = self._extract_title(lines)
        description = self._extract_description(lines)

        # Parse sections and requirements
        requirements = []
        sections = []
        current_section = "General"
        current_requirement: Optional[Requirement] = None
        in_acceptance_criteria = False
        req_counter = 1

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Check for section header
            section_match = re.match(r"^(#{1,4})\s+(.+)$", line)
            if section_match:
                level = len(section_match.group(1))
                section_name = section_match.group(2).strip()

                # Save current requirement if exists
                if current_requirement:
                    requirements.append(current_requirement)
                    current_requirement = None

                if level <= 2:
                    current_section = section_name
                    if section_name not in sections:
                        sections.append(section_name)

                in_acceptance_criteria = False
                i += 1
                continue

            # Check for numbered requirement (1.1, 1.2.3, etc.)
            # Supports: "1.1 Text", "1.1. Text", "1.1) Text"
            numbered_match = re.match(
                r"^\s*(\d+(?:\.\d+)+)[.\)]?\s+(.+)$", stripped
            )
            if numbered_match:
                # Save previous requirement
                if current_requirement:
                    requirements.append(current_requirement)

                req_id = numbered_match.group(1)
                req_text = numbered_match.group(2)

                current_requirement = Requirement(
                    id=req_id,
                    title=req_text,
                    description="",
                    section=current_section,
                    priority=self._infer_priority(req_id, req_text),
                    raw_text=stripped,
                )
                in_acceptance_criteria = False
                i += 1
                continue

            # Check for REQ-XXX style requirement
            req_id_match = re.match(
                r"^\s*(REQ[-_]?\d+|FR[-_]?\d+|NFR[-_]?\d+|R\d+)[:\s]+(.+)$",
                stripped,
                re.IGNORECASE,
            )
            if req_id_match:
                if current_requirement:
                    requirements.append(current_requirement)

                req_id = req_id_match.group(1).upper()
                req_text = req_id_match.group(2)

                current_requirement = Requirement(
                    id=req_id,
                    title=req_text,
                    description="",
                    section=current_section,
                    priority=self._infer_priority(req_id, req_text),
                    raw_text=stripped,
                )
                in_acceptance_criteria = False
                i += 1
                continue

            # Check for user story format
            story_match = re.match(
                r"^\s*[*-]?\s*[Aa]s\s+(?:a|an)\s+(.+),?\s+[Ii]\s+want\s+(.+?)(?:\s+[Ss]o\s+that\s+(.+))?$",
                stripped,
            )
            if story_match:
                if current_requirement:
                    requirements.append(current_requirement)

                role = story_match.group(1)
                want = story_match.group(2)
                so_that = story_match.group(3) or ""

                current_requirement = Requirement(
                    id=f"US-{req_counter}",
                    title=f"As {role}, {want}",
                    description=so_that,
                    section=current_section,
                    priority=3,
                    raw_text=stripped,
                )
                req_counter += 1
                in_acceptance_criteria = False
                i += 1
                continue

            # Check for acceptance criteria header
            if re.match(
                r"^\s*[*-]?\s*(acceptance\s+criteria|ac)[:\s]*$",
                stripped,
                re.IGNORECASE,
            ):
                in_acceptance_criteria = True
                i += 1
                continue

            # Check for bullet/numbered item under current requirement
            bullet_match = re.match(r"^\s*[-*+]\s+(.+)$", stripped)
            numbered_sub_match = re.match(r"^\s*\d+[.\)]\s+(.+)$", stripped)

            if (bullet_match or numbered_sub_match) and current_requirement:
                item_text = (
                    bullet_match.group(1)
                    if bullet_match
                    else numbered_sub_match.group(1)
                )
                if in_acceptance_criteria:
                    current_requirement.acceptance_criteria.append(item_text)
                else:
                    # Add to description
                    current_requirement.description += f"\n- {item_text}"
                i += 1
                continue

            # Regular text - add to current requirement description
            if stripped and current_requirement:
                current_requirement.description += f"\n{stripped}"

            i += 1

        # Don't forget the last requirement
        if current_requirement:
            requirements.append(current_requirement)

        # If no requirements found, create them from bullet points
        if not requirements:
            requirements = self._extract_from_bullets(lines, current_section)

        # Clean up descriptions
        for req in requirements:
            req.description = req.description.strip()

        return ParsedSpec(
            title=title,
            description=description,
            requirements=requirements,
            sections=sections,
        )

    def _extract_title(self, lines: list[str]) -> str:
        """Extract document title from first H1."""
        for line in lines[:10]:
            match = re.match(r"^#\s+(.+)$", line)
            if match:
                return match.group(1).strip()
        return "Untitled Spec"

    def _extract_description(self, lines: list[str]) -> str:
        """Extract description from text after title, before first section."""
        description_lines = []
        started = False

        for line in lines:
            # Skip until after title
            if re.match(r"^#\s+", line):
                started = True
                continue

            # Stop at next header
            if started and re.match(r"^#{1,4}\s+", line):
                break

            if started and line.strip():
                description_lines.append(line.strip())

        return " ".join(description_lines[:5])  # First few lines

    def _infer_priority(self, req_id: str, text: str) -> int:
        """Infer priority from requirement ID or text."""
        text_lower = text.lower()

        # High priority signals
        if any(
            word in text_lower
            for word in ["must", "critical", "essential", "required", "security"]
        ):
            return 1

        # Medium-high priority
        if any(word in text_lower for word in ["should", "important", "core"]):
            return 2

        # Lower priority signals
        if any(
            word in text_lower
            for word in ["could", "nice to have", "optional", "future"]
        ):
            return 4

        # Default based on ID position
        if "." in req_id:
            parts = req_id.split(".")
            if parts[0] == "1":
                return 2  # First section often more important
            return 3

        return 3

    def _extract_from_bullets(
        self, lines: list[str], section: str
    ) -> list[Requirement]:
        """Fallback: extract requirements from bullet points."""
        requirements = []
        counter = 1

        for line in lines:
            match = re.match(r"^\s*[-*+]\s+(.+)$", line.strip())
            if match:
                text = match.group(1)
                # Skip short items or obvious non-requirements
                if len(text) > 15 and not text.lower().startswith(("note:", "see ")):
                    requirements.append(
                        Requirement(
                            id=f"R{counter}",
                            title=text,
                            description="",
                            section=section,
                            priority=3,
                            raw_text=line,
                        )
                    )
                    counter += 1

        return requirements

    def requirements_to_stories(self, parsed: ParsedSpec) -> list[dict]:
        """
        Convert parsed requirements to story format for PRD.

        Args:
            parsed: ParsedSpec from parse()

        Returns:
            List of story dicts compatible with PRD format
        """
        stories = []

        for i, req in enumerate(parsed.requirements):
            # Build acceptance criteria list
            ac_list: list[str] = []
            if req.acceptance_criteria:
                ac_list = list(req.acceptance_criteria)
            else:
                ac_list = [f"{req.title} is implemented and working"]

            # Determine dependencies from section ordering
            depends_on = []
            if i > 0:
                # Simple dependency: later items may depend on earlier ones in same section
                for j in range(max(0, i - 2), i):
                    prev_req = parsed.requirements[j]
                    if prev_req.section == req.section:
                        # Only add dependency if IDs suggest it (1.1 before 1.2)
                        if self._is_prerequisite(prev_req.id, req.id):
                            depends_on.append(prev_req.id)

            story = {
                "id": req.id,
                "title": req.title,
                "description": req.description or req.title,
                "priority": req.priority,
                "acceptanceCriteria": ac_list,
                "dependencies": depends_on,
                "section": req.section,
                "passes": False,
                "attempts": 0,
                "notes": "",
            }
            stories.append(story)

        return stories

    def _is_prerequisite(self, id1: str, id2: str) -> bool:
        """Check if id1 should be a prerequisite for id2."""
        # Handle numbered format (1.1, 1.2)
        if "." in id1 and "." in id2:
            parts1 = id1.split(".")
            parts2 = id2.split(".")
            # Same major section, earlier minor
            if parts1[0] == parts2[0] and len(parts1) > 1 and len(parts2) > 1:
                try:
                    return int(parts1[1]) == int(parts2[1]) - 1
                except ValueError:
                    pass
        return False
