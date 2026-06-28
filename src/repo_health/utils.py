"""General helpers and domain exceptions."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath


class RepoHealthError(Exception):
    """Base exception for clean CLI error handling."""


class InvalidGitHubURLError(RepoHealthError):
    """Raised when a GitHub repository URL cannot be parsed safely."""


class RepositoryNotFoundError(RepoHealthError):
    """Raised when GitHub reports that a repository cannot be found."""


class RateLimitError(RepoHealthError):
    """Raised when the GitHub API rate limit prevents inspection."""


class GitHubAPIError(RepoHealthError):
    """Raised for non-rate-limit GitHub API failures."""


class NetworkFailureError(RepoHealthError):
    """Raised for connection failures and timeouts."""


class MalformedAPIResponseError(RepoHealthError):
    """Raised when GitHub returns data that does not match expected shapes."""


class ArchiveTooLargeError(RepoHealthError):
    """Raised when a downloaded archive exceeds configured size limits."""


class UnsafeArchiveError(RepoHealthError):
    """Raised when an archive contains unsafe paths or unexpected layout."""


class InvalidLocalPathError(RepoHealthError):
    """Raised when a local repository path is invalid."""


class InvalidOutputDirectoryError(RepoHealthError):
    """Raised when reports cannot be written to the requested output directory."""


SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password|passwd|private[_-]?key)\b\s*[:=]\s*"
    r"['\"]?([A-Za-z0-9_./+=-]{16,})['\"]?"
)
HIGH_CONFIDENCE_SECRET_RES = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),
)


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(tz=UTC)


def score_label(score: float) -> str:
    """Return the human score label for a 0-100 score."""

    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Strong"
    if score >= 60:
        return "Fair"
    if score >= 40:
        return "Needs work"
    return "Poor"


def normalize_repo_path(path: Path) -> str:
    """Normalize a path for repository-wide static matching."""

    normalized = path.as_posix()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lower()


def is_probably_text_file(path: Path) -> bool:
    """Return whether a file extension is suitable for lightweight text scanning."""

    text_suffixes = {
        "",
        ".cfg",
        ".css",
        ".env",
        ".example",
        ".gitignore",
        ".ini",
        ".json",
        ".lock",
        ".md",
        ".py",
        ".rst",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
    if path.name.lower() in {".gitignore", ".env", ".env.example", "license", "makefile"}:
        return True
    return path.suffix.lower() in text_suffixes


def contains_secret_pattern(text: str) -> bool:
    """Detect high-confidence committed secret patterns in a text blob."""

    if any(pattern.search(text) for pattern in HIGH_CONFIDENCE_SECRET_RES):
        return True
    for match in SECRET_ASSIGNMENT_RE.finditer(text):
        value = match.group(2)
        if not value.lower().startswith(("example", "sample", "changeme", "placeholder")):
            return True
    return False


def safe_archive_member_name(name: str) -> PurePosixPath:
    """Validate and normalize a zip archive member path."""

    normalized = name.replace("\\", "/")
    member = PurePosixPath(normalized)
    if member.is_absolute() or ".." in member.parts or ":" in normalized:
        msg = f"Unsafe archive member path: {name}"
        raise UnsafeArchiveError(msg)
    return member


def report_file_stem(owner: str | None, name: str) -> str:
    """Return a stable report filename stem."""

    pieces = [owner, name] if owner else ["local", name]
    raw = "-".join(piece for piece in pieces if piece)
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-").lower()
