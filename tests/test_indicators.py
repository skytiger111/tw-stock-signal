"""
Unit tests for strategy/indicators.py.

Tests cover:
  - RSI calculation (RSI > 50 → bullish, RSI < 50 → bearish)
  - KD calculation (K > D for bullish)
  - MACD calculation (DIF = fast EMA - slow EMA)
  - Bollinger Bands (upper = middle + 2*std)
  - calculate_indicators() main entry point

Acceptance criteria (Sprint 1 Stage 1):
  - mypy --strict passes
  - RSI initial warmup period yields NaN for first 14 bars
  - RSI of a rising series > 50
  - RSI of a falling series < 50
  - K > D when price is in uptrend
"""

import pytest
import pandas as pd
import numpy as np
from strategy.indicators import (
    calculate_rsi,
    calculate_kd,
    calculate_macd,
    calculate_bollinger_bands,
    calculate_indicators,
)


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def rising_price() -> pd.Series:
    """ monotonically rising price → RSI should be > 50 """
    return pd.Series(np.arange(1, 101, dtype=float), name="Close")


@pytest.fixture
def falling_price() -> pd.Series:
    """ monotonically falling price → RSI should be < 50 """
    return pd.Series(np.arange(100, 0, -1, dtype=float), name="Close")


@pytest.fixture
def ohlcv_rising() -> pd.DataFrame:
    """OHLCV DataFrame with steadily rising prices."""
    n = 60
    close = np.arange(1, n + 1, dtype=float) * 10
    return pd.DataFrame({
        "Open":  close * 0.99,
        "High":  close * 1.02,
        "Low":   close * 0.97,
        "Close": close,
        "Volume": np.full(n, 1000.0),
    })


@pytest.fixture
def ohlcv_falling() -> pd.DataFrame:
    """OHLCV DataFrame with steadily falling prices."""
    n = 60
    close = np.arange(n, 0, -1, dtype=float) * 10
    return pd.DataFrame({
        "Open":  close * 1.01,
        "High":  close * 1.03,
        "Low":   close * 0.98,
        "Close": close,
        "Volume": np.full(n, 1000.0),
    })


# ─────────────────────────────────────────────
# RSI tests
# ─────────────────────────────────────────────

class TestRSI:
    def test_rsi_warmup_period_returns_nan(self, rising_price: pd.Series) -> None:
        rsi = calculate_rsi(rising_price, period=14)
        # First 13 values (0-indexed) should be NaN (need at least 14 deltas)
        assert rsi.iloc[:13].isna().all(), "First 13 RSI values should be NaN during warmup"
        assert rsi.iloc[13:].notna().any(), "RSI should produce values after warmup"

    def test_rsi_bullish_series_above_50(self, rising_price: pd.Series) -> None:
        rsi = calculate_rsi(rising_price, period=14)
        valid_rsi = rsi.dropna()
        assert (valid_rsi > 50).all(), "RSI of rising price should always be > 50"

    def test_rsi_bearish_series_below_50(self, falling_price: pd.Series) -> None:
        rsi = calculate_rsi(falling_price, period=14)
        valid_rsi = rsi.dropna()
        assert (valid_rsi < 50).all(), "RSI of falling price should always be < 50"

    def test_rsi_bounds_0_to_100(self, rising_price: pd.Series) -> None:
        rsi = calculate_rsi(rising_price, period=14)
        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()


# ─────────────────────────────────────────────
# KD tests
# ─────────────────────────────────────────────

class TestKD:
    def test_kd_bullish_k_above_d(self) -> None:
        """In a sustained uptrend K should be above D."""
        close = pd.Series([10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40] * 3)
        high  = close * 1.01
        low   = close * 0.99
        k, d = calculate_kd(high, low, close)
        valid_k = k.dropna()
        valid_d = d.dropna()
        assert (valid_k.values > valid_d.values).all(), "K should be above D in uptrend"

    def test_kd_bearish_k_below_d(self) -> None:
        """In a sustained downtrend K should be below D."""
        close = pd.Series([40, 38, 36, 34, 32, 30, 28, 26, 24, 22, 20, 18, 16, 14, 12, 10] * 3)
        high  = close * 1.01
        low   = close * 0.99
        k, d = calculate_kd(high, low, close)
        valid_k = k.dropna()
        valid_d = d.dropna()
        assert (valid_k.values < valid_d.values).all(), "K should be below D in downtrend"

    def test_kd_bounds_0_to_100(self) -> None:
        close = pd.Series(np.linspace(10, 100, 60))
        high  = close * 1.02
        low   = close * 0.98
        k, d = calculate_kd(high, low, close)
        valid_k = k.dropna()
        valid_d = d.dropna()
        assert (valid_k >= 0).all() and (valid_k <= 100).all()
        assert (valid_d >= 0).all() and (valid_d <= 100).all()


