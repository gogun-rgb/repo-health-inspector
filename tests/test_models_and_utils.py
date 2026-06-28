from __future__ import annotations

import pytest

from repo_health.models import Category, RuleResult, RuleStatus
from repo_health.utils import contains_secret_pattern, score_label


def test_rule_result_rejects_score_above_max() -> None:
    with pytest.raises(ValueError, match="earned_score cannot exceed max_score"):
        RuleResult(
            rule_id="X001",
            title="Bad score",
            category=Category.DOCUMENTATION,
            max_score=1,
            earned_score=2,
            status=RuleStatus.PASSED,
            explanation="Invalid",
            recommendation="Use valid scores.",
        )


def test_score_labels() -> None:
    assert score_label(95) == "Excellent"
    assert score_label(80) == "Strong"
    assert score_label(65) == "Fair"
    assert score_label(45) == "Needs work"
    assert score_label(10) == "Poor"


def test_secret_pattern_ignores_examples_but_flags_realistic_values() -> None:
    assert not contains_secret_pattern('TOKEN = "example-token-value"')
    secret_value = "a" * 20
    assert contains_secret_pattern(f'API_KEY = "{secret_value}"')
