"""Transparent rule-based scoring engine."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from repo_health import __version__
from repo_health.config import APP_NAME, STATIC_ANALYSIS_DISCLAIMER
from repo_health.models import AnalysisReport, Category, CategoryScore, RuleResult, RuleStatus
from repo_health.repository_loader import RepositorySnapshot
from repo_health.rules import all_rule_definitions, evaluate_all
from repo_health.utils import score_label, utc_now

CATEGORY_MAX_SCORE = 20.0


def analyze_repository(
    snapshot: RepositorySnapshot,
    *,
    generated_at: datetime | None = None,
) -> AnalysisReport:
    """Evaluate all rules and return a reproducible report.

    Skipped rules receive zero points in the raw ``total_score``. The
    ``evaluated_score`` field reports performance across non-skipped rules only,
    which helps local analyses stay readable when GitHub-only metadata is absent.
    """

    rule_results = evaluate_all(snapshot)
    category_scores = calculate_category_scores(rule_results)
    total_score = round(sum(result.earned_score for result in rule_results), 1)
    evaluated_score = calculate_evaluated_score(rule_results)
    skipped_rule_count = sum(1 for result in rule_results if result.status is RuleStatus.SKIPPED)
    skipped_score = round(
        sum(result.max_score for result in rule_results if result.status is RuleStatus.SKIPPED),
        1,
    )
    strengths = _build_strengths(rule_results)
    warnings = _build_warnings(rule_results)
    recommendations = _build_recommendations(rule_results)
    generated_by = f"{APP_NAME} {__version__}"
    return AnalysisReport(
        repository=snapshot.info,
        analysis_timestamp=generated_at or utc_now(),
        total_score=total_score,
        score_label=score_label(total_score),
        evaluated_score=evaluated_score,
        evaluated_score_label=score_label(evaluated_score),
        evaluated_rule_count=len(rule_results) - skipped_rule_count,
        skipped_rule_count=skipped_rule_count,
        total_rule_count=len(rule_results),
        skipped_score=skipped_score,
        category_scores=category_scores,
        strengths=strengths,
        warnings=warnings,
        recommendations=recommendations,
        rule_results=rule_results,
        disclaimer=STATIC_ANALYSIS_DISCLAIMER,
        generated_by=generated_by,
        report_notes=_build_report_notes(generated_by),
    )


def calculate_category_scores(rule_results: list[RuleResult]) -> list[CategoryScore]:
    """Aggregate rule scores by category."""

    earned_by_category: dict[Category, float] = defaultdict(float)
    max_by_category: dict[Category, float] = defaultdict(float)
    for result in rule_results:
        earned_by_category[result.category] += result.earned_score
        max_by_category[result.category] += result.max_score

    scores: list[CategoryScore] = []
    for category in Category:
        max_score = max_by_category.get(category, CATEGORY_MAX_SCORE)
        scores.append(
            CategoryScore(
                category=category,
                earned_score=round(earned_by_category.get(category, 0.0), 1),
                max_score=round(max_score, 1),
            )
        )
    return scores


def calculate_evaluated_score(rule_results: list[RuleResult]) -> float:
    """Return the percentage earned from non-skipped rules only."""

    evaluated = [result for result in rule_results if result.status is not RuleStatus.SKIPPED]
    evaluated_max = sum(result.max_score for result in evaluated)
    if evaluated_max == 0:
        return 0
    evaluated_earned = sum(result.earned_score for result in evaluated)
    return round((evaluated_earned / evaluated_max) * 100, 1)


def validate_rule_catalog() -> None:
    """Ensure the rule catalog stays at exactly 20 points per category."""

    totals: dict[Category, float] = defaultdict(float)
    ids: set[str] = set()
    for definition in all_rule_definitions():
        if definition.rule_id in ids:
            msg = f"Duplicate rule ID: {definition.rule_id}"
            raise ValueError(msg)
        ids.add(definition.rule_id)
        totals[definition.category] += definition.max_score
    for category in Category:
        if round(totals[category], 5) != CATEGORY_MAX_SCORE:
            msg = f"{category.value} rules must total 20 points; got {totals[category]}"
            raise ValueError(msg)


def _build_strengths(rule_results: list[RuleResult]) -> list[str]:
    passed = sorted(
        [result for result in rule_results if result.status is RuleStatus.PASSED],
        key=lambda result: (-result.earned_score, result.rule_id),
    )
    if not passed:
        return ["No strengths were detected by the configured static checks."]
    return [f"{result.title}: {result.explanation}" for result in passed[:8]]


def _build_warnings(rule_results: list[RuleResult]) -> list[str]:
    flagged = [
        result
        for result in rule_results
        if result.status in {RuleStatus.WARNING, RuleStatus.FAILED}
    ]
    if not flagged:
        return ["No warnings were detected by the configured static checks."]
    return [f"{result.title}: {result.explanation}" for result in flagged]


def _build_recommendations(rule_results: list[RuleResult]) -> list[str]:
    flagged = [
        result
        for result in rule_results
        if result.status in {RuleStatus.WARNING, RuleStatus.FAILED, RuleStatus.SKIPPED}
    ]
    prioritized = sorted(
        flagged,
        key=lambda result: (-(result.max_score - result.earned_score), result.rule_id),
    )
    if not prioritized:
        return ["Keep the current quality signals healthy as the project evolves."]
    return [f"[{result.rule_id}] {result.recommendation}" for result in prioritized[:12]]


def _build_report_notes(generated_by: str) -> list[str]:
    return [
        f"Generated by {generated_by}.",
        (
            "This report represents the repository state at the recorded analysis timestamp; "
            "scores can change when the repository changes."
        ),
        "The analysis is based on lightweight static checks and GitHub metadata when available.",
        (
            "Skipped rules earn 0 points in the raw score; the evaluated score is calculated "
            "from non-skipped rules only."
        ),
    ]
