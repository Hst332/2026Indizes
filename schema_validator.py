import pandas as pd

FORECAST_COLUMNS = [
    "timestamp_utc",
    "asset",
    "ticker",
    "price_current",
    "price_prev_close",
    "return_daily_pct",
    "score",
    "prob_up",
    "prob_down",
    "confidence",
    "regime",
    "rule_long_min",
    "rule_short_max",
    "signal_raw",
    "signal_final",
    "rule_label",
    "data_status",
]

def validate_forecast_dataframe(df: pd.DataFrame):

    # 1. Spalten prüfen
    missing = [c for c in FORECAST_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing forecast columns: {missing}")

    # 2. Reihenfolge erzwingen
    df = df[FORECAST_COLUMNS]

    # 3. Leere Ergebnisse verhindern
    if df.empty:
        raise ValueError("Forecast DataFrame is empty.")

    # 4. Numerische Felder prüfen
    numeric_cols = [
        "price_current",
        "price_prev_close",
        "return_daily_pct",
        "score",
        "prob_up",
        "prob_down",
        "confidence",
        "rule_long_min",
        "rule_short_max",
    ]

    for col in numeric_cols:
        if df[col].isnull().any():
            raise ValueError(f"NaN values detected in column: {col}")

    return df
