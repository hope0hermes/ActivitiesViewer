"""Shared metric calculation utilities."""

from typing import Any

import pandas as pd


def safe_mean(series: pd.Series) -> float:
    """Calculate mean, handling NaN values. Returns 0 if empty."""
    valid = series.dropna()
    return float(valid.mean()) if len(valid) > 0 else 0.0


def safe_sum(series: pd.Series) -> float:
    """Calculate sum, handling NaN values."""
    return float(series.fillna(0).sum())


def safe_max(series: pd.Series) -> float:
    """Calculate max, handling NaN values. Returns 0 if empty."""
    valid = series.dropna()
    return float(valid.max()) if len(valid) > 0 else 0.0


def get_metric_from_df(
    df: pd.DataFrame, column: str, agg: str = "sum", default: float = 0
) -> float:
    """Safely get aggregated metric from DataFrame.

    Args:
        df: Source DataFrame
        column: Column name to aggregate
        agg: Aggregation method ("sum", "mean", "max", "min")
        default: Default value if column missing or empty

    Returns:
        Aggregated value or default
    """
    if column not in df.columns:
        return default

    series = df[column].dropna()
    if series.empty:
        return default

    if agg == "sum":
        return float(series.sum())
    elif agg == "mean":
        return float(series.mean())
    elif agg == "max":
        return float(series.max())
    elif agg == "min":
        return float(series.min())

    return default


def get_metric_from_object(obj: Any, field: str, default: Any = None) -> Any:
    """Safely get a metric value from an object, handling NaN.

    Args:
        obj: Source object (Activity, etc.)
        field: Attribute name
        default: Default value if missing or NaN

    Returns:
        Attribute value or default
    """
    val = getattr(obj, field, default)
    if val is not None and pd.notna(val):
        return val
    return default


def calculate_tid(
    df: pd.DataFrame, metric_view: str = "Moving", time_col: str = "moving_time"
) -> dict[str, float]:
    """Calculate time-weighted Training Intensity Distribution.

    Args:
        df: DataFrame with TID columns and time column
        metric_view: View mode ("Moving" or "Raw"), for compatibility (not used)
        time_col: Column to use for time-weighting

    Returns:
        Dictionary with z1, z2, z3 percentages
    """
    z1_col = "power_tid_z1_percentage"
    z2_col = "power_tid_z2_percentage"
    z3_col = "power_tid_z3_percentage"

    required_cols = [z1_col, z2_col, z3_col, time_col]
    if not all(col in df.columns for col in required_cols):
        return {"z1": 0, "z2": 0, "z3": 0}

    total_time = df[time_col].sum()
    if total_time == 0:
        return {"z1": 0, "z2": 0, "z3": 0}

    z1 = (df[z1_col].fillna(0) * df[time_col]).sum() / total_time
    z2 = (df[z2_col].fillna(0) * df[time_col]).sum() / total_time
    z3 = (df[z3_col].fillna(0) * df[time_col]).sum() / total_time

    return {"z1": z1, "z2": z2, "z3": z3}
