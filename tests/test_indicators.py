"""Unit tests for strategy/indicators.py"""

import unittest
import pandas as pd
import numpy as np
from strategy.indicators import (
    calculate_rsi,
    calculate_kd,
    calculate_macd,
    calculate_bollinger_bands,
    calculate_indicators,
)


class TestRSI(unittest.TestCase):
    def test_rsi_range(self):
        """RSI values should be between 0 and 100."""
        close = pd.Series(np.random.randn(100) + np.linspace(1, 10, 100)).cumsum() + 100
        rsi = calculate_rsi(close)
        valid = rsi.dropna()
        self.assertTrue((valid >= 0).all() and (valid <= 100).all())

    def test_rsi_first_14_nan(self):
        """First 14 RSI values should be NaN."""
        close = pd.Series([100.0] * 20)
        rsi = calculate_rsi(close)
        self.assertTrue(rsi.iloc[:14].isna().all())


class TestKD(unittest.TestCase):
    def test_kd_range(self):
        """K and D values should be between 0 and 100."""
        np.random.seed(42)
        n = 50
        close = pd.Series(np.random.randn(n).cumsum() + 100 + np.linspace(0, 10, n))
        high = close + abs(np.random.randn(n))
        low = close - abs(np.random.randn(n))

        k, d = calculate_kd(high, low, close)
        valid_k = k.dropna()
        valid_d = d.dropna()
        self.assertTrue((valid_k >= 0).all() and (valid_k <= 100).all())
        self.assertTrue((valid_d >= 0).all() and (valid_d <= 100).all())


class TestMACD(unittest.TestCase):
    def test_macd_histogram(self):
        """Histogram = DIF - Signal."""
        close = pd.Series(np.random.randn(100).cumsum() + 100 + np.linspace(0, 20, 100))
        dif, signal, hist = calculate_macd(close)
        reconstructed = dif - signal
        np.testing.assert_allclose(hist.dropna().values, reconstructed.dropna().values, rtol=1e-9)


class TestBollingerBands(unittest.TestCase):
    def test_bb_width_positive(self):
        """Bandwidth must be positive."""
        close = pd.Series(np.random.randn(100).cumsum() + 100)
        upper, middle, lower, bw = calculate_bollinger_bands(close)
        valid = bw.dropna()
        self.assertTrue((valid > 0).all())

    def test_bb_middle_is_sma20(self):
        """Middle band should equal 20-period SMA."""
        close = pd.Series(np.random.randn(100).cumsum() + 100)
        _, middle, _, _ = calculate_bollinger_bands(close)
        sma20 = close.rolling(20).mean()
        np.testing.assert_allclose(middle.dropna().values, sma20.dropna().values, rtol=1e-9)


class TestCalculateIndicators(unittest.TestCase):
    def test_etf_no_kd(self):
        """ETF type should have NaN for K and D."""
        np.random.seed(42)
        n = 60
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame({
            "Open":   np.random.rand(n) * 10 + 100,
            "High":   np.random.rand(n) * 10 + 105,
            "Low":    np.random.rand(n) * 10 + 95,
            "Close":  np.random.rand(n) * 10 + 100,
            "Volume": np.random.randint(1000, 10000, n),
        }, index=dates)

        result = calculate_indicators(df, "ETF")
        self.assertTrue(result["k"].isna().all())
        self.assertTrue(result["d"].isna().all())

    def test_stock_has_kd(self):
        """STOCK type should have numeric K and D after convergence."""
        np.random.seed(42)
        n = 60
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame({
            "Open":   np.random.rand(n) * 10 + 100,
            "High":   np.random.rand(n) * 10 + 105,
            "Low":    np.random.rand(n) * 10 + 95,
            "Close":  np.random.rand(n) * 10 + 100,
            "Volume": np.random.randint(1000, 10000, n),
        }, index=dates)

        result = calculate_indicators(df, "STOCK")
        # After 20 rows, K and D should be non-NaN
        self.assertFalse(result["k"].iloc[-1:].isna().all())
        self.assertFalse(result["d"].iloc[-1:].isna().all())


if __name__ == "__main__":
    unittest.main()
