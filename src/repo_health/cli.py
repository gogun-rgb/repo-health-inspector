"""Typer command-line interface for repo-health-inspector."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from repo_health import __version__
from repo_health.config import CLI_NAME, DEFAULT_REPORT_DIR
from repo_health.models import AnalysisReport, ReportFormat, RuleResult, RuleStatus
from repo_health.report_generator import write_reports
from repo_health.repository_loader import load_local_repository, load_remote_repository
from repo_health.rules import all_rule_definitions
from repo_health.scoring import analyze_repository, validate_rule_catalog
from repo_health.utils import RepoHealthError

console = Console()

app = typer.Typer(
    name=CLI_NAME,
    help="Analyze GitHub repository health and portfolio readiness.",
    no_args_is_help=True,
)


@app.command("inspect")
def inspect_command(
    repository_url: Annotated[str, typer.Argument(help="GitHub repository URL to inspect.")],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Directory where report files will be written.",
        ),
    ] = DEFAULT_REPORT_DIR,
    report_format: Annotated[
        ReportFormat,
        typer.Option(
            "--format",
            help="Report format to generate.",
            case_sensitive=False,
        ),
    ] = ReportFormat.MARKDOWN,
    token: Annotated[
        str | None,
        typer.Option(
            "--token",
            envvar="GITHUB_TOKEN",
            help="GitHub token for higher API limits or private-accessible repositories.",
        ),
    ] = None,
    fail_under: Annotated[
        int | None,
        typer.Option(
            "--fail-under",
            min=0,
            max=100,
            help="Exit with code 1 if the total score is below this threshold.",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            help="Show raw exception details when an error occurs.",
        ),
    ] = False,
) -> None:
    """Inspect a public GitHub repository."""

    try:
        with (
            console.status("Fetching repository data from GitHub...", spinner="dots"),
            load_remote_repository(repository_url, token=token) as snapshot,
        ):
            report = analyze_repository(snapshot)
        _finish_report(report, output=output, report_format=report_format, fail_under=fail_under)
    except Exception as exc:
        _handle_cli_exception(exc, verbose=verbose)


@app.command("inspect-local")
def inspect_local_command(
    path: Annotated[Path, typer.Argument(help="Local repository path to inspect.")],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Directory where report files will be written.",
        ),
    ] = DEFAULT_REPORT_DIR,
    report_format: Annotated[
        ReportFormat,
        typer.Option(
            "--format",
            help="Report format to generate.",
            case_sensitive=False,
        ),
    ] = ReportFormat.MARKDOWN,
    fail_under: Annotated[
        int | None,
        typer.Option(
            "--fail-under",
            min=0,
            max=100,
            help="Exit with code 1 if the total score is below this threshold.",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            help="Show raw exception details when an error occurs.",
        ),
    ] = False,
) -> None:
    """Inspect a local repository without contacting GitHub."""

    try:
        with console.status("Inspecting local repository...", spinner="dots"):
            snapshot = load_local_repository(path)
            report = analyze_repository(snapshot)
        _finish_report(report, output=output, report_format=report_format, fail_under=fail_under)
    except Exception as exc:
        _handle_cli_exception(exc, verbose=verbose)


@app.command("rules")
def rules_command() -> None:
    """Show the scoring rules and their point values."""

    validate_rule_catalog()
    table = Table(title="Repo Health Scoring Rules")
    table.add_column("Rule", style="bold")
    table.add_column("Category")
    table.add_column("Max", justify="right")
    table.add_column("Title")
    table.add_column("Recommendation")
    for rule in all_rule_definitions():
        table.add_row(
            rule.rule_id,
            escape(rule.category.value),
            f"{rule.max_score:.1f}",
            escape(rule.title),
            escape(rule.recommendation),
        )
    console.print(table)


@app.command("version")
def version_command() -> None:
    """Show the installed version."""

    console.print(f"{CLI_NAME} {__version__}")


def _finish_report(
    report: AnalysisReport,
    *,
    output: Path,
    report_format: ReportFormat,
    fail_under: int | None,
) -> None:
    _print_summary(report)
    written = write_reports(report, output_dir=output, report_format=report_format)
    for path in written:
        console.print(f"[green]Saved report:[/] {path.resolve()}")
    if fail_under is not None and report.total_score < fail_under:
        console.print(
            f"[red]Score {report.total_score:.1f} is below fail-under threshold {fail_under}.[/]"
        )
        raise typer.Exit(1)


def _print_summary(report: AnalysisReport) -> None:
    panel_style = _score_style(report.total_score)
    console.print(
        Panel.fit(
            f"[bold]{report.repository.display_name}[/]\n"
            f"Raw score: [bold]{report.total_score:.1f}/100[/] ({report.score_label})\n"
            f"Evaluated score: [bold]{report.evaluated_score:.1f}%[/] "
            f"({report.evaluated_score_label})\n"
            f"Skipped rules: [bold]{report.skipped_rule_count}/{report.total_rule_count}[/]",
            title="Repository Health",
            border_style=panel_style,
        )
    )
    category_table = Table(title="Category Scores")
    category_table.add_column("Category")
    category_table.add_column("Score", justify="right")
    category_table.add_column("Percent", justify="right")
    for category_score in report.category_scores:
        category_table.add_row(
            category_score.category.value,
            f"{category_score.earned_score:.1f}/{category_score.max_score:.1f}",
            f"{category_score.percentage:.1f}%",
        )
    console.print(category_table)
    _print_rule_group("Passed checks", report.rule_results, RuleStatus.PASSED, "green")
    _print_rule_group("Warnings", report.rule_results, RuleStatus.WARNING, "yellow")
    _print_rule_group("Failures", report.rule_results, RuleStatus.FAILED, "red")
    _print_rule_group("Skipped checks", report.rule_results, RuleStatus.SKIPPED, "cyan")
    if report.skipped_rule_count:
        console.print("[cyan]Skipped rules count as 0 points in the raw score.[/]")


def _print_rule_group(
    title: str,
    results: list[RuleResult],
    status: RuleStatus,
    style: str,
) -> None:
    matching = [result for result in results if result.status is status]
    console.print(f"[{style}]{title}: {len(matching)}[/]")
    for result in matching[:8]:
        console.print(
            f"  [{style}]{result.rule_id}[/] {result.title} "
            f"({result.earned_score:.1f}/{result.max_score:.1f})"
        )
    if len(matching) > 8:
        console.print(f"  [{style}]...and {len(matching) - 8} more[/]")


def _score_style(score: float) -> str:
    if score >= 75:
        return "green"
    if score >= 60:
        return "yellow"
    return "red"


def _handle_cli_exception(exc: Exception, *, verbose: bool) -> NoReturn:
    if isinstance(exc, typer.Exit):
        raise exc
    if verbose:
        console.print_exception(show_locals=False)
    elif isinstance(exc, RepoHealthError):
        console.print(f"[red]Error:[/] {exc}")
    else:
        console.print(f"[red]Unexpected error:[/] {exc}")
    raise typer.Exit(2) from exc
