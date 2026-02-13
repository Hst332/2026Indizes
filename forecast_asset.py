import yfinance as yf
import pandas as pd

from model_core import model_score
from forecast_utils import forecast_trend
from decision_engine import decide
from signal_guard import guard_dataframe


ASSETS = [
    ("GOLD", "GC=F", "STRONG_SUPPORT"),
    ("SILVER", "SI=F", "NO_SUPPORT"),
    ("NATURAL GAS", "NG=F", "STRONG_SUPPORT"),
    ("COPPER", "HG=F", "STRONG_SUPPORT"),
]


def _normalize_yfinance_df(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def _last_scalar(df, col):
    v = df[col].iloc[-1]
    if isinstance(v, pd.Series):
        v = v.dropna().iloc[0] if not v.dropna().empty else v.iloc[0]
    return float(v)


def forecast_asset(asset, ticker, macro_bias):

    df = yf.download(ticker, period="6mo", interval="1d", progress=False)
    df = _normalize_yfinance_df(df)

    guard = guard_dataframe(asset, df)

    if not guard.data_ok:
        return {
            "asset": asset,
            "close": None,
            "score": 0.0,
            "signal": "NO_TRADE",
            "f_1_5": 0.0,
            "f_2_3": 0.0,
            "gpt_1_5d": "NA",
            "gpt_2_3w": "NA",
            "final": "NO_TRADE(DATA)",
            "zusatzinfo": guard.reason,
            **guard.to_dict()
        }

    close = round(_last_scalar(df, "Close"), 1)

    score = model_score(df)
    f_1_5 = forecast_trend(df, days=5)
    f_2_3 = forecast_trend(df, days=15)

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
        "signal": decision["rule_signal"],
        "f_1_5": f_1_5,
        "f_2_3": f_2_3,
        "gpt_1_5d": decision["gpt_1_5d"],
        "gpt_2_3w": decision["gpt_2_3w"],
        "final": decision["action"],
        "zusatzinfo": decision["zusatzinfo"],
        **guard.to_dict()
    }


def run_all():
    results = []
    for asset, ticker, macro_bias in ASSETS:
        try:
            results.append(forecast_asset(asset, ticker, macro_bias))
        except Exception as e:
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
                "zusatzinfo": str(e),
                "data_ok": False
            })
    return results
