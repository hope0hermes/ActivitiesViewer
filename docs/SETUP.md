# Setup Guide

This guide will help you set up ActivitiesViewer for local development.

## Prerequisites

- **Python 3.12+** - Required for this project
- **UV** - Fast Python package manager (required)
- **Git** - Version control
- **Enriched activities data** - From StravaAnalyzer

## Quick Start

### 1. Install UV

UV is the required package manager for this project:

```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Add to PATH (usually automatic)
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
uv --version
```

### 2. Clone the Repository

```bash
git clone https://github.com/hope0hermes/ActivitiesViewer.git
cd ActivitiesViewer
```

### 3. Set Up Environment

```bash
# One command does it all!
uv sync

# UV automatically:
# - Creates .venv virtual environment
# - Installs runtime dependencies
# - Installs dev dependencies
# - Sets up the project
```

### 4. Configure Data Paths

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` with your actual data paths:

```env
# Example paths - update these!
DATA_DIR=/home/user/Workspace/ActivitiesViewer/dev/data
ACTIVITIES_PATH=/home/user/Workspace/ActivitiesViewer/dev/data_processed/activities_enriched.csv
SUMMARY_PATH=/home/user/Workspace/ActivitiesViewer/dev/data_processed/activity_summary.json
STREAMS_DIR=/home/user/Workspace/ActivitiesViewer/dev/data/Streams

# User settings
USER_FTP=295
USER_WEIGHT=77
USER_MAX_HR=185
```

### 5. Verify Setup

```bash
# Run tests
uv run pytest

# Validate configuration
uv run python -c "from activities_viewer.config import config; config.validate(); print('✅ Configuration valid')"
```

### 6. Run the Dashboard

```bash
# Using UV (recommended)
uv run streamlit run src/activities_viewer/app.py

# Or activate venv manually
source .venv/bin/activate  # Windows: .venv\Scripts\activate
streamlit run src/activities_viewer/app.py
```

The dashboard opens at `http://localhost:8501`.

> **Note**: With `uv run`, you don't need to manually activate the virtual environment!

## Development Workflow

### Daily Commands

```bash
# Run the app
uv run streamlit run src/activities_viewer/app.py

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/activities_viewer --cov-report=html

# Format code
uv run ruff format src/ tests/

# Lint code
uv run ruff check src/ tests/

# Fix auto-fixable issues
uv run ruff check --fix src/ tests/

# Type checking
uv run mypy src/activities_viewer
```

### Managing Dependencies

```bash
# Add a runtime dependency
uv add streamlit

# Add a dev dependency
uv add --dev pytest-mock

# Add to optional group
uv add --optional ai langchain

# Remove a dependency
uv remove package-name

# Update all dependencies
uv sync --upgrade

# List installed packages
uv pip list
```

### Testing

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_config.py

# With markers
uv run pytest -m unit          # Fast unit tests
uv run pytest -m integration   # Integration tests

# Verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x

# Show print statements
uv run pytest -s
```

### Code Quality

```bash
# Full quality check
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/activities_viewer
uv run pytest

# Or individually
uv run ruff format src/ tests/    # Format
uv run ruff check --fix src/      # Fix issues
uv run mypy src/                  # Type check
```

## Troubleshooting

### UV Not Found

```bash
# Check installation
which uv
uv --version

# Reinstall if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH
export PATH="$HOME/.local/bin:$PATH"

# Make permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

### Data Files Not Found

Ensure `.env` has correct paths and files exist:

```bash
# Check files exist
ls -la $DATA_DIR/data_processed/activities_enriched.csv
ls -la $DATA_DIR/data_processed/activity_summary.json
ls -la $DATA_DIR/Streams/

# Validate config
uv run python -c "from activities_viewer.config import config; config.validate()"
```

### Import Errors

```bash
# Resync environment
uv sync

# Or clean and resync
rm -rf .venv
uv sync
```

### Port Already in Use

```bash
# Use different port
uv run streamlit run src/activities_viewer/app.py --server.port=8502

# Or update .streamlit/config.toml
[server]
port = 8502
```

### Test Failures

```bash
# Verbose output to see details
uv run pytest -vv

# Show print statements
uv run pytest -s

# Run single test
uv run pytest tests/test_config.py::test_config_validation -v
```

### Python Version Issues

```bash
# Check Python version
python --version

# UV uses the system Python, ensure it's 3.12+
# On Ubuntu/Debian:
sudo apt install python3.12

# On macOS with Homebrew:
brew install python@3.12
```

## Next Steps

After successful setup:

1. **Explore the Code** - Check `src/activities_viewer/`
2. **Read Documentation**:
   - [Development Guide](DEVELOPMENT.md) - Detailed dev workflow
   - [Publishing Guide](PUBLISHING.md) - How to publish packages
   - [Implementation Plan](../DASHBOARD_IMPLEMENTATION_PLAN.md) - Feature roadmap
3. **Run Tests** - Make sure everything works
4. **Make Changes** - Follow conventional commits
5. **Create PR** - Automated CI/CD takes over

## Additional Resources

- [UV Documentation](https://github.com/astral-sh/uv)
- [Streamlit Documentation](https://docs.streamlit.io)
- [StravaAnalyzer](https://github.com/hope0hermes/StravaAnalyzer)
- [SharedWorkflows](https://github.com/hope0hermes/SharedWorkflows)
- [Conventional Commits](https://www.conventionalcommits.org/)

## Support

Having issues? Check:

1. This troubleshooting section
2. [GitHub Issues](https://github.com/hope0hermes/ActivitiesViewer/issues)
3. [Development Guide](DEVELOPMENT.md)

## Quick Reference

```bash
# Setup
uv sync                                          # Install dependencies
cp .env.example .env                             # Configure

# Run
uv run streamlit run src/activities_viewer/app.py

# Test
uv run pytest                                    # All tests
uv run pytest --cov                              # With coverage

# Quality
uv run ruff format src/ tests/                   # Format
uv run ruff check src/ tests/                    # Lint
uv run mypy src/activities_viewer                # Type check

# Dependencies
uv add <package>                                 # Add
uv remove <package>                              # Remove
uv sync --upgrade                                # Update all
```
