from __future__ import annotations

import io
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
import pytest

from repo_health.github_client import GitHubClient
from repo_health.utils import ArchiveTooLargeError, RateLimitError, RepositoryNotFoundError


def test_github_client_fetches_metadata_with_mocked_responses() -> None:
    client = GitHubClient(transport=httpx.MockTransport(_metadata_handler))

    info, metadata = client.fetch_repository_metadata("owner", "repo")

    assert info.display_name == "owner/repo"
    assert metadata.open_issues_count == 2
    assert metadata.closed_issues_count == 5
    assert metadata.release_count == 1
    assert metadata.contributor_count == 2
    assert metadata.default_branch == "main"


def test_github_rate_limit_handling() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={"message": "API rate limit exceeded"},
            headers={"X-RateLimit-Remaining": "0"},
            request=request,
        )

    client = GitHubClient(transport=httpx.MockTransport(handler))

    with pytest.raises(RateLimitError):
        client.fetch_repository_metadata("owner", "repo")


def test_github_repository_not_found_handling() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"}, request=request)

    client = GitHubClient(transport=httpx.MockTransport(handler))

    with pytest.raises(RepositoryNotFoundError):
        client.fetch_repository_metadata("owner", "missing")


def test_github_client_downloads_archive_with_limit() -> None:
    archive = _zip_bytes({"owner-repo/README.md": "# Hello\n"})

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/owner/repo/zipball/main"
        return httpx.Response(200, content=archive, request=request)

    client = GitHubClient(transport=httpx.MockTransport(handler), max_archive_bytes=1024)

    downloaded = client.download_repository_archive("owner", "repo", ref="main")

    assert zipfile.is_zipfile(io.BytesIO(downloaded))


def test_github_client_rejects_oversized_archive() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 20, request=request)

    client = GitHubClient(transport=httpx.MockTransport(handler), max_archive_bytes=5)

    with pytest.raises(ArchiveTooLargeError):
        client.download_repository_archive("owner", "repo", ref=None)


def _metadata_handler(request: httpx.Request) -> httpx.Response:
    routes: dict[str, Callable[[httpx.Request], httpx.Response]] = {
        "/repos/owner/repo": _repo_response,
        "/search/issues": _closed_issues_response,
        "/repos/owner/repo/releases": _releases_response,
        "/repos/owner/repo/contributors": _contributors_response,
    }
    handler = routes.get(request.url.path)
    if handler is None:
        return httpx.Response(404, json={"message": "Not Found"}, request=request)
    return handler(request)


def _repo_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "name": "repo",
            "owner": {"login": "owner"},
            "html_url": "https://github.com/owner/repo",
            "default_branch": "main",
            "pushed_at": datetime(2026, 6, 1, tzinfo=UTC).isoformat(),
            "open_issues_count": 2,
            "archived": False,
            "description": "A useful repository description.",
            "topics": ["python", "cli"],
        },
        request=request,
    )


def _closed_issues_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"total_count": 5}, request=request)


def _releases_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json=[{"published_at": "2026-05-01T00:00:00Z"}],
        request=request,
    )


def _contributors_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=[{"login": "one"}, {"login": "two"}], request=request)


def _zip_bytes(members: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return buffer.getvalue()
