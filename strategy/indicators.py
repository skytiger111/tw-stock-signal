"""
Technical indicators for MA Momentum Strategy v2.

Implements:
  - MA (MA5/MA10 for STOCK, MA10/MA20 for ETF)
  - RSI(14)
  - KD(9,3,3) — STOCK only, ETF returns NaN
  - MACD(12,26,9) — DIF, Signal, Histogram
  - Bollinger Bands(20) — Upper, Middle, Lower, Bandwidth

Reference: SPEC.md v2.0 Sections 3 & 4.
"""

from __future__ import annotations

from typing import Tuple

import pandas as pd
import numpy as np


# ─────────────────────────────────────────────
# RSI
# ─────────────────────────────────────────────

def calculate_rsi(series: pd.Series[float], period: int = 14) -> pd.Series[float]:
    """
    Calculate Wilder's RSI.

    Args:
        series: Price series (typically Close).
        period: RSI lookback period (default 14).

    Returns:
        Series of RSI values (0–100). First `period` values are NaN.
    """
    delta = series.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    # Wilder's smoothed average
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ─────────────────────────────────────────────
# Stochastic KD
# ─────────────────────────────────────────────

def calculate_kd(
    high: pd.Series[float],
    low: pd.Series[float],
    close: pd.Series[float],
    k_period: int = 9,
    d_period: int = 3,
    smooth_k: int = 3,
) -> Tuple[pd.Series[float], pd.Series[float]]:
    """
    Calculate Slow Stochastic %K and %D.

    Args:
        high, low, close: OHLC price series.
        k_period: %K lookback period (default 9).
        d_period: %D smoothing period (default 3).
        smooth_k: Slow %K smoothing (default 3).

    Returns:
        (K_series, D_series). First `k_period + smooth_k - 1` values are NaN.
    """
    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()

    raw_k = 100.0 * (close - lowest_low) / (highest_high - lowest_low)
    # Fast %K → Slow %K (smoothing)
    k = raw_k.rolling(window=smooth_k, min_periods=smooth_k).mean()
    d = k.rolling(window=d_period, min_periods=d_period).mean()

    return k, d


# ─────────────────────────────────────────────
# MACD
# ─────────────────────────────────────────────

def calculate_macd(
    series: pd.Series[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> Tuple[pd.Series[float], pd.Series[float], pd.Series[float]]:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Args:
        series: Price series (typically Close).
        fast: Fast EMA period (default 12).
        slow: Slow EMA period (default 26).
        signal_period: Signal line EMA period (default 9).

    Returns:
        (DIF, Signal, Histogram). DIF = Fast EMA - Slow EMA.
        Histogram = DIF - Signal.
    """
    ema_fast = series.ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = series.ewm(span=slow, adjust=False, min_periods=slow).mean()

    dif = ema_fast - ema_slow
    signal = dif.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
    histogram = dif - signal

    return dif, signal, histogram


# ─────────────────────────────────────────────
# Bollinger Bands
# ─────────────────────────────────────────────

def calculate_bollinger_bands(
    series: pd.Series[float],
    period: int = 20,
    num_std: float = 2.0,
) -> Tuple[pd.Series[float], pd.Series[float], pd.Series[float], pd.Series[float]]:

    """
    Calculate Bollinger Bands.

    Args:
        series: Price series (typically Close).
        period: Moving average period (default 20).
        num_std: Number of standard deviations (default 2.0).

    Returns:
        (Upper, Middle, Lower, Bandwidth).
        Bandwidth = (Upper - Lower) / Middle * 100 (%).
    """
    middle = series.rolling(window=period, min_periods=period).mean()
    std: pd.Series[float] = series.rolling(window=period, min_periods=period).std()

    upper = middle + num_std * std
    lower = middle - num_std * std
    bandwidth = (upper - lower) / middle * 100

    return upper, middle, lower, bandwidth


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def calculate_indicators(df: pd.DataFrame, ticker_type: str) -> pd.DataFrame:
    """
    Calculate all v2 indicators for the given OHLCV DataFrame.

    Args:
        df: OHLCV DataFrame with columns [Open, High, Low, Close, Volume].
        ticker_type: "STOCK" or "ETF" (from classify_ticker).

    Returns:
        DataFrame with original columns plus all indicator columns:
        ma5, ma10, ma20, rsi14, k, d,
        macd_dif, macd_signal, macd_histogram,
        bb_upper, bb_middle, bb_lower, bb_bandwidth.

    Note:
        - STOCK: MA5/MA10/MA20 all computed; KD computed.
        - ETF:   MA5/MA10/MA20 all computed; KD set to NaN.
        - MACD and Bollinger Bands computed for both types.
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    # MA (both stock and ETF compute all three; logic picks which pair to use later)
    ma5 = close.rolling(window=5, min_periods=5).mean()
    ma10 = close.rolling(window=10, min_periods=10).mean()
    ma20 = close.rolling(window=20, min_periods=20).mean()

    # RSI(14)
    rsi14 = calculate_rsi(close, period=14)

    # KD — only for STOCK
    if ticker_type == "STOCK":
        k, d = calculate_kd(high, low, close)
    else:
        k = pd.Series(np.nan, index=close.index)
        d = pd.Series(np.nan, index=close.index)

    # MACD(12,26,9)
    macd_dif, macd_signal, macd_histogram = calculate_macd(close)

    # Bollinger Bands(20)
    bb_upper, bb_middle, bb_lower, bb_bandwidth = calculate_bollinger_bands(close)

    # Assemble result
    result = df.copy()
    result["ma5"] = ma5
    result["ma10"] = ma10
    result["ma20"] = ma20
    result["rsi14"] = rsi14
    result["k"] = k
    result["d"] = d
    result["macd_dif"] = macd_dif
    result["macd_signal"] = macd_signal
    result["macd_histogram"] = macd_histogram
    result["bb_upper"] = bb_upper
    result["bb_middle"] = bb_middle
    result["bb_lower"] = bb_lower
    result["bb_bandwidth"] = bb_bandwidth

    return result


if __name__ == "__main__":
    # Quick sanity check using real data
    from data.data_loader import load_ohlcv

    ticker = "2330.TW"
    df_raw = load_ohlcv(ticker, days=60)
    df_ind = calculate_indicators(df_raw, "STOCK")

    latest = df_ind.iloc[-1]
    print(f"Ticker: {ticker}")
    print(f"  Close:   {latest['Close']:.2f}")
    print(f"  MA5:     {latest['ma5']:.2f}  MA10: {latest['ma10']:.2f}  MA20: {latest['ma20']:.2f}")
    print(f"  RSI(14): {latest['rsi14']:.2f}")
    print(f"  K:       {latest['k']:.2f}  D: {latest['d']:.2f}")
    print(f"  MACD DIF: {latest['macd_dif']:.4f}  Signal: {latest['macd_signal']:.4f}  Hist: {latest['macd_histogram']:.4f}")
    print(f"  BB Upper: {latest['bb_upper']:.2f}  Middle: {latest['bb_middle']:.2f}  Lower: {latest['bb_lower']:.2f}")
    print("✅ strategy/indicators.py OK")
