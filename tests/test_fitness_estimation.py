"""Tests for Fitness Auto-Estimation page functions."""

import pandas as pd

from activities_viewer.services import fitness_estimation as feh

# ═══════════════════════════════════════════════════════════════════════════
# Test helpers – we import from the page module directly
# ═══════════════════════════════════════════════════════════════════════════


class TestEstimateFTPFromActivities:
    """Tests for estimate_ftp_from_activities."""

    def _make_df(self, **kwargs):
        """Build a minimal activities DataFrame."""
        defaults = {
            "start_date_local": ["2024-06-01", "2024-06-15", "2024-07-01"],
            "best_power_20min": [250, 260, 270],
            "name": ["Ride 1", "Ride 2", "Ride 3"],
        }
        defaults.update(kwargs)
        return pd.DataFrame(defaults)

    def test_basic_estimation(self):
        df = self._make_df()
        result = feh.estimate_ftp_from_activities(df)
        assert not result.empty
        assert len(result) == 3
        # 95% of 270 = 256.5 → rounds to 256 or 257
        assert result.iloc[0]["estimated_ftp"] == round(270 * 0.95)

    def test_custom_factor(self):
        df = self._make_df()
        result = feh.estimate_ftp_from_activities(df, factor=0.90)
        assert result.iloc[0]["estimated_ftp"] == round(270 * 0.90)

    def test_missing_power_column(self):
        df = pd.DataFrame({"start_date_local": ["2024-01-01"], "name": ["Ride"]})
        result = feh.estimate_ftp_from_activities(df)
        assert result.empty

    def test_fallback_columns(self):
        """Should pick up mmp_1200 if best_power_20min is absent."""
        df = pd.DataFrame({
            "start_date_local": ["2024-01-01"],
            "mmp_1200": [300],
            "name": ["Ride"],
        })
        result = feh.estimate_ftp_from_activities(df)
        assert not result.empty
        assert result.iloc[0]["estimated_ftp"] == round(300 * 0.95)

    def test_nan_values_filtered(self):
        df = pd.DataFrame({
            "start_date_local": ["2024-01-01", "2024-01-02"],
            "best_power_20min": [250, None],
            "name": ["Ride 1", "Ride 2"],
        })
        result = feh.estimate_ftp_from_activities(df)
        assert len(result) == 1

    def test_sorted_descending_by_date(self):
        df = self._make_df()
        result = feh.estimate_ftp_from_activities(df)
        dates = result["date"].tolist()
        assert dates == sorted(dates, reverse=True)


class TestEstimateMaxHRFromActivities:
    """Tests for estimate_max_hr_from_activities."""

    def _make_df(self, **kwargs):
        defaults = {
            "start_date_local": ["2024-01-01", "2024-02-01", "2024-03-01"],
            "max_heartrate": [175, 185, 180],
            "name": ["Run 1", "Run 2", "Run 3"],
        }
        defaults.update(kwargs)
        return pd.DataFrame(defaults)

    def test_basic_estimation(self):
        df = self._make_df()
        result = feh.estimate_max_hr_from_activities(df)
        assert not result.empty
        # Sorted by max HR, highest first
        assert result.iloc[0]["max_hr_recorded"] == 185

    def test_missing_hr_column(self):
        df = pd.DataFrame({"start_date_local": ["2024-01-01"], "name": ["Ride"]})
        result = feh.estimate_max_hr_from_activities(df)
        assert result.empty

    def test_alternative_column_name(self):
        df = pd.DataFrame({
            "start_date_local": ["2024-01-01"],
            "max_hr": [190],
            "name": ["Ride"],
        })
        result = feh.estimate_max_hr_from_activities(df)
        assert not result.empty
        assert result.iloc[0]["max_hr_recorded"] == 190

    def test_limits_to_50_results(self):
        df = pd.DataFrame({
            "start_date_local": [f"2024-{i:02d}-01" for i in range(1, 13)] * 6,
            "max_heartrate": list(range(140, 212)),
            "name": [f"Activity {i}" for i in range(72)],
        })
        result = feh.estimate_max_hr_from_activities(df)
        assert len(result) <= 50


class TestEstimateWeightTrend:
    """Tests for estimate_weight_trend."""

    def test_basic(self):
        df = pd.DataFrame({
            "start_date_local": ["2024-01-01", "2024-02-01"],
            "rider_weight_kg": [75.0, 74.5],
        })
        result = feh.estimate_weight_trend(df)
        assert not result.empty
        assert len(result) == 2

    def test_missing_column(self):
        df = pd.DataFrame({"start_date_local": ["2024-01-01"], "name": ["Ride"]})
        result = feh.estimate_weight_trend(df)
        assert result.empty

    def test_sorted_ascending_by_date(self):
        df = pd.DataFrame({
            "start_date_local": ["2024-03-01", "2024-01-01", "2024-02-01"],
            "weight_kg": [74.0, 76.0, 75.0],
        })
        result = feh.estimate_weight_trend(df)
        dates = result["date"].tolist()
        assert dates == sorted(dates)


class TestComputeRollingFTP:
    """Tests for compute_rolling_ftp."""

    def test_basic_rolling(self):
        ftp_df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=10, freq="7D"),
            "estimated_ftp": [250 + i * 2 for i in range(10)],
            "best_20min": [263 + i * 2 for i in range(10)],
            "activity_name": [f"Ride {i}" for i in range(10)],
        })
        result = feh.compute_rolling_ftp(ftp_df, window_days=28)
        assert not result.empty
        # Last value should be close to the max recent FTP
        assert result.iloc[-1]["rolling_ftp"] >= 266

    def test_empty_input(self):
        result = feh.compute_rolling_ftp(pd.DataFrame())
        assert result.empty
