#!/usr/bin/env python3
"""
Report Generation Script (TASK-152).

Generates performance analysis reports.

Usage:
    python scripts/generate_report.py [--db PATH] [--output DIR] [--format text|json]
"""

import argparse
import json
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


def load_trades(db: Database, days: int = 7) -> list:
    """Load trades from database."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                trade_id, coin, direction, entry_price, exit_price,
                position_size_usd, pnl_usd, pnl_pct, entry_time, exit_time,
                exit_reason, pattern_id, strategy_id, duration_seconds
            FROM trade_journal
            WHERE exit_time >= ?
            ORDER BY exit_time ASC
        """, (cutoff,))

        rows = cursor.fetchall()

    return [
        {
            "trade_id": r[0],
            "coin": r[1],
            "direction": r[2],
            "entry_price": r[3],
            "exit_price": r[4],
            "position_size_usd": r[5],
            "pnl_usd": r[6],
            "pnl_pct": r[7],
            "entry_time": r[8],
            "exit_time": r[9],
            "exit_reason": r[10],
            "pattern_id": r[11],
            "strategy_id": r[12],
            "duration_seconds": r[13],
        }
        for r in rows
    ]


def generate_summary_report(db: Database, trades: list, days: int) -> str:
    """Generate one-page summary report."""
    metrics = calculate_metrics(trades)
    comparison = compare_periods(trades)
    consistency = calculate_consistency(trades)

    # Learning analysis
    coin_accuracy = analyze_coin_score_accuracy(db)
    adapt_effectiveness = analyze_adaptation_effectiveness(db)
    pattern_accuracy = analyze_pattern_confidence_accuracy(db)
    knowledge_growth = analyze_knowledge_growth(db, days)
    learning_score = calculate_learning_score(
        coin_accuracy, adapt_effectiveness, pattern_accuracy, knowledge_growth
    )

    # Determine overall assessment
    checks_passed = 0
    total_checks = 6

    if metrics.total_pnl > 0:
        checks_passed += 1
    if metrics.profit_factor > 1.0:
        checks_passed += 1
    if metrics.win_rate > 45:
        checks_passed += 1
    if metrics.max_drawdown_pct < 20:
        checks_passed += 1
    if adapt_effectiveness.get("effectiveness_rate", 0) > 50:
        checks_passed += 1
    if comparison["comparison"].get("improved", False):
        checks_passed += 1

    if checks_passed >= 5:
        overall = "PASS"
        recommendation = "PROCEED TO LIVE TRADING (with caution)"
    elif checks_passed >= 3:
        overall = "NEEDS IMPROVEMENT"
        recommendation = "CONTINUE PAPER TRADING - Address issues first"
    else:
        overall = "FAIL"
        recommendation = "MAJOR CHANGES NEEDED - Do not go live"

    # Build report
    lines = [
        "=" * 80,
        "                    PAPER TRADING PERFORMANCE REPORT",
        "=" * 80,
        f"Period: {metrics.start_date.strftime('%Y-%m-%d') if metrics.start_date else 'N/A'} to "
        f"{metrics.end_date.strftime('%Y-%m-%d') if metrics.end_date else 'N/A'} ({days} days)",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"OVERALL ASSESSMENT: {overall} ({checks_passed}/{total_checks} checks passed)",
        "",
        "KEY METRICS",
        "-" * 40,
        f"Total Trades:     {metrics.total_trades}",
        f"Win Rate:         {metrics.win_rate:.1f}% ({metrics.wins}/{metrics.total_trades})"
        f"  {'[OK]' if metrics.win_rate > 45 else '[LOW]'}",
        f"Total P&L:        ${metrics.total_pnl:+.2f}"
        f"  {'[OK]' if metrics.total_pnl > 0 else '[NEGATIVE]'}",
        f"Profit Factor:    {metrics.profit_factor:.2f}"
        f"  {'[OK]' if metrics.profit_factor > 1.0 else '[LOW]'}",
        f"Max Drawdown:     {metrics.max_drawdown_pct:.1f}%"
        f"  {'[OK]' if metrics.max_drawdown_pct < 20 else '[HIGH]'}",
        f"Sharpe Ratio:     {metrics.sharpe_ratio:.2f}",
        f"Avg Win:          ${metrics.avg_win:.2f}",
        f"Avg Loss:         ${metrics.avg_loss:.2f}",
        f"Consistency:      {consistency['consistency_rate']:.1f}% profitable days",
        "",
        "LEARNING METRICS",
        "-" * 40,
        f"Learning Score:   {learning_score['total_score']:.0f}/100 (Grade: {learning_score['grade']})",
        f"Adaptations:      {adapt_effectiveness['total_adaptations']} applied",
        f"Effective Rate:   {adapt_effectiveness['effectiveness_rate']:.1f}%"
        f"  {'[OK]' if adapt_effectiveness['effectiveness_rate'] > 50 else '[LOW]'}",
        f"Harmful Rate:     {adapt_effectiveness['harmful_rate']:.1f}%"
        f"  {'[OK]' if adapt_effectiveness['harmful_rate'] < 20 else '[HIGH]'}",
        f"Knowledge Items:  {knowledge_growth['total_patterns']} patterns, "
        f"{knowledge_growth['total_rules']} rules, "
        f"{knowledge_growth['coins_tracked']} coins",
        "",
        "IMPROVEMENT TREND",
        "-" * 40,
        f"First Half Win Rate:   {comparison['first_half'].get('win_rate', 0):.1f}%",
        f"Second Half Win Rate:  {comparison['second_half'].get('win_rate', 0):.1f}%  "
        f"({comparison['comparison'].get('win_rate_change', 0):+.1f}%)",
        f"Trend:                 {'IMPROVING' if comparison['comparison'].get('improved') else 'NOT IMPROVING'}",
        "",
        "=" * 80,
        f"RECOMMENDATION: {recommendation}",
        "=" * 80,
    ]

    return "\n".join(lines)


