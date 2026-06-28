"""Helpers shared by rule modules."""

from __future__ import annotations

from pathlib import Path

from repo_health.models import RuleDefinition, RuleResult, RuleStatus
from repo_health.repository_loader import RepositorySnapshot


def passed(definition: RuleDefinition, explanation: str) -> RuleResult:
    """Return a passed rule with full credit."""

    return definition.to_result(
        earned_score=definition.max_score,
        status=RuleStatus.PASSED,
        explanation=explanation,
    )


def failed(definition: RuleDefinition, explanation: str) -> RuleResult:
    """Return a failed rule with no credit."""

    return definition.to_result(earned_score=0, status=RuleStatus.FAILED, explanation=explanation)


def warning(definition: RuleDefinition, explanation: str, *, earned_score: float) -> RuleResult:
    """Return a warning rule with explicit partial credit."""

    return definition.to_result(
        earned_score=earned_score,
        status=RuleStatus.WARNING,
        explanation=explanation,
    )


def skipped(definition: RuleDefinition, explanation: str) -> RuleResult:
    """Return a skipped rule with no credit."""

    return definition.to_result(earned_score=0, status=RuleStatus.SKIPPED, explanation=explanation)


def contains_any(text: str, needles: tuple[str, ...]) -> bool:
    """Return whether any lowercase needle appears in text."""

    lowered = text.lower()
    return any(needle in lowered for needle in needles)


def pyproject_text(snapshot: RepositorySnapshot) -> str:
    """Return pyproject.toml content when present."""

    return snapshot.read_named_file("pyproject.toml")


def workflow_files(snapshot: RepositorySnapshot) -> list[Path]:
    """Return GitHub Actions workflow files."""

    return [
        path
        for path in snapshot.files()
        if path.as_posix().lower().startswith(".github/workflows/")
        and path.suffix.lower() in {".yml", ".yaml"}
    ]


def source_python_files(snapshot: RepositorySnapshot) -> list[Path]:
    """Return Python source files excluding tests and generated caches."""

    files: list[Path] = []
    for path in snapshot.files():
        normalized = path.as_posix().lower()
        if path.suffix == ".py" and not normalized.startswith("tests/"):
            files.append(path)
    return files
