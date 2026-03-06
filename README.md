# ActivitiesViewer 🚴‍♂️📊

A Streamlit dashboard for visualizing and analyzing cycling activities from Strava. Built for athletes who want deep insights into their training performance, trends, and physiological metrics.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)

## Features

### 📊 Unified Analysis Page
A **fluid explorer** with selectable time range and view mode:

- **Overview** — Volume trends, Training Intensity Distribution (TID) with polarization analysis, periodization check, cumulative progression charts
- **Physiology** — Efficiency Factor trends (Z2 rides), power-HR decoupling, daily intensity patterns, device color-coding for HR source tracking
- **Power Profile** — Mean Maximum Power curve with yearly comparison, sprint/VO2max/FTP/endurance benchmarks
- **Recovery** — Monotony & Strain indices, Performance Management Chart (CTL/ATL/TSB), rest day analysis

### 🏠 Goal-Driven Dashboard
- Visual W/kg progress tracking toward a power-to-weight goal
- PMC with fitness/fatigue/form indicators
- Recent activity sparklines and training calendar

### ⚡ Fitness Auto-Estimation
- Estimate FTP from 20-minute power peaks (Coggan protocol)
- Estimate max HR from hard efforts across all activities
- Device-aware color coding (chest strap vs. watch HR source)
- Weight tracking from activity metadata

### 📋 Training Plan
- AI-generated periodized training plans
- Weekly TSS tracking with actuals vs. planned
- Current-week analysis with plan boundary sync

### 🚴 Activity Detail
- Context-aware header (top 4 metrics based on activity type)
- Interactive route maps with GPS overlay
- Power/HR profiles, zone distributions, 100+ metrics

### 🤖 AI Coach
- Natural language querying of training data (Google Gemini)
- Stream-level analytics for per-activity deep dives
- Training pattern and trend identification

### ⚙️ Settings Editor
- Edit athlete profile (FTP, weight, max HR, CP, W') from the UI
- Configure analyzer and training plan parameters
- Saves directly to your YAML config file

## Quick Start

### Prerequisites

- Python 3.12+
- [UV package manager](https://github.com/astral-sh/uv)
- Enriched activity data from [StravaAnalyzer](https://github.com/hope0hermes/StravaAnalyzer)

> **Want to share with friends?** See [docs/SHARING.md](docs/SHARING.md) for Docker-based deployment — no Python setup required.

### Install and Run

```bash
# Clone and install
git clone https://github.com/hope0hermes/ActivitiesViewer.git
cd ActivitiesViewer
uv sync

# Configure
cp examples/config.yaml config.yaml
# Edit config.yaml with your athlete settings and data paths

# Launch the dashboard
activities-viewer run --config config.yaml
```

### Full Pipeline (Fetch → Analyze → View)

If you also want to fetch and analyze data automatically:

```bash
cp examples/unified_config.yaml config.yaml
# Edit config.yaml with your Strava API credentials and athlete settings

activities-viewer sync --config config.yaml
```

This will:
1. Fetch new activities from the Strava API (via `strava-fetcher`)
2. Analyze and enrich the data (via `strava-analyzer`)
3. Launch the Streamlit dashboard

## Configuration

Two config modes are supported:

| Mode | Config file | Command | Use case |
|------|-------------|---------|----------|
| **Viewer-only** | `examples/config.yaml` | `activities-viewer run` | You already have enriched CSVs |
| **Full pipeline** | `examples/unified_config.yaml` | `activities-viewer sync` | Fetch + analyze + view in one step |

Key settings in both modes:

```yaml
# Athlete profile (required)
ftp: 285.0              # Functional Threshold Power (watts)
rider_weight_kg: 77.0   # Weight (kg)
max_hr: 185             # Maximum heart rate (bpm)

# Data paths
data_dir: "~/.strava_fetcher/data"
activities_raw_file: "activities_raw.csv"
activities_moving_file: "activities_moving.csv"
streams_dir: "Streams"
```

See the example files in [`examples/`](examples/) for all available options including goal tracking, AI features, and analyzer tuning.

## CLI Reference

```
activities-viewer run      --config config.yaml       # Launch dashboard
activities-viewer sync     --config config.yaml       # Full pipeline
activities-viewer validate --config config.yaml       # Validate config
activities-viewer version                              # Show version
```

## Project Structure

```
ActivitiesViewer/
├── src/activities_viewer/
│   ├── app.py                     # Main Streamlit dashboard
│   ├── cli.py                     # CLI (run, sync, validate, version)
│   ├── config.py                  # Pydantic Settings model
│   ├── pipeline.py                # Unified fetch→analyze→view pipeline
│   ├── ai/                        # Gemini AI client & context
│   ├── domain/                    # Domain models (Activity, Goal, TrainingPlan)
│   ├── services/                  # Business logic layer
│   │   ├── activity_service.py    # Activity data access
│   │   ├── analysis_service.py    # Metric aggregation & trends
│   │   ├── fitness_estimation.py  # FTP & max HR estimation
│   │   ├── goal_service.py        # Goal tracking
│   │   └── training_plan_service.py
│   ├── repository/                # Data access layer
│   │   ├── base.py                # Repository interface
│   │   └── csv_repo.py            # CSV implementation
│   ├── pages/                     # Streamlit pages
│   │   ├── 1_analysis.py          # Unified analysis (4 view modes)
│   │   ├── 3_detail.py            # Activity detail
│   │   ├── 5_ai_coach.py          # AI coaching
│   │   ├── 6_training_plan.py     # Training plan
│   │   ├── 7_fitness_estimation.py # FTP/HR estimation
│   │   ├── 8_strava_connect.py    # OAuth (for Docker)
│   │   ├── 9_settings.py          # Settings editor
│   │   └── components/            # Reusable UI components
│   ├── data/                      # Help texts & metric descriptions
│   └── utils/                     # Formatting, device utils, metrics
├── tests/                         # pytest test suite
├── docs/                          # Documentation
├── examples/                      # Example config files
└── pyproject.toml                 # Project metadata & dependencies
```

## Development

```bash
uv sync                                        # Install all deps
uv run pytest                                  # Run tests
uv run pytest --cov=src/activities_viewer       # Tests with coverage
uv run ruff check src/ tests/                  # Lint
uv run ruff format src/ tests/                 # Format
uv run mypy src/activities_viewer              # Type check
```

This project uses [conventional commits](https://www.conventionalcommits.org/) enforced by CI.

## Documentation

| Document | Description |
|----------|-------------|
| [QUICK_START.md](docs/QUICK_START.md) | Install, configure, and run in 5 minutes |
| [SETUP.md](docs/SETUP.md) | Detailed setup with prerequisites and troubleshooting |
| [DATA_STRUCTURE.md](docs/DATA_STRUCTURE.md) | Expected data files, columns, and stream format |
| [CLI_CONFIGURATION.md](docs/CLI_CONFIGURATION.md) | CLI commands and configuration reference |
| [SHARING.md](docs/SHARING.md) | Share with friends via Docker |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | Development setup, CI/CD, testing |
| [PUBLISHING.md](docs/PUBLISHING.md) | Publishing to private Devpi index |

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- Built with [Streamlit](https://streamlit.io)
- Data pipeline: [StravaAnalyzer](https://github.com/hope0hermes/StravaAnalyzer) and [StravaFetcher](https://github.com/hope0hermes/StravaFetcher)
- Inspired by TrainingPeaks and the sports science community

---

**Made with ❤️ for cyclists who love data**
