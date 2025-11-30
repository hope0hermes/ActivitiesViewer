"""
Pytest configuration and fixtures.
"""

import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_activities_csv(fixtures_dir: Path) -> Path:
    """Return path to sample activities CSV."""
    return fixtures_dir / "sample_activities.csv"
