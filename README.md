# ActivitiesViewer 🚴‍♂️📊

A powerful Streamlit dashboard for visualizing and analyzing cycling activities data from Strava. Built for athletes who want deep insights into their training performance, trends, and metrics.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![UV](https://img.shields.io/badge/uv-package%20manager-green.svg)](https://github.com/astral-sh/uv)

## 🌟 Features

### 📊 Year Overview
- Comprehensive annual statistics and performance metrics
- Monthly trends for distance, elevation, and time
- Training load visualization (CTL/ATL/TSB)
- Power and heart rate zone distribution
- Top performances and personal records

### 📅 Weekly Analysis
- Recent performance tracking (last 12 weeks)
- Week-over-week comparisons
- Training load evolution
- Recovery recommendations based on TSB and ACWR
- Daily activity breakdown

### 🚴 Activity Details
- Deep-dive analysis of individual activities
- Interactive route maps with GPS overlay
- Power and heart rate profiles over time
- Efficiency metrics and pacing analysis
- Zone distribution and comparative analysis

### 🔍 Segment Analysis *(Phase 2)*
- Auto-detected recurring segments (climbs, flats, descents)
- Performance trends over time
- Effort-by-effort comparison
- Personal records tracking
- Vector similarity search for segment matching

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- [UV package manager](https://github.com/astral-sh/uv) (required - this project uses UV)
- Enriched activities data from [StravaAnalyzer](https://github.com/hope0hermes/StravaAnalyzer)

### Installation

```bash
# Clone the repository
git clone https://github.com/hope0hermes/ActivitiesViewer.git
cd ActivitiesViewer

# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Run the dashboard
uv run streamlit run src/activities_viewer/app.py
```

The dashboard will open in your browser at `http://localhost:8501`.

### Data Setup

ActivitiesViewer requires enriched activity data from StravaAnalyzer:

1. Run StravaAnalyzer to generate enriched data:
   ```bash
   strava-analyzer process --config config.yaml
   ```

2. Configure ActivitiesViewer data paths in `.env`:
   ```env
   DATA_DIR=/home/hope0hermes/Workspace/ActivitiesViewer/dev/data
   ACTIVITIES_PATH=/home/hope0hermes/Workspace/ActivitiesViewer/dev/data_processed/activities_enriched.csv
   SUMMARY_PATH=/home/hope0hermes/Workspace/ActivitiesViewer/dev/data_processed/activity_summary.json
   STREAMS_DIR=/home/hope0hermes/Workspace/ActivitiesViewer/dev/data/Streams
   ```

3. Launch the dashboard:
   ```bash
   uv run streamlit run src/activities_viewer/app.py
   ```

## 📁 Project Structure

```
ActivitiesViewer/
├── src/
│   └── activities_viewer/
│       ├── app.py                  # Main Streamlit application
│       ├── config.py               # Configuration management
│       ├── pages/                  # Multi-page app
│       │   ├── 1_📊_Year_Overview.py
│       │   ├── 2_📅_Weekly_Analysis.py
│       │   └── 3_🚴_Activity_Detail.py
│       ├── data/                   # Data loading and processing
│       ├── components/             # Reusable UI components
│       ├── analytics/              # Business logic and calculations
│       ├── viz/                    # Visualization builders
│       └── utils/                  # Utility functions
├── tests/                          # Test suite
├── docs/                           # Documentation
├── scripts/                        # Utility scripts
├── assets/                         # Static assets
├── .streamlit/                     # Streamlit configuration
└── pyproject.toml                  # Project dependencies
```

## 🔧 Development

### Setup Development Environment

```bash
# Sync dependencies (creates venv and installs all dependencies including dev)
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/activities_viewer --cov-report=html

# Format code
uv run ruff format src/ tests/

# Lint code
uv run ruff check src/ tests/

# Type checking
uv run mypy src/activities_viewer
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_config.py

# Run with markers
uv run pytest -m unit          # Only unit tests
uv run pytest -m integration   # Only integration tests

# Run with verbose output
uv run pytest -v
```

## 📊 Metrics & Analytics

ActivitiesViewer displays a comprehensive set of cycling metrics:

- **Power Metrics**: NP, IF, TSS, VI, power zones
- **Heart Rate**: HR zones, HR-TSS, efficiency factor
- **Training Load**: CTL, ATL, TSB, ACWR
- **Advanced**: Power-HR decoupling, fatigue index, sustainability
- **Comparative**: Week-over-week, month-over-month trends

For detailed metric definitions, see [docs/METRICS_GLOSSARY.md](docs/METRICS_GLOSSARY.md).

## 🗺️ Roadmap

### Phase 1: MVP (Weeks 1-3) 🚧
- [ ] Year overview page
- [ ] Weekly analysis page
- [ ] Activity detail page
- [ ] Data loading and caching
- [ ] Basic visualizations

### Phase 2: Enhanced Features (Weeks 4-6)
- [ ] Segment analysis with vector similarity
- [ ] AI chatbot for performance questions
- [ ] Automated insights generation
- [ ] Export functionality (PDF reports)

### Phase 3: Multi-User (Weeks 7-10)
- [ ] User authentication
- [ ] PostgreSQL database backend
- [ ] Strava API integration
- [ ] Production deployment
- [ ] Mobile responsiveness

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io)
- Data processing powered by [StravaAnalyzer](https://github.com/hope0hermes/StravaAnalyzer)
- Inspired by the sports science community and Training Peaks

## 📧 Contact

Israel Barragan - [@hope0hermes](https://github.com/hope0hermes)

Project Link: [https://github.com/hope0hermes/ActivitiesViewer](https://github.com/hope0hermes/ActivitiesViewer)

---

**Made with ❤️ for cyclists who love data**
