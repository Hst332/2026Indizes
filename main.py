from __future__ import annotations

from datetime import datetime, timezone
import os
import pandas as pd

from config import ASSETS
from forecast_asset import forecast_asset
from forecast_writer import write_index_forecast_txt


def main() -> None:
    """Run live forecasts for all configured indices and write CSV + TXT."""
    os.makedirs("forecasts", exist_ok=True)

    results = []
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    for asset_name, cfg in ASSETS.items():
        print(f"Running forecast for {asset_name}")

        try:
            forecast = forecast_asset(asset_name, cfg)

            # forecast_asset already applies the trade filter and returns the final signal + rule
            results.append(
                {
                    "timestamp_utc": timestamp,
                    "asset": asset_name,
                    "ticker": cfg.get("ticker", ""),
                    "price_current": forecast.get("close", 0.0),
                    "price_prev_close": forecast.get("prev_close", 0.0),
                    "return_daily_pct": forecast.get("daily_return", 0.0),
                    "score": forecast.get("score", 0.0),
                    "prob_up": forecast.get("prob_up", 0.5),
                    "prob_down": forecast.get("prob_down", 0.5),
                    "confidence": forecast.get("confidence", 0.0),
                    "regime": forecast.get("regime", ""),
                    "signal_raw": "NA",
                    "signal_final": forecast.get("signal", "HOLD"),
                    "rule_label": forecast.get("rule", ""),
                    "data_status": "ok",
                }
            )

        except Exception as e:
            # Write an error row so the TXT isn't empty and you can see what failed
            print(f"ERROR {asset_name}: {e}")
            results.append(
                {
                    "timestamp_utc": timestamp,
                    "asset": asset_name,
                    "ticker": cfg.get("ticker", ""),
                    "price_current": 0.0,
                    "price_prev_close": 0.0,
                    "return_daily_pct": 0.0,
                    "score": 0.0,
                    "prob_up": 0.5,
                    "prob_down": 0.5,
                    "confidence": 0.0,
                    "regime": "error",
                    "signal_raw": "ERROR",
                    "signal_final": "ERROR",
                    "rule_label": f"ERROR: {type(e).__name__}: {e}",
                    "data_status": str(e),
                }
            )

    df = pd.DataFrame(results)

    # CSV
    csv_path = "forecasts/daily_index_forecast.csv"
    df.to_csv(csv_path, index=False)
    print("Saved:", csv_path)
    from forecast_tracker import append_history, validate_yesterday

    # TXT
    write_index_forecast_txt(df, "index_forecast.txt")
    print("Saved: index_forecast.txt")
    
    run_ts_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    append_history(df, run_ts_utc)
    validate_yesterday(df, run_ts_utc)


if __name__ == "__main__":
    main()
