"""Testing and CI scoring rules."""

from __future__ import annotations

from repo_health.models import Category, RuleDefinition, RuleResult
from repo_health.repository_loader import RepositorySnapshot
from repo_health.rules._helpers import contains_any, failed, passed, pyproject_text, workflow_files

RULES: tuple[RuleDefinition, ...] = (
    RuleDefinition(
        rule_id="TST001",
        title="Tests directory exists",
        category=Category.TESTING,
        max_score=4,
        recommendation="Add a tests/ directory with meaningful automated tests.",
    ),
    RuleDefinition(
        rule_id="TST002",
        title="Test files exist",
        category=Category.TESTING,
        max_score=4,
        recommendation="Add pytest or unittest files that cover behavior, not only imports.",
    ),
    RuleDefinition(
        rule_id="TST003",
        title="GitHub Actions workflow exists",
        category=Category.TESTING,
        max_score=3,
        recommendation="Add a GitHub Actions workflow that runs on push and pull_request.",
    ),
    RuleDefinition(
        rule_id="TST004",
        title="Workflow runs tests",
        category=Category.TESTING,
        max_score=3,
        recommendation="Run pytest, unittest, tox, or nox from CI.",
    ),
    RuleDefinition(
        rule_id="TST005",
        title="Coverage configuration exists",
        category=Category.TESTING,
        max_score=2,
        recommendation="Configure coverage.py or pytest-cov and enforce a threshold.",
    ),
    RuleDefinition(
        rule_id="TST006",
        title="Lint configuration exists",
        category=Category.TESTING,
        max_score=2,
        recommendation="Configure a linter such as Ruff and run it in CI.",
    ),
    RuleDefinition(
        rule_id="TST007",
        title="Type-check configuration exists",
        category=Category.TESTING,
        max_score=2,
        recommendation="Configure mypy or pyright and run type checks in CI.",
    ),
)


def evaluate(snapshot: RepositorySnapshot) -> list[RuleResult]:
    """Evaluate testing and CI rules."""

    workflows = workflow_files(snapshot)
    workflow_text = "\n".join(snapshot.read_text(path) for path in workflows)
    pyproject = pyproject_text(snapshot)
    test_files = _test_files(snapshot)
    return [
        passed(RULES[0], "tests/ directory is present.")
        if snapshot.has_directory("tests")
        else failed(RULES[0], "No tests/ directory was found."),
        passed(RULES[1], f"Found {len(test_files)} test file(s).")
        if test_files
        else failed(RULES[1], "No test_*.py or *_test.py files were found."),
        passed(RULES[2], f"Found {len(workflows)} GitHub Actions workflow file(s).")
        if workflows
        else failed(RULES[2], "No workflow files were found under .github/workflows/."),
        passed(RULES[3], "A CI workflow appears to run tests.")
        if contains_any(workflow_text, ("pytest", "python -m unittest", "tox", "nox"))
        else failed(RULES[3], "No test command was detected in CI workflow files."),
        passed(RULES[4], "Coverage configuration or CI coverage command is present.")
        if _has_coverage_config(snapshot, pyproject, workflow_text)
        else failed(RULES[4], "No coverage configuration was detected."),
        passed(RULES[5], "Lint configuration or CI lint command is present.")
        if _has_lint_config(snapshot, pyproject, workflow_text)
        else failed(RULES[5], "No lint configuration was detected."),
        passed(RULES[6], "Type-check configuration or CI command is present.")
        if _has_type_check_config(snapshot, pyproject, workflow_text)
        else failed(RULES[6], "No type-check configuration was detected."),
    ]


def _test_files(snapshot: RepositorySnapshot) -> list[str]:
    return [
        path.as_posix()
        for path in snapshot.files()
        if path.suffix == ".py"
        and (path.name.startswith("test_") or path.name.endswith("_test.py"))
    ]


def _has_coverage_config(snapshot: RepositorySnapshot, pyproject: str, workflow_text: str) -> bool:
    return (
        snapshot.has_file(".coveragerc")
        or "[tool.coverage" in pyproject
        or contains_any(workflow_text, ("--cov", "coverage run", "coverage xml"))
    )


def _has_lint_config(snapshot: RepositorySnapshot, pyproject: str, workflow_text: str) -> bool:
    return (
        snapshot.has_file(".ruff.toml", "ruff.toml", ".flake8")
        or "[tool.ruff" in pyproject
        or contains_any(workflow_text, ("ruff check", "flake8", "pylint"))
    )


def _has_type_check_config(
    snapshot: RepositorySnapshot,
    pyproject: str,
    workflow_text: str,
) -> bool:
    return (
        snapshot.has_file("mypy.ini", ".mypy.ini", "pyrightconfig.json")
        or "[tool.mypy" in pyproject
        or contains_any(workflow_text, ("mypy", "pyright"))
    )
