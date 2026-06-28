# Contributing

Thanks for helping improve repo-health-inspector. The project is intentionally rule-based,
small enough to understand, and strict about tests so changes remain reviewable.

## Development Setup

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
```

## Quality Checks

Run these before opening a pull request:

```bash
ruff format .
ruff check .
mypy src tests
pytest
```

## Rule Changes

Scoring rules must stay transparent and reproducible. When adding or changing a rule:

- keep each category at exactly 20 points
- include a clear rule ID, title, explanation, and recommendation
- update or add focused tests
- avoid claims that static analysis can prove security or quality

## Pull Requests

Prefer small pull requests with a focused description, a test summary, and any known limitations.
