# Justification of the technology stack

The choices below follow the criteria used in the report: fit to the task, maturity and
community, the team's competence (one developer), licence and cost, ecosystem and
integration, reproducibility, and long-term maintainability.

| Concern | Choice | Alternatives considered | Why this choice |
|---|---|---|---|
| Language | **Python 3.11+** | R, Java, Julia | De-facto standard for ML and data processing; same language for the model, the SLA logic and the CLI; known by the developer; `tomllib` and `StrEnum` are in the standard library from 3.11. |
| ML library | **scikit-learn** (TF-IDF + logistic regression) | PyTorch / transformers, spaCy | Small synthetic dataset; a linear model trains in seconds on a CPU, gives calibrated probabilities for the review queue, and is easy to explain (NFR7). Transformers would need a GPU and much more data, which the zero budget does not allow. |
| Numerical core | **NumPy** | — | Required by scikit-learn; used for probability arrays. |
| Model persistence | **joblib** | pickle, ONNX | Recommended by scikit-learn for pipelines; stores metadata (model version, data fingerprint) together with the model. |
| Visualisation | **matplotlib** | seaborn, plotly | Mature, no browser needed, works headless in CI (Agg backend), produces figures for reports. |
| Configuration | **TOML** (`tomllib`) | YAML, JSON | Built into Python (no dependency), supports comments, readable for non-programmers who maintain holidays and SLA terms (NFR3). |
| Data format | **CSV** | Parquet, SQLite | Human-readable, opens in Excel, enough for a prototype; the schema is fixed in `models.py`. |
| CLI | **argparse** | click, typer | Standard library, no dependency, sufficient for five commands. |
| REST API | **http.server** (standard library) | FastAPI, Flask | Five endpoints for one operator; no extra dependency or server to install. The service layer is separate, so moving to FastAPI in the pilot changes only `api.py`. |
| Front end | **React 19 + TypeScript** | Vue, Svelte, plain HTML, Streamlit | Largest ecosystem and hiring pool; components map directly to dashboard parts (tiles, table, review control); TypeScript types mirror the Python data schema and catch API mismatches. Streamlit would be faster to write but gives less control over the operator workflow. |
| Front-end build | **Vite** | webpack, Create React App (deprecated) | Fast dev server with an `/api` proxy, simple production build. |
| Front-end tests | **vitest + Testing Library** | Jest, Cypress | Same configuration as Vite; tests the UI as a user sees it (roles, labels). |
| Tests | **pytest + pytest-cov** | unittest | Concise tests, fixtures, parametrisation for date boundary cases, branch coverage. |
| Lint / format | **ruff** | flake8 + black + isort | One fast tool replacing three. |
| Static typing | **mypy** | pyright | Catches interface mismatches between modules (integration risk from Assignment 1). |
| Packaging | **pyproject.toml + setuptools** | poetry, hatch | PEP 621 standard; `pip install .` works everywhere without extra tools. |
| Version control | **Git + GitHub** | GitLab, Bitbucket | Free public hosting, issues, pull requests, Actions minutes for public repositories. |
| CI/CD | **GitHub Actions** | GitLab CI, Jenkins | Integrated with the repository, no server to maintain (Jenkins would need one), free for public repositories, OS matrix (Linux/Windows/macOS). |
| Licence | **MIT** | Apache-2.0, GPL-3.0 | Permissive and short; allows a city administration to reuse the code. |
