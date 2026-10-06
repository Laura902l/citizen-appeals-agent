# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-05

### Added
- Business-day calendar with configurable weekend and holidays.
- SLA engine: deadlines, urgent terms, statuses on track / at risk / overdue / closed.
- Rule-based masking of phones, e-mails and introduced names.
- Reproducible synthetic dataset generator (seeded).
- TF-IDF + logistic regression classifier with a confidence-based review queue
  and a model version tied to the training-data fingerprint.
- Agent orchestrator, CSV I/O, matplotlib reports and the `appeal-agent` CLI.
- REST API (`appeal-agent serve`) and a React + TypeScript monitoring dashboard: overview,
  appeals register with detail panel, operator review queue and model quality page.
- GitHub Actions CI (lint, type check, test matrix, reproducible experiment)
  and CD (GitHub Release on version tags); a separate job type-checks, tests and builds
  the dashboard.