def generate_learning_report(db: Database, days: int) -> str:
    """Generate learning effectiveness report."""
    coin_accuracy = analyze_coin_score_accuracy(db)
    adapt_effectiveness = analyze_adaptation_effectiveness(db)
    pattern_accuracy = analyze_pattern_confidence_accuracy(db)
    knowledge_growth = analyze_knowledge_growth(db, days)
    learning_score = calculate_learning_score(
        coin_accuracy, adapt_effectiveness, pattern_accuracy, knowledge_growth
    )

    lines = [
        "=" * 80,
        "                    LEARNING EFFECTIVENESS ANALYSIS",
        "=" * 80,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Period: Last {days} days",
        "",
        f"OVERALL LEARNING SCORE: {learning_score['total_score']:.0f}/100 (Grade: {learning_score['grade']})",
        f"Assessment: {learning_score['assessment']}",
        "",
        "COIN SCORE ACCURACY",
        "-" * 40,
        f"Coins with data:        {coin_accuracy.get('coins_with_enough_data', 0)}",
        f"High score coins (>60): {len(coin_accuracy.get('high_score_coins', []))}",
        f"  Avg Win Rate:         {coin_accuracy.get('high_score_avg_win_rate', 0):.1f}%",
        f"  Avg P&L:              ${coin_accuracy.get('high_score_avg_pnl', 0):.2f}",
        f"Low score coins (<40):  {len(coin_accuracy.get('low_score_coins', []))}",
        f"  Avg Win Rate:         {coin_accuracy.get('low_score_avg_win_rate', 0):.1f}%",
        f"  Avg P&L:              ${coin_accuracy.get('low_score_avg_pnl', 0):.2f}",
        f"Correlation:            {coin_accuracy.get('correlation', 0):.2f}",
        f"Assessment:             {coin_accuracy.get('accuracy_assessment', 'N/A')}",
        "",
        "ADAPTATION EFFECTIVENESS",
        "-" * 40,
        f"Total Adaptations:      {adapt_effectiveness.get('total_adaptations', 0)}",
        f"Measured:               {adapt_effectiveness.get('measured_adaptations', 0)}",
        f"Highly Effective:       {adapt_effectiveness.get('highly_effective', 0)}",
        f"Effective:              {adapt_effectiveness.get('effective', 0)}",
        f"Neutral:                {adapt_effectiveness.get('neutral', 0)}",
        f"Ineffective:            {adapt_effectiveness.get('ineffective', 0)}",
        f"Harmful:                {adapt_effectiveness.get('harmful', 0)}",
        f"Pending:                {adapt_effectiveness.get('pending', 0)}",
        f"Effectiveness Rate:     {adapt_effectiveness.get('effectiveness_rate', 0):.1f}%",
        f"Harmful Rate:           {adapt_effectiveness.get('harmful_rate', 0):.1f}%",
        "",
        "PATTERN CONFIDENCE ACCURACY",
        "-" * 40,
        f"Patterns with data:     {pattern_accuracy.get('patterns_with_data', 0)}",
        f"High confidence (>0.6): {len(pattern_accuracy.get('high_confidence_patterns', []))}",
        f"  Avg Win Rate:         {pattern_accuracy.get('high_conf_avg_win_rate', 0):.1f}%",
        f"Low confidence (<0.4):  {len(pattern_accuracy.get('low_confidence_patterns', []))}",
        f"  Avg Win Rate:         {pattern_accuracy.get('low_conf_avg_win_rate', 0):.1f}%",
        f"Confidence Predicts:    {pattern_accuracy.get('assessment', 'N/A')}",
        "",
        "KNOWLEDGE GROWTH",
        "-" * 40,
        f"Total Patterns:         {knowledge_growth.get('total_patterns', 0)}",
        f"New Patterns:           {knowledge_growth.get('new_patterns', 0)}",
        f"Deactivated:            {knowledge_growth.get('deactivated_patterns', 0)}",
        f"Total Rules:            {knowledge_growth.get('total_rules', 0)}",
        f"New Rules:              {knowledge_growth.get('new_rules', 0)}",
        f"Coins Tracked:          {knowledge_growth.get('coins_tracked', 0)}",
        f"Coins Blacklisted:      {knowledge_growth.get('coins_blacklisted', 0)}",
        f"Total Insights:         {knowledge_growth.get('total_insights', 0)}",
        f"Total Adaptations:      {knowledge_growth.get('total_adaptations', 0)}",
        "",
        "=" * 80,
    ]

    return "\n".join(lines)


