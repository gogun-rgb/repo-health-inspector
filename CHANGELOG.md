# Changelog

All notable changes to repo-health-inspector are documented here.

## 0.1.0 - 2026-06-28

- Implemented the Typer and Rich powered `repo-health` CLI.
- Added remote GitHub repository inspection with safe archive download, API metadata, and static analysis.
- Added local repository inspection without network access or file uploads.
- Added transparent 100-point rule-based scoring across documentation, testing, structure, security, and maintenance.
- Added evaluated-score and skipped-rule summaries for local and limited analyses.
- Added Markdown and JSON report generation.
- Added real-world example reports generated from public GitHub repositories.
- Added pytest coverage, Ruff linting and formatting, mypy type checking, and GitHub Actions CI.
- Added package build and Twine validation support for release preparation.
