"""
Yahoo Finance data loader for tw-stock-signal v2.
Cache-first: reads from local CSV if fresh (< 24 h), otherwise downloads.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf

# ── Cache config ──────────────────────────────────────────────────────────────
CACHE_DIR = Path(__file__).parent           # …/tw-stock-signal/data/
CACHE_TTL_HOURS = 24
CACHE_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]

# ── Public API ────────────────────────────────────────────────────────────────

def load_ohlcv(ticker: str, days: int = 60) -> pd.DataFrame:
    """
    Load daily OHLCV data.  Cache-first: reads from data/{ticker}.csv
    if it exists and was updated within CACHE_TTL_HOURS; otherwise downloads
    fresh data from Yahoo Finance and overwrites the cache.

    Args:
        ticker: Yahoo Finance ticker symbol (e.g. "2330.TW").
        days:   Minimum lookback rows to return (default 60).

    Returns:
        DataFrame with columns [Open, High, Low, Close, Volume], index=Datetime.

    Raises:
        ValueError: If ticker is invalid or no data returned.
        yfinance.HTTPError: On HTTP errors (429 with backoff in load_ohlcv_with_retry).
    """
    if days < 30:
        raise ValueError("days must be >= 30 to ensure indicator convergence")

    cache_path = CACHE_DIR / f"{ticker}.csv"

    # ── 1. Try cache ──────────────────────────────────────────────────────────
    if cache_path.exists():
        age_hours = (datetime.now(timezone.utc) - datetime.fromtimestamp(
            cache_path.stat().st_mtime, tz=timezone.utc
        )).total_seconds() / 3600
        if age_hours < CACHE_TTL_HOURS:
            df = _read_cache(cache_path)
            if df is not None and len(df) >= days:
                print(f"[data_loader] {ticker} ← cache ({len(df)} rows, {age_hours:.1f}h old)")
                return _tail(df, days)

    # ── 2. Download ───────────────────────────────────────────────────────────
    print(f"[data_loader] {ticker} → downloading (cache miss or stale)")
    df = _download_ohlcv(ticker)
    _write_cache(cache_path, df)
    return _tail(df, days)


def load_ohlcv_with_retry(
    ticker: str,
    days: int = 60,
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> pd.DataFrame:
    """
    Load OHLCV with exponential backoff on HTTP 429.

    Args:
        ticker:     Ticker symbol.
        days:       Lookback days.
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
                print(f"[data_loader] HTTP 429 — retrying in {delay}s ({attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                raise
    return load_ohlcv(ticker, days)   # unreachable, for type checker


# ── Internal helpers ─────────────────────────────────────────────────────────

def _download_ohlcv(ticker: str) -> pd.DataFrame:
    """Fetch 5 years of OHLCV from Yahoo Finance."""
    df = yf.download(
        ticker,
        period="5y",
        auto_adjust=True,
        progress=False,
        timeout=30,
    )
    if df.empty:
        raise ValueError(f"No data returned for ticker: {ticker}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in yfinance response: {missing}")
    return df[required]


def _read_cache(cache_path: Path) -> Optional[pd.DataFrame]:
    """Read CSV cache; return None on parse error."""
    try:
        df = pd.read_csv(
            cache_path,
            parse_dates=["Date"],
            index_col="Date",
        )
        return df
    except Exception as exc:
        print(f"[data_loader] cache read error {cache_path}: {exc}")
        return None


def _write_cache(cache_path: Path, df: pd.DataFrame) -> None:
    """Write DataFrame to CSV cache."""
    try:
        df.to_csv(cache_path)
        print(f"[data_loader] {cache_path.name} cached ({len(df)} rows)")
    except Exception as exc:
        print(f"[data_loader] cache write error {cache_path}: {exc}")


def _tail(df: pd.DataFrame, days: int) -> pd.DataFrame:
    """Return last `days` rows."""
    return df.tail(days) if len(df) > days else df


# ── CLI quick-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "2330.TW"
    print(f"Loading {ticker} ...")
    df = load_ohlcv(ticker, days=60)
    print(f"  Rows: {len(df)}")
    print(f"  Latest: {df.index[-1].date()}  Close: {df['Close'].iloc[-1]:.2f}")
    print("✅ data/data_loader.py OK")