def generate_improvement_report(trades: list) -> str:
    """Generate improvement over time report."""
    comparison = compare_periods(trades)
    first = comparison["first_half"]
    second = comparison["second_half"]
    change = comparison["comparison"]

    lines = [
        "=" * 80,
        "                    PERFORMANCE IMPROVEMENT ANALYSIS",
        "=" * 80,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "PERIOD COMPARISON",
        "-" * 40,
        f"{'Metric':<20} {'First Half':>15} {'Second Half':>15} {'Change':>15}",
        "-" * 65,
        f"{'Trades':<20} {first.get('total_trades', 0):>15} {second.get('total_trades', 0):>15} "
        f"{change.get('trades_change', 0):>+15}",
        f"{'Win Rate':<20} {first.get('win_rate', 0):>14.1f}% {second.get('win_rate', 0):>14.1f}% "
        f"{change.get('win_rate_change', 0):>+14.1f}%",
        f"{'Profit Factor':<20} {first.get('profit_factor', 0):>15.2f} {second.get('profit_factor', 0):>15.2f} "
        f"{change.get('profit_factor_change', 0):>+15.2f}",
        f"{'Total P&L':<20} ${first.get('total_pnl', 0):>14.2f} ${second.get('total_pnl', 0):>14.2f} "
        f"${change.get('total_pnl_change', 0):>+14.2f}",
        f"{'Avg Trade P&L':<20} ${first.get('avg_pnl', 0):>14.2f} ${second.get('avg_pnl', 0):>14.2f} "
        f"${change.get('avg_pnl_change', 0):>+14.2f}",
        f"{'Max Drawdown':<20} {first.get('max_drawdown_pct', 0):>14.1f}% {second.get('max_drawdown_pct', 0):>14.1f}% "
        f"{change.get('drawdown_change', 0):>+14.1f}%",
        f"{'Sharpe Ratio':<20} {first.get('sharpe_ratio', 0):>15.2f} {second.get('sharpe_ratio', 0):>15.2f} "
        f"{change.get('sharpe_change', 0):>+15.2f}",
        "",
        "CONCLUSION",
        "-" * 40,
    ]

    if change.get("improved"):
        lines.extend([
            "The system shows clear improvement over time:",
            f"  - Win rate improved by {change.get('win_rate_change', 0):+.1f} percentage points",
            f"  - Profit factor changed by {change.get('profit_factor_change', 0):+.2f}",
            f"  - Average P&L per trade changed by ${change.get('avg_pnl_change', 0):+.2f}",
            "",
            "STATUS: LEARNING IS WORKING",
        ])
    else:
        lines.extend([
            "The system does not show clear improvement:",
            f"  - Win rate changed by {change.get('win_rate_change', 0):+.1f} percentage points",
            f"  - Profit factor changed by {change.get('profit_factor_change', 0):+.2f}",
            "",
            "STATUS: LEARNING NEEDS INVESTIGATION",
        ])

    lines.append("=" * 80)

    return "\n".join(lines)


