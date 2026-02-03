"""
Performance Breakdown Analysis (TASK-152).

Analyzes trading performance by various dimensions:
- By hour of day
- By coin
- By pattern
- By time period (early vs late)
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from src.analysis.metrics import TradingMetrics, calculate_metrics, build_equity_curve


def analyze_by_hour(trades: List[dict]) -> Dict[int, TradingMetrics]:
    """
    Analyze trading performance by hour of day.

    Args:
        trades: List of trade dictionaries.

    Returns:
        Dictionary mapping hour (0-23) to TradingMetrics.
    """
    by_hour = defaultdict(list)

    for trade in trades:
        ts = trade.get("entry_time") or trade.get("exit_time") or trade.get("timestamp")
        if ts:
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    continue
            hour = ts.hour
            by_hour[hour].append(trade)

    return {hour: calculate_metrics(hour_trades) for hour, hour_trades in by_hour.items()}


def analyze_by_coin(trades: List[dict]) -> Dict[str, TradingMetrics]:
    """
    Analyze trading performance by coin.

    Args:
        trades: List of trade dictionaries.

    Returns:
        Dictionary mapping coin symbol to TradingMetrics.
    """
    by_coin = defaultdict(list)

    for trade in trades:
        coin = trade.get("coin") or trade.get("symbol") or "UNKNOWN"
        by_coin[coin].append(trade)

    return {coin: calculate_metrics(coin_trades) for coin, coin_trades in by_coin.items()}


def analyze_by_pattern(trades: List[dict]) -> Dict[str, TradingMetrics]:
    """
    Analyze trading performance by pattern.

    Args:
        trades: List of trade dictionaries.

    Returns:
        Dictionary mapping pattern_id to TradingMetrics.
    """
    by_pattern = defaultdict(list)

    for trade in trades:
        pattern = trade.get("pattern_id") or trade.get("pattern") or "no_pattern"
        by_pattern[pattern].append(trade)

    return {pattern: calculate_metrics(pattern_trades) for pattern, pattern_trades in by_pattern.items()}


def analyze_by_day(trades: List[dict]) -> Dict[str, TradingMetrics]:
    """
    Analyze trading performance by day of week.

    Args:
        trades: List of trade dictionaries.

    Returns:
        Dictionary mapping day name to TradingMetrics.
    """
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    by_day = defaultdict(list)

    for trade in trades:
        ts = trade.get("exit_time") or trade.get("timestamp")
        if ts:
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    continue
            day_name = days[ts.weekday()]
            by_day[day_name].append(trade)

    return {day: calculate_metrics(day_trades) for day, day_trades in by_day.items()}


def analyze_by_session(trades: List[dict]) -> Dict[str, TradingMetrics]:
    """
    Analyze trading performance by market session.

    Sessions (UTC):
    - Asian: 00:00-08:00
    - European: 08:00-16:00
    - US: 16:00-24:00

    Args:
        trades: List of trade dictionaries.

    Returns:
        Dictionary mapping session name to TradingMetrics.
    """
    by_session = defaultdict(list)

    for trade in trades:
        ts = trade.get("entry_time") or trade.get("exit_time") or trade.get("timestamp")
        if ts:
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    continue
            hour = ts.hour
            if 0 <= hour < 8:
                session = "Asian"
            elif 8 <= hour < 16:
                session = "European"
            else:
                session = "US"
            by_session[session].append(trade)

    return {session: calculate_metrics(session_trades) for session, session_trades in by_session.items()}


def compare_periods(
    trades: List[dict],
    split_point: Optional[datetime] = None
) -> Dict[str, dict]:
    """
    Compare early vs late trading performance.

    Args:
        trades: List of trade dictionaries.
        split_point: DateTime to split periods (default: midpoint).

    Returns:
        Dictionary with 'first_half', 'second_half', and 'comparison' keys.
    """
    if not trades:
        return {
            "first_half": TradingMetrics().to_dict(),
            "second_half": TradingMetrics().to_dict(),
            "comparison": {},
        }

    # Sort by timestamp
    sorted_trades = sorted(
        trades,
        key=lambda t: t.get("exit_time") or t.get("timestamp") or ""
    )

    # Determine split point
    if split_point is None:
        midpoint_idx = len(sorted_trades) // 2
        first_half = sorted_trades[:midpoint_idx]
        second_half = sorted_trades[midpoint_idx:]
    else:
        first_half = []
        second_half = []
        for trade in sorted_trades:
            ts = trade.get("exit_time") or trade.get("timestamp")
            if ts:
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                if ts < split_point:
                    first_half.append(trade)
                else:
                    second_half.append(trade)

    metrics_first = calculate_metrics(first_half)
    metrics_second = calculate_metrics(second_half)

    # Calculate improvements
    comparison = {
        "trades_change": metrics_second.total_trades - metrics_first.total_trades,
        "win_rate_change": metrics_second.win_rate - metrics_first.win_rate,
        "profit_factor_change": metrics_second.profit_factor - metrics_first.profit_factor,
        "avg_pnl_change": metrics_second.avg_pnl - metrics_first.avg_pnl,
        "total_pnl_change": metrics_second.total_pnl - metrics_first.total_pnl,
        "drawdown_change": metrics_second.max_drawdown_pct - metrics_first.max_drawdown_pct,
        "sharpe_change": metrics_second.sharpe_ratio - metrics_first.sharpe_ratio,
        "improved": (
            metrics_second.win_rate > metrics_first.win_rate and
            metrics_second.profit_factor > metrics_first.profit_factor
        ),
    }

    return {
        "first_half": metrics_first.to_dict(),
        "second_half": metrics_second.to_dict(),
        "comparison": comparison,
    }


def get_best_worst_hours(hour_metrics: Dict[int, TradingMetrics], min_trades: int = 3) -> dict:
    """
    Identify best and worst trading hours.

    Args:
        hour_metrics: Dictionary from analyze_by_hour().
        min_trades: Minimum trades required for consideration.

    Returns:
        Dictionary with best/worst hours and their metrics.
    """
    filtered = {
        h: m for h, m in hour_metrics.items()
        if m.total_trades >= min_trades
    }

    if not filtered:
        return {"best_hours": [], "worst_hours": [], "message": "Not enough data"}

    # Sort by win rate
    sorted_hours = sorted(
        filtered.items(),
        key=lambda x: (x[1].win_rate, x[1].profit_factor),
        reverse=True
    )

    best = sorted_hours[:3]
    worst = sorted_hours[-3:] if len(sorted_hours) >= 3 else []

    return {
        "best_hours": [
            {"hour": h, "win_rate": m.win_rate, "pnl": m.total_pnl, "trades": m.total_trades}
            for h, m in best
        ],
        "worst_hours": [
            {"hour": h, "win_rate": m.win_rate, "pnl": m.total_pnl, "trades": m.total_trades}
            for h, m in worst
        ],
    }


def get_best_worst_coins(coin_metrics: Dict[str, TradingMetrics], min_trades: int = 3) -> dict:
    """
    Identify best and worst performing coins.

    Args:
        coin_metrics: Dictionary from analyze_by_coin().
        min_trades: Minimum trades required for consideration.

    Returns:
        Dictionary with best/worst coins and their metrics.
    """
    filtered = {
        c: m for c, m in coin_metrics.items()
        if m.total_trades >= min_trades
    }

    if not filtered:
        return {"best_coins": [], "worst_coins": [], "message": "Not enough data"}

    # Sort by total P&L
    sorted_coins = sorted(
        filtered.items(),
        key=lambda x: x[1].total_pnl,
        reverse=True
    )

    best = sorted_coins[:3]
    worst = sorted_coins[-3:] if len(sorted_coins) >= 3 else []

    return {
        "best_coins": [
            {"coin": c, "pnl": m.total_pnl, "win_rate": m.win_rate, "trades": m.total_trades}
            for c, m in best
        ],
        "worst_coins": [
            {"coin": c, "pnl": m.total_pnl, "win_rate": m.win_rate, "trades": m.total_trades}
            for c, m in worst
        ],
    }


def calculate_consistency(trades: List[dict], period_days: int = 1) -> dict:
    """
    Calculate trading consistency metrics.

    Args:
        trades: List of trade dictionaries.
        period_days: Period size for grouping (1 = daily).

    Returns:
        Dictionary with consistency metrics.
    """
    if not trades:
        return {"profitable_periods": 0, "total_periods": 0, "consistency_rate": 0}

    # Group by period
    by_period = defaultdict(float)

    for trade in trades:
        ts = trade.get("exit_time") or trade.get("timestamp")
        pnl = trade.get("pnl_usd") or trade.get("pnl") or 0

        if ts:
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    continue
            # Group by date (or period)
            period_key = ts.date()
            by_period[period_key] += pnl

    profitable = sum(1 for pnl in by_period.values() if pnl > 0)
    total = len(by_period)

    return {
        "profitable_periods": profitable,
        "total_periods": total,
        "consistency_rate": (profitable / total * 100) if total > 0 else 0,
        "period_type": "daily" if period_days == 1 else f"{period_days}-day",
    }
