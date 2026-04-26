"""
Position manager for MA Momentum Strategy v2.

Manages:
  - Entry/exit decisions based on signal
  - Fixed stop loss and take profit (ticker-specific for HIGH_DIV_ETF)
  - Overnight holding (always True per spec)

Reference: SPEC.md v2.0 Section 5 (Risk Parameters).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal

# ─────────────────────────────────────────────
# Default risk parameters
# ─────────────────────────────────────────────

DEFAULT_STOP_LOSS_PCT = 20.0
DEFAULT_TAKE_PROFIT_PCT = 20.0
HOLDING_OVERNIGHT = True

# HIGH_DIV_ETF (00919) uses tighter bands for low-volatility micro-trading
HIGH_DIV_STOP_LOSS_PCT = 7.0
HIGH_DIV_TAKE_PROFIT_PCT = 7.0


class StopLossError(Exception):
    """Raised when stop loss is hit."""


class TakeProfitError(Exception):
    """Raised when take profit is hit."""


# ─────────────────────────────────────────────
# Entry / Exit logic
# ─────────────────────────────────────────────

def should_enter(signal: dict) -> bool:
    """
    Determine whether to enter a position based on signal.

    Args:
        signal: Signal dict from generate_signal().

    Returns:
        True if signal is LONG or SHORT (i.e., directional, not NEUTRAL).
    """
    return signal["signal"] in ("LONG", "SHORT")


def _get_risk_params(ticker: str) -> tuple[float, float]:
    """
    Return (stop_loss_pct, take_profit_pct) for the given ticker.
    HIGH_DIV_ETF uses tighter bands.
    """
    if "00919" in ticker:
        return HIGH_DIV_STOP_LOSS_PCT, HIGH_DIV_TAKE_PROFIT_PCT
    return DEFAULT_STOP_LOSS_PCT, DEFAULT_TAKE_PROFIT_PCT


def should_exit(
    signal: dict,
    entry_price: float,
    position_type: str,  # "LONG" or "SHORT"
) -> bool:
    """
    Determine whether to exit an existing position.

    Args:
        signal: Latest signal dict from generate_signal().
        entry_price: The price at which the position was entered.
        position_type: "LONG" or "SHORT".

    Returns:
        True if any exit condition is met:
        - MA death cross (LONG position + MA bearish) → exit LONG
        - MA golden cross (SHORT position + MA bullish) → exit SHORT
        - Stop loss threshold hit
        - Take profit threshold hit

    Raises:
        StopLossError: If stop loss is hit.
        TakeProfitError: If take profit is hit.
    """
    current_price = signal["price"]
    ma5 = signal["indicators"].get("ma5")
    ma10 = signal["indicators"].get("ma10")
    ma20 = signal["indicators"].get("ma20")
    ticker = signal["ticker"]

    stop_loss_pct, take_profit_pct = _get_risk_params(ticker)

    # Determine which MA pair to use based on ticker type (ETF vs STOCK)
    ma_short = ma5 if ma5 is not None else ma10
    ma_long = ma10 if ma5 is not None else ma20

    # ── Stop loss / Take profit ──
    if position_type == "LONG":
        drop_pct = (entry_price - current_price) / entry_price * 100
        if drop_pct >= stop_loss_pct:
            raise StopLossError(
                f"Stop loss triggered: price dropped {drop_pct:.2f}% "
                f"from entry {entry_price:.2f} to {current_price:.2f}"
            )
        gain_pct = (current_price - entry_price) / entry_price * 100
        if gain_pct >= take_profit_pct:
            raise TakeProfitError(
                f"Take profit triggered: price rose {gain_pct:.2f}% "
                f"from entry {entry_price:.2f} to {current_price:.2f}"
            )
        # MA death cross → exit LONG (for STOCK tickers)
        if (ma_short is not None and ma_long is not None) and ma_short < ma_long:
            return True

    elif position_type == "SHORT":
        rise_pct = (current_price - entry_price) / entry_price * 100
        if rise_pct >= stop_loss_pct:
            raise StopLossError(
                f"Stop loss triggered (short): price rose {rise_pct:.2f}% "
                f"from entry {entry_price:.2f} to {current_price:.2f}"
            )
        gain_pct = (entry_price - current_price) / entry_price * 100
        if gain_pct >= take_profit_pct:
            raise TakeProfitError(
                f"Take profit triggered (short): price dropped {gain_pct:.2f}% "
                f"from entry {entry_price:.2f} to {current_price:.2f}"
            )
        # MA golden cross → exit SHORT (for STOCK tickers)
        if (ma_short is not None and ma_long is not None) and ma_short > ma_long:
            return True

    return False


def get_stop_loss(entry_price: float, position_type: str, ticker: str = "") -> float:
    """
    Calculate stop loss price from entry price.

    Args:
        entry_price: Position entry price.
        position_type: "LONG" or "SHORT".
        ticker: Optional ticker for per-ticker params.

    Returns:
        Stop loss price (absolute value).
    """
    sl_pct, _ = _get_risk_params(ticker) if ticker else (DEFAULT_STOP_LOSS_PCT, DEFAULT_TAKE_PROFIT_PCT)
    if position_type == "LONG":
        return round(entry_price * (1 - sl_pct / 100), 2)
    else:
        return round(entry_price * (1 + sl_pct / 100), 2)


def get_take_profit(entry_price: float, position_type: str, ticker: str = "") -> float:
    """
    Calculate take profit price from entry price.

    Args:
        entry_price: Position entry price.
        position_type: "LONG" or "SHORT".
        ticker: Optional ticker for per-ticker params.

    Returns:
        Take profit price (absolute value).
    """
    _, tp_pct = _get_risk_params(ticker) if ticker else (DEFAULT_STOP_LOSS_PCT, DEFAULT_TAKE_PROFIT_PCT)
    if position_type == "LONG":
        return round(entry_price * (1 + tp_pct / 100), 2)
    else:
        return round(entry_price * (1 - tp_pct / 100), 2)


# ─────────────────────────────────────────────
# Position state tracker (dataclass)
# ─────────────────────────────────────────────

@dataclass
class Position:
    """Represents an active position."""
    ticker: str
    entry_price: float
    position_type: str   # "LONG" or "SHORT"
    entry_date: str       # ISO date string

    @property
    def stop_loss(self) -> float:
        return get_stop_loss(self.entry_price, self.position_type, self.ticker)

    @property
    def take_profit(self) -> float:
        return get_take_profit(self.entry_price, self.position_type, self.ticker)


if __name__ == "__main__":
    entry = 100.0
    print(f"Entry: {entry} → SL(LONG): {get_stop_loss(entry, 'LONG')}  TP(LONG): {get_take_profit(entry, 'LONG')}")
    print(f"Entry: {entry} → SL(SHORT): {get_stop_loss(entry, 'SHORT')}  TP(SHORT): {get_take_profit(entry, 'SHORT')}")
    print(f"\n00919 Entry: {entry} → SL: {get_stop_loss(entry, 'LONG', '00919.TW')}  TP: {get_take_profit(entry, 'LONG', '00919.TW')}")

    # Test should_exit
    sig_long_exit = {
        "signal": "SHORT",
        "price": 78.0,
        "ticker": "2330.TW",
        "indicators": {"ma5": 79.0, "ma10": 80.0, "ma20": 82.0},
    }
    print(f"\n  should_exit LONG @ 100, price now 78 (20% drop = stop loss): ", end="")
    try:
        should_exit(sig_long_exit, 100.0, "LONG")
        print("False (no exit)")
    except StopLossError as e:
        print(f"StopLossError: {e}")

    print("✅ portfolio/position_manager.py OK")
