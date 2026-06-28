# repo-health-inspector

[![CI](actions/workflows/ci.yml/badge.svg)](actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Code style](https://img.shields.io/badge/code%20style-ruff-46a0f5)

`repo-health-inspector` is a Python CLI that evaluates GitHub repositories for documentation,
testing, project structure, lightweight security signals, and maintenance readiness.

It is designed for beginner developers, students, open-source maintainers, and AI-assisted coding
users who want a concrete answer to a hard question: “Is this repository portfolio-ready?”

## Why this project exists

Many beginner developers can now build working projects with AI coding tools, but still struggle to
evaluate the qualities that make a repository trustworthy: documentation, tests, maintainability,
release hygiene, and safe handling of secrets. repo-health-inspector turns those expectations into
transparent checks with clear recommendations instead of vague advice.

## Features

- Scores repositories from 0 to 100 using five 20-point categories.
- Explains every rule result with an ID, status, score, explanation, and recommendation.
- Generates Markdown and JSON reports.
- Inspects public GitHub repositories through the GitHub API.
- Inspects local repositories without uploading files or contacting GitHub.
- Works without an OpenAI API key or any database.
- Handles common API and filesystem errors without raw stack traces unless `--verbose` is enabled.

## Installation

Install from a local checkout:

```bash
git clone https://github.com/gogun-rgb/repo-health-inspector.git
cd repo-health-inspector
python -m pip install -e .
```

For development:

```bash
python -m pip install -e ".[dev]"
```

## Usage

Inspect a public GitHub repository:

```bash
repo-health inspect https://github.com/OWNER/REPOSITORY
```

Generate both report formats:

```bash
repo-health inspect https://github.com/gogun-rgb/ai-hype-radar \
  --format both \
  --output reports
```

Inspect the current local repository without using GitHub:

```bash
repo-health inspect-local . --format both
```

Show scoring rules:

```bash
repo-health rules
```

Show the installed version:

```bash
repo-health version
```

Fail a script or CI step when the score is below a threshold:

```bash
repo-health inspect-local . --fail-under 75
```

## Sample Output

```text
Repository Health
repo-health-inspector
Score: 80.0/100 (Strong)

Category Scores
Documentation               20.0/20.0
Testing and CI              20.0/20.0
Project structure           20.0/20.0
Security and reliability    20.0/20.0
Maintenance and community    0.0/20.0

Saved report: reports/local-repo-health-inspector-report.md
Saved report: reports/local-repo-health-inspector-report.json
```

Local inspections skip GitHub-only maintenance signals, so a local-only score may be lower than the
same repository inspected through GitHub.

## GitHub Token

The tool works without a token for public repositories, but unauthenticated GitHub API requests have
lower rate limits. To raise the limit, pass a token directly or set `GITHUB_TOKEN`:

```bash
repo-health inspect https://github.com/OWNER/REPOSITORY --token "$GITHUB_TOKEN"
```

Tokens are not written to reports.

## Scoring

The total score is the sum of rule results. Each category is worth exactly 20 points:

- Documentation
- Testing and CI
- Project structure
- Security and reliability
- Maintenance and community

Score labels:

| Score | Label |
| ---: | --- |
| 90-100 | Excellent |
| 75-89 | Strong |
| 60-74 | Fair |
| 40-59 | Needs work |
| 0-39 | Poor |

Every rule includes:

- rule ID
- title
- category
- maximum score
- earned score
- status
- explanation
- recommendation

Statuses are `passed`, `warning`, `failed`, and `skipped`.

## Reports

Markdown and JSON reports are written to the selected output directory:

```text
reports/<owner>-<repo>-report.md
reports/<owner>-<repo>-report.json
```

The Markdown report includes category scores, strengths, warnings, prioritized recommendations,
detailed rule results, and a static-analysis disclaimer. The JSON report is validated with Pydantic
models and is suitable for downstream automation.

Sample generated reports are included in the `reports/` directory. They are generated from the test
fixture and clearly marked as sample reports.

## Project Architecture

```text
src/repo_health/
  cli.py                 Typer/Rich command-line interface
  github_client.py       GitHub REST API client and error mapping
  repository_loader.py   Safe local and archive-based repository snapshots
  models.py              Pydantic report and rule models
  scoring.py             Rule orchestration and score aggregation
  report_generator.py    Markdown and JSON rendering
  rules/                 Documentation, testing, structure, security, maintenance checks
```

The analyzer never installs dependencies from inspected repositories, never runs shell scripts from
them, and never executes inspected source code.

## Local Repository Analysis

`inspect-local` checks files already on disk:

- README, license, changelog, and contribution docs
- test directories and test files
- source layout and dependency manifests
- `.gitignore` and example environment files
- CI, coverage, lint, and type-check configuration
- suspicious secret and token patterns

It does not upload local files anywhere.

## Security Notes

repo-health-inspector performs lightweight static checks only. It can detect common warning signs,
such as token-like strings, `.env` tracking risk, unsafe `eval` usage, and missing security policy
files. It cannot prove that a repository is secure, free of vulnerabilities, or maintained.

Remote inspection downloads a GitHub zip archive into a temporary directory, validates archive paths,
and enforces size limits before static analysis.

## Development

```bash
python -m pip install -e ".[dev]"
ruff format .
ruff check .
mypy src tests
pytest
```

The test suite uses mocked GitHub API responses and does not depend on live internet access.

## Roadmap

- Add optional SARIF output for code scanning dashboards.
- Add configurable rule profiles for Python libraries, CLIs, and data projects.
- Add richer local Git metadata for local-only maintenance scoring.
- Add documentation examples for common portfolio project types.

## Limitations

- Static checks are heuristic and intentionally lightweight.
- GitHub maintenance data depends on API availability and rate limits.
- Local analysis skips GitHub-only signals such as issues, releases, topics, and archived status.
- The tool does not clone repositories or run project code.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, testing, and rule
change guidance.

## License

repo-health-inspector is distributed under the MIT License. See [LICENSE](LICENSE).
