"""Project structure scoring rules."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from repo_health.models import Category, RuleDefinition, RuleResult
from repo_health.repository_loader import RepositorySnapshot
from repo_health.rules._helpers import (
    contains_any,
    failed,
    passed,
    pyproject_text,
    source_python_files,
    warning,
)

RULES: tuple[RuleDefinition, ...] = (
    RuleDefinition(
        rule_id="STR001",
        title="Source directory structure exists",
        category=Category.STRUCTURE,
        max_score=4,
        recommendation="Use a clear package layout such as src/package_name/.",
    ),
    RuleDefinition(
        rule_id="STR002",
        title="Dependency manifest exists",
        category=Category.STRUCTURE,
        max_score=3,
        recommendation=(
            "Add pyproject.toml, requirements.txt, setup.cfg, or an equivalent manifest."
        ),
    ),
    RuleDefinition(
        rule_id="STR003",
        title=".gitignore exists",
        category=Category.STRUCTURE,
        max_score=2,
        recommendation=(
            "Add .gitignore entries for caches, virtualenvs, secrets, and build outputs."
        ),
    ),
    RuleDefinition(
        rule_id="STR004",
        title="Example environment file exists",
        category=Category.STRUCTURE,
        max_score=2,
        recommendation=(
            "Add .env.example or .env.sample documenting optional environment variables."
        ),
    ),
    RuleDefinition(
        rule_id="STR005",
        title="Modular Python organization exists",
        category=Category.STRUCTURE,
        max_score=3,
        recommendation=(
            "Split non-trivial behavior into focused modules instead of one large script."
        ),
    ),
    RuleDefinition(
        rule_id="STR006",
        title="Package metadata exists",
        category=Category.STRUCTURE,
        max_score=3,
        recommendation=(
            "Populate [project] metadata such as name, version, description, and Python support."
        ),
    ),
    RuleDefinition(
        rule_id="STR007",
        title="Dependencies are declared",
        category=Category.STRUCTURE,
        max_score=2,
        recommendation="Declare runtime dependencies in pyproject.toml or requirements files.",
    ),
    RuleDefinition(
        rule_id="STR008",
        title="Command-line entry point exists",
        category=Category.STRUCTURE,
        max_score=1,
        recommendation="Expose CLI tools through [project.scripts] or equivalent entry points.",
    ),
)


def evaluate(snapshot: RepositorySnapshot) -> list[RuleResult]:
    """Evaluate project structure rules."""

    pyproject = pyproject_text(snapshot)
    source_files = source_python_files(snapshot)
    return [
        _source_layout_result(snapshot),
        passed(RULES[1], "A dependency manifest is present.")
        if snapshot.has_file(
            "pyproject.toml",
            "requirements.txt",
            "setup.cfg",
            "setup.py",
            "Pipfile",
        )
        else failed(RULES[1], "No Python dependency manifest was found."),
        passed(RULES[2], ".gitignore is present.")
        if snapshot.has_file(".gitignore")
        else failed(RULES[2], ".gitignore was not found."),
        passed(RULES[3], "An example environment file is present.")
        if snapshot.has_file(".env.example", ".env.sample", "env.example")
        else warning(RULES[3], "No example environment file was found.", earned_score=0.5),
        _modular_result(source_files),
        passed(RULES[5], "pyproject.toml contains project metadata.")
        if _has_project_metadata(pyproject)
        else failed(RULES[5], "Package metadata was incomplete or missing."),
        passed(RULES[6], "Runtime dependencies are declared.")
        if _has_dependency_declarations(snapshot, pyproject)
        else failed(RULES[6], "No runtime dependency declarations were detected."),
        passed(RULES[7], "A command-line script entry point is declared.")
        if contains_any(pyproject, ("[project.scripts]", "[project.entry-points"))
        else warning(RULES[7], "No CLI entry point was detected.", earned_score=0.3),
    ]


def _source_layout_result(snapshot: RepositorySnapshot) -> RuleResult:
    normalized = snapshot.normalized_files()
    src_packages = [
        name for name in normalized if name.startswith("src/") and name.endswith("/__init__.py")
    ]
    top_level_packages = [
        name
        for name in normalized
        if "/" in name and not name.startswith(("tests/", "src/")) and name.endswith("/__init__.py")
    ]
    if src_packages:
        return passed(RULES[0], "A src/ package layout is present.")
    if top_level_packages:
        return warning(RULES[0], "A top-level package layout is present.", earned_score=2.5)
    return failed(RULES[0], "No importable Python package layout was detected.")


def _modular_result(source_files: Sequence[Path]) -> RuleResult:
    count = len(source_files)
    if count >= 4:
        return passed(RULES[4], f"Found {count} Python source files outside tests.")
    if count >= 2:
        return warning(RULES[4], f"Only {count} Python source files were found.", earned_score=1.5)
    return failed(RULES[4], "No modular Python source organization was detected.")


def _has_project_metadata(pyproject: str) -> bool:
    required = ("[project]", "name =", "version =", "description =", "requires-python")
    return all(item in pyproject for item in required)


def _has_dependency_declarations(snapshot: RepositorySnapshot, pyproject: str) -> bool:
    if "dependencies =" in pyproject or "[project.optional-dependencies]" in pyproject:
        return True
    return snapshot.has_file("requirements.txt", "requirements-dev.txt")