def generate_detailed_report(db: Database, trades: list, output_dir: str, days: int) -> None:
    """Generate all detailed reports to a directory."""
    os.makedirs(output_dir, exist_ok=True)

    # Breakdown analyses
    by_hour = analyze_by_hour(trades)
    by_coin = analyze_by_coin(trades)
    by_pattern = analyze_by_pattern(trades)

    # Hour analysis
    hour_lines = ["PERFORMANCE BY HOUR", "=" * 60, ""]
    hour_lines.append(f"{'Hour':>6} {'Trades':>8} {'Win Rate':>10} {'P&L':>12} {'Profit Factor':>15}")
    hour_lines.append("-" * 60)
    for hour in sorted(by_hour.keys()):
        m = by_hour[hour]
        hour_lines.append(
            f"{hour:>6} {m.total_trades:>8} {m.win_rate:>9.1f}% ${m.total_pnl:>10.2f} {m.profit_factor:>15.2f}"
        )

    best_worst_hours = get_best_worst_hours(by_hour)
    hour_lines.extend(["", "Best Hours:"])
    for h in best_worst_hours.get("best_hours", []):
        hour_lines.append(f"  Hour {h['hour']}: {h['win_rate']:.1f}% win rate, ${h['pnl']:.2f} P&L")
    hour_lines.extend(["", "Worst Hours:"])
    for h in best_worst_hours.get("worst_hours", []):
        hour_lines.append(f"  Hour {h['hour']}: {h['win_rate']:.1f}% win rate, ${h['pnl']:.2f} P&L")

    with open(os.path.join(output_dir, "by_hour.txt"), "w") as f:
        f.write("\n".join(hour_lines))

    # Coin analysis
    coin_lines = ["PERFORMANCE BY COIN", "=" * 60, ""]
    coin_lines.append(f"{'Coin':>10} {'Trades':>8} {'Win Rate':>10} {'P&L':>12} {'Profit Factor':>15}")
    coin_lines.append("-" * 60)
    for coin in sorted(by_coin.keys(), key=lambda c: by_coin[c].total_pnl, reverse=True):
        m = by_coin[coin]
        coin_lines.append(
            f"{coin:>10} {m.total_trades:>8} {m.win_rate:>9.1f}% ${m.total_pnl:>10.2f} {m.profit_factor:>15.2f}"
        )

    best_worst_coins = get_best_worst_coins(by_coin)
    coin_lines.extend(["", "Best Coins:"])
    for c in best_worst_coins.get("best_coins", []):
        coin_lines.append(f"  {c['coin']}: ${c['pnl']:.2f} P&L, {c['win_rate']:.1f}% win rate")
    coin_lines.extend(["", "Worst Coins:"])
    for c in best_worst_coins.get("worst_coins", []):
        coin_lines.append(f"  {c['coin']}: ${c['pnl']:.2f} P&L, {c['win_rate']:.1f}% win rate")

    with open(os.path.join(output_dir, "by_coin.txt"), "w") as f:
        f.write("\n".join(coin_lines))

    # Pattern analysis
    pattern_lines = ["PERFORMANCE BY PATTERN", "=" * 60, ""]
    pattern_lines.append(f"{'Pattern':>25} {'Trades':>8} {'Win Rate':>10} {'P&L':>12}")
    pattern_lines.append("-" * 60)
    for pattern in sorted(by_pattern.keys(), key=lambda p: by_pattern[p].total_pnl, reverse=True):
        m = by_pattern[pattern]
        pattern_lines.append(
            f"{pattern[:25]:>25} {m.total_trades:>8} {m.win_rate:>9.1f}% ${m.total_pnl:>10.2f}"
        )

    with open(os.path.join(output_dir, "by_pattern.txt"), "w") as f:
        f.write("\n".join(pattern_lines))

    print(f"Detailed reports saved to {output_dir}/")


