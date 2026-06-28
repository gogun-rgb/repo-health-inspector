from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from repo_health.cli import app

runner = CliRunner()


def test_cli_version_smoke() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "repo-health" in result.output


def test_cli_rules_smoke() -> None:
    result = runner.invoke(app, ["rules"])

    assert result.exit_code == 0
    assert "DOC001" in result.output


def test_cli_inspect_local_smoke(fixture_repo_path: Path, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "inspect-local",
            str(fixture_repo_path),
            "--format",
            "both",
            "--output",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Saved report" in result.output
    assert list(tmp_path.glob("*-report.md"))
    assert list(tmp_path.glob("*-report.json"))


def test_cli_inspect_rejects_invalid_github_url() -> None:
    result = runner.invoke(app, ["inspect", "not-a-url"])

    assert result.exit_code == 2
    assert "Expected a repository URL" in result.output


def test_cli_fail_under_exits_with_one(fixture_repo_path: Path, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "inspect-local",
            str(fixture_repo_path),
            "--output",
            str(tmp_path),
            "--fail-under",
            "90",
        ],
    )

    assert result.exit_code == 1
    assert "below fail-under threshold" in result.output
