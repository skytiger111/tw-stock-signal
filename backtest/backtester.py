"""
Backtesting engine for MA Momentum Strategy v2.

Calculates performance metrics:
  - Profit Factor
  - Max Drawdown
  - Win Rate

Supports train/test split for out-of-sample testing:
  - Training: 2020-01-01 to 2023-12-31
  - Testing:  2024-01-01 to 2025-12-31

Reference: SPEC.md v2.0 — validation criteria.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from data.data_loader import load_ohlcv
from portfolio.position_manager import (
    Position,
    StopLossError,
    TakeProfitError,
    should_exit,
    get_stop_loss,
    get_take_profit,
)
from signals.signal_generator import generate_signal
from strategy.indicators import calculate_indicators
from strategy.ticker_classifier import classify_ticker

# ─────────────────────────────────────────────
# Result type
# ─────────────────────────────────────────────

@dataclass
class BacktestResult:
    ticker: str
    start_date: str
    end_date: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    total_return_pct: float = 0.0
    equity_curve: list = field(default_factory=list)
    trades: list = field(default_factory=list)


# ─────────────────────────────────────────────
# Core backtest
# ─────────────────────────────────────────────

def run_backtest(
    ticker: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 1_000_000.0,
    verbose: bool = True,
) -> BacktestResult:
    """
    Run a historical backtest for the given ticker and date range.

    Args:
        ticker: Yahoo Finance ticker.
        start_date: Backtest start (YYYY-MM-DD).
        end_date: Backtest end (YYYY-MM-DD).
        initial_capital: Starting capital (default 1M TWD).
        verbose: Print progress.

    Returns:
        BacktestResult with performance metrics.
    """
    if verbose:
        print(f"[backtest] Loading {ticker} from {start_date} to {end_date}...")

    # ── 1. Load & prepare data ──
    df_raw = load_ohlcv(ticker, days=500)
    df_raw.index = pd.to_datetime(df_raw.index)
    df_raw = df_raw[df_raw.index >= start_date]
    df_raw = df_raw[df_raw.index <= end_date]

    if len(df_raw) < 30:
        raise ValueError(f"Insufficient data for {ticker} in range {start_date}–{end_date}")

    ticker_type = classify_ticker(ticker)
    df = calculate_indicators(df_raw, ticker_type)

    # ── 2. Simulate trading bar-by-bar ──
    capital = initial_capital
    position: Optional[Position] = None
    equity_curve: list[float] = []
    trades: list[dict] = []
    trade_pnls: list[float] = []

    for i in range(1, len(df)):
        # Generate signal using all bars up to current index
        signal = generate_signal(ticker, df.iloc[: i + 1])
        price = float(df.iloc[i]["Close"])
        date = df.index[i].strftime("%Y-%m-%d")

        # ── Entry logic ──
        if position is None:
            if signal["signal"] in ("LONG", "SHORT"):
                position = Position(
                    ticker=ticker,
                    entry_price=price,
                    position_type=signal["signal"],
                    entry_date=date,
                )
                if verbose:
                    print(f"  [{date}] ENTER {position.position_type} @ {price:.2f}")

        # ── Exit logic ──
        else:
            try:
                # Check if position should exit
                if should_exit(signal, position.entry_price, position.position_type):
                    # Calculate PnL
                    if position.position_type == "LONG":
                        pnl_pct = (price - position.entry_price) / position.entry_price * 100
                    else:  # SHORT
                        pnl_pct = (position.entry_price - price) / position.entry_price * 100

                    pnl_twd = capital * pnl_pct / 100
                    capital += pnl_twd
                    trade_pnls.append(pnl_twd)
                    trades.append({
                        "entry_date": position.entry_date,
                        "exit_date": date,
                        "type": position.position_type,
                        "entry_price": position.entry_price,
                        "exit_price": price,
                        "pnl_pct": round(pnl_pct, 4),
                        "pnl_twd": round(pnl_twd, 2),
                        "exit_reason": "SIGNAL_EXIT",
                    })
                    if verbose:
                        print(f"  [{date}] EXIT  {position.position_type} @ {price:.2f} | PnL: {pnl_pct:.2f}%")
                    position = None

            except StopLossError as e:
                if verbose:
                    print(f"  [{date}] STOP LOSS — {e}")
                sl_price = price
                pnl_pct = (sl_price - position.entry_price) / position.entry_price * 100 \
                    if position.position_type == "LONG" \
                    else (position.entry_price - sl_price) / position.entry_price * 100
                pnl_twd = capital * pnl_pct / 100
                capital += pnl_twd
                trade_pnls.append(pnl_twd)
                trades.append({
                    "entry_date": position.entry_date,
                    "exit_date": date,
                    "type": position.position_type,
                    "entry_price": position.entry_price,
                    "exit_price": sl_price,
                    "pnl_pct": round(pnl_pct, 4),
                    "pnl_twd": round(pnl_twd, 2),
                    "exit_reason": "STOP_LOSS",
                })
                position = None

            except TakeProfitError as e:
                if verbose:
                    print(f"  [{date}] TAKE PROFIT — {e}")
                tp_price = price
                pnl_pct = (tp_price - position.entry_price) / position.entry_price * 100 \
                    if position.position_type == "LONG" \
                    else (position.entry_price - tp_price) / position.entry_price * 100
                pnl_twd = capital * pnl_pct / 100
                capital += pnl_twd
                trade_pnls.append(pnl_twd)
                trades.append({
                    "entry_date": position.entry_date,
                    "exit_date": date,
                    "type": position.position_type,
                    "entry_price": position.entry_price,
                    "exit_price": tp_price,
                    "pnl_pct": round(pnl_pct, 4),
                    "pnl_twd": round(pnl_twd, 2),
                    "exit_reason": "TAKE_PROFIT",
                })
                position = None

        equity_curve.append(capital)

    # ── 3. Compute metrics ──
    total_trades = len(trade_pnls)
    winning_trades = sum(1 for p in trade_pnls if p > 0)
    losing_trades = sum(1 for p in trade_pnls if p <= 0)

    win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

    gross_profit = sum(p for p in trade_pnls if p > 0)
    gross_loss = abs(sum(p for p in trade_pnls if p < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0

    # Max drawdown
    equity_series = pd.Series(equity_curve) if equity_curve else pd.Series([initial_capital])
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max * 100
    max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0.0

    total_return_pct = (capital - initial_capital) / initial_capital * 100

    result = BacktestResult(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=round(win_rate, 4),
        profit_factor=round(profit_factor, 4) if profit_factor != float("inf") else 999.999,
        max_drawdown=round(max_drawdown, 4),
        total_return_pct=round(total_return_pct, 4),
        equity_curve=equity_curve,
        trades=trades,
    )

    if verbose:
        print(f"\n[backtest] Results for {ticker} ({start_date} – {end_date})")
        print(f"  Total trades:    {total_trades}")
        print(f"  Win rate:         {win_rate:.2%}")
        print(f"  Profit factor:    {result.profit_factor:.4f}")
        print(f"  Max drawdown:      {max_drawdown:.2f}%")
        print(f"  Total return:      {total_return_pct:.2f}%")

    return result


def run_train_test_split(ticker: str, verbose: bool = True) -> dict:
    """
    Run backtest with train/test split:
      - Training: 2020-01-01 to 2023-12-31
      - Testing:  2024-01-01 to 2025-12-31

    Returns dict with 'train' and 'test' BacktestResult objects plus OOS check.
    """
    train = run_backtest(
        ticker=ticker,
        start_date="2020-01-01",
        end_date="2023-12-31",
        verbose=verbose,
    )
    test = run_backtest(
        ticker=ticker,
        start_date="2024-01-01",
        end_date="2025-12-31",
        verbose=verbose,
    )

    # Out-of-sample check: test >= train × 50%
    train_return = train.total_return_pct
    test_return = test.total_return_pct

    if abs(train_return) < 0.01:
        # Near-zero baseline — treat as pass if test is also near zero or positive
        oos_pass = test_return >= -0.01
        threshold = 0.0
    else:
        threshold = abs(train_return) * 0.5
        oos_pass = test_return >= threshold

    if verbose:
        print(f"\n[OOS Check] Train: {train_return:.2f}% | Test: {test_return:.2f}% "
              f"| Threshold: {threshold:.2f}% | Pass: {oos_pass}")

    return {
        "train": train,
        "test": test,
        "oos_pass": oos_pass,
        "threshold_pct": round(threshold, 4),
    }


if __name__ == "__main__":
    result = run_backtest(
        ticker="2330.TW",
        start_date="2024-01-01",
        end_date="2025-12-31",
        verbose=True,
    )
    print("\n✅ backtest/backtester.py OK")
