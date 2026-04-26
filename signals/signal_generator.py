"""
Signal generator for MA Momentum Strategy v2.

Signal logic (SPEC.md v2.0 Section 3):
  1. Core indicators (MA + RSI + KD) must ALL satisfy directional condition.
  2. Filters (MACD + BB) must NOT be in opposite direction (otherwise NEUTRAL).
  3. OVERBOUGHT/OVERSOLD alerts are independent附加，不推翻訊號。

ETF vs STOCK:
  - STOCK: MA5>MA10 + RSI>50 + K>D (low-turn) → LONG
  - ETF:   MA10>MA20 + RSI>50                → LONG
  (Short is mirror logic)

Reference: SPEC.md v2.0 Sections 3, 4, 8.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

import pandas as pd

from strategy.ticker_classifier import classify_ticker, TickerType

# ─────────────────────────────────────────────
# Types
# ─────────────────────────────────────────────

SignalType = Literal["LONG", "SHORT", "NEUTRAL", "OVERBOUGHT", "OVERSOLD"]


# ─────────────────────────────────────────────
# Core indicator checks
# ─────────────────────────────────────────────

def _ma_bullish(ma_short: float, ma_long: float) -> bool:
    return ma_short > ma_long


def _ma_bearish(ma_short: float, ma_long: float) -> bool:
    return ma_short < ma_long


def _rsi_bullish(rsi: float) -> bool:
    return rsi > 50


def _rsi_bearish(rsi: float) -> bool:
    return rsi < 50


def _kd_bullish(k: float, d: float, k_prev: float, k_low_thresh: float = 30.0) -> bool:
    """
    KD bullish: K > D and K is turning up from low area (low-turn).
    A 'turn' is approximated by K rising above its previous value while still low.
    """
    return (k > d) and (k > k_prev) and (k < k_low_thresh + 30)  # still in lower half


def _kd_bearish(k: float, d: float, k_prev: float, k_high_thresh: float = 70.0) -> bool:
    """KD bearish: K < D and K is turning down from high area (high-turn)."""
    return (k < d) and (k < k_prev) and (k > k_high_thresh - 30)


# ─────────────────────────────────────────────
# Filter checks (return True if opposite condition triggered → veto)
# ─────────────────────────────────────────────

def _macd_vetoes_long(dif: float, macd: float) -> bool:
    """
    MACD vetoes LONG if in bearish territory:
    DIF < 0 AND MACD < Signal.
    """
    return (dif < 0) and (macd < 0)


def _macd_vetoes_short(dif: float, macd: float) -> bool:
    """
    MACD vetoes SHORT if in bullish territory:
    DIF > 0 AND MACD > Signal.
    """
    return (dif > 0) and (macd > 0)


def _bb_vetoes_long(bb_upper: float, price: float, bb_bandwidth: float, prev_bandwidth: float) -> bool:
    """
    BB vetoes LONG if: Bandwidth expanding AND price breaks below lower band.
    (Simplified: Bandwidth expanding + price near lower band as proxy.)
    """
    bandwidth_expanding = bb_bandwidth > prev_bandwidth
    near_or_below_lower = price <= bb_upper  # simplified: any price below upper = potential reversal
    # Actually for veto LONG we want: BB in bearish state (bandwidth expanding + price below lower)
    return False  # placeholder; actual logic requires lower band which we compute separately


def _bb_bearish_filter(bb_upper: float, bb_middle: float, bb_lower: float,
                        price: float, bb_bandwidth: float, prev_bandwidth: float) -> bool:
    """
    BB bearish filter: Bandwidth expanding AND price <= lower band.
    This vetoes LONG.
    """
    bandwidth_expanding = bb_bandwidth > prev_bandwidth
    at_or_below_lower = price <= bb_lower
    return bandwidth_expanding and at_or_below_lower


def _bb_bullish_filter(bb_upper: float, bb_middle: float, bb_lower: float,
                        price: float, bb_bandwidth: float, prev_bandwidth: float) -> bool:
    """
    BB bullish filter: Bandwidth expanding AND price >= upper band.
    This vetoes SHORT.
    """
    bandwidth_expanding = bb_bandwidth > prev_bandwidth
    at_or_above_upper = price >= bb_upper
    return bandwidth_expanding and at_or_above_upper


# ─────────────────────────────────────────────
# Main signal generator
# ─────────────────────────────────────────────

def generate_signal(ticker: str, df: pd.DataFrame) -> dict[str, Any]:
    """
    Generate a standardized signal JSON for the latest bar in `df`.

    Args:
        ticker: Ticker symbol (e.g. "2330.TW").
        df: OHLCV DataFrame with all indicators pre-calculated
            (from calculate_indicators).

    Returns:
        Standardized signal dict (SPEC.md v2.0 Section 8 JSON format).

    Raises:
        ValueError: If df has fewer than 2 rows (need prev for KD turn).
    """
    if len(df) < 2:
        raise ValueError("df must have at least 2 rows for KD turn detection")

    # Determine ticker type
    ticker_type: TickerType = classify_ticker(ticker)

    # Use the last two rows
    curr = df.iloc[-1]
    prev = df.iloc[-2]

    close = float(curr["Close"])
    price = close

    # ── Extract indicator values ──
    ma5 = float(curr["ma5"])
    ma10 = float(curr["ma10"])
    ma20 = float(curr["ma20"])
    rsi14 = float(curr["rsi14"])

    k = float(curr["k"]) if pd.notna(curr["k"]) else None
    d = float(curr["d"]) if pd.notna(curr["d"]) else None
    k_prev = float(prev["k"]) if pd.notna(prev["k"]) else None

    macd_dif = float(curr["macd_dif"])
    macd_signal = float(curr["macd_signal"])
    macd_histogram = float(curr["macd_histogram"])

    bb_upper = float(curr["bb_upper"])
    bb_middle = float(curr["bb_middle"])
    bb_lower = float(curr["bb_lower"])
    bb_bandwidth = float(curr["bb_bandwidth"])
    bb_bandwidth_prev = float(prev["bb_bandwidth"]) if pd.notna(prev["bb_bandwidth"]) else bb_bandwidth

    # ── Determine MA pair based on ticker type ──
    if ticker_type == "ETF":
        ma_short: float = ma10
        ma_long: float = ma20
    else:  # STOCK
        ma_short = ma5
        ma_long = ma10

    # ── Core indicator conditions ──
    ma_long_cond = _ma_bullish(ma_short, ma_long)
    ma_short_cond = _ma_bearish(ma_short, ma_long)
    rsi_bull = _rsi_bullish(rsi14)
    rsi_bear = _rsi_bearish(rsi14)

    # KD — only for STOCK
    if ticker_type == "STOCK" and k is not None and d is not None and k_prev is not None:
        kd_bull = _kd_bullish(k, d, k_prev)
        kd_bear = _kd_bearish(k, d, k_prev)
    else:
        kd_bull = True   # ETF doesn't use KD, treat as satisfied
        kd_bear = True

    # ── Filter vetoes ──
    macd_veto_long = _macd_vetoes_long(macd_dif, macd_histogram)
    macd_veto_short = _macd_vetoes_short(macd_dif, macd_histogram)

    bb_veto_long = _bb_bearish_filter(
        bb_upper, bb_middle, bb_lower, price, bb_bandwidth, bb_bandwidth_prev
    )
    bb_veto_short = _bb_bullish_filter(
        bb_upper, bb_middle, bb_lower, price, bb_bandwidth, bb_bandwidth_prev
    )

    # ── Signal determination ──
    core_all_bull = ma_long_cond and rsi_bull and kd_bull
    core_all_bear = ma_short_cond and rsi_bear and kd_bear

    filters_passed = True

    if core_all_bull and not (macd_veto_long or bb_veto_long):
        signal: SignalType = "LONG"
    elif core_all_bear and not (macd_veto_short or bb_veto_short):
        signal = "SHORT"
    else:
        signal = "NEUTRAL"
        filters_passed = False

    # ── Alerts (independent, do NOT override signal) ──
    alert: Optional[str] = None
    emoji = "➡️"

    if rsi14 > 70:
        alert = "OVERBOUGHT"
        emoji = "⚠️"
    elif rsi14 < 30:
        alert = "OVERSOLD"
        emoji = "⚠️"

    if signal == "LONG":
        emoji = "📈"
    elif signal == "SHORT":
        emoji = "📉"

    # ── Assemble output ──
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "ticker": ticker,
        "signal": signal,
        "price": round(price, 2),
        "indicators": {
            "ma5": round(ma5, 2) if pd.notna(ma5) else None,
            "ma10": round(ma10, 2) if pd.notna(ma10) else None,
            "ma20": round(ma20, 2) if pd.notna(ma20) else None,
            "rsi14": round(rsi14, 2) if pd.notna(rsi14) else None,
            "k": round(k, 2) if k is not None else None,
            "d": round(d, 2) if d is not None else None,
            "macd_dif": round(macd_dif, 4) if pd.notna(macd_dif) else None,
            "macd_signal": round(macd_signal, 4) if pd.notna(macd_signal) else None,
            "macd_histogram": round(macd_histogram, 4) if pd.notna(macd_histogram) else None,
            "bb_upper": round(bb_upper, 2) if pd.notna(bb_upper) else None,
            "bb_middle": round(bb_middle, 2) if pd.notna(bb_middle) else None,
            "bb_lower": round(bb_lower, 2) if pd.notna(bb_lower) else None,
            "bb_bandwidth": round(bb_bandwidth, 4) if pd.notna(bb_bandwidth) else None,
        },
        "filters_passed": filters_passed,
        "stop_loss_pct": 20.0,
        "take_profit_pct": 20.0,
        "holding_overnight": True,
        "alert": alert,
        "emoji": emoji,
    }


if __name__ == "__main__":
    from data.data_loader import load_ohlcv
    from strategy.indicators import calculate_indicators

    for ticker in ["2330.TW", "0050.TW"]:
        try:
            df_raw = load_ohlcv(ticker, days=60)
            df_ind = calculate_indicators(df_raw, classify_ticker(ticker))
            sig = generate_signal(ticker, df_ind)
            print(f"\n{ticker}: {sig['signal']} {sig['emoji']}")
            print(f"  Price: {sig['price']}  RSI: {sig['indicators']['rsi14']}")
            print(f"  filters_passed: {sig['filters_passed']}")
        except Exception as e:
            print(f"Error for {ticker}: {e}")

    print("\n✅ signals/signal_generator.py OK")
