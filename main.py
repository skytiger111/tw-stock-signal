"""
Main integration module for MA Momentum Strategy v2.

Provides unified entry points:
  - get_signal(ticker)         → signal dict
  - run_full_backtest(...)    → BacktestResult
  - run_train_test_split(...) → dict with train/test results
"""

from __future__ import annotations

from data.data_loader import load_ohlcv
from backtest.backtester import run_backtest as _run_backtest, run_train_test_split as _run_tt_split
from signals.signal_generator import generate_signal
from strategy.indicators import calculate_indicators
from strategy.ticker_classifier import classify_ticker


def get_signal(ticker: str) -> dict:
    """
    Generate the latest signal for the given ticker.

    Args:
        ticker: Yahoo Finance ticker (e.g. "2330.TW").

    Returns:
        Standardized signal dict.
    """
    df_raw = load_ohlcv(ticker, days=60)
    ticker_type = classify_ticker(ticker)
    df_ind = calculate_indicators(df_raw, ticker_type)
    return generate_signal(ticker, df_ind)


def run_full_backtest(
    ticker: str,
    start_date: str = "2020-01-01",
    end_date: str = "2025-12-31",
    verbose: bool = True,
):
    """
    Run a full historical backtest.

    Args:
        ticker: Yahoo Finance ticker.
        start_date: Backtest start (YYYY-MM-DD).
        end_date: Backtest end (YYYY-MM-DD).
        verbose: Print progress.

    Returns:
        BacktestResult object.
    """
    return _run_backtest(ticker, start_date, end_date, verbose=verbose)


def run_train_test_split(ticker: str, verbose: bool = True) -> dict:
    """
    Run out-of-sample (train/test split) backtest.

    Returns:
        dict with 'train', 'test', 'oos_pass', 'threshold_pct'.
    """
    return _run_tt_split(ticker, verbose=verbose)
