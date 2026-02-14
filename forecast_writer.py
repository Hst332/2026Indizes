from datetime import datetime, timezone
import pandas as pd

from trade_filter import FILTER_PARAMS


def _utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _fmt_pct(x) -> str:
    try:
        return f"{float(x):.2f}%"
    except Exception:
        return "n/a"


def _fmt_float(x, nd=2) -> str:
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return "n/a"


def _rule_text(asset: str) -> str:
    cfg = FILTER_PARAMS.get(asset, {})
    long_thr = cfg.get("long_thr")
    short_thr = cfg.get("short_thr")
    note = cfg.get("note", "")

    if long_thr is None or short_thr is None:
        return "n/a"

    s = f"LONG≥{long_thr:.2f} / SHORT≤{short_thr:.2f}"
    if note:
        s += f" ({note})"
    return s


def write_index_forecast_txt(df: pd.DataFrame, filename: str = "index_forecast.txt") -> None:
    """
    Erwartet DataFrame mit Spalten:
    asset, prev_close, close, daily_return, signal, confidence, regime, prob_up, rule
    (main.py / trade_filter füllen das)
    """
    ts = _utc_now_str()

    lines = []
    lines.append(f"Index Forecasts – {ts}")
    lines.append("=" * 110)
    lines.append("")
    header = (
        "Index    | Prev Close | Current | Δ %    | Signal | Conf | Regime   | ProbUp | Rule"
    )
    lines.append(header)
    lines.append("-" * len(header))

    if df is None or df.empty:
        lines.append("No forecast results (data fetch failed).")
        lines.append("")
    else:
        # sichere Spalten
        for col in ["asset", "prev_close", "close", "daily_return", "signal", "confidence", "regime", "prob_up", "rule"]:
            if col not in df.columns:
                df[col] = None

        for _, r in df.iterrows():
            asset = str(r["asset"])
            prev_close = _fmt_float(r["prev_close"], 2)
            close = _fmt_float(r["close"], 2)
            dlt = _fmt_pct(r["daily_return"])
            signal = str(r["signal"])
            conf = _fmt_float(r["confidence"], 2)
            regime = str(r["regime"])
            probup = _fmt_float(r["prob_up"], 2)
            rule = str(r["rule"]) if pd.notna(r["rule"]) else _rule_text(asset)

            lines.append(
                f"{asset:<8} | {prev_close:>9} | {close:>7} | {dlt:>6} | {signal:<6} | {conf:>4} | {regime:<8} | {probup:>5} | {rule}"
            )

        lines.append("")

    # Regeln-Block (immer anzeigen)
    lines.append("")
    lines.append("TRADING RULES (Thresholds)")
    lines.append("")
    for asset, cfg in FILTER_PARAMS.items():
        long_thr = cfg.get("long_thr")
        short_thr = cfg.get("short_thr")
        note = cfg.get("note", "")

        lines.append(asset)
        if long_thr is None or short_thr is None:
            lines.append("- n/a")
        else:
            lines.append(f"- LONG  if prob_up >= {long_thr:.2f}")
            lines.append(f"- SHORT if prob_up <= {short_thr:.2f}")
            lines.append("- Otherwise: HOLD")
            if note:
                lines.append(f"- Note: {note}")
        lines.append("")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
