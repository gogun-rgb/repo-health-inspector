from __future__ import annotations

from pathlib import Path

from repo_health.repository_loader import load_local_repository
from repo_health.rules.documentation import evaluate as evaluate_documentation
from repo_health.rules.security import find_secret_findings
from repo_health.rules.testing import evaluate as evaluate_testing


def test_readme_rule_detection(fixture_repo_path: Path) -> None:
    snapshot = load_local_repository(fixture_repo_path)
    results = {result.rule_id: result for result in evaluate_documentation(snapshot)}

    assert results["DOC001"].status.value == "passed"
    assert results["DOC002"].earned_score == results["DOC002"].max_score


def test_test_directory_detection(fixture_repo_path: Path) -> None:
    snapshot = load_local_repository(fixture_repo_path)
    results = {result.rule_id: result for result in evaluate_testing(snapshot)}

    assert results["TST001"].status.value == "passed"
    assert results["TST002"].status.value == "passed"


def test_secret_pattern_detection(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("# Project\n", encoding="utf-8")
    token = "ghp_" + ("A" * 36)
    (project / "settings.py").write_text(f'API_TOKEN = "{token}"\n', encoding="utf-8")

    snapshot = load_local_repository(project)

    assert [path.as_posix() for path in find_secret_findings(snapshot)] == ["settings.py"]
