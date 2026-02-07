# Development Guide

## Development Environment Setup

This project uses **UV** as the package manager. UV is a fast, modern Python package manager that replaces pip, poetry, and other tools.

### Initial Setup

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/hope0hermes/ActivitiesViewer.git
cd ActivitiesViewer

# Sync environment (creates .venv and installs all dependencies)
uv sync

# Verify installation
uv run python -c "import activities_viewer; print(activities_viewer.__version__)"
```

### Daily Workflow

```bash
# Run the dashboard
uv run streamlit run src/activities_viewer/app.py

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/activities_viewer --cov-report=html

# Format code
uv run ruff format src/ tests/

# Lint code
uv run ruff check src/ tests/

# Fix auto-fixable lint issues
uv run ruff check --fix src/ tests/

# Type checking
uv run mypy src/activities_viewer
```

### Adding Dependencies

```bash
# Add a runtime dependency
uv add streamlit

# Add a dev dependency
uv add --dev pytest

# Add an optional dependency group
uv add --optional ai langchain

# Remove a dependency
uv remove package-name

# Update dependencies
uv sync --upgrade
```

## Project Structure

```
ActivitiesViewer/
├── .github/                        # GitHub workflows and templates
│   ├── workflows/
│   │   ├── tests.yml              # CI: Tests and linting
│   │   ├── commitlint.yml         # Commit message validation
│   │   ├── release.yml            # Automated version bumping
│   │   ├── create-release.yml     # GitHub release creation
│   │   └── publish.yml            # Publish to Devpi
│   ├── CODEOWNERS                 # Code ownership
│   └── pull_request_template.md   # PR template
├── src/
│   └── activities_viewer/
│       ├── __init__.py            # Package version
│       ├── app.py                 # Main Streamlit app
│       ├── config.py              # Configuration management
│       ├── cli.py                 # CLI entry point
│       ├── pages/                 # Streamlit pages
│       ├── data/                  # Data loading
│       ├── components/            # UI components
│       ├── analytics/             # Business logic
│       ├── viz/                   # Visualizations
│       └── utils/                 # Utilities
├── tests/                         # Test suite
├── docs/                          # Documentation
├── scripts/                       # Utility scripts
├── assets/                        # Static assets
├── .streamlit/                    # Streamlit config
├── pyproject.toml                 # Project configuration
├── README.md                      # User documentation
└── CHANGELOG.md                   # Version history
```

## CI/CD Pipeline

This project uses SharedWorkflows for consistent CI/CD:

### Workflows

1. **Tests** (`.github/workflows/tests.yml`)
   - Runs on: PRs to main, pushes to main
   - Actions: Linting (ruff, mypy) + Testing (pytest)
   - Uses: `hope0hermes/SharedWorkflows/.github/workflows/reusable-tests.yml@main`

2. **Commit Linting** (`.github/workflows/commitlint.yml`)
   - Runs on: PRs to main
   - Validates: Conventional commit format
   - Uses: `hope0hermes/SharedWorkflows/.github/workflows/reusable-commitlint.yml@main`

3. **Release** (`.github/workflows/release.yml`)
   - Runs on: Pushes to main
   - Creates: Version bump PRs based on conventional commits
   - Uses: `hope0hermes/SharedWorkflows/.github/workflows/reusable-release.yml@main`
   - Requires: `PAT_TOKEN` secret

4. **Create Release** (`.github/workflows/create-release.yml`)
   - Runs on: Pushes to main (after version bump)
   - Creates: GitHub releases with changelog
   - Uses: `hope0hermes/SharedWorkflows/.github/workflows/reusable-create-release.yml@main`

5. **Publish** (`.github/workflows/publish.yml`)
   - Runs on: Manual dispatch
   - Publishes: Package to Devpi private index
   - Uses: `hope0hermes/SharedWorkflows/.github/workflows/reusable-publish.yml@main`
   - Requires: `DEVPI_PASSWORD`, `DEVPI_URL`, `DEVPI_USERNAME` secrets

### Conventional Commits

All commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat:` - New feature (minor version bump)
- `fix:` - Bug fix (patch version bump)
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting)
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks
- `ci:` - CI/CD changes
- `build:` - Build system changes

