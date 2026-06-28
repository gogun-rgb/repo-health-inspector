from __future__ import annotations

import tomllib
from importlib.metadata import entry_points
from pathlib import Path

from repo_health import __version__


def test_project_metadata_version_and_author_are_consistent() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]

    assert project["version"] == __version__
    assert project["authors"] == [{"name": "Go Geon", "email": "gogun000209@gmail.com"}]
    assert project["license"]["text"] == "MIT"


def test_console_script_entry_point_is_registered() -> None:
    scripts = entry_points(group="console_scripts")
    repo_health_scripts = [script for script in scripts if script.name == "repo-health"]

    assert repo_health_scripts
    assert repo_health_scripts[0].value == "repo_health.cli:app"
