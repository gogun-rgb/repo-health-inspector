from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_health.models import AnalysisReport, ReportFormat
from repo_health.report_generator import render_markdown_report, write_reports
from repo_health.repository_loader import load_local_repository
from repo_health.scoring import analyze_repository
from repo_health.utils import InvalidOutputDirectoryError


def test_report_generation_markdown_and_json(fixture_repo_path: Path, tmp_path: Path) -> None:
    report = analyze_repository(load_local_repository(fixture_repo_path))

    paths = write_reports(report, output_dir=tmp_path, report_format=ReportFormat.BOTH)

    assert {path.suffix for path in paths} == {".md", ".json"}
    payload = json.loads(next(path for path in paths if path.suffix == ".json").read_text())
    AnalysisReport.model_validate(payload)
    markdown = next(path for path in paths if path.suffix == ".md").read_text()
    assert "Static Analysis Disclaimer" in markdown


def test_sample_report_notice_renders(fixture_repo_path: Path) -> None:
    report = analyze_repository(load_local_repository(fixture_repo_path)).with_sample_notice(
        "This is a sample report generated from a fixture."
    )

    markdown = render_markdown_report(report)

    assert "**Sample report:**" in markdown
    assert report.sample_report is True


def test_report_generation_rejects_file_output_path(
    fixture_repo_path: Path,
    tmp_path: Path,
) -> None:
    report = analyze_repository(load_local_repository(fixture_repo_path))
    output_file = tmp_path / "not-a-directory"
    output_file.write_text("content", encoding="utf-8")

    with pytest.raises(InvalidOutputDirectoryError):
        write_reports(report, output_dir=output_file, report_format=ReportFormat.JSON)
