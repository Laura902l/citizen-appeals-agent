# Contributing

## Workflow (GitHub Flow)

1. Open an issue describing the bug or feature (templates are provided).
2. Create a branch from `main`: `feature/<short-name>`, `fix/<short-name>` or `docs/<short-name>`.
3. Commit in small steps using [Conventional Commits](https://www.conventionalcommits.org/):
   `feat: ...`, `fix: ...`, `test: ...`, `docs: ...`, `ci: ...`, `refactor: ...`.
4. Open a pull request; CI must be green before merging into `main`.
5. Releases are made by bumping the version in `pyproject.toml` and
   `src/appeal_agent/__init__.py`, updating `CHANGELOG.md` and pushing a tag `vX.Y.Z`.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install                 # optional: run ruff on every commit
```

## Checks (the same as in CI)

```bash
ruff check .
ruff format --check .
mypy
pytest --cov --cov-fail-under=90
```

## Rules of thumb

- Business rules (categories, SLA terms, holidays, urgency keywords) belong in
  `src/appeal_agent/data/default_config.toml`, never in code.
- Every bug in date arithmetic gets a regression test in `tests/test_business_calendar.py`
  or `tests/test_sla.py`.
- Any change that affects the model must report new metrics together with the seed.
