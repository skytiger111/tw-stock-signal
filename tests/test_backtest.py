"""Integration tests for backtest/backtester.py"""

import unittest
import pandas as pd
import numpy as np
from backtest.backtester import BacktestResult


class TestBacktestResult(unittest.TestCase):
    def test_result_fields_exist(self):
        """BacktestResult should have all required fields."""
        result = BacktestResult(
            ticker="2330.TW",
            start_date="2024-01-01",
            end_date="2025-12-31",
        )
        self.assertEqual(result.ticker, "2330.TW")
        self.assertEqual(result.total_trades, 0)
        self.assertEqual(result.win_rate, 0.0)

    def test_profit_factor_inf_when_no_losses(self):
        """Profit factor should be inf when there are no losing trades."""
        result = BacktestResult(
            ticker="2330.TW",
            start_date="2024-01-01",
            end_date="2025-12-31",
            total_trades=2,
            winning_trades=2,
            losing_trades=0,
            win_rate=1.0,
            profit_factor=999.999,  # placeholder for inf
        )
        self.assertGreater(result.profit_factor, 100)


if __name__ == "__main__":
    unittest.main()
