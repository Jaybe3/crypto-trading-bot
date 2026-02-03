#!/usr/bin/env python3
"""
Performance Analysis Script (TASK-152).

Main entry point for analyzing paper trading results.
Generates all reports and provides overall assessment.

Usage:
    python scripts/analyze_performance.py [--db PATH] [--days 7] [--output DIR]
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database
from src.analysis.metrics import calculate_metrics
from src.analysis.performance import (
    analyze_by_hour,
    analyze_by_coin,
    analyze_by_pattern,
    compare_periods,
    get_best_worst_hours,
    get_best_worst_coins,
    calculate_consistency,
)
from src.analysis.learning import (
    analyze_coin_score_accuracy,
    analyze_adaptation_effectiveness,
    analyze_pattern_confidence_accuracy,
    analyze_knowledge_growth,
    calculate_learning_score,
)

# Import report generation
from scripts.generate_report import (
    load_trades,
    generate_summary_report,
    generate_learning_report,
    generate_improvement_report,
    generate_detailed_report,
)
from scripts.export_trades import export_trades_csv, export_full_dataset


def print_banner():
    """Print analysis banner."""
    print()
    print("=" * 80)
    print("              PAPER TRADING PERFORMANCE ANALYSIS")
    print("=" * 80)
    print()


def assess_readiness(metrics, comparison, adapt_effectiveness, learning_score) -> dict:
    """
    Assess readiness for live trading.

    Returns dictionary with assessment details.
    """
    checks = []

    # Check 1: Profitability
    if metrics.total_pnl > 0:
        checks.append({"name": "Profitability", "passed": True, "detail": f"P&L: ${metrics.total_pnl:+.2f}"})
    else:
        checks.append({"name": "Profitability", "passed": False, "detail": f"P&L: ${metrics.total_pnl:+.2f} (negative)"})

    # Check 2: Profit Factor
    if metrics.profit_factor > 1.0:
        checks.append({"name": "Profit Factor", "passed": True, "detail": f"PF: {metrics.profit_factor:.2f}"})
    else:
        checks.append({"name": "Profit Factor", "passed": False, "detail": f"PF: {metrics.profit_factor:.2f} (<1.0)"})

    # Check 3: Win Rate
    if metrics.win_rate > 45:
        checks.append({"name": "Win Rate", "passed": True, "detail": f"WR: {metrics.win_rate:.1f}%"})
    else:
        checks.append({"name": "Win Rate", "passed": False, "detail": f"WR: {metrics.win_rate:.1f}% (<45%)"})

    # Check 4: Drawdown
    if metrics.max_drawdown_pct < 20:
        checks.append({"name": "Max Drawdown", "passed": True, "detail": f"DD: {metrics.max_drawdown_pct:.1f}%"})
    else:
        checks.append({"name": "Max Drawdown", "passed": False, "detail": f"DD: {metrics.max_drawdown_pct:.1f}% (>20%)"})

    # Check 5: Learning Effectiveness
    eff_rate = adapt_effectiveness.get("effectiveness_rate", 0)
    if eff_rate > 50:
        checks.append({"name": "Learning Effective", "passed": True, "detail": f"Eff: {eff_rate:.1f}%"})
    else:
        checks.append({"name": "Learning Effective", "passed": False, "detail": f"Eff: {eff_rate:.1f}% (<50%)"})

    # Check 6: Improvement
    improved = comparison["comparison"].get("improved", False)
    wr_change = comparison["comparison"].get("win_rate_change", 0)
    if improved:
        checks.append({"name": "Improving", "passed": True, "detail": f"WR change: {wr_change:+.1f}%"})
    else:
        checks.append({"name": "Improving", "passed": False, "detail": f"WR change: {wr_change:+.1f}%"})

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)

    if passed >= 5:
        status = "READY"
        recommendation = "PROCEED TO LIVE TRADING"
        color = "\033[92m"  # Green
    elif passed >= 3:
        status = "NEEDS WORK"
        recommendation = "CONTINUE PAPER TRADING"
        color = "\033[93m"  # Yellow
    else:
        status = "NOT READY"
        recommendation = "MAJOR CHANGES NEEDED"
        color = "\033[91m"  # Red

    return {
        "checks": checks,
        "passed": passed,
        "total": total,
        "status": status,
        "recommendation": recommendation,
        "color": color,
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze Paper Trading Performance")
    parser.add_argument("--db", default="data/trading_bot.db", help="Database path")
    parser.add_argument("--days", type=int, default=7, help="Days to analyze")
    parser.add_argument("--output", "-o", default="reports", help="Output directory")
    parser.add_argument("--export", action="store_true", help="Export trade data")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    args = parser.parse_args()

    print_banner()

    if not os.path.exists(args.db):
        print(f"ERROR: Database not found at {args.db}")
        print("Make sure you have run paper trading first.")
        sys.exit(1)

    print(f"Analyzing {args.days} days of trading data...")
    print(f"Database: {args.db}")
    print()

    db = Database(db_path=args.db)
    trades = load_trades(db, args.days)

    if not trades:
        print("ERROR: No trades found in the specified period.")
        print("Make sure paper trading has been running.")
        sys.exit(1)

    print(f"Found {len(trades)} trades")
    print()

    # Calculate metrics
    print("Calculating metrics...")
    metrics = calculate_metrics(trades)

    print("Analyzing by dimension...")
    by_hour = analyze_by_hour(trades)
    by_coin = analyze_by_coin(trades)
    by_pattern = analyze_by_pattern(trades)

    print("Measuring learning effectiveness...")
    coin_accuracy = analyze_coin_score_accuracy(db)
    adapt_effectiveness = analyze_adaptation_effectiveness(db)
    pattern_accuracy = analyze_pattern_confidence_accuracy(db)
    knowledge_growth = analyze_knowledge_growth(db, args.days)
    learning_score = calculate_learning_score(
        coin_accuracy, adapt_effectiveness, pattern_accuracy, knowledge_growth
    )

    print("Comparing periods...")
    comparison = compare_periods(trades)
    consistency = calculate_consistency(trades)

    print()

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Generate reports
    print("Generating reports...")

    summary = generate_summary_report(db, trades, args.days)
    with open(os.path.join(args.output, "summary.txt"), "w") as f:
        f.write(summary)
    print(f"  - {args.output}/summary.txt")

    learning = generate_learning_report(db, args.days)
    with open(os.path.join(args.output, "learning.txt"), "w") as f:
        f.write(learning)
    print(f"  - {args.output}/learning.txt")

    improvement = generate_improvement_report(trades)
    with open(os.path.join(args.output, "improvement.txt"), "w") as f:
        f.write(improvement)
    print(f"  - {args.output}/improvement.txt")

    # Detailed reports
    generate_detailed_report(db, trades, os.path.join(args.output, "detailed"), args.days)
    print(f"  - {args.output}/detailed/")

    # Export data if requested
    if args.export:
        print()
        print("Exporting data...")
        export_trades_csv(db, os.path.join(args.output, "trades.csv"), args.days)
        print(f"  - {args.output}/trades.csv")
        export_full_dataset(db, os.path.join(args.output, "data_export"), args.days)
        print(f"  - {args.output}/data_export/")

    print()

    # Final assessment
    assessment = assess_readiness(metrics, comparison, adapt_effectiveness, learning_score)

    print("=" * 80)
    print("                         ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print("KEY FINDINGS:")
    print(f"  Win Rate:       {metrics.win_rate:.1f}% (Target: >45%) "
          f"{'[OK]' if metrics.win_rate > 45 else '[LOW]'}")
    print(f"  Profit Factor:  {metrics.profit_factor:.2f} (Target: >1.0) "
          f"{'[OK]' if metrics.profit_factor > 1.0 else '[LOW]'}")
    print(f"  Total P&L:      ${metrics.total_pnl:+.2f} (Target: >$0) "
          f"{'[OK]' if metrics.total_pnl > 0 else '[NEGATIVE]'}")
    print(f"  Max Drawdown:   {metrics.max_drawdown_pct:.1f}% (Target: <20%) "
          f"{'[OK]' if metrics.max_drawdown_pct < 20 else '[HIGH]'}")
    print()
    print(f"  Learning Score: {learning_score['total_score']:.0f}/100 (Grade: {learning_score['grade']})")
    print(f"  Adaptations:    {adapt_effectiveness.get('effectiveness_rate', 0):.1f}% effective "
          f"{'[OK]' if adapt_effectiveness.get('effectiveness_rate', 0) > 50 else '[LOW]'}")
    print(f"  Improving:      {'Yes' if comparison['comparison'].get('improved') else 'No'} "
          f"(WR change: {comparison['comparison'].get('win_rate_change', 0):+.1f}%)")
    print()

    # Checklist
    print("READINESS CHECKLIST:")
    for check in assessment["checks"]:
        icon = "\033[92m[PASS]\033[0m" if check["passed"] else "\033[91m[FAIL]\033[0m"
        print(f"  {icon} {check['name']}: {check['detail']}")
    print()

    reset = "\033[0m"
    print(f"{assessment['color']}RECOMMENDATION: {assessment['recommendation']}{reset}")
    print(f"Status: {assessment['passed']}/{assessment['total']} checks passed")
    print()
    print(f"Reports saved to: {args.output}/")
    print("=" * 80)

    # Exit with appropriate code
    if assessment["status"] == "READY":
        sys.exit(0)
    elif assessment["status"] == "NEEDS WORK":
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
