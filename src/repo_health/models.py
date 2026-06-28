"""Pydantic models used by the analyzer and reports."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RuleStatus(StrEnum):
    """Outcome for a single scoring rule."""

    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


class Category(StrEnum):
    """Top-level scoring categories."""

    DOCUMENTATION = "Documentation"
    TESTING = "Testing and CI"
    STRUCTURE = "Project structure"
    SECURITY = "Security and reliability"
    MAINTENANCE = "Maintenance and community"


class ReportFormat(StrEnum):
    """Supported report output formats."""

    MARKDOWN = "markdown"
    JSON = "json"
    BOTH = "both"


class RepositoryInfo(BaseModel):
    """Repository identity included in reports."""

    model_config = ConfigDict(extra="forbid")

    name: str
    owner: str | None = None
    url: str | None = None
    default_branch: str | None = None
    local_path: str | None = None

    @property
    def display_name(self) -> str:
        """Return owner/name when an owner is known, otherwise the repository name."""

        if self.owner:
            return f"{self.owner}/{self.name}"
        return self.name


class MaintenanceMetadata(BaseModel):
    """GitHub-derived maintenance information.

    Fields may be missing when unauthenticated API calls are rate-limited or a local
    repository is analyzed.
    """

    model_config = ConfigDict(extra="forbid")

    pushed_at: datetime | None = None
    open_issues_count: int | None = None
    closed_issues_count: int | None = None
    release_count: int | None = None
    latest_release_published_at: datetime | None = None
    contributor_count: int | None = None
    archived: bool | None = None
    description: str | None = None
    topics: list[str] = Field(default_factory=list)
    default_branch: str | None = None
    limited: bool = False


class RuleDefinition(BaseModel):
    """Static metadata for a scoring rule."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    title: str
    category: Category
    max_score: float = Field(gt=0)
    recommendation: str

    def to_result(
        self,
        *,
        earned_score: float,
        status: RuleStatus,
        explanation: str,
        recommendation: str | None = None,
    ) -> RuleResult:
        """Create a rule result while preserving the rule definition."""

        return RuleResult(
            rule_id=self.rule_id,
            title=self.title,
            category=self.category,
            max_score=self.max_score,
            earned_score=earned_score,
            status=status,
            explanation=explanation,
            recommendation=recommendation or self.recommendation,
        )


class RuleResult(BaseModel):
    """Scored result for one rule."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    title: str
    category: Category
    max_score: float = Field(gt=0)
    earned_score: float = Field(ge=0)
    status: RuleStatus
    explanation: str
    recommendation: str

    @field_validator("earned_score")
    @classmethod
    def earned_score_cannot_exceed_max(cls, value: float, info: object) -> float:
        """Validate rule score bounds after pydantic has parsed values."""

        data = getattr(info, "data", {})
        max_score = data.get("max_score")
        if isinstance(max_score, int | float) and value > float(max_score):
            msg = "earned_score cannot exceed max_score"
            raise ValueError(msg)
        return value


class CategoryScore(BaseModel):
    """Aggregated score for one category."""

    model_config = ConfigDict(extra="forbid")

    category: Category
    earned_score: float = Field(ge=0)
    max_score: float = Field(gt=0)

    @property
    def percentage(self) -> float:
        """Return the category score percentage."""

        return round((self.earned_score / self.max_score) * 100, 1)


class AnalysisReport(BaseModel):
    """Machine-readable report produced by the analyzer.

    ``total_score`` is the raw 100-point score. Skipped rules earn zero raw
    points so users can see when GitHub-only or unavailable checks reduce the
    overall score. ``evaluated_score`` is the percentage earned from rules that
    were actually evaluated.
    """

    model_config = ConfigDict(extra="forbid")

    repository: RepositoryInfo
    analysis_timestamp: datetime
    total_score: float = Field(ge=0, le=100)
    score_label: str
    evaluated_score: float = Field(default=0, ge=0, le=100)
    evaluated_score_label: str = "Poor"
    evaluated_rule_count: int = Field(default=0, ge=0)
    skipped_rule_count: int = Field(default=0, ge=0)
    total_rule_count: int = Field(default=0, ge=0)
    skipped_score: float = Field(default=0, ge=0, le=100)
    category_scores: list[CategoryScore]
    strengths: list[str]
    warnings: list[str]
    recommendations: list[str]
    rule_results: list[RuleResult]
    disclaimer: str
    generated_by: str
    report_notes: list[str] = Field(default_factory=list)
    sample_report: bool = False
    sample_report_notice: str | None = None

    @field_validator("total_score")
    @classmethod
    def round_total_score(cls, value: float) -> float:
        """Normalize total scores for stable reports."""

        return round(value, 1)

    @field_validator("evaluated_score", "skipped_score")
    @classmethod
    def round_summary_scores(cls, value: float) -> float:
        """Normalize summary scores for stable reports."""

        return round(value, 1)

    def with_sample_notice(self, notice: str) -> Self:
        """Return a copy of the report marked as sample output."""

        return self.model_copy(update={"sample_report": True, "sample_report_notice": notice})
