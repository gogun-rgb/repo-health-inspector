from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def fixture_repo_path() -> Path:
    return Path(__file__).parent / "fixtures" / "sample_project"
