"""Maintenance and community scoring rules."""

from __future__ import annotations

from datetime import UTC

from repo_health.models import Category, MaintenanceMetadata, RuleDefinition, RuleResult
from repo_health.repository_loader import RepositorySnapshot
from repo_health.rules._helpers import failed, passed, skipped, warning
from repo_health.utils import utc_now

RULES: tuple[RuleDefinition, ...] = (
    RuleDefinition(
        rule_id="MNT001",
        title="Recent commit activity",
        category=Category.MAINTENANCE,
        max_score=4,
        recommendation=(
            "Keep the default branch active or explain maintenance status in the README."
        ),
    ),
    RuleDefinition(
        rule_id="MNT002",
        title="Issue activity is visible",
        category=Category.MAINTENANCE,
        max_score=3,
        recommendation=(
            "Use GitHub issues to track bugs, questions, and completed maintenance work."
        ),
    ),
    RuleDefinition(
        rule_id="MNT003",
        title="Release history exists",
        category=Category.MAINTENANCE,
        max_score=3,
        recommendation="Create GitHub releases for meaningful milestones.",
    ),
    RuleDefinition(
        rule_id="MNT004",
        title="Contributor activity is visible",
        category=Category.MAINTENANCE,
        max_score=3,
        recommendation=(
            "Make contribution paths clear and acknowledge contributors when they appear."
        ),
    ),
    RuleDefinition(
        rule_id="MNT005",
        title="Repository is not archived",
        category=Category.MAINTENANCE,
        max_score=3,
        recommendation=(
            "Unarchive active projects or document that the project is intentionally archived."
        ),
    ),
    RuleDefinition(
        rule_id="MNT006",
        title="Repository description exists",
        category=Category.MAINTENANCE,
        max_score=2,
        recommendation="Add a concise GitHub repository description.",
    ),
    RuleDefinition(
        rule_id="MNT007",
        title="Repository topics exist",
        category=Category.MAINTENANCE,
        max_score=1,
        recommendation="Add relevant GitHub topics so the project is easier to discover.",
    ),
    RuleDefinition(
        rule_id="MNT008",
        title="Default branch is known",
        category=Category.MAINTENANCE,
        max_score=1,
        recommendation="Ensure the repository exposes a clear default branch.",
    ),
)


def evaluate(snapshot: RepositorySnapshot) -> list[RuleResult]:
    """Evaluate maintenance rules from GitHub metadata when available."""

    metadata = snapshot.maintenance
    if metadata is None:
        return [
            skipped(rule, "GitHub maintenance metadata is unavailable in local mode.")
            for rule in RULES
        ]
    return [
        _recent_activity_result(metadata),
        _issue_activity_result(metadata),
        _release_result(metadata),
        _contributor_result(metadata),
        _archived_result(metadata),
        _description_result(metadata),
        _topics_result(metadata),
        _default_branch_result(metadata),
    ]


def _recent_activity_result(metadata: MaintenanceMetadata) -> RuleResult:
    if metadata.pushed_at is None:
        return skipped(RULES[0], "GitHub did not provide the last pushed timestamp.")
    pushed_at = metadata.pushed_at.astimezone(UTC)
    age_days = (utc_now() - pushed_at).days
    if age_days <= 180:
        return passed(RULES[0], f"Default branch was updated {age_days} day(s) ago.")
    if age_days <= 365:
        return warning(
            RULES[0],
            f"Default branch was updated {age_days} day(s) ago.",
            earned_score=2,
        )
    return failed(
        RULES[0],
        f"Default branch appears inactive; last push was {age_days} day(s) ago.",
    )


def _issue_activity_result(metadata: MaintenanceMetadata) -> RuleResult:
    open_count = metadata.open_issues_count
    closed_count = metadata.closed_issues_count
    if open_count is None and closed_count is None:
        return skipped(RULES[1], "Issue counts were not available from the GitHub API.")
    if closed_count and closed_count > 0:
        return passed(RULES[1], f"{closed_count} closed issue(s) show maintenance history.")
    if open_count and open_count > 0:
        return warning(
            RULES[1],
            f"{open_count} open issue(s) exist but no closed issues were visible.",
            earned_score=1.5,
        )
    return warning(RULES[1], "No issue activity was visible.", earned_score=1)


def _release_result(metadata: MaintenanceMetadata) -> RuleResult:
    if metadata.release_count is None:
        return skipped(RULES[2], "Release data was not available from the GitHub API.")
    if metadata.release_count > 0:
        detail = f"{metadata.release_count} release(s) were found."
        if metadata.latest_release_published_at:
            latest = metadata.latest_release_published_at.date().isoformat()
            detail = f"{detail} Latest release: {latest}."
        return passed(RULES[2], detail)
    return failed(RULES[2], "No GitHub releases were found.")


def _contributor_result(metadata: MaintenanceMetadata) -> RuleResult:
    if metadata.contributor_count is None:
        return skipped(RULES[3], "Contributor data was not available from the GitHub API.")
    if metadata.contributor_count >= 2:
        return passed(RULES[3], f"{metadata.contributor_count} contributor(s) were found.")
    if metadata.contributor_count == 1:
        return warning(RULES[3], "One contributor was found.", earned_score=1.5)
    return failed(RULES[3], "No contributors were visible.")


def _archived_result(metadata: MaintenanceMetadata) -> RuleResult:
    if metadata.archived is None:
        return skipped(RULES[4], "Archived status was not available from the GitHub API.")
    if metadata.archived:
        return failed(RULES[4], "Repository is archived.")
    return passed(RULES[4], "Repository is not archived.")


def _description_result(metadata: MaintenanceMetadata) -> RuleResult:
    if metadata.description and len(metadata.description.strip()) >= 15:
        return passed(RULES[5], "GitHub repository description is present.")
    return warning(
        RULES[5],
        "GitHub repository description is missing or very short.",
        earned_score=0.5,
    )


def _topics_result(metadata: MaintenanceMetadata) -> RuleResult:
    if metadata.topics:
        return passed(RULES[6], f"{len(metadata.topics)} topic(s) are configured.")
    return warning(RULES[6], "No GitHub topics were found.", earned_score=0.3)


def _default_branch_result(metadata: MaintenanceMetadata) -> RuleResult:
    if metadata.default_branch:
        return passed(RULES[7], f"Default branch is {metadata.default_branch}.")
    return skipped(RULES[7], "Default branch was not available from the GitHub API.")
