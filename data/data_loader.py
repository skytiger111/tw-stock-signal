"""
Yahoo Finance data loader for tw-stock-signal v2.
Loads daily OHLCV data with lookback >= 30 trading days.
"""

from __future__ import annotations

import time
from typing import Optional

import pandas as pd
import yfinance as yf


def load_ohlcv(ticker: str, days: int = 60) -> pd.DataFrame:
    """
    Load daily OHLCV data from Yahoo Finance.

    Args:
        ticker: Yahoo Finance ticker symbol (e.g. "2330.TW").
        days: Minimum lookback days (default 60, ensures MACD/KD convergence).

    Returns:
        DataFrame with columns [Open, High, Low, Close, Volume], index=Datetime.

    Raises:
        ValueError: If ticker is invalid or no data returned.
        yfinance.HTTPError: On HTTP errors (caller should handle 429 with backoff).
    """
    if days < 30:
        raise ValueError("days must be >= 30 to ensure indicator convergence")

    # yfinance expects YY-MM-DD for end date; use a far future to get latest data
    end = "2026-12-31"
    start_offset = max(days + 30, 90)  # extra buffer for weekends/holidays
    start = f"2024-01-01"  # conservative start; actual period derived from days below

    # Use period='id't'd' and explicitly calculate date range instead
    df = yf.download(
        ticker,
        period="5y",          # fetch 2 years, enough for any lookback
        auto_adjust=True,
        progress=False,
        timeout=30,
    )

    if df.empty:
        raise ValueError(f"No data returned for ticker: {ticker}")

    # Normalize column names (yfinance may return multi-level columns)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.index = pd.to_datetime(df.index).tz_localize(None)  # remove timezone

    # Keep only required columns
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in yfinance response: {missing}")

    df = df[required]

    # Trim to last `days` rows
    if len(df) > days:
        df = df.tail(days)

    return df


def load_ohlcv_with_retry(
    ticker: str,
    days: int = 60,
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> pd.DataFrame:
    """
    Load OHLCV with exponential backoff on HTTP 429.

    Args:
        ticker: Ticker symbol.
        days: Lookback days.
        max_retries: Number of retry attempts.
        base_delay: Initial delay in seconds (doubles each retry).

    Returns:
        DataFrame of OHLCV data.
    """
    for attempt in range(max_retries):
        try:
            return load_ohlcv(ticker, days)
        except Exception as exc:
            if "429" in str(exc) or attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"[data_loader] HTTP 429 — retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                raise
    # Should not reach here, but satisfy type checker
    return load_ohlcv(ticker, days)


if __name__ == "__main__":
    # Quick sanity check
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "2330.TW"
    print(f"Loading {ticker}...")
    df = load_ohlcv(ticker, days=60)
    print(f"  Rows: {len(df)}")
    print(f"  Latest close: {df['Close'].iloc[-1]:.2f}")
    print("✅ data/data_loader.py OK")
