# ActivitiesViewer 🚴‍♂️📊

**Version 2.0** - A goal-driven training companion with powerful analytics for Strava cyclists.

A comprehensive Streamlit dashboard for visualizing and analyzing cycling activities data from Strava. Built for athletes who want deep insights into their training performance, trends, and metrics with a focus on achieving power-to-weight ratio goals.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![UV](https://img.shields.io/badge/uv-package%20manager-green.svg)](https://github.com/astral-sh/uv)

## 🌟 Features (v2.0)

### 🎯 Goal-Driven Dashboard
- Visual progress tracking toward your power-to-weight goal (e.g., 4.0 W/kg)
- Performance Management Chart (PMC) with CTL/ATL/TSB indicators
- Recent activity sparklines for quick trend overview
- Smart status indicators (Ahead, On Track, Behind, Critical)

### 📊 Unified Analysis Page
The new **fluid explorer** replaces separate Year/Month/Week pages with one powerful interface:

#### Overview Mode
- Volume trends (daily/weekly/monthly aggregation based on range)
- Training Intensity Distribution (TID) with polarization analysis
- Training type distribution with workout classification
- Periodization check and phase identification
- Cumulative charts (distance, elevation, TSS)

#### Physiology Mode
- Efficiency Factor trends (Z2 rides only)
- Power-HR decoupling analysis
- Daily intensity patterns (for periods ≤30 days)
- Weekly TID evolution (for periods >4 weeks)
- Physiological readiness indicators

#### Power Profile Mode
- Power curve (Mean Maximum Power) with yearly best comparison
- Best performances across all durations (5s to 1hr)
- Key power benchmarks (Sprint, VO2max, FTP, Endurance)
- Clickable drill-down to activity details

#### Recovery Mode
- Monotony Index and Strain Index tracking
- Rest day analysis and recommendations
- Performance Management Chart (PMC) time series
- CTL (Fitness), ATL (Fatigue), TSB (Form) tracking
- Personalized recovery recommendations

### 🚴 Context-Aware Activity Detail
- Smart header showing top 4 metrics based on activity type
- Contextual analysis sections (intervals, endurance, race, recovery)
- Interactive route maps with GPS overlay
- Power and heart rate profiles over time
- Comprehensive metric grid with 100+ data points
- Zone distribution and comparative analysis

### 🤖 AI Coach
- Natural language querying of your training data
- Gemini-powered insights and recommendations
- Training pattern analysis
- Performance trend identification

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- [UV package manager](https://github.com/astral-sh/uv) (required - this project uses UV)
- Enriched activities data from [StravaAnalyzer](https://github.com/hope0hermes/StravaAnalyzer)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/hope0hermes/ActivitiesViewer.git
   cd ActivitiesViewer
   ```

2. **Install UV** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install dependencies**
   ```bash
   uv sync
   ```

4. **Configure your settings**
   ```bash
   cp examples/config.yaml config.yaml
   # Edit config.v2.0 uses the dual-file format from StravaAnalyzer:

1. **Generate enriched data** using StravaAnalyzer:
   ```bash
   strava-analyzer process --config config.yaml
   ```

   This creates:
   - `activities_raw.csv` - Metrics calculated over total elapsed time
   - `activities_moving.csv` - Metrics calculated over moving time only

2. **Configure data paths** in `config.yaml`:
   ```yaml
   # Athlete Settings
   ftp: 250              # Your current FTP in watts
   weight_kg: 70.0       # Your weight in kg
   max_hr: 185           # Your maximum heart rate

   # Goal Settings (optional)
   target_wkg: 4.0       # Target power-to-weight ratio
   target_date: "2026-06-01"  # Goal date

   # Data Paths
   data_dir: /path/to/your/data
   activities_raw_file: activities_raw.csv
   activities_moving_file: activities_moving.csv
   streams_dir: Streams  # Optional:   # Main dashboard (goal-driven)
│       ├── cli.py                     # Command-line interface
│       ├── config.py                  # Configuration management
│       ├── domain/                    # Domain models
│       │   ├── models.py              # Activity, Goal models
│       │   └── metrics.py             # MetricRegistry & definitions
│       ├── services/                  # Business logic
│       │   ├── activity_service.py    # Activity data access
│       │   ├── analysis_service.py    # Metric aggregation
│       │   └── goal_service.py        # Goal tracking logic
│       ├── repository/                # Data access layer
│       │   ├── base.py                # Repository interface
│       │   └── csv_repo.py            # CSV implementation
│       ├── pages/                     # Multi-page app
│       │   ├── 1_analysis.py          # Unified analysis (4 view modes)
│       │   ├── 3_detail.py            # Context-aware activity detail
│       │   ├── 5_ai_coach.py          # AI-powered insights
│       │   └── components/            # Reusable UI components
│       │       ├── dashboard_components.py
│       │       └── activity_detail_components.py
│       ├── data/                      # Static data (help texts)
│       └── utils/                     # Utility functions
├── tests/                             # Test suite
├── docs/                              # Documentation
├── examples/                          # Example configurations
└── pyproject.toml                     # Project metadata &
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

### Training Load Metrics
- **CTL (Chronic Training Load)**: 42-day fitness level
- **ATL (Acute Training Load)**: 7-day fatigue level
- **TSB (Training Stress Balance)**: Current form/freshness
- **ACWR (Acute:Chronic Workload Ratio)**: Injury risk indicator

### Power Profile Metrics
- **CP (Critical Power)**: Sustainable threshold power
- **W' (W-prime)**: Anaerobic work capacity
- **CP R²**: Model fit quality and reliability
- **AEI (Aerobic Efficiency Index)**: Aerobic vs anaerobic split

### Durability Metrics
- **Power Sustainability**: Ability to maintain power over duration
- **Variability Index (VI)**: Pacing consistency
- **Fatigue Index**: Power fade during activity
- **Power-HR Decoupling**: Aerobic fitness indicator

### Standard Metrics
- **Power**: NP, IF, TSS, power zones
- **Heart Rate**: HR zones, HR-TSS, efficiency factor
- **Comparative**: Week-over-week, month-over-month trends

### Full Documentation
📖 **[NEW_METRICS.md](docs/NEW_METRICS.md)** - Comprehensive guide including:
- Detailed definitions of all training load, power profile, and durability metrics
- Optimal ranges and interpretation guidelines
- Usage examples and training decision trees
- FAQ and technical details

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
