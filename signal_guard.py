"""
signal_guard.py

Data-Safety Guard for trading signals.

Purpose:
- Detect empty/short data, missing columns, NaNs on the last bar
- Detect stale data (last bar too old vs inferred/declared timeframe)
- Return a compact dict you can attach to your result output
- Optionally force FINAL = NO_TRADE(DATA) in your writer/decision layer

This module is intentionally dependency-light: only pandas + stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any

import pandas as pd


@dataclass
class GuardResult:
    asset: str
    data_ok: bool
    last_bar_utc: str
    age_s: int
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


def infer_timeframe_seconds(index: pd.Index, *, fallback_seconds: int = 86400) -> int:
    """Infer bar timeframe from a DateTimeIndex (median delta of last ~50 points)."""
    try:
        if not isinstance(index, (pd.DatetimeIndex,)):
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

        tf = max(1, min(tf, 7 * 86400))
        return tf
    except Exception:
        return fallback_seconds


def guard_dataframe(
    asset: str,
    df: Optional[pd.DataFrame],
    *,
    now_utc: Optional[datetime] = None,
    required_cols: Tuple[str, ...] = ("Open", "High", "Low", "Close", "Volume"),
    critical_last_cols: Tuple[str, ...] = ("Close",),
    min_rows: int = 30,
    timeframe_seconds: Optional[int] = None,
    max_stale_multiplier: int = 2,
    assume_index_is_utc: bool = True,
) -> GuardResult:
    """Validate df for signal generation / manual trading safety."""

    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    reasons = []
    data_ok = True

    if df is None or len(df) == 0:
        return GuardResult(
            asset=asset,
            data_ok=False,
            last_bar_utc="NA",
            age_s=10**9,
            rows=0,
            nan_last=1,
            stale=1,
            timeframe_s=_safe_int(timeframe_seconds, 0),
            reason="EMPTY_DF",
        )

    rows = len(df)

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        data_ok = False
        reasons.append("MISSING_COLS:" + ",".join(missing))

    if rows < min_rows:
        data_ok = False
        reasons.append("HISTORY_SHORT")

    try:
        last_bar = df.index[-1]
        if isinstance(last_bar, pd.Timestamp):
            last_bar = last_bar.to_pydatetime()
    except Exception:
        return GuardResult(
            asset=asset,
            data_ok=False,
            last_bar_utc="NA",
            age_s=10**9,
            rows=rows,
            nan_last=1,
            stale=1,
            timeframe_s=_safe_int(timeframe_seconds, 0),
            reason="BAD_INDEX",
        )

    if getattr(last_bar, "tzinfo", None) is None:
        if assume_index_is_utc:
            last_bar = last_bar.replace(tzinfo=timezone.utc)
        else:
            last_bar = last_bar.replace(tzinfo=timezone.utc)

    tf = timeframe_seconds
    if tf is None:
        tf = infer_timeframe_seconds(df.index)
    tf = _safe_int(tf, 0)
    if tf <= 0:
        tf = 86400

    age_s = _safe_int((now_utc - last_bar.astimezone(timezone.utc)).total_seconds(), 10**9)
    max_stale_s = tf * max_stale_multiplier
    stale = 1 if age_s > max_stale_s else 0
    if stale:
        data_ok = False
        reasons.append("STALE_DATA")

    nan_last = 0
    for c in critical_last_cols:
        if c in df.columns and pd.isna(df[c].iloc[-1]):
            nan_last = 1
            break
    if nan_last:
        data_ok = False
        reasons.append("NAN_LAST_ROW")

    last_bar_utc = last_bar.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    return GuardResult(
        asset=asset,
        data_ok=data_ok,
        last_bar_utc=last_bar_utc,
        age_s=age_s,
        rows=rows,
        nan_last=nan_last,
        stale=stale,
        timeframe_s=tf,
        reason="OK" if data_ok else ";".join(reasons),
    )
