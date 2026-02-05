"""
Financial Calculations - Single Source of Truth.

This module consolidates all financial math used in the trading system.
All P&L, metrics, and risk calculations should import from here.

TASK-AUDIT: Financial Math Consolidation
"""

import math
from typing import List, Tuple, Optional


# =============================================================================
# Core P&L Calculations
# =============================================================================

def calculate_pnl(
    entry_price: float,
    current_price: float,
    size_usd: float,
    direction: str = "LONG"
) -> float:
    """
    Calculate profit/loss for a position.

    This is the canonical P&L formula used throughout the system.

    Args:
        entry_price: Price at position entry
        current_price: Current market price (or exit price)
        size_usd: Position size in USD
        direction: "LONG" or "SHORT"

    Returns:
        P&L in USD (positive = profit, negative = loss)

    Example:
        >>> calculate_pnl(100, 105, 1000, "LONG")
        50.0  # 5% gain on $1000 = $50

        >>> calculate_pnl(100, 95, 1000, "SHORT")
        50.0  # 5% drop = profit for short
    """
    if entry_price <= 0 or size_usd <= 0:
        return 0.0

    price_change_pct = (current_price - entry_price) / entry_price

    if direction.upper() == "SHORT":
        price_change_pct = -price_change_pct

    return size_usd * price_change_pct


def calculate_pnl_percentage(
    pnl_usd: float,
    size_usd: float
) -> float:
    """
    Calculate P&L as a percentage of position size.

    Args:
        pnl_usd: Profit/loss in USD
        size_usd: Position size in USD

    Returns:
        P&L percentage (e.g., 5.0 for 5%)

    Example:
        >>> calculate_pnl_percentage(50, 1000)
        5.0
    """
    if size_usd <= 0:
        return 0.0
    return (pnl_usd / size_usd) * 100


def calculate_return_pct(
    entry_price: float,
    exit_price: float,
    direction: str = "LONG"
) -> float:
    """
    Calculate return percentage from entry to exit.

    Args:
        entry_price: Price at position entry
        exit_price: Price at position exit
        direction: "LONG" or "SHORT"

    Returns:
        Return percentage (e.g., 5.0 for 5%)

    Example:
        >>> calculate_return_pct(100, 105, "LONG")
        5.0

        >>> calculate_return_pct(100, 95, "SHORT")
        5.0
    """
    if entry_price <= 0:
        return 0.0

    if direction.upper() == "LONG":
        return ((exit_price - entry_price) / entry_price) * 100
    else:
        return ((entry_price - exit_price) / entry_price) * 100


# =============================================================================
# Performance Metrics
# =============================================================================

def calculate_win_rate(wins: int, total_trades: int) -> float:
    """
    Calculate win rate as a percentage.

    Args:
        wins: Number of winning trades
        total_trades: Total number of trades

    Returns:
        Win rate percentage (e.g., 60.0 for 60%)

    Example:
        >>> calculate_win_rate(6, 10)
        60.0
    """
    if total_trades <= 0:
        return 0.0
    return (wins / total_trades) * 100


def calculate_profit_factor(
    gross_profit: float,
    gross_loss: float
) -> float:
    """
    Calculate profit factor (gross profit / gross loss).

    Args:
        gross_profit: Total profit from winning trades (positive)
        gross_loss: Total loss from losing trades (positive, not negative)

    Returns:
        Profit factor. Values > 1 indicate profitability.
        Returns float('inf') if no losses but has profit.
        Returns 0 if no profit.

    Example:
        >>> calculate_profit_factor(1000, 500)
        2.0  # Makes $2 for every $1 lost
    """
    if gross_loss <= 0:
        return float('inf') if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def calculate_avg_win_loss_ratio(
    avg_win: float,
    avg_loss: float
) -> float:
    """
    Calculate average win to average loss ratio.

    Args:
        avg_win: Average winning trade amount (positive)
        avg_loss: Average losing trade amount (positive, not negative)

    Returns:
        Win/loss ratio. Values > 1 mean wins are larger than losses.

    Example:
        >>> calculate_avg_win_loss_ratio(100, 50)
        2.0  # Average win is 2x average loss
    """
    if avg_loss <= 0:
        return float('inf') if avg_win > 0 else 0.0
    return avg_win / avg_loss


def calculate_expectancy(
    win_rate_pct: float,
    avg_win: float,
    avg_loss: float
) -> float:
    """
    Calculate expected value per trade.

    Args:
        win_rate_pct: Win rate as percentage (e.g., 60 for 60%)
        avg_win: Average winning trade amount
        avg_loss: Average losing trade amount (positive)

    Returns:
        Expected value per trade in USD

    Example:
        >>> calculate_expectancy(60, 100, 50)
        40.0  # (0.6 * 100) - (0.4 * 50) = 60 - 20 = 40
    """
    win_rate = win_rate_pct / 100
    loss_rate = 1 - win_rate
    return (win_rate * avg_win) - (loss_rate * avg_loss)


