"""Rule catalog and evaluators."""

from __future__ import annotations

from collections.abc import Callable

from repo_health.models import RuleDefinition, RuleResult
from repo_health.repository_loader import RepositorySnapshot
from repo_health.rules import documentation, maintenance, security, structure, testing

Evaluator = Callable[[RepositorySnapshot], list[RuleResult]]

EVALUATORS: tuple[Evaluator, ...] = (
    documentation.evaluate,
    testing.evaluate,
    structure.evaluate,
    security.evaluate,
    maintenance.evaluate,
)


def all_rule_definitions() -> list[RuleDefinition]:
    """Return every rule definition in CLI display order."""

    return [
        *documentation.RULES,
        *testing.RULES,
        *structure.RULES,
        *security.RULES,
        *maintenance.RULES,
    ]


def evaluate_all(snapshot: RepositorySnapshot) -> list[RuleResult]:
    """Evaluate all rule categories."""

    results: list[RuleResult] = []
    for evaluator in EVALUATORS:
        results.extend(evaluator(snapshot))
    return results
