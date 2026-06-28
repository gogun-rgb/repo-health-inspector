"""Documentation scoring rules."""

from __future__ import annotations

from repo_health.models import Category, RuleDefinition, RuleResult
from repo_health.repository_loader import RepositorySnapshot
from repo_health.rules._helpers import contains_any, failed, passed, warning

README_CANDIDATES = ("README.md", "README.rst", "README.txt", "readme.md")

RULES: tuple[RuleDefinition, ...] = (
    RuleDefinition(
        rule_id="DOC001",
        title="README exists",
        category=Category.DOCUMENTATION,
        max_score=4,
        recommendation="Add a README that explains what the project does and how to use it.",
    ),
    RuleDefinition(
        rule_id="DOC002",
        title="README has meaningful content",
        category=Category.DOCUMENTATION,
        max_score=3,
        recommendation="Expand the README beyond a title with practical setup and usage details.",
    ),
    RuleDefinition(
        rule_id="DOC003",
        title="Project description is present",
        category=Category.DOCUMENTATION,
        max_score=2,
        recommendation="Add a concise value proposition in the README or repository metadata.",
    ),
    RuleDefinition(
        rule_id="DOC004",
        title="Installation instructions are present",
        category=Category.DOCUMENTATION,
        max_score=2,
        recommendation="Document installation steps such as pip, uv, Poetry, or source installs.",
    ),
    RuleDefinition(
        rule_id="DOC005",
        title="Usage instructions are present",
        category=Category.DOCUMENTATION,
        max_score=2,
        recommendation="Show at least one command or code example for normal project usage.",
    ),
    RuleDefinition(
        rule_id="DOC006",
        title="License file exists",
        category=Category.DOCUMENTATION,
        max_score=2,
        recommendation="Add an OSI-approved license file so users know the reuse terms.",
    ),
    RuleDefinition(
        rule_id="DOC007",
        title="Changelog exists",
        category=Category.DOCUMENTATION,
        max_score=1,
        recommendation="Add a CHANGELOG to make project evolution easy to scan.",
    ),
    RuleDefinition(
        rule_id="DOC008",
        title="Contributing guide exists",
        category=Category.DOCUMENTATION,
        max_score=1,
        recommendation="Add CONTRIBUTING.md with setup, testing, and contribution expectations.",
    ),
    RuleDefinition(
        rule_id="DOC009",
        title="Screenshots or demos are referenced",
        category=Category.DOCUMENTATION,
        max_score=3,
        recommendation="Add a screenshot, terminal capture, GIF, demo link, or example output.",
    ),
)


def evaluate(snapshot: RepositorySnapshot) -> list[RuleResult]:
    """Evaluate documentation rules."""

    readme_path = snapshot.find_first(*README_CANDIDATES)
    readme = snapshot.read_text(readme_path) if readme_path else ""
    metadata_description = snapshot.maintenance.description if snapshot.maintenance else None

    results: list[RuleResult] = []
    results.append(
        passed(RULES[0], f"Found {readme_path.as_posix()}.")
        if readme_path
        else failed(RULES[0], "No README file was found.")
    )
    results.append(_readme_content_result(readme))
    results.append(_description_result(readme, metadata_description))
    results.append(
        passed(RULES[3], "Installation guidance is present.")
        if contains_any(
            readme,
            ("installation", "install", "pip install", "uv pip", "poetry install"),
        )
        else failed(RULES[3], "No installation section or install command was detected.")
    )
    results.append(
        passed(RULES[4], "Usage guidance is present.")
        if contains_any(readme, ("usage", "quickstart", "example", "repo-health", "python -m"))
        else failed(RULES[4], "No usage section or command example was detected.")
    )
    results.append(
        passed(RULES[5], "A license file is present.")
        if snapshot.has_file("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")
        else failed(RULES[5], "No license file was found.")
    )
    results.append(
        passed(RULES[6], "A changelog file is present.")
        if snapshot.has_file("CHANGELOG.md", "CHANGELOG.rst", "HISTORY.md")
        else failed(RULES[6], "No changelog file was found.")
    )
    results.append(
        passed(RULES[7], "A contributing guide is present.")
        if snapshot.has_file("CONTRIBUTING.md", "CONTRIBUTING.rst")
        else failed(RULES[7], "No contributing guide was found.")
    )
    results.append(_demo_reference_result(readme))
    return results


def _readme_content_result(readme: str) -> RuleResult:
    words = readme.split()
    if len(words) >= 80:
        return passed(RULES[1], f"README contains {len(words)} words.")
    if len(words) >= 20:
        return warning(
            RULES[1],
            f"README is present but short at {len(words)} words.",
            earned_score=1.5,
        )
    return failed(RULES[1], "README is missing or nearly empty.")


def _description_result(readme: str, metadata_description: str | None) -> RuleResult:
    if metadata_description and len(metadata_description.strip()) >= 20:
        return passed(RULES[2], "Repository metadata contains a useful description.")
    paragraphs = [
        line.strip() for line in readme.splitlines() if line.strip() and not line.startswith("#")
    ]
    if any(len(paragraph.split()) >= 8 for paragraph in paragraphs[:5]):
        return passed(RULES[2], "README opens with a useful project description.")
    return failed(RULES[2], "No clear project description was detected.")


def _demo_reference_result(readme: str) -> RuleResult:
    if contains_any(
        readme,
        ("![", "screenshot", "demo", ".gif", ".png", "asciinema", "sample output", "terminal"),
    ):
        return passed(RULES[8], "README references screenshots, demos, or sample output.")
    return warning(
        RULES[8],
        "No screenshot, demo, or sample output reference was detected.",
        earned_score=1,
    )
