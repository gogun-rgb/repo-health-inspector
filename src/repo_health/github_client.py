"""Small GitHub API client used by the CLI."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

import httpx

from repo_health.config import DEFAULT_MAX_ARCHIVE_BYTES
from repo_health.models import MaintenanceMetadata, RepositoryInfo
from repo_health.utils import (
    ArchiveTooLargeError,
    GitHubAPIError,
    MalformedAPIResponseError,
    NetworkFailureError,
    RateLimitError,
    RepositoryNotFoundError,
)

GITHUB_API_URL = "https://api.github.com"


class GitHubClient:
    """Minimal GitHub REST client with explicit error mapping."""

    def __init__(
        self,
        *,
        token: str | None = None,
        timeout: float = 20.0,
        max_archive_bytes: int = DEFAULT_MAX_ARCHIVE_BYTES,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._token = token
        self._timeout = timeout
        self._max_archive_bytes = max_archive_bytes
        self._transport = transport

    def fetch_repository_metadata(
        self,
        owner: str,
        repo: str,
    ) -> tuple[RepositoryInfo, MaintenanceMetadata]:
        """Fetch repository and maintenance metadata from GitHub."""

        repository = self._get_json(f"/repos/{owner}/{repo}")
        if not isinstance(repository, dict):
            msg = "GitHub repository response was not an object"
            raise MalformedAPIResponseError(msg)

        repo_name = _required_str(repository, "name")
        repo_owner = _nested_required_str(repository, ("owner", "login"))
        html_url = _required_str(repository, "html_url")
        default_branch = _optional_str(repository, "default_branch")

        closed_issues_count = self._fetch_closed_issue_count(owner, repo)
        release_count, latest_release_published_at = self._fetch_release_summary(owner, repo)
        contributor_count = self._fetch_contributor_count(owner, repo)

        info = RepositoryInfo(
            owner=repo_owner,
            name=repo_name,
            url=html_url,
            default_branch=default_branch,
        )
        maintenance = MaintenanceMetadata(
            pushed_at=_parse_datetime(repository.get("pushed_at")),
            open_issues_count=_optional_int(repository, "open_issues_count"),
            closed_issues_count=closed_issues_count,
            release_count=release_count,
            latest_release_published_at=latest_release_published_at,
            contributor_count=contributor_count,
            archived=_optional_bool(repository, "archived"),
            description=_optional_str(repository, "description"),
            topics=_optional_str_list(repository, "topics"),
            default_branch=default_branch,
            limited=False,
        )
        return info, maintenance

    def download_repository_archive(self, owner: str, repo: str, *, ref: str | None) -> bytes:
        """Download a repository zip archive with a hard byte limit."""

        suffix = f"/repos/{owner}/{repo}/zipball"
        if ref:
            suffix = f"{suffix}/{ref}"
        downloaded = bytearray()
        try:
            with self._client() as client, client.stream("GET", suffix) as response:
                self._raise_for_status(response)
                for chunk in response.iter_bytes():
                    downloaded.extend(chunk)
                    if len(downloaded) > self._max_archive_bytes:
                        msg = "Repository archive exceeds the configured download limit"
                        raise ArchiveTooLargeError(msg)
        except httpx.HTTPError as exc:
            msg = f"Network failure while downloading repository archive: {exc}"
            raise NetworkFailureError(msg) from exc
        return bytes(downloaded)

    def _fetch_closed_issue_count(self, owner: str, repo: str) -> int | None:
        query = f"repo:{owner}/{repo} type:issue state:closed"
        try:
            payload = self._get_json("/search/issues", params={"q": query, "per_page": "1"})
        except GitHubAPIError:
            return None
        if isinstance(payload, Mapping) and isinstance(payload.get("total_count"), int):
            return int(payload["total_count"])
        return None

    def _fetch_release_summary(self, owner: str, repo: str) -> tuple[int | None, datetime | None]:
        try:
            payload = self._get_json(f"/repos/{owner}/{repo}/releases", params={"per_page": "100"})
        except RepositoryNotFoundError:
            return 0, None
        except GitHubAPIError:
            return None, None
        if not isinstance(payload, list):
            return None, None
        latest = None
        if payload and isinstance(payload[0], Mapping):
            latest = _parse_datetime(payload[0].get("published_at"))
        return len(payload), latest

    def _fetch_contributor_count(self, owner: str, repo: str) -> int | None:
        try:
            payload = self._get_json(
                f"/repos/{owner}/{repo}/contributors",
                params={"per_page": "100", "anon": "false"},
            )
        except GitHubAPIError:
            return None
        if isinstance(payload, list):
            return len(payload)
        return None

    def _get_json(self, path: str, *, params: Mapping[str, str] | None = None) -> Any:
        try:
            with self._client() as client:
                response = client.get(path, params=params)
                self._raise_for_status(response)
                return response.json()
        except ValueError as exc:
            msg = "GitHub returned malformed JSON"
            raise MalformedAPIResponseError(msg) from exc
        except httpx.HTTPError as exc:
            msg = f"Network failure while calling GitHub: {exc}"
            raise NetworkFailureError(msg) from exc

    def _client(self) -> httpx.Client:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "repo-health-inspector",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return httpx.Client(
            base_url=GITHUB_API_URL,
            headers=headers,
            follow_redirects=True,
            timeout=self._timeout,
            transport=self._transport,
        )

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        message = _response_message(response)
        if response.status_code == 404:
            raise RepositoryNotFoundError("Repository not found or not accessible")
        remaining = response.headers.get("X-RateLimit-Remaining")
        if response.status_code in {403, 429} and (
            remaining == "0" or "rate limit" in message.lower()
        ):
            raise RateLimitError("GitHub API rate limit exceeded")
        msg = f"GitHub API request failed with HTTP {response.status_code}: {message}"
        raise GitHubAPIError(msg)


def _response_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:200]
    if isinstance(payload, Mapping):
        message = payload.get("message")
        if isinstance(message, str):
            return message
    return response.text[:200]


def _required_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        msg = f"GitHub response missing required string field: {key}"
        raise MalformedAPIResponseError(msg)
    return value


def _nested_required_str(payload: Mapping[str, Any], keys: tuple[str, str]) -> str:
    outer = payload.get(keys[0])
    if not isinstance(outer, Mapping):
        msg = f"GitHub response missing required object field: {keys[0]}"
        raise MalformedAPIResponseError(msg)
    return _required_str(outer, keys[1])


def _optional_str(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) and value else None


def _optional_int(payload: Mapping[str, Any], key: str) -> int | None:
    value = payload.get(key)
    return value if isinstance(value, int) else None


def _optional_bool(payload: Mapping[str, Any], key: str) -> bool | None:
    value = payload.get(key)
    return value if isinstance(value, bool) else None


def _optional_str_list(payload: Mapping[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
