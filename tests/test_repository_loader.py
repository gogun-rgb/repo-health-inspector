from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from repo_health.repository_loader import extract_zip_archive, load_local_repository
from repo_health.utils import InvalidLocalPathError, UnsafeArchiveError


def test_extract_zip_archive_safely(tmp_path: Path) -> None:
    root = extract_zip_archive(_zip_bytes({"owner-repo/README.md": "# Hello\n"}), tmp_path)

    assert (root / "README.md").read_text(encoding="utf-8") == "# Hello\n"


def test_extract_zip_archive_rejects_unsafe_paths(tmp_path: Path) -> None:
    with pytest.raises(UnsafeArchiveError):
        extract_zip_archive(_zip_bytes({"../secret.txt": "bad"}), tmp_path)


def test_extract_zip_archive_rejects_large_uncompressed_size(tmp_path: Path) -> None:
    with pytest.raises(UnsafeArchiveError):
        extract_zip_archive(
            _zip_bytes({"owner-repo/large.txt": "too large"}),
            tmp_path,
            max_uncompressed_bytes=1,
        )


def test_snapshot_read_text_rejects_path_escape(tmp_path: Path) -> None:
    snapshot = load_local_repository(tmp_path)

    with pytest.raises(InvalidLocalPathError):
        snapshot.read_text(Path("../outside.txt"))


def _zip_bytes(members: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return buffer.getvalue()