def main():
    parser = argparse.ArgumentParser(description="Generate Performance Reports")
    parser.add_argument("--db", default="data/trading_bot.db", help="Database path")
    parser.add_argument("--output", "-o", default="reports", help="Output directory")
    parser.add_argument("--days", type=int, default=7, help="Days to analyze")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                       help="Output format")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"ERROR: Database not found at {args.db}")
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)

    db = Database(db_path=args.db)
    trades = load_trades(db, args.days)

    print(f"Analyzing {len(trades)} trades from the last {args.days} days...")
    print(f"Database: {args.db}")
    print()

    if not trades:
        print("No trades found. Cannot generate reports.")
        sys.exit(1)

    # Generate reports
    summary = generate_summary_report(db, trades, args.days)
    learning = generate_learning_report(db, args.days)
    improvement = generate_improvement_report(trades)

    if args.format == "text":
        # Save text reports
        with open(os.path.join(args.output, "summary.txt"), "w") as f:
            f.write(summary)

        with open(os.path.join(args.output, "learning.txt"), "w") as f:
            f.write(learning)

        with open(os.path.join(args.output, "improvement.txt"), "w") as f:
            f.write(improvement)

        # Generate detailed breakdowns
        generate_detailed_report(db, trades, os.path.join(args.output, "detailed"), args.days)

        # Print summary to console
        print(summary)

    elif args.format == "json":
        metrics = calculate_metrics(trades)
        comparison = compare_periods(trades)

        output = {
            "generated_at": datetime.now().isoformat(),
            "days_analyzed": args.days,
            "trade_count": len(trades),
            "metrics": metrics.to_dict(),
            "comparison": comparison,
            "coin_accuracy": analyze_coin_score_accuracy(db),
            "adaptation_effectiveness": analyze_adaptation_effectiveness(db),
            "pattern_accuracy": analyze_pattern_confidence_accuracy(db),
            "knowledge_growth": analyze_knowledge_growth(db, args.days),
        }

        output_path = os.path.join(args.output, "analysis.json")
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2, default=str)

        print(f"JSON report saved to {output_path}")

    print(f"\nReports saved to {args.output}/")


if __name__ == "__main__":
    main()
