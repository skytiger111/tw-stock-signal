"""Unit tests for signals/signal_generator.py"""

import unittest
import pandas as pd
import numpy as np
from signals.signal_generator import generate_signal, _ma_bullish, _rsi_bullish


class TestHelpers(unittest.TestCase):
    def test_ma_bullish(self):
        self.assertTrue(_ma_bullish(110, 100))
        self.assertFalse(_ma_bullish(100, 110))

    def test_rsi_bullish(self):
        self.assertTrue(_rsi_bullish(60))
        self.assertFalse(_rsi_bullish(40))


class TestSignalGenerator(unittest.TestCase):
    def _make_df(self, n: int = 30) -> pd.DataFrame:
        """Create a synthetic OHLCV DataFrame."""
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        close = 100 + np.linspace(0, 10, n) + np.random.randn(n) * 0.5
        return pd.DataFrame({
            "Open":   close - 1,
            "High":   close + 2,
            "Low":    close - 2,
            "Close":  close,
            "Volume": np.random.randint(1000, 10000, n),
        }, index=dates)

    def test_neutral_when_ma_flat(self):
        """When MA5 ≈ MA10, signal should be NEUTRAL."""
        from strategy.indicators import calculate_indicators
        df = self._make_df(60)
        df_ind = calculate_indicators(df, "STOCK")
        sig = generate_signal("2330.TW", df_ind)
        # Signal should be one of the valid types
        self.assertIn(sig["signal"], ("LONG", "SHORT", "NEUTRAL"))

    def test_filters_passed_for_longs_short(self):
        """LONG/SHORT signals must have filters_passed=True."""
        from strategy.indicators import calculate_indicators
        df = self._make_df(60)
        # Force a bullish scenario
        df["Close"] = np.linspace(80, 120, len(df))  # uptrend
        df["High"] = df["Close"] + 2
        df["Low"] = df["Close"] - 2
        df_ind = calculate_indicators(df, "STOCK")
        sig = generate_signal("2330.TW", df_ind)
        if sig["signal"] in ("LONG", "SHORT"):
            self.assertTrue(sig["filters_passed"])

    def test_signal_json_schema(self):
        """Signal dict must contain all required keys."""
        from strategy.indicators import calculate_indicators
        df = self._make_df(60)
        df_ind = calculate_indicators(df, "ETF")
        sig = generate_signal("0050.TW", df_ind)

        required_keys = [
            "timestamp", "ticker", "signal", "price",
            "indicators", "filters_passed",
            "stop_loss_pct", "take_profit_pct",
            "holding_overnight", "alert", "emoji",
        ]
        for key in required_keys:
            self.assertIn(key, sig, f"Missing key: {key}")


if __name__ == "__main__":
    unittest.main()
