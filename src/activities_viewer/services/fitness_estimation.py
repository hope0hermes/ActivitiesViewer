"""
Fitness auto-estimation helper functions.

Pure computation functions for estimating FTP, max HR, and weight
from historical activity data. These are separated from the Streamlit
page for testability.
"""

import pandas as pd


def estimate_ftp_from_activities(
    df: pd.DataFrame, factor: float = 0.95
) -> pd.DataFrame:
    """Estimate FTP from 20-minute best power across activities.

    Uses the standard Coggan protocol: FTP ≈ 95% of best 20-min power.
    Looks at the ``best_power_20min`` column (if available) or falls back
    to ``mmp_20min`` / ``power_curve_20min`` / ``mmp_1200``.

    Args:
        df: Activities DataFrame.
        factor: Estimation factor (default 0.95).

    Returns:
        DataFrame with columns: date, best_20min, estimated_ftp, activity_name.
        Sorted by date descending.
    """
    power_20_col = None
    for col in ("best_power_20min", "mmp_20min", "power_curve_20min", "mmp_1200"):
        if col in df.columns:
            power_20_col = col
            break

    if power_20_col is None:
        return pd.DataFrame()

    mask = pd.to_numeric(df[power_20_col], errors="coerce").notna()
    data = df.loc[mask].copy()

    if data.empty:
        return pd.DataFrame()

    date_col = "start_date_local" if "start_date_local" in data.columns else "start_date"
    data["date"] = pd.to_datetime(data[date_col], errors="coerce")
    data = data.dropna(subset=["date"])

    data["best_20min"] = pd.to_numeric(data[power_20_col], errors="coerce")
    data["estimated_ftp"] = (data["best_20min"] * factor).round(0)
    data["activity_name"] = data.get("name", "")

    result = (
        data[["date", "best_20min", "estimated_ftp", "activity_name"]]
        .sort_values("date", ascending=False)
        .reset_index(drop=True)
    )
    return result


def estimate_max_hr_from_activities(df: pd.DataFrame) -> pd.DataFrame:
    """Estimate max HR from the highest heart rates recorded in activities.

    Looks at ``max_heartrate``, ``max_hr``, or ``max_heart_rate`` columns.

    Args:
        df: Activities DataFrame.

    Returns:
        DataFrame with columns: date, max_hr_recorded, activity_name.
        Sorted by max_hr_recorded descending, limited to top 50.
    """
    hr_col = None
    for col in ("max_heartrate", "max_hr", "max_heart_rate"):
        if col in df.columns:
            hr_col = col
            break

    if hr_col is None:
        return pd.DataFrame()

    mask = pd.to_numeric(df[hr_col], errors="coerce").notna()
    data = df.loc[mask].copy()

    if data.empty:
        return pd.DataFrame()

    date_col = "start_date_local" if "start_date_local" in data.columns else "start_date"
    data["date"] = pd.to_datetime(data[date_col], errors="coerce")
    data = data.dropna(subset=["date"])

    data["max_hr_recorded"] = pd.to_numeric(data[hr_col], errors="coerce").astype(int)
    data["activity_name"] = data.get("name", "")

    result = (
        data[["date", "max_hr_recorded", "activity_name"]]
        .sort_values("max_hr_recorded", ascending=False)
        .head(50)
        .reset_index(drop=True)
    )
    return result


def estimate_weight_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Extract weight data if available from activities.

    Args:
        df: Activities DataFrame.

    Returns:
        DataFrame with columns: date, weight_kg.
    """
    weight_col = None
    for col in ("rider_weight_kg", "weight_kg", "athlete_weight"):
        if col in df.columns:
            weight_col = col
            break

    if weight_col is None:
        return pd.DataFrame()

    mask = pd.to_numeric(df[weight_col], errors="coerce").notna()
    data = df.loc[mask].copy()

    if data.empty:
        return pd.DataFrame()

    date_col = "start_date_local" if "start_date_local" in data.columns else "start_date"
    data["date"] = pd.to_datetime(data[date_col], errors="coerce")
    data = data.dropna(subset=["date"])
    data["weight_kg"] = pd.to_numeric(data[weight_col], errors="coerce")

    return (
        data[["date", "weight_kg"]]
        .sort_values("date")
        .reset_index(drop=True)
    )


def compute_rolling_ftp(ftp_df: pd.DataFrame, window_days: int = 42) -> pd.DataFrame:
    """Compute rolling max estimated FTP over a window.

    Args:
        ftp_df: Output of estimate_ftp_from_activities().
        window_days: Rolling window in days.

    Returns:
        DataFrame with columns: date, rolling_ftp.
    """
    if ftp_df.empty:
        return pd.DataFrame()

    data = ftp_df.sort_values("date").set_index("date")
    daily = data["estimated_ftp"].resample("D").max().dropna()
    rolling = daily.rolling(f"{window_days}D", min_periods=1).max()

    return rolling.reset_index().rename(columns={"estimated_ftp": "rolling_ftp"})
