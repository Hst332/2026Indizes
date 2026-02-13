from forecast_asset import forecast_asset
from config import ASSETS
import pandas as pd
from datetime import datetime, timezone
import os

from forecast_writer import write_index_forecast_txt


def main():
    os.makedirs("forecasts", exist_ok=True)

    all_results = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    for asset, cfg in ASSETS.items():
        print(f"Running live forecast for {asset}")
        try:
            r = forecast_asset(asset, cfg)
            r["date"] = now
            all_results.append(r)
        except Exception as e:
            print(f"ERROR {asset}: {e}")

    df = pd.DataFrame(all_results)

    csv_path = "forecasts/daily_index_forecast.csv"
    df.to_csv(csv_path, index=False)
    print("Saved:", csv_path)

    write_index_forecast_txt(df, "index_forecast.txt")
    print("Saved: index_forecast.txt")


if __name__ == "__main__":
    main()
