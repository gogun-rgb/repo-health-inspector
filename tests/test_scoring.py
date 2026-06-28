from __future__ import annotations

from pathlib import Path

from repo_health.models import Category, RuleResult, RuleStatus
from repo_health.repository_loader import load_local_repository
from repo_health.scoring import (
    analyze_repository,
    calculate_category_scores,
    calculate_evaluated_score,
    validate_rule_catalog,
)


def test_rule_catalog_category_limits() -> None:
    validate_rule_catalog()


def test_score_calculation_is_sum_of_rules(fixture_repo_path: Path) -> None:
    snapshot = load_local_repository(fixture_repo_path)
    report = analyze_repository(snapshot)

    assert report.total_score == round(sum(rule.earned_score for rule in report.rule_results), 1)


def test_skipped_rules_count_as_zero_in_raw_score(fixture_repo_path: Path) -> None:
    snapshot = load_local_repository(fixture_repo_path)
    report = analyze_repository(snapshot)

    assert report.skipped_rule_count == 8
    assert report.skipped_score == 20
    assert report.evaluated_rule_count == report.total_rule_count - report.skipped_rule_count
    assert report.total_score == 78.5
    assert report.evaluated_score == 98.1


def test_category_score_limits(fixture_repo_path: Path) -> None:
    snapshot = load_local_repository(fixture_repo_path)
    report = analyze_repository(snapshot)
    scores = calculate_category_scores(report.rule_results)

    assert {score.category for score in scores} == set(Category)
    assert all(score.max_score == 20 for score in scores)
    assert all(0 <= score.earned_score <= score.max_score for score in scores)


def test_evaluated_score_excludes_skipped_rules() -> None:
    results = [
        RuleResult(
            rule_id="X001",
            title="Passed",
            category=Category.DOCUMENTATION,
            max_score=5,
            earned_score=5,
            status=RuleStatus.PASSED,
            explanation="Passed.",
            recommendation="Keep it.",
        ),
        RuleResult(
            rule_id="X002",
            title="Warning",
            category=Category.DOCUMENTATION,
            max_score=5,
            earned_score=2.5,
            status=RuleStatus.WARNING,
            explanation="Partial.",
            recommendation="Improve it.",
        ),
        RuleResult(
            rule_id="X003",
            title="Skipped",
            category=Category.MAINTENANCE,
            max_score=10,
            earned_score=0,
            status=RuleStatus.SKIPPED,
            explanation="Unavailable.",
            recommendation="Use remote analysis.",
        ),
    ]

    assert calculate_evaluated_score(results) == 75
