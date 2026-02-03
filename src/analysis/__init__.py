"""
Performance Analysis Package (TASK-152).

Tools for analyzing paper trading results:
- metrics: Core trading metrics (Sharpe, drawdown, profit factor)
- performance: Breakdown by hour, coin, pattern
- learning: Learning effectiveness analysis
"""

from src.analysis.metrics import (
    TradingMetrics,
    calculate_metrics,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_profit_factor,
)

from src.analysis.performance import (
    analyze_by_hour,
    analyze_by_coin,
    analyze_by_pattern,
    compare_periods,
    build_equity_curve,
)

from src.analysis.learning import (
    analyze_coin_score_accuracy,
    analyze_adaptation_effectiveness,
    analyze_pattern_confidence_accuracy,
    analyze_knowledge_growth,
)

__all__ = [
    # Metrics
    "TradingMetrics",
    "calculate_metrics",
    "calculate_sharpe_ratio",
    "calculate_max_drawdown",
    "calculate_profit_factor",
    # Performance
    "analyze_by_hour",
    "analyze_by_coin",
    "analyze_by_pattern",
    "compare_periods",
    "build_equity_curve",
    # Learning
    "analyze_coin_score_accuracy",
    "analyze_adaptation_effectiveness",
    "analyze_pattern_confidence_accuracy",
    "analyze_knowledge_growth",
]
