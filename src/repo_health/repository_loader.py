"""Local and remote repository loading without executing repository code."""

from __future__ import annotations

import io
import re
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from repo_health.config import (
    DEFAULT_MAX_UNCOMPRESSED_BYTES,
    MAX_TEXT_FILE_BYTES,
    MAX_TEXT_FILES_TO_SCAN,
)
from repo_health.github_client import GitHubClient
from repo_health.models import MaintenanceMetadata, RepositoryInfo
from repo_health.utils import (
    InvalidGitHubURLError,
    InvalidLocalPathError,
    UnsafeArchiveError,
    is_probably_text_file,
    normalize_repo_path,
    safe_archive_member_name,
)

GITHUB_REPOSITORY_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)

IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}


@dataclass(frozen=True)
class ParsedGitHubURL:
    """Parsed GitHub owner and repository name."""

    owner: str
    repo: str


@dataclass
class RepositorySnapshot:
    """Read-only view of a repository tree used by rules."""

    root: Path
    info: RepositoryInfo
    maintenance: MaintenanceMetadata | None = None
    _files_cache: list[Path] | None = field(default=None, init=False, repr=False)

    def files(self) -> list[Path]:
        """Return all non-ignored files relative to the repository root."""

        if self._files_cache is None:
            files: list[Path] = []
            for path in self.root.rglob("*"):
                if not path.is_file():
                    continue
                relative = path.relative_to(self.root)
                if any(part in IGNORED_DIRECTORY_NAMES for part in relative.parts):
                    continue
                files.append(relative)
            self._files_cache = sorted(files, key=lambda item: item.as_posix().lower())
        return list(self._files_cache)

    def normalized_files(self) -> set[str]:
        """Return normalized relative file names."""

        return {normalize_repo_path(path) for path in self.files()}

    def has_file(self, *candidates: str) -> bool:
        """Return whether any candidate file exists, case-insensitively."""

        normalized = self.normalized_files()
        return any(candidate.lower().replace("\\", "/") in normalized for candidate in candidates)

    def has_directory(self, directory: str) -> bool:
        """Return whether any file exists under the requested directory."""

        prefix = directory.strip("/").lower() + "/"
        return any(name.startswith(prefix) for name in self.normalized_files())

    def find_first(self, *candidates: str) -> Path | None:
        """Return the first matching relative file path."""

        lookup = {normalize_repo_path(path): path for path in self.files()}
        for candidate in candidates:
            match = lookup.get(candidate.lower().replace("\\", "/"))
            if match is not None:
                return match
        return None

    def matching_files(self, pattern: str) -> list[Path]:
        """Return relative files matching a glob pattern."""

        return [path for path in self.files() if path.match(pattern)]

    def read_text(self, relative_path: Path, *, limit: int = MAX_TEXT_FILE_BYTES) -> str:
        """Read a repository file as UTF-8 text with replacement."""

        absolute = (self.root / relative_path).resolve()
        root = self.root.resolve()
        if root not in absolute.parents and absolute != root:
            msg = f"Path escapes repository root: {relative_path}"
            raise InvalidLocalPathError(msg)
        if absolute.stat().st_size > limit:
            return ""
        return absolute.read_text(encoding="utf-8", errors="replace")

    def read_named_file(self, *candidates: str) -> str:
        """Read the first existing candidate file."""

        match = self.find_first(*candidates)
        if match is None:
            return ""
        return self.read_text(match)

    def text_files(self, *, max_files: int = MAX_TEXT_FILES_TO_SCAN) -> Iterator[tuple[Path, str]]:
        """Yield text files for lightweight static scanning."""

        yielded = 0
        for relative in self.files():
            if yielded >= max_files:
                return
            absolute = self.root / relative
            if not is_probably_text_file(relative) or absolute.stat().st_size > MAX_TEXT_FILE_BYTES:
                continue
            yielded += 1
            yield relative, self.read_text(relative)


def parse_github_url(url: str) -> ParsedGitHubURL:
    """Parse and validate a public GitHub repository URL."""

    match = GITHUB_REPOSITORY_RE.fullmatch(url.strip())
    if match is None:
        msg = "Expected a repository URL like https://github.com/OWNER/REPOSITORY"
        raise InvalidGitHubURLError(msg)
    owner = match.group("owner")
    repo = match.group("repo")
    if owner in {".", ".."} or repo in {".", ".."}:
        msg = "GitHub owner and repository names must be explicit path segments"
        raise InvalidGitHubURLError(msg)
    return ParsedGitHubURL(owner=owner, repo=repo)


def load_local_repository(path: Path | str) -> RepositorySnapshot:
    """Create a snapshot for a local repository path."""

    root = Path(path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        msg = f"Local repository path does not exist or is not a directory: {path}"
        raise InvalidLocalPathError(msg)
    info = RepositoryInfo(name=root.name, local_path=str(root))
    return RepositorySnapshot(root=root, info=info)


@contextmanager
def load_remote_repository(
    url: str,
    *,
    token: str | None = None,
    client: GitHubClient | None = None,
) -> Iterator[RepositorySnapshot]:
    """Download a public GitHub repository archive into a temporary directory."""

    parsed = parse_github_url(url)
    github = client or GitHubClient(token=token)
    repository_info, maintenance = github.fetch_repository_metadata(parsed.owner, parsed.repo)
    archive = github.download_repository_archive(
        parsed.owner,
        parsed.repo,
        ref=repository_info.default_branch or maintenance.default_branch,
    )
    with tempfile.TemporaryDirectory(prefix="repo-health-") as temp_root:
        root = extract_zip_archive(archive, Path(temp_root))
        yield RepositorySnapshot(root=root, info=repository_info, maintenance=maintenance)


def extract_zip_archive(
    archive_bytes: bytes,
    target_dir: Path,
    *,
    max_uncompressed_bytes: int = DEFAULT_MAX_UNCOMPRESSED_BYTES,
) -> Path:
    """Safely extract a GitHub zip archive and return its top-level directory."""

    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        total_size = 0
        top_level: str | None = None
        for member_info in archive.infolist():
            member = safe_archive_member_name(member_info.filename)
            if not member.parts:
                continue
            top_level = top_level or member.parts[0]
            if member.parts[0] != top_level:
                msg = "Archive contains multiple top-level directories"
                raise UnsafeArchiveError(msg)
            total_size += member_info.file_size
            if total_size > max_uncompressed_bytes:
                msg = "Repository archive is too large after decompression"
                raise UnsafeArchiveError(msg)
        archive.extractall(target_dir)
    if top_level is None:
        msg = "Repository archive is empty"
        raise UnsafeArchiveError(msg)
    root = (target_dir / top_level).resolve()
    if not root.exists() or not root.is_dir():
        msg = "Repository archive did not contain a readable project directory"
        raise UnsafeArchiveError(msg)
    return root
