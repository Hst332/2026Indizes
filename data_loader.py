import yfinance as yf
import pandas as pd


def _flatten_columns(cols):
    """
    yfinance can return MultiIndex columns (tuples). Flatten them safely.
    """
    out = []
    for c in cols:
        if isinstance(c, tuple):
            # take first non-empty element
            c2 = next((x for x in c if x not in (None, "", " ")), c[0])
            out.append(str(c2).lower())
        else:
            out.append(str(c).lower())
    return out


def load_market_data(ticker, cfg=None):
    print(f"Loading market data for {ticker}")

    # Daily data (safe default for backtest AND forecast)
    df_daily = yf.download(
        ticker,
        period="10y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False
    )

    # Intraday data for live forecast (optional)
    df_intraday = yf.download(
        ticker,
        period="5d",
        interval="1h",
        auto_adjust=True,
        progress=False,
        threads=False
    )

    if df_daily.empty and df_intraday.empty:
        raise ValueError(f"No data returned for {ticker}")

    # Combine + sort safely
    df = pd.concat([df_daily, df_intraday], axis=0)

    # Normalize datetime index to avoid tz-aware vs tz-naive sorting errors
    # -> always utc aware then convert to naive
    df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)

    df = df[~df.index.duplicated(keep="last")].sort_index()

    # Normalize column names
    df.columns = _flatten_columns(df.columns)

    # Ensure we have "close"
    # (auto_adjust=True gives close, sometimes adj close)
    if "close" not in df.columns:
        if "adj close" in df.columns:
            df["close"] = df["adj close"]
        elif "price" in df.columns:
            df["close"] = df["price"]
        else:
            raise KeyError(f"'close' not found in columns: {df.columns.tolist()}")

    return df
