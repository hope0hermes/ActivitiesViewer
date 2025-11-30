"""
CSV implementation of the ActivityRepository.
"""

import pandas as pd
import streamlit as st
from pathlib import Path
from typing import List, Optional
from datetime import date, datetime

from activities_viewer.domain.models import Activity, YearSummary
from activities_viewer.repository.base import ActivityRepository


@st.cache_data(ttl=3600)
def _load_activities_df(file_path: Path) -> pd.DataFrame:
    """
    Load and preprocess the activities CSV.
    Cached by Streamlit to avoid reloading on every interaction.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Activities file not found: {file_path}")

    # Read CSV with semicolon separator
    df = pd.read_csv(file_path, sep=';')

    # Convert date columns
    df['start_date'] = pd.to_datetime(df['start_date'])
    df['start_date_local'] = pd.to_datetime(df['start_date_local'])

    # Ensure numeric columns are correct types (handling potential NaNs)
    numeric_cols = [
        'distance', 'moving_time', 'elapsed_time', 'total_elevation_gain',
        'moving_normalized_power', 'moving_training_stress_score'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Sort by date descending (most recent first)
    df = df.sort_values('start_date_local', ascending=False).reset_index(drop=True)

    return df


class CSVActivityRepository(ActivityRepository):
    """
    Repository that reads from a local CSV file (exported by StravaAnalyzer).
    """

    def __init__(self, file_path: Path):
        self.file_path = file_path
        # We load the DF lazily or on init.
        # Since _load_activities_df is cached, calling it here is cheap after first run.
        self._df = _load_activities_df(self.file_path)

    def get_activity(self, activity_id: int) -> Optional[Activity]:
        row = self._df[self._df['id'] == activity_id]
        if row.empty:
            return None

        return Activity(**row.iloc[0].to_dict())

    def get_activities(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Activity]:

        df_filtered = self._df

        if start_date:
            df_filtered = df_filtered[df_filtered['start_date_local'].dt.date >= start_date]

        if end_date:
            df_filtered = df_filtered[df_filtered['start_date_local'].dt.date <= end_date]

        # Convert to list of Activity objects
        # iterrows is slow, but for <2000 activities it's acceptable for MVP.
        # For better performance, we can use to_dict('records')
        return [Activity(**record) for record in df_filtered.to_dict('records')]

    def get_year_summary(self, year: int) -> YearSummary:
        df_year = self._df[self._df['start_date_local'].dt.year == year]

        if df_year.empty:
            return YearSummary(
                year=year,
                total_distance=0,
                total_time=0,
                total_elevation=0,
                activity_count=0
            )

        return YearSummary(
            year=year,
            total_distance=df_year['distance'].sum(),
            total_time=df_year['moving_time'].sum(),
            total_elevation=df_year['total_elevation_gain'].sum(),
            activity_count=len(df_year),
            avg_power=df_year['moving_normalized_power'].mean(),
            total_tss=df_year['moving_training_stress_score'].sum()
        )

    def get_activity_stream(self, activity_id: int) -> pd.DataFrame:
        """
        Load stream data for a specific activity.
        Assumes streams are stored in a 'Streams' directory relative to the data file.
        """
        # Assuming file_path is .../data_enriched/activities_enriched.csv
        # And streams are in .../data/Streams/stream_{id}.csv
        # We need to navigate from data_enriched to data/Streams

        # This path logic depends on the project structure.
        # Based on workspace info:
        # dev/data/Streams/
        # dev/data_enriched/activities_enriched.csv

        streams_dir = self.file_path.parent.parent / "data" / "Streams"
        stream_file = streams_dir / f"stream_{activity_id}.csv"

        if not stream_file.exists():
            return pd.DataFrame()

        try:
            return pd.read_csv(stream_file, sep=';')
        except Exception:
            return pd.DataFrame()
