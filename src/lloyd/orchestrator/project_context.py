"""Project context detection for Lloyd."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProjectContext:
    """Detected project context information."""

    language: str = "unknown"
    test_framework: str | None = None
    package_manager: str | None = None
    framework: str | None = None
    project_root: Path | None = None
    detected_from: list[str] = field(default_factory=list)


class ProjectDetector:
    """Detect project language and framework from marker files."""

    def detect(self, project_root: Path | None = None) -> ProjectContext:
        """Detect project context from marker files.

        Args:
            project_root: Root directory to scan. Defaults to cwd.

        Returns:
            ProjectContext with detected information.
        """
        if project_root is None:
            project_root = Path.cwd()

        context = ProjectContext(project_root=project_root)

        # Python
        for marker in ["pyproject.toml", "setup.py", "requirements.txt"]:
            if (project_root / marker).exists():
                context.language = "python"
                context.test_framework = "pytest"
                context.package_manager = "pip"
                context.detected_from.append(marker)
                # Check for uv
                if (project_root / "uv.lock").exists():
                    context.package_manager = "uv"
                    context.detected_from.append("uv.lock")
                break

        # JavaScript/TypeScript
        if context.language == "unknown" and (project_root / "package.json").exists():
            context.language = "javascript"
            context.test_framework = "jest"
            context.package_manager = "npm"
            context.detected_from.append("package.json")
            if (project_root / "tsconfig.json").exists():
                context.language = "typescript"
                context.detected_from.append("tsconfig.json")
            # Check for yarn/pnpm
            if (project_root / "yarn.lock").exists():
                context.package_manager = "yarn"
            elif (project_root / "pnpm-lock.yaml").exists():
                context.package_manager = "pnpm"

        # Rust
        if context.language == "unknown" and (project_root / "Cargo.toml").exists():
            context.language = "rust"
            context.test_framework = "cargo test"
            context.package_manager = "cargo"
            context.detected_from.append("Cargo.toml")

        # Go
        if context.language == "unknown" and (project_root / "go.mod").exists():
            context.language = "go"
            context.test_framework = "go test"
            context.package_manager = "go"
            context.detected_from.append("go.mod")

        return context

    def get_agent_context_prompt(self, context: ProjectContext) -> str:
        """Generate a prompt snippet for agents with project context.

        Args:
            context: Detected project context.

        Returns:
            Formatted prompt string.
        """
        return f"""Project Context:
- Language: {context.language}
- Test Framework: {context.test_framework or 'unknown'}
- Package Manager: {context.package_manager or 'unknown'}

IMPORTANT: Always use {context.language.upper()} syntax. Never use syntax from other languages."""
