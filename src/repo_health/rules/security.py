"""Security and reliability scoring rules."""

from __future__ import annotations

import re
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
from repo_health.utils import contains_secret_pattern

TOKEN_PATTERN_RE = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{40,}|"
    r"sk-[A-Za-z0-9]{32,}|AKIA[0-9A-Z]{16})\b"
)

RULES: tuple[RuleDefinition, ...] = (
    RuleDefinition(
        rule_id="SEC001",
        title="No obvious committed secrets",
        category=Category.SECURITY,
        max_score=4,
        recommendation=(
            "Remove committed secrets, rotate exposed credentials, and keep real values out of Git."
        ),
    ),
    RuleDefinition(
        rule_id="SEC002",
        title=".env is ignored",
        category=Category.SECURITY,
        max_score=3,
        recommendation="Add .env to .gitignore while keeping .env.example tracked.",
    ),
    RuleDefinition(
        rule_id="SEC003",
        title="Dependency versions are constrained",
        category=Category.SECURITY,
        max_score=2,
        recommendation="Use version ranges or lock files so dependency changes are intentional.",
    ),
    RuleDefinition(
        rule_id="SEC004",
        title="Exception handling is present",
        category=Category.SECURITY,
        max_score=2,
        recommendation="Handle expected network, parsing, and filesystem errors explicitly.",
    ),
    RuleDefinition(
        rule_id="SEC005",
        title="Input validation is present",
        category=Category.SECURITY,
        max_score=2,
        recommendation="Validate URLs, paths, and external data before using them.",
    ),
    RuleDefinition(
        rule_id="SEC006",
        title="No unsafe eval usage",
        category=Category.SECURITY,
        max_score=3,
        recommendation="Avoid eval, exec, and unsafe deserialization on untrusted input.",
    ),
    RuleDefinition(
        rule_id="SEC007",
        title="No hardcoded API token patterns",
        category=Category.SECURITY,
        max_score=2,
        recommendation="Use environment variables or secret stores for tokens and API keys.",
    ),
    RuleDefinition(
        rule_id="SEC008",
        title="Security policy exists",
        category=Category.SECURITY,
        max_score=2,
        recommendation="Add SECURITY.md with vulnerability reporting guidance.",
    ),
)


def evaluate(snapshot: RepositorySnapshot) -> list[RuleResult]:
    """Evaluate security and reliability rules."""

    secret_findings = find_secret_findings(snapshot)
    token_findings = find_token_pattern_findings(snapshot)
    pyproject = pyproject_text(snapshot)
    source_text = "\n".join(snapshot.read_text(path) for path in source_python_files(snapshot))
    return [
        passed(RULES[0], "No high-confidence committed secret patterns were detected.")
        if not secret_findings
        else failed(
            RULES[0],
            f"Potential secrets detected in: {_format_findings(secret_findings)}.",
        ),
        passed(RULES[1], ".env is ignored by .gitignore.")
        if _env_is_ignored(snapshot)
        else failed(RULES[1], ".env was not found in .gitignore."),
        passed(RULES[2], "Dependency declarations include version constraints or lock files.")
        if _dependencies_are_constrained(snapshot, pyproject)
        else warning(
            RULES[2],
            "Dependency declarations do not appear version-constrained.",
            earned_score=0.5,
        ),
        passed(RULES[3], "Python source contains explicit exception handling.")
        if "try:" in source_text and "except " in source_text
        else warning(
            RULES[3],
            "Little or no explicit exception handling was detected.",
            earned_score=0.5,
        ),
        passed(RULES[4], "Input validation patterns are present.")
        if _has_input_validation(source_text)
        else warning(
            RULES[4],
            "No obvious input validation patterns were detected.",
            earned_score=0.5,
        ),
        passed(RULES[5], "No unsafe dynamic execution or deserialization was detected.")
        if not _has_unsafe_eval_usage(source_text)
        else failed(RULES[5], "Unsafe dynamic execution or deserialization was detected."),
        passed(RULES[6], "No hardcoded API token patterns were detected.")
        if not token_findings
        else failed(
            RULES[6],
            f"Hardcoded token-like values detected in: {_format_findings(token_findings)}.",
        ),
        passed(RULES[7], "SECURITY.md is present.")
        if snapshot.has_file("SECURITY.md", "SECURITY.rst")
        else warning(RULES[7], "No security policy file was found.", earned_score=0.5),
    ]


def find_secret_findings(snapshot: RepositorySnapshot) -> list[Path]:
    """Return files containing high-confidence secret-like patterns."""

    findings: list[Path] = []
    for relative, text in snapshot.text_files():
        if relative.name.lower() in {".env.example", ".env.sample"}:
            continue
        if contains_secret_pattern(text):
            findings.append(relative)
    return findings


def find_token_pattern_findings(snapshot: RepositorySnapshot) -> list[Path]:
    """Return files containing token-like values."""

    findings: list[Path] = []
    for relative, text in snapshot.text_files():
        if relative.name.lower() in {".env.example", ".env.sample"}:
            continue
        if TOKEN_PATTERN_RE.search(text):
            findings.append(relative)
    return findings


def _env_is_ignored(snapshot: RepositorySnapshot) -> bool:
    gitignore = snapshot.read_named_file(".gitignore")
    lines = {
        line.strip() for line in gitignore.splitlines() if line.strip() and not line.startswith("#")
    }
    return ".env" in lines or ".env*" in lines


def _dependencies_are_constrained(snapshot: RepositorySnapshot, pyproject: str) -> bool:
    dependency_text = "\n".join(
        [
            pyproject,
            snapshot.read_named_file("requirements.txt"),
            snapshot.read_named_file("requirements-dev.txt"),
        ]
    )
    return any(operator in dependency_text for operator in (">=", "==", "~=", "<")) or (
        snapshot.has_file(
            "uv.lock",
            "poetry.lock",
            "Pipfile.lock",
        )
    )


def _has_input_validation(source_text: str) -> bool:
    return contains_any(
        source_text,
        (
            "basemodel",
            "field_validator",
            "validator",
            "re.compile",
            "fullmatch",
            "raise valueerror",
        ),
    )


def _has_unsafe_eval_usage(source_text: str) -> bool:
    risky_patterns = (
        "ev" + "al(",
        "ex" + "ec(",
        "pickle" + "." + "loads(",
        "yaml" + "." + "load(",
    )
    return contains_any(source_text, risky_patterns)


def _format_findings(findings: list[Path]) -> str:
    return ", ".join(path.as_posix() for path in findings[:5])
