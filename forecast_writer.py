from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from trade_filter import RULES


def write_index_forecast_txt(df: pd.DataFrame, txt_file: str = "index_forecast.txt") -> str:
    """Write a human-readable forecast report.

    Expected columns (from main.py):
      asset, price_prev_close, price_current, return_daily_pct,
      signal_final, confidence, regime, prob_up, rule_label
    """
    runtime = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(f"Index Forecasts – {runtime}\n")
        f.write("=" * 110 + "\n\n")
        f.write("Index    | Prev Close | Current | Δ %    | Signal | Conf | Regime   | ProbUp | Rule\n")
        f.write("-" * 110 + "\n")

        if df is None or df.empty:
            f.write("No forecasts available.\n")
        else:
            for _, row in df.iterrows():
                asset = str(row.get("asset", ""))
                prev_close = float(row.get("price_prev_close", 0.0) or 0.0)
                close = float(row.get("price_current", 0.0) or 0.0)
                daily_return = float(row.get("return_daily_pct", 0.0) or 0.0)
                signal = str(row.get("signal_final", "HOLD"))
                conf = float(row.get("confidence", 0.0) or 0.0)
                regime = str(row.get("regime", ""))
                prob_up = float(row.get("prob_up", 0.5) or 0.5)
                rule = str(row.get("rule_label", ""))

                f.write(
                    f"{asset:<8} | {prev_close:>10.2f} | {close:>7.2f} | "
                    f"{daily_return:>6.2f}% | {signal:<6} | {conf:<4.2f} | "
                    f"{regime:<8} | {prob_up:>5.2f} | {rule}\n"
                )

        f.write("\n\nTRADING RULES (Thresholds)\n\n")
        for asset, rule in RULES.items():
            # RULES can be {'long','short'} or {'long_entry','short_entry'} depending on version
            long_th = rule.get("long_entry", rule.get("long", 0.0))
            short_th = rule.get("short_entry", rule.get("short", 0.0))
            f.write(f"{asset}\n")
            f.write(f"- LONG  if prob_up >= {float(long_th):.2f}\n")
            f.write(f"- SHORT if prob_up <= {float(short_th):.2f}\n")
            f.write("- Otherwise: HOLD\n")
            note = rule.get("note", "")
            if note:
                f.write(f"- Note: {note}\n")
            f.write("\n")

    return txt_file


def write_forecasts(forecasts: list[dict[str, Any]], out_dir: str = "forecasts") -> tuple[str, str]:
    """Backwards compatible helper: accepts list[dict] and writes CSV + TXT."""
    Path(out_dir).mkdir(exist_ok=True)
    df = pd.DataFrame(forecasts)

    csv_path = Path(out_dir) / "daily_index_forecast.csv"
    df.to_csv(csv_path, index=False)

    txt_file = write_index_forecast_txt(df, "index_forecast.txt")
    return str(csv_path), txt_file
