from __future__ import annotations

from pathlib import Path

import pytest

from repo_health.repository_loader import load_local_repository
from repo_health.scoring import analyze_repository
from repo_health.utils import InvalidLocalPathError


def test_local_repository_inspection(fixture_repo_path: Path) -> None:
    snapshot = load_local_repository(fixture_repo_path)
    report = analyze_repository(snapshot)

    assert report.repository.name == "sample_project"
    assert report.total_score >= 75
    assert any(result.status.value == "skipped" for result in report.rule_results)


def test_invalid_local_path(tmp_path: Path) -> None:
    with pytest.raises(InvalidLocalPathError):
        load_local_repository(tmp_path / "missing")