# ─────────────────────────────────────────────
# MACD tests
# ─────────────────────────────────────────────

class TestMACD:
    def test_macd_dif_positive_in_uptrend(self) -> None:
        close = pd.Series(np.arange(1, 101, dtype=float) * 10)
        dif, signal, histogram = calculate_macd(close)
        valid_dif = dif.dropna()
        assert (valid_dif > 0).all(), "DIF should be positive in sustained uptrend"

    def test_macd_dif_negative_in_downtrend(self) -> None:
        close = pd.Series(np.arange(100, 0, -1, dtype=float) * 10)
        dif, signal, histogram = calculate_macd(close)
        valid_dif = dif.dropna()
        assert (valid_dif < 0).all(), "DIF should be negative in sustained downtrend"

    def test_histogram_sign_matches_dif_minus_signal(self) -> None:
        close = pd.Series(np.linspace(10, 100, 60))
        dif, signal, histogram = calculate_macd(close)
        valid = histogram.dropna()
        expected = (dif - signal).dropna()
        np.testing.assert_array_almost_equal(valid.values, expected.values[:len(valid)])


# ─────────────────────────────────────────────
# Bollinger Bands tests
# ─────────────────────────────────────────────

class TestBollingerBands:
    def test_upper_above_middle(self) -> None:
        close = pd.Series(np.linspace(10, 100, 60))
        upper, middle, lower, bandwidth = calculate_bollinger_bands(close)
        valid = upper.dropna()
        valid_m = middle.dropna()
        assert (valid > valid_m).all(), "Upper band must be above middle band"

    def test_middle_above_lower(self) -> None:
        close = pd.Series(np.linspace(10, 100, 60))
        upper, middle, lower, bandwidth = calculate_bollinger_bands(close)
        valid_m = middle.dropna()
        valid_l = lower.dropna()
        assert (valid_m > valid_l).all(), "Middle band must be above lower band"

    def test_bandwidth_positive(self) -> None:
        close = pd.Series(np.linspace(10, 100, 60))
        upper, middle, lower, bandwidth = calculate_bollinger_bands(close)
        valid_bw = bandwidth.dropna()
        assert (valid_bw > 0).all(), "Bandwidth must be positive"


# ─────────────────────────────────────────────
# calculate_indicators integration test
# ─────────────────────────────────────────────

class TestCalculateIndicators:
    def test_stock_ticker_returns_kd_columns(self, ohlcv_rising: pd.DataFrame) -> None:
        result = calculate_indicators(ohlcv_rising, ticker_type="STOCK")
        assert "k" in result.columns
        assert "d" in result.columns
        # KD should be non-NaN once enough data accumulated
        valid_k = result["k"].dropna()
        assert len(valid_k) > 0, "KD should produce values for STOCK"

    def test_etf_ticker_kd_is_nan(self, ohlcv_rising: pd.DataFrame) -> None:
        result = calculate_indicators(ohlcv_rising, ticker_type="ETF")
        assert result["k"].isna().all(), "KD should be NaN for ETF"

    def test_all_required_columns_present(self, ohlcv_rising: pd.DataFrame) -> None:
        result = calculate_indicators(ohlcv_rising, ticker_type="STOCK")
        required = [
            "ma5", "ma10", "ma20",
            "rsi14", "k", "d",
            "macd_dif", "macd_signal", "macd_histogram",
            "bb_upper", "bb_middle", "bb_lower", "bb_bandwidth",
        ]
        for col in required:
            assert col in result.columns, f"Missing column: {col}"

    def test_original_ohlcv_columns_preserved(self, ohlcv_rising: pd.DataFrame) -> None:
        result = calculate_indicators(ohlcv_rising, ticker_type="STOCK")
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            assert col in result.columns, f"Original column {col} should be preserved"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
