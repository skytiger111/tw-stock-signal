"""
Ticker classifier — distinguishes ETF vs STOCK for MA period selection.
Reference: SPEC.md v2.0 Section 6 (Supported Stocks).
"""

from __future__ import annotations

SUPPORTED_TICKERS: dict[str, str] = {
    # Individual stocks (use MA5/MA10 + KD)
    "2330.TW": "STOCK",
    "2890.TW": "STOCK",
    "2881.TW": "STOCK",
    "2317.TW": "STOCK",
    # ETFs (use MA10/MA20, no KD)
    "0050.TW": "ETF",
    "0052.TW": "ETF",
    "00919.TW": "ETF",
    "009816.TW": "ETF",
}

TickerType = str  # "STOCK" | "ETF"


def classify_ticker(ticker: str) -> TickerType:
    """
    Classify ticker as 'STOCK' or 'ETF'.

    Args:
        ticker: Yahoo Finance ticker (e.g. "2330.TW").

    Returns:
        "STOCK" or "ETF".

    Raises:
        ValueError: If ticker is not in SUPPORTED_TICKERS.
    """
    if ticker not in SUPPORTED_TICKERS:
        raise ValueError(
            f"Unsupported ticker '{ticker}'. "
            f"Supported: {list(SUPPORTED_TICKERS.keys())}"
        )
    return SUPPORTED_TICKERS[ticker]


if __name__ == "__main__":
    # Sanity check
    for t, expected in [
        ("2330.TW", "STOCK"),
        ("0050.TW", "ETF"),
        ("00919.TW", "ETF"),
        ("2881.TW", "STOCK"),
    ]:
        result = classify_ticker(t)
        assert result == expected, f"{t}: expected {expected}, got {result}"
    print("✅ strategy/ticker_classifier.py OK")
