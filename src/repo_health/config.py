"""Shared configuration for repo-health-inspector."""

from __future__ import annotations

from pathlib import Path

APP_NAME = "repo-health-inspector"
CLI_NAME = "repo-health"
DEFAULT_REPORT_DIR = Path("reports")
DEFAULT_MAX_ARCHIVE_BYTES = 25 * 1024 * 1024
DEFAULT_MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_TEXT_FILE_BYTES = 512 * 1024
MAX_TEXT_FILES_TO_SCAN = 500

STATIC_ANALYSIS_DISCLAIMER = (
    "Repo Health Inspector performs lightweight static analysis. It can highlight common "
    "readiness signals, but it does not prove that a repository is bug-free, secure, "
    "maintained, or production-ready."
)
