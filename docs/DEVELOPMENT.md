# Development Guide

## Setup

```bash
git clone https://github.com/hope0hermes/ActivitiesViewer.git
cd ActivitiesViewer
uv sync
```

This installs all runtime and dev dependencies (`pytest`, `ruff`, `mypy`).

## Project Structure

```
src/activities_viewer/
├── app.py                 # Main Streamlit dashboard
├── cli.py                 # Click CLI (run, sync, validate, version)
├── config.py              # Pydantic Settings model (35+ fields)
├── pipeline.py            # Unified fetch→analyze→view pipeline
├── ai/
│   ├── client.py          # Gemini client + model selector
│   └── context.py         # Activity context builder for AI
├── data/
│   ├── help_texts.py      # UI help text registry
│   └── metric_descriptions.py
├── domain/
│   ├── models.py          # Activity, Goal, TrainingPlan models
│   └── metrics.py         # MetricRegistry & definitions
├── services/
│   ├── activity_service.py       # Activity data access
│   ├── analysis_service.py       # Metric aggregation & trends
│   ├── fitness_estimation.py     # FTP & max HR estimation
│   ├── goal_service.py           # Goal tracking logic
│   ├── strava_oauth.py           # OAuth flow
│   └── training_plan_service.py  # Plan generation & tracking
├── repository/
│   ├── base.py            # Repository interface
│   └── csv_repo.py        # CSV implementation with caching
├── pages/
│   ├── 1_analysis.py      # Unified analysis (4 view modes)
│   ├── 3_detail.py        # Activity detail
│   ├── 5_ai_coach.py      # AI coaching
│   ├── 6_training_plan.py # Training plan
│   ├── 7_fitness_estimation.py  # FTP/HR estimation
│   ├── 8_strava_connect.py      # OAuth page (Docker)
│   ├── 9_settings.py      # Settings editor
│   └── components/         # Reusable UI widgets
├── utils/
│   ├── device_utils.py    # Device color mapping for plots
│   ├── formatting.py      # Metric rendering helpers
│   └── metrics.py         # Metric computation utilities
└── viz/                    # (reserved for future chart builders)
```

## Testing

```bash
# Run all tests
uv run pytest

# With coverage report
uv run pytest --cov=src/activities_viewer --cov-report=html

# Specific test file
uv run pytest tests/test_fitness_estimation.py -v

# Only unit tests
uv run pytest -m unit
```

### Test Files

| File | Coverage |
|------|----------|
| `test_config.py` | Settings model validation |
| `test_csv_repo.py` | CSV repository loading |
| `test_data_contract.py` | Data column contracts |
| `test_fitness_estimation.py` | FTP/HR estimation logic |
| `test_pipeline.py` | Unified pipeline |
| `test_strava_connect.py` | OAuth flow |
| `test_sync_button.py` | Sync UI component |

## Code Quality

### Linting (Ruff)

```bash
uv run ruff check src/ tests/         # Check
uv run ruff check --fix src/ tests/   # Auto-fix
uv run ruff format src/ tests/        # Format
```

Rules: `E`, `F`, `W`, `I` (isort), `UP` (pyupgrade), `B` (bugbear), `C4` (comprehensions).

### Type Checking (Mypy)

```bash
uv run mypy src/activities_viewer
```

### Pre-commit Checklist

Before pushing:

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/activities_viewer
uv run pytest
```

## CI/CD

### Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `tests.yml` | Push & PR | Run pytest + ruff + mypy |
| `commitlint.yml` | PR | Validate conventional commit titles |
| `release.yml` | Manual | Create version bump PR |
| `create-release.yml` | Version tag | Create GitHub Release |
| `publish.yml` | Manual | Publish to Devpi index |

All workflows use shared actions from [SharedWorkflows](https://github.com/hope0hermes/SharedWorkflows).

### Conventional Commits

PR titles **must** follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new feature
fix: correct calculation bug
docs: update setup guide
chore: bump dependency
ci: fix workflow permissions
```

### Version Management

Version lives in `src/activities_viewer/__init__.py`:

```python
__version__ = "1.7.0"
```

Hatch reads this dynamically for `pyproject.toml`.

## Building

```bash
uv build
# Creates dist/activities_viewer-1.7.0.tar.gz and .whl
```

## Publishing

See [PUBLISHING.md](PUBLISHING.md) for Devpi publishing instructions.
