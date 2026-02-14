import pandas as pd

REQUIRED_COLUMNS = [
    "asset",
    "signal",
    "confidence",
    "prob_up",
    "prob_down",
    "regime",
    "close",
    "prev_close",
    "daily_return",
    "rule",
    "timestamp_utc",
]

def validate_forecast_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and return df (so main can do df = validate_forecast_dataframe(df))."""
    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError("Forecast result is not a DataFrame")

    if df.empty:
        return df

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Forecast DataFrame missing columns: {missing}")

    return df