def calculate_return_on_balance(
    total_pnl: float,
    initial_balance: float
) -> float:
    """
    Calculate return as percentage of initial balance.

    Args:
        total_pnl: Total profit/loss in USD
        initial_balance: Starting balance in USD

    Returns:
        Return percentage (e.g., 10.0 for 10% return)

    Example:
        >>> calculate_return_on_balance(1000, 10000)
        10.0
    """
    if initial_balance <= 0:
        return 0.0
    return (total_pnl / initial_balance) * 100


# =============================================================================
# Risk Metrics
# =============================================================================

def calculate_max_drawdown(
    equity_curve: List[float]
) -> Tuple[float, float]:
    """
    Calculate maximum drawdown from equity curve.

    Drawdown is the peak-to-trough decline during a specific period.

    Args:
        equity_curve: List of equity values over time

    Returns:
        Tuple of (max_drawdown_amount, max_drawdown_percentage)

    Example:
        >>> calculate_max_drawdown([1000, 1100, 900, 950, 1050])
        (200.0, 18.18...)  # Dropped from 1100 to 900
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0.0, 0.0

    peak = equity_curve[0]
    max_dd_amount = 0.0
    max_dd_pct = 0.0

    for equity in equity_curve:
        if equity > peak:
            peak = equity

        drawdown = peak - equity
        drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0

        if drawdown > max_dd_amount:
            max_dd_amount = drawdown
            max_dd_pct = drawdown_pct

    return max_dd_amount, max_dd_pct


def build_equity_curve(
    pnl_values: List[float],
    starting_balance: float = 10000.0
) -> List[float]:
    """
    Build equity curve from P&L values.

    Args:
        pnl_values: List of trade P&L values
        starting_balance: Initial account balance

    Returns:
        List of equity values after each trade

    Example:
        >>> build_equity_curve([100, -50, 200], 1000)
        [1000, 1100, 1050, 1250]
    """
    curve = [starting_balance]
    current = starting_balance

    for pnl in pnl_values:
        current += pnl
        curve.append(current)

    return curve


def calculate_sharpe_ratio(
    returns: List[float],
    risk_free_rate: float = 0.0,
    annualize: bool = True,
    periods_per_year: int = 365
) -> float:
    """
    Calculate Sharpe ratio.

    Sharpe ratio measures risk-adjusted return: (return - risk_free) / volatility

    Args:
        returns: List of periodic returns (daily, per-trade, etc.)
        risk_free_rate: Annual risk-free rate (default 0)
        annualize: Whether to annualize the ratio
        periods_per_year: Number of periods in a year (365 for daily, 252 for trading days)

    Returns:
        Sharpe ratio (higher is better, >1 is good, >2 is great)

    Example:
        >>> # Daily returns averaging 0.1% with 1% std dev
        >>> calculate_sharpe_ratio([0.001] * 100, periods_per_year=252)
        1.58...  # Annualized
    """
    if not returns or len(returns) < 2:
        return 0.0

    # Calculate mean and standard deviation
    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
    std_return = math.sqrt(variance) if variance > 0 else 0

    if std_return == 0:
        return 0.0

    # Adjust risk-free rate to per-period
    rf_per_period = risk_free_rate / periods_per_year if annualize else risk_free_rate

    # Calculate Sharpe
    sharpe = (mean_return - rf_per_period) / std_return

    # Annualize if requested
    if annualize:
        sharpe *= math.sqrt(periods_per_year)

    return sharpe


# =============================================================================
# Position Sizing
# =============================================================================

def calculate_position_size(
    balance: float,
    risk_pct: float,
    stop_loss_pct: float
) -> float:
    """
    Calculate position size based on risk management.

    Uses the formula: size = (balance * risk%) / stop_loss%

    Args:
        balance: Available balance in USD
        risk_pct: Percentage of balance willing to risk (e.g., 1.0 for 1%)
        stop_loss_pct: Stop loss percentage (e.g., 2.0 for 2%)

    Returns:
        Position size in USD

    Example:
        >>> calculate_position_size(10000, 1.0, 2.0)
        500.0  # Risk 1% of $10k = $100, with 2% SL = $500 position
    """
    if stop_loss_pct <= 0 or balance <= 0:
        return 0.0

    risk_amount = balance * (risk_pct / 100)
    return risk_amount / (stop_loss_pct / 100)


def apply_position_modifier(
    base_size: float,
    modifier: float,
    max_size: Optional[float] = None
) -> float:
    """
    Apply a position size modifier (e.g., for coin status).

    Args:
        base_size: Base position size in USD
        modifier: Multiplier (0.5 for reduced, 1.0 for normal, 1.5 for favored)
        max_size: Maximum allowed position size

    Returns:
        Adjusted position size in USD

    Example:
        >>> apply_position_modifier(100, 0.5)
        50.0  # Reduced to 50%
    """
    size = base_size * modifier

    if max_size is not None and size > max_size:
        size = max_size

    return size


# =============================================================================
# Utility Functions
# =============================================================================

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.

    Args:
        numerator: The dividend
        denominator: The divisor
        default: Value to return if denominator is zero

    Returns:
        Result of division or default value
    """
    if denominator == 0:
        return default
    return numerator / denominator


def clamp_percentage(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """
    Clamp a percentage value to valid range.

    Args:
        value: Percentage value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Clamped value
    """
    return max(min_val, min(max_val, value))
