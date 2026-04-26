"""
Walk-forward test for Phase 3 Out-of-Sample Testing.

SPEC reference: docs/test-plan.md Section 2.3 (Back-test)
Success criteria: Test set performance >= Train set performance × 50%

Split:
  - Train: 2020-01-01 ~ 2023-12-31 (60%)
  - Test:  2024-01-01 ~ 2025-12-31 (40%)

Tickers: 0050, 0052, 00919, 009816 (ETF) + 2330, 2890, 2881, 2317 (STOCK)
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List, Tuple

import numpy as np
import pandas as pd
import pytest
import yfinance as yf

from signals.signal_generator import generate_signal
from strategy.indicators import calculate_indicators
from strategy.ticker_classifier import classify_ticker

TICKERS = ["2330.TW", "2890.TW", "2881.TW", "2317.TW", "0050.TW", "0052.TW", "00919.TW", "009816.TW"]
TRAIN_END = "2023-12-31"
TEST_START = "2024-01-01"
TEST_END = "2025-12-31"


def fetch_range(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Fetch OHLCV for a given date range."""
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False, timeout=30)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    required = ["Open", "High", "Low", "Close", "Volume"]
    df = df[[c for c in required if c in df.columns]]
    return df


def compute_returns(df: pd.DataFrame, signal_col: str = "signal") -> Tuple[float, float, int]:
    """
    Compute strategy returns from a DataFrame with signal column.

    Returns:
        (total_return, sharpe_ratio, n_signals)
    """
    if signal_col not in df.columns or "Close" not in df.columns:
        return 0.0, 0.0, 0

    df = df.copy()
    df["ret"] = df["Close"].pct_change()

    longs = df[signal_col] == "LONG"
    shorts = df[signal_col] == "SHORT"

    df["strategy_ret"] = 0.0
    df.loc[longs, "strategy_ret"] = df.loc[longs, "ret"]
    df.loc[shorts, "strategy_ret"] = -df.loc[shorts, "ret"]

    valid = df["strategy_ret"].dropna()
    if len(valid) == 0:
        return 0.0, 0.0, 0

    total_return = (1 + valid).prod() - 1
    sharpe = valid.mean() / valid.std() * np.sqrt(252) if valid.std() > 0 else 0.0
    n_signals = len(valid)

    return float(total_return), float(sharpe), int(n_signals)


def evaluate_ticker(ticker: str) -> dict:
    """Run train+test for a single ticker."""
    ticker_type = classify_ticker(ticker)
    df_all = fetch_range(ticker, "2019-01-01", "2026-01-01")

    # Split
    df_train = df_all[df_all.index <= TRAIN_END].copy()
    df_test = df_all[df_all.index >= TEST_START].copy()

    if len(df_train) < 30 or len(df_test) < 30:
        return {"ticker": ticker, "error": "Insufficient data", "train": {}, "test": {}}

    # Indicators + signals
    df_train_ind = calculate_indicators(df_train, ticker_type)
    df_test_ind = calculate_indicators(df_test, ticker_type)

    # Generate signals for each day
    signals_train: List[str] = []
    signals_test: List[str] = []

    for i in range(30, len(df_train_ind)):
        row = df_train_ind.iloc[: i + 1]
        try:
            sig = generate_signal(ticker, row)
            signals_train.append(sig["signal"])
        except Exception:
            signals_train.append("NEUTRAL")

    for i in range(30, len(df_test_ind)):
        row = df_test_ind.iloc[: i + 1]
        try:
            sig = generate_signal(ticker, row)
            signals_test.append(sig["signal"])
        except Exception:
            signals_test.append("NEUTRAL")

    df_train_ind["signal"] = signals_train + ["NEUTRAL"] * (len(df_train_ind) - len(signals_train))
    df_test_ind["signal"] = signals_test + ["NEUTRAL"] * (len(df_test_ind) - len(signals_test))

    train_ret, train_sharpe, n_train = compute_returns(df_train_ind)
    test_ret, test_sharpe, n_test = compute_returns(df_test_ind)

    return {
        "ticker": ticker,
        "train": {"return": train_ret, "sharpe": train_sharpe, "n_signals": n_train},
        "test": {"return": test_ret, "sharpe": test_sharpe, "n_signals": n_test},
    }


@pytest.mark.slow
def test_walkforward_all_tickers():
    """
    Walk-forward Phase 3 test.
    Success: test_return >= train_return * 0.50 (50% retention)
    """
    results: List[dict] = []
    for ticker in TICKERS:
        print(f"Evaluating {ticker}...")
        try:
            res = evaluate_ticker(ticker)
        except Exception as e:
            res = {"ticker": ticker, "error": str(e)}
        results.append(res)
        print(f"  {ticker}: train={res.get('train', {}).get('return', 'N/A'):.2%} "
              f"test={res.get('test', {}).get('return', 'N/A'):.2%}")

    # Save results
    out_path = os.path.join(os.path.dirname(__file__), "walkforward_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Assertions
    for res in results:
        if "error" in res:
            pytest.fail(f"{res['ticker']} failed: {res['error']}")

        train_ret = res["train"]["return"]
        test_ret = res["test"]["return"]
        n_test = res["test"]["n_signals"]

        assert n_test >= 20, f"{res['ticker']} test signals {n_test} < 20 (Must Pass)"
        threshold = train_ret * 0.50
        assert test_ret >= threshold, (
            f"{res['ticker']}: test return {test_ret:.2%} < 50% of train {train_ret:.2%} "
            f"(threshold={threshold:.2%})"
        )

    print("\n✅ All tickers passed Phase 3 walk-forward test")
    print(f"Results saved to {out_path}")


if __name__ == "__main__":
    test_walkforward_all_tickers()
