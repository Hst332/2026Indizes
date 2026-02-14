from __future__ import annotations

from datetime import datetime

from data_loader import load_market_data
from model_core import run_model
from decision_engine import generate_signal
from regime_adjustment import adjust_for_regime
from trade_filter import apply_trade_filter


def forecast_asset(asset_name: str, asset_cfg: dict, df_override=None) -> dict:
    # Daten
    df = df_override if df_override is not None else load_market_data(asset_cfg["ticker"], asset_cfg)

    # Standardisiere Column-Names
    df.columns = [str(c).lower() for c in df.columns]

    if "close" not in df.columns:
        raise KeyError("close")

    model_output = run_model(df)
    regime = adjust_for_regime(df)
    decision = generate_signal(model_output, regime)

    latest_close = float(df["close"].iloc[-1])
    prev_close = float(df["close"].iloc[-2])
    daily_return_pct = ((latest_close / prev_close) - 1.0) * 100.0

    # prob_up/prob_down robust
    prob_up = float(decision.get("prob_up", 0.5))
    prob_down = 1.0 - prob_up

    # Filter (Maßnahme 1-4)
    decision = apply_trade_filter(asset_name, decision, df, daily_return_pct)

    return {
        "asset": asset_name,
        "timestamp_utc": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "signal": decision.get("signal", "HOLD"),
        "confidence": float(decision.get("confidence", 0.0)),
        "prob_up": round(prob_up, 4),
        "prob_down": round(prob_down, 4),
        "regime": str(regime),
        "close": round(latest_close, 2),
        "prev_close": round(prev_close, 2),
        "daily_return": round(daily_return_pct, 2),
        "rule": decision.get("rule", "no_rule"),
    }
