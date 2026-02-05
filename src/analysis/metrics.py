"""
Trading Metrics Calculator (TASK-152).

Calculates core trading performance metrics:
- Win rate, profit factor, total P&L
- Sharpe ratio, max drawdown
- Average win/loss statistics
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple, Optional

from src.calculations import (
    calculate_win_rate,
    calculate_profit_factor,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    build_equity_curve,
)


@dataclass
class TradingMetrics:
    """Complete trading performance metrics."""

    # Trade counts
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0

    # Win rate
    win_rate: float = 0.0

    # P&L metrics
    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: float = 0.0

    # Average metrics
    avg_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_win_loss_ratio: float = 0.0

    # Extremes
    largest_win: float = 0.0
    largest_loss: float = 0.0

    # Risk metrics
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0

    # Time metrics
    avg_trade_duration_sec: float = 0.0
    total_duration_sec: float = 0.0

    # Period info
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    trading_days: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "breakeven": self.breakeven,
            "win_rate": self.win_rate,
            "total_pnl": self.total_pnl,
            "gross_profit": self.gross_profit,
            "gross_loss": self.gross_loss,
            "profit_factor": self.profit_factor,
            "avg_pnl": self.avg_pnl,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "avg_win_loss_ratio": self.avg_win_loss_ratio,
            "largest_win": self.largest_win,
            "largest_loss": self.largest_loss,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "avg_trade_duration_sec": self.avg_trade_duration_sec,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "trading_days": self.trading_days,
        }

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Total Trades: {self.total_trades}",
            f"Win Rate: {self.win_rate:.1f}% ({self.wins}/{self.total_trades})",
            f"Total P&L: ${self.total_pnl:+.2f}",
            f"Profit Factor: {self.profit_factor:.2f}",
            f"Avg Win: ${self.avg_win:.2f}, Avg Loss: ${self.avg_loss:.2f}",
            f"Largest Win: ${self.largest_win:.2f}, Largest Loss: ${self.largest_loss:.2f}",
            f"Max Drawdown: ${self.max_drawdown:.2f} ({self.max_drawdown_pct:.1f}%)",
            f"Sharpe Ratio: {self.sharpe_ratio:.2f}",
        ]
        return "\n".join(lines)


def calculate_metrics(trades: List[dict], starting_balance: float = 1000.0) -> TradingMetrics:
    """
    Calculate all trading metrics from a list of trades.

    Args:
        trades: List of trade dictionaries with at least:
            - pnl_usd or pnl: Trade profit/loss
            - exit_time or timestamp: Trade timestamp
            - duration_seconds (optional): Trade duration
        starting_balance: Initial account balance for drawdown calculation.

    Returns:
        TradingMetrics with all calculated values.
    """
    metrics = TradingMetrics()

    if not trades:
        return metrics

    # Sort by exit time
    sorted_trades = sorted(
        trades,
        key=lambda t: t.get("exit_time") or t.get("timestamp") or ""
    )

    metrics.total_trades = len(sorted_trades)

    # Calculate P&L metrics
    pnl_values = []
    durations = []
    timestamps = []

    for trade in sorted_trades:
        pnl = trade.get("pnl_usd") or trade.get("pnl") or 0
        pnl_values.append(pnl)

        # Track wins/losses
        if pnl > 0:
            metrics.wins += 1
            metrics.gross_profit += pnl
            if pnl > metrics.largest_win:
                metrics.largest_win = pnl
        elif pnl < 0:
            metrics.losses += 1
            metrics.gross_loss += abs(pnl)
            if pnl < metrics.largest_loss:
                metrics.largest_loss = pnl
        else:
            metrics.breakeven += 1

        # Track duration
        duration = trade.get("duration_seconds") or trade.get("duration_sec") or 0
        if duration:
            durations.append(duration)

        # Track timestamps
        ts = trade.get("exit_time") or trade.get("timestamp")
        if ts:
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    ts = None
            if ts:
                timestamps.append(ts)

    # Win rate
    metrics.win_rate = calculate_win_rate(metrics.wins, metrics.total_trades)

    # P&L totals
    metrics.total_pnl = sum(pnl_values)

    # Profit factor
    metrics.profit_factor = calculate_profit_factor(
        metrics.gross_profit, metrics.gross_loss
    )

    # Averages
    if metrics.total_trades > 0:
        metrics.avg_pnl = metrics.total_pnl / metrics.total_trades

    if metrics.wins > 0:
        metrics.avg_win = metrics.gross_profit / metrics.wins

    if metrics.losses > 0:
        metrics.avg_loss = metrics.gross_loss / metrics.losses

    if metrics.avg_loss > 0:
        metrics.avg_win_loss_ratio = metrics.avg_win / metrics.avg_loss

    # Duration
    if durations:
        metrics.avg_trade_duration_sec = sum(durations) / len(durations)
        metrics.total_duration_sec = sum(durations)

    # Date range
    if timestamps:
        metrics.start_date = min(timestamps)
        metrics.end_date = max(timestamps)
        delta = metrics.end_date - metrics.start_date
        metrics.trading_days = max(1, delta.days + 1)

    # Build equity curve and calculate drawdown
    equity_curve = build_equity_curve(pnl_values, starting_balance)
    dd_amount, dd_pct = calculate_max_drawdown(equity_curve)
    metrics.max_drawdown = dd_amount
    metrics.max_drawdown_pct = dd_pct

    # Sharpe ratio (using daily returns if we have dates)
    if metrics.trading_days > 1 and timestamps:
        daily_returns = calculate_daily_returns(sorted_trades)
        metrics.sharpe_ratio = calculate_sharpe_ratio(daily_returns)
    elif pnl_values:
        # Fallback: use trade returns as proxy
        returns = [p / starting_balance for p in pnl_values]
        metrics.sharpe_ratio = calculate_sharpe_ratio(returns)

    return metrics


def calculate_daily_returns(trades: List[dict]) -> List[float]:
    """
    Calculate daily returns from trades.

    Args:
        trades: List of trades with exit_time/timestamp and pnl.

    Returns:
        List of daily return values.
    """
    from collections import defaultdict

    daily_pnl = defaultdict(float)

    for trade in trades:
        ts = trade.get("exit_time") or trade.get("timestamp")
        pnl = trade.get("pnl_usd") or trade.get("pnl") or 0

        if ts:
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    continue
            date_key = ts.date()
            daily_pnl[date_key] += pnl

    # Sort by date and return values
    sorted_dates = sorted(daily_pnl.keys())
    return [daily_pnl[d] for d in sorted_dates]
