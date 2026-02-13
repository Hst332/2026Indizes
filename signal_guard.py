from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any

import pandas as pd


@dataclass
class GuardResult:
    asset: str
    data_ok: bool
    last_bar_utc: str              # full timestamp (backward compatible)
    last_bar_utc_display: str      # pretty display (no seconds / date-only if 00:00)
    age_s: int
    age_h: float
    rows: int
    nan_last: int
    stale: int
    timeframe_s: int
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _safe_int(x, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def infer_timeframe_seconds(index: pd.Index, fallback_seconds: int = 86400) -> int:
    try:
        if not isinstance(index, pd.DatetimeIndex):
            return fallback_seconds
        if len(index) < 3:
            return fallback_seconds

        n = min(len(index), 50)
        idx = index[-n:]
        deltas = (idx[1:] - idx[:-1]).to_series().dt.total_seconds().dropna()

        if deltas.empty:
            return fallback_seconds

        tf = int(round(float(deltas.median())))
        if tf <= 0:
            return fallback_seconds

        return max(1, min(tf, 7 * 86400))
    except Exception:
        return fallback_seconds


def _last_scalar(df: pd.DataFrame, col: str):
    try:
        v = df[col].iloc[-1]
        if isinstance(v, pd.Series):
            v = v.dropna().iloc[0] if not v.dropna().empty else v.iloc[0]
        return v
    except Exception:
        return None


def _format_display(dt_utc: datetime) -> str:
    if dt_utc.hour == 0 and dt_utc.minute == 0 and dt_utc.second == 0:
        return dt_utc.strftime("%Y-%m-%d")
    return dt_utc.strftime("%Y-%m-%d %H:%M")


def guard_dataframe(
    asset: str,
    df: Optional[pd.DataFrame],
    *,
    now_utc: Optional[datetime] = None,
    required_cols: Tuple[str, ...] = ("Open", "High", "Low", "Close"),
    critical_last_cols: Tuple[str, ...] = ("Close",),
    min_rows: int = 30,
    timeframe_seconds: Optional[int] = None,
    max_stale_multiplier: int = 2,
    assume_index_is_utc: bool = True,
) -> GuardResult:

    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    if df is None or len(df) == 0:
        return GuardResult(
            asset, False, "NA", "NA",
            10**9, float(10**9)/3600, 0, 1, 1,
            _safe_int(timeframe_seconds, 0),
            "EMPTY_DF"
        )

    rows = len(df)
    reasons = []
    data_ok = True

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        data_ok = False
        reasons.append("MISSING_COLS")

    if rows < min_rows:
        data_ok = False
        reasons.append("HISTORY_SHORT")

    try:
        last_bar = df.index[-1]
        if isinstance(last_bar, pd.Timestamp):
            last_bar = last_bar.to_pydatetime()
    except Exception:
        return GuardResult(
            asset, False, "NA", "NA",
            10**9, float(10**9)/3600, rows, 1, 1,
            _safe_int(timeframe_seconds, 0),
            "BAD_INDEX"
        )

    if last_bar.tzinfo is None:
        last_bar = last_bar.replace(tzinfo=timezone.utc)

    last_bar_utc = last_bar.astimezone(timezone.utc)

    tf = timeframe_seconds if timeframe_seconds else infer_timeframe_seconds(df.index)
    tf = _safe_int(tf, 86400)

    age_s = _safe_int((now_utc - last_bar_utc).total_seconds(), 10**9)
    age_h = round(age_s / 3600.0, 2)

    stale = 1 if age_s > tf * max_stale_multiplier else 0
    if stale:
        data_ok = False
        reasons.append("STALE_DATA")

    nan_last = 0
    for c in critical_last_cols:
        v = _last_scalar(df, c)
        if v is None or pd.isna(v):
            nan_last = 1
            break

    if nan_last:
        data_ok = False
        reasons.append("NAN_LAST_ROW")

    return GuardResult(
        asset,
        data_ok,
        last_bar_utc.strftime("%Y-%m-%d %H:%M:%S"),
        _format_display(last_bar_utc),
        age_s,
        age_h,
        rows,
        nan_last,
        stale,
        tf,
        "OK" if data_ok else ";".join(reasons),
    )
