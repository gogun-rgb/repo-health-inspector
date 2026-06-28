from __future__ import annotations

import pytest

from repo_health.repository_loader import parse_github_url
from repo_health.utils import InvalidGitHubURLError


@pytest.mark.parametrize(
    ("url", "owner", "repo"),
    [
        ("https://github.com/owner/repo", "owner", "repo"),
        ("https://github.com/owner/repo.git", "owner", "repo"),
        ("https://github.com/owner-name/repo.name/", "owner-name", "repo.name"),
    ],
)
def test_valid_github_url_parsing(url: str, owner: str, repo: str) -> None:
    parsed = parse_github_url(url)
    assert parsed.owner == owner
    assert parsed.repo == repo


@pytest.mark.parametrize(
    "url",
    [
        "https://gitlab.com/owner/repo",
        "https://github.com/owner",
        "https://github.com/owner/repo/issues",
        "not-a-url",
    ],
)
def test_invalid_github_url_rejection(url: str) -> None:
    with pytest.raises(InvalidGitHubURLError):
        parse_github_url(url)
