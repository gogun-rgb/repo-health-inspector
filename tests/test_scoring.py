from __future__ import annotations

from pathlib import Path

from repo_health.models import Category
from repo_health.repository_loader import load_local_repository
from repo_health.scoring import analyze_repository, calculate_category_scores, validate_rule_catalog


def test_rule_catalog_category_limits() -> None:
    validate_rule_catalog()


def test_score_calculation_is_sum_of_rules(fixture_repo_path: Path) -> None:
    snapshot = load_local_repository(fixture_repo_path)
    report = analyze_repository(snapshot)

    assert report.total_score == round(sum(rule.earned_score for rule in report.rule_results), 1)


def test_category_score_limits(fixture_repo_path: Path) -> None:
    snapshot = load_local_repository(fixture_repo_path)
    report = analyze_repository(snapshot)
    scores = calculate_category_scores(report.rule_results)

    assert {score.category for score in scores} == set(Category)
    assert all(score.max_score == 20 for score in scores)
    assert all(0 <= score.earned_score <= score.max_score for score in scores)
