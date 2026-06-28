"""Markdown and JSON report generation."""

from __future__ import annotations

import json
from pathlib import Path

from repo_health.models import AnalysisReport, ReportFormat, RuleStatus
from repo_health.utils import InvalidOutputDirectoryError, report_file_stem


def write_reports(
    report: AnalysisReport,
    *,
    output_dir: Path,
    report_format: ReportFormat,
) -> list[Path]:
    """Write the requested report files and return their paths."""

    if output_dir.exists() and not output_dir.is_dir():
        msg = f"Output path exists and is not a directory: {output_dir}"
        raise InvalidOutputDirectoryError(msg)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = report_file_stem(report.repository.owner, report.repository.name)
    written: list[Path] = []
    if report_format in {ReportFormat.MARKDOWN, ReportFormat.BOTH}:
        markdown_path = output_dir / f"{stem}-report.md"
        markdown_path.write_text(render_markdown_report(report), encoding="utf-8")
        written.append(markdown_path)
    if report_format in {ReportFormat.JSON, ReportFormat.BOTH}:
        json_path = output_dir / f"{stem}-report.json"
        payload = report.model_dump(mode="json")
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        written.append(json_path)
    return written


def render_markdown_report(report: AnalysisReport) -> str:
    """Render a human-readable Markdown report."""

    lines = [
        f"# Repository Health Report: {report.repository.display_name}",
        "",
    ]
    if report.sample_report and report.sample_report_notice:
        lines.extend([f"> **Sample report:** {report.sample_report_notice}", ""])
    lines.extend(
        [
            f"- **Repository URL:** {report.repository.url or 'Local repository'}",
            f"- **Analysis timestamp:** {report.analysis_timestamp.isoformat()}",
            f"- **Total score:** {report.total_score:.1f}/100",
            f"- **Score label:** {report.score_label}",
            "",
            "## Category Scores",
            "",
            "| Category | Score | Percentage |",
            "| --- | ---: | ---: |",
        ]
    )
    for category_score in report.category_scores:
        lines.append(
            "| "
            f"{category_score.category.value} | "
            f"{category_score.earned_score:.1f}/{category_score.max_score:.1f} | "
            f"{category_score.percentage:.1f}% |"
        )
    lines.extend(["", "## Strengths", ""])
    lines.extend(_bullet_list(report.strengths))
    lines.extend(["", "## Warnings", ""])
    lines.extend(_bullet_list(report.warnings))
    lines.extend(["", "## Prioritized Recommendations", ""])
    lines.extend(_numbered_list(report.recommendations))
    lines.extend(
        [
            "",
            "## Detailed Rule Results",
            "",
            "| Rule | Category | Status | Score | Explanation | Recommendation |",
            "| --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for result in report.rule_results:
        lines.append(
            "| "
            f"{result.rule_id} {result.title} | "
            f"{result.category.value} | "
            f"{_status_icon(result.status)} {result.status.value} | "
            f"{result.earned_score:.1f}/{result.max_score:.1f} | "
            f"{_escape_table(result.explanation)} | "
            f"{_escape_table(result.recommendation)} |"
        )
    lines.extend(["", "## Static Analysis Disclaimer", "", report.disclaimer, ""])
    return "\n".join(lines)


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def _numbered_list(items: list[str]) -> list[str]:
    return [f"{index}. {item}" for index, item in enumerate(items, start=1)]


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _status_icon(status: RuleStatus) -> str:
    if status is RuleStatus.PASSED:
        return "PASS"
    if status is RuleStatus.WARNING:
        return "WARN"
    if status is RuleStatus.FAILED:
        return "FAIL"
    return "SKIP"