**Breaking Changes:**
- Add `!` after type: `feat!:` or add `BREAKING CHANGE:` in footer
- Triggers major version bump

**Examples:**
```bash
git commit -m "feat: add power curve visualization"
git commit -m "fix: correct CTL calculation for missing data"
git commit -m "docs: update installation instructions"
git commit -m "feat!: redesign data loading API"
```

## Testing

### Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_config.py

# With coverage
uv run pytest --cov=src/activities_viewer --cov-report=html

# Specific markers
uv run pytest -m unit
uv run pytest -m integration

# Verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x
```

### Writing Tests

```python
# tests/test_example.py
import pytest
from activities_viewer.config import Config

def test_config_validation():
    """Test that config validation works correctly."""
    config = Config()
    # Test logic here
    assert config.PAGE_TITLE == "Activities Viewer"

@pytest.mark.unit
def test_fast_unit():
    """Fast unit test."""
    pass

@pytest.mark.integration
def test_with_filesystem(tmp_path):
    """Integration test using filesystem."""
    pass
```

## Code Quality

### Linting

```bash
# Check with ruff
uv run ruff check src/ tests/

# Fix auto-fixable issues
uv run ruff check --fix src/ tests/

# Check formatting
uv run ruff format --check src/ tests/

# Format code
uv run ruff format src/ tests/
```

### Type Checking

```bash
# Check types
uv run mypy src/activities_viewer

# Check specific file
uv run mypy src/activities_viewer/config.py
```

## Building and Publishing

### Building

```bash
# Build distribution packages
uv build

# Output: dist/activities_viewer-0.1.0-py3-none-any.whl
#         dist/activities_viewer-0.1.0.tar.gz
```

### Publishing to Devpi

```bash
# Manual publish (requires authentication)
uv publish \
  --publish-url http://144.24.233.179/hope0hermes/dev/ \
  --username hope0hermes \
  --password <password>

# Or use GitHub Actions (workflow_dispatch)
# Navigate to Actions → Publish to Devpi → Run workflow
```

### Installing from Devpi

```bash
# Install from private index
pip install --index-url http://144.24.233.179/hope0hermes/dev/ activities-viewer

# With UV
uv pip install --index-url http://144.24.233.179/hope0hermes/dev/ activities-viewer
```

## Release Process

1. **Develop features** on feature branches using conventional commits
2. **Create PR** to main - triggers tests and commit linting
3. **Merge PR** - triggers release workflow
4. **Release workflow** analyzes commits and creates version bump PR
5. **Merge version PR** - triggers create-release workflow
6. **GitHub release** is created automatically
7. **Publish manually** via GitHub Actions workflow_dispatch

## Configuration

### Environment Variables

Create a `.env` file:

```bash
cp .env.example .env
```

Edit with your paths:

```env
DATA_DIR=/path/to/data
ACTIVITIES_PATH=/path/to/activities_enriched.csv
SUMMARY_PATH=/path/to/activity_summary.json
STREAMS_DIR=/path/to/Streams

USER_FTP=295
USER_WEIGHT=77
USER_MAX_HR=185
```

### Streamlit Configuration

Edit `.streamlit/config.toml` for UI customization:

```toml
[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"

[server]
port = 8501
```

## Troubleshooting

### UV Commands Not Working

```bash
# Ensure UV is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Or reinstall UV
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Import Errors

```bash
# Resync environment
uv sync

# Clear cache
rm -rf .venv
uv sync
```

### Test Failures

```bash
# Verbose output
uv run pytest -vv

# Show print statements
uv run pytest -s

# Run specific test
uv run pytest tests/test_config.py::test_config_validation -v
```

## Resources

- [UV Documentation](https://github.com/astral-sh/uv)
- [Streamlit Documentation](https://docs.streamlit.io)
- [SharedWorkflows](https://github.com/hope0hermes/SharedWorkflows)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Devpi Documentation](https://devpi.net/)
