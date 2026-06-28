from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from repo_health.models import MaintenanceMetadata, RepositoryInfo
from repo_health.repository_loader import RepositorySnapshot
from repo_health.rules.maintenance import evaluate


def test_maintenance_rules_pass_with_healthy_metadata(tmp_path: Path) -> None:
    snapshot = RepositorySnapshot(
        root=tmp_path,
        info=RepositoryInfo(name="repo", owner="owner"),
        maintenance=MaintenanceMetadata(
            pushed_at=datetime(2026, 6, 1, tzinfo=UTC),
            open_issues_count=2,
            closed_issues_count=5,
            release_count=1,
            latest_release_published_at=datetime(2026, 5, 1, tzinfo=UTC),
            contributor_count=3,
            archived=False,
            description="A useful repository description.",
            topics=["python", "cli"],
            default_branch="main",
        ),
    )

    results = {result.rule_id: result for result in evaluate(snapshot)}

    assert all(result.status.value == "passed" for result in results.values())


def test_maintenance_rules_flag_inactive_or_sparse_metadata(tmp_path: Path) -> None:
    snapshot = RepositorySnapshot(
        root=tmp_path,
        info=RepositoryInfo(name="repo", owner="owner"),
        maintenance=MaintenanceMetadata(
            pushed_at=datetime(2024, 1, 1, tzinfo=UTC),
            open_issues_count=4,
            closed_issues_count=0,
            release_count=0,
            contributor_count=1,
            archived=True,
            description="",
            topics=[],
            default_branch=None,
        ),
    )

    results = {result.rule_id: result for result in evaluate(snapshot)}

    assert results["MNT001"].status.value == "failed"
    assert results["MNT002"].status.value == "warning"
    assert results["MNT003"].status.value == "failed"
    assert results["MNT004"].status.value == "warning"
    assert results["MNT005"].status.value == "failed"
    assert results["MNT008"].status.value == "skipped"
