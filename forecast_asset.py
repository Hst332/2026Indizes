import yfinance as yf

from model_core import model_score
from forecast_utils import forecast_trend
from decision_engine import decide
from signal_guard import guard_dataframe


# --------------------------------------------------
# ASSET DEFINITIONS
# --------------------------------------------------

ASSETS = [
    ("GOLD", "GC=F", "STRONG_SUPPORT"),
    ("SILVER", "SI=F", "NO_SUPPORT"),
    ("NATURAL GAS", "NG=F", "STRONG_SUPPORT"),
    ("COPPER", "HG=F", "STRONG_SUPPORT"),
]


# --------------------------------------------------
# SINGLE ASSET FORECAST
# --------------------------------------------------

def forecast_asset(asset, ticker, macro_bias):
    # NOTE:
    # If you switch to intraday (e.g. interval="1m"), the guard will automatically
    # infer the bar timeframe from the index and block stale/NaN data.
    df = yf.download(ticker, period="6mo", interval="1d", progress=False)

    # Hard fail-safe: do NOT compute signals on empty data
    guard = guard_dataframe(
        asset=asset,
        df=df,
        required_cols=("Open", "High", "Low", "Close", "Volume"),
        critical_last_cols=("Close",),
        min_rows=30,
        timeframe_seconds=None,      # auto-infer
        max_stale_multiplier=2,
        assume_index_is_utc=True
    )

    # If data is unusable: return a blocked result instead of crashing the whole run
    if not guard.data_ok:
        close = float(df["Close"].iloc[-1]) if df is not None and len(df) > 0 and "Close" in df.columns else None
        return {
            "asset": asset,
            "close": round(close, 1) if close is not None else None,
            "score": 0.0,
            "signal": "NO_TRADE",
            "f_1_5": 0.0,
            "f_2_3": 0.0,
            "gpt_1_5d": "NA",
            "gpt_2_3w": "NA",
            "final": "NO_TRADE(DATA)",
            "zusatzinfo": f"DATA BLOCK: {guard.reason}",
            "data_ok": guard.data_ok,
            "last_bar_utc": guard.last_bar_utc,
            "age_s": guard.age_s,
            "rows": guard.rows,
            "nan_last": guard.nan_last,
            "stale": guard.stale,
            "timeframe_s": guard.timeframe_s,
            "guard_reason": guard.reason,
        }

    # Existing pipeline
    close = round(df["Close"].iloc[-1].item(), 1)

    score = model_score(df)

    f_1_5 = forecast_trend(df, days=5)
    f_2_3 = forecast_trend(df, days=15)

    # ---- MINI BACKTEST LOG ----
    print(
        f"{asset:<10} | SCORE={score:.3f} | "
        f"1-5D={f_1_5:+.3f} | 2-3W={f_2_3:+.3f} | "
        f"DATA_OK={guard.data_ok} AGE_s={guard.age_s}"
    )

    decision = decide(
        asset=asset,
        score=score,
        signal_1_5d=f_1_5,
        signal_2_3w=f_2_3,
        macro_bias=macro_bias
    )

    return {
        "asset": asset,
        "close": close,
        "score": score,
        "signal": decision["rule_signal"],   # nur Regelstatus
        "f_1_5": f_1_5,
        "f_2_3": f_2_3,
        "gpt_1_5d": decision["gpt_1_5d"],
        "gpt_2_3w": decision["gpt_2_3w"],
        "final": decision["action"],         # echte Handlung
        "zusatzinfo": decision["zusatzinfo"],

        # Guard fields (so du siehst sofort, ob du dem Signal trauen kannst)
        "data_ok": guard.data_ok,
        "last_bar_utc": guard.last_bar_utc,
        "age_s": guard.age_s,
        "rows": guard.rows,
        "nan_last": guard.nan_last,
        "stale": guard.stale,
        "timeframe_s": guard.timeframe_s,
        "guard_reason": guard.reason,
    }


# --------------------------------------------------
# RUN ALL ASSETS
# --------------------------------------------------

def run_all():
    results = []

    for asset, ticker, macro_bias in ASSETS:
        try:
            results.append(
                forecast_asset(asset, ticker, macro_bias)
            )
        except Exception as e:
            # Never crash the whole run for one asset
            results.append({
                "asset": asset,
                "close": None,
                "score": 0.0,
                "signal": "NO_TRADE",
                "f_1_5": 0.0,
                "f_2_3": 0.0,
                "gpt_1_5d": "NA",
                "gpt_2_3w": "NA",
                "final": "NO_TRADE(ERROR)",
                "zusatzinfo": f"ERROR: {type(e).__name__}: {e}",

                "data_ok": False,
                "last_bar_utc": "NA",
                "age_s": 10**9,
                "rows": 0,
                "nan_last": 1,
                "stale": 1,
                "timeframe_s": 0,
                "guard_reason": f"ERROR: {type(e).__name__}",
            })

    return results
