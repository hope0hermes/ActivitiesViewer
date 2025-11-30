"""
Tests for configuration module.
"""

import pytest
from activities_viewer.config import Settings, load_settings


def test_settings_has_required_attributes():
    """Test that Settings class has all required attributes."""
    settings = Settings()
    assert hasattr(settings, "data_dir")
    assert hasattr(settings, "activities_enriched_file")
    assert hasattr(settings, "activity_summary_file")
    assert hasattr(settings, "streams_dir")
    assert hasattr(settings, "ftp")
    assert hasattr(settings, "weight_kg")
    assert hasattr(settings, "max_hr")
    assert hasattr(settings, "page_title")
    assert hasattr(settings, "page_icon")


def test_settings_user_values_are_numeric():
    """Test that user settings have correct types."""
    settings = Settings()
    assert isinstance(settings.ftp, float)
    assert isinstance(settings.weight_kg, float)
    assert isinstance(settings.max_hr, int)


def test_settings_get_stream_path():
    """Test stream path generation."""
    settings = Settings()
    activity_id = 123456
    stream_path = settings.get_stream_path(activity_id)
    assert "stream_123456.csv" in str(stream_path)
