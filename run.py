#!/usr/bin/env python3
"""
CLI entry point for MA Momentum Strategy v2.

Usage:
  python run.py --ticker 2330.TW              # generate signal
  python run.py --ticker 2330.TW --backtest   # run backtest
  python run.py --ticker 2330.TW --oos        # train/test split
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from main import get_signal, run_full_backtest, run_train_test_split


def main() -> None:
    parser = argparse.ArgumentParser(description="MA Momentum Strategy v2")
    parser.add_argument(
        "--ticker",
        type=str,
        default="2330.TW",
        help="Yahoo Finance ticker (default: 2330.TW)",
    )
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run full backtest instead of generating a signal",
    )
    parser.add_argument(
        "--oos",
        action="store_true",
        help="Run out-of-sample (train/test split) backtest",
    )
    parser.add_argument(
        "--start",
        type=str,
        default="2024-01-01",
        help="Backtest start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        type=str,
        default="2025-12-31",
        help="Backtest end date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output signal as raw JSON (no emoji)",
    )

    args = parser.parse_args()

    try:
        if args.oos:
            result = run_train_test_split(args.ticker)
            print(json.dumps({
                "ticker": args.ticker,
                "train": {
                    "total_trades": result["train"].total_trades,
                    "win_rate": result["train"].win_rate,
                    "profit_factor": result["train"].profit_factor,
                    "max_drawdown": result["train"].max_drawdown,
                    "total_return_pct": result["train"].total_return_pct,
                },
                "test": {
                    "total_trades": result["test"].total_trades,
                    "win_rate": result["test"].win_rate,
                    "profit_factor": result["test"].profit_factor,
                    "max_drawdown": result["test"].max_drawdown,
                    "total_return_pct": result["test"].total_return_pct,
                },
                "oos_pass": result["oos_pass"],
                "threshold_pct": result["threshold_pct"],
            }, indent=2))

        elif args.backtest:
            result = run_full_backtest(args.ticker, args.start, args.end)
            print(json.dumps({
                "ticker": result.ticker,
                "start_date": result.start_date,
                "end_date": result.end_date,
                "total_trades": result.total_trades,
                "win_rate": result.win_rate,
                "profit_factor": result.profit_factor,
                "max_drawdown": result.max_drawdown,
                "total_return_pct": result.total_return_pct,
            }, indent=2))

        else:
            signal = get_signal(args.ticker)
            if args.json:
                print(json.dumps(signal, indent=2, ensure_ascii=False))
            else:
                print(f"\n{'='*40}")
                print(f"  {signal['emoji']} {signal['ticker']} — {signal['signal']}")
                print(f"  Price: {signal['price']}")
                ind = signal["indicators"]
                print(f"  MA5: {ind['ma5']}  MA10: {ind['ma10']}  MA20: {ind['ma20']}")
                print(f"  RSI(14): {ind['rsi14']}  K: {ind['k']}  D: {ind['d']}")
                print(f"  MACD DIF: {ind['macd_dif']}  Signal: {ind['macd_signal']}  Hist: {ind['macd_histogram']}")
                print(f"  BB Upper: {ind['bb_upper']}  Middle: {ind['bb_middle']}  Lower: {ind['bb_lower']}")
                print(f"  Filters passed: {signal['filters_passed']}")
                print(f"  Stop loss: {signal['stop_loss_pct']}%  Take profit: {signal['take_profit_pct']}%")
                if signal["alert"]:
                    print(f"  ⚠️  Alert: {signal['alert']}")
                print(f"{'='*40}\n")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
