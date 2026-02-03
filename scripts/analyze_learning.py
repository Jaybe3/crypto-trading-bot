#!/usr/bin/env python3
"""
Learning Analysis Script (TASK-151).

Analyzes historical data to measure learning effectiveness:
1. How coin scores correlate with actual performance
2. How pattern confidence correlates with outcomes
3. Whether adaptations improved performance
4. Overall learning velocity and accuracy

Usage:
    python scripts/analyze_learning.py [--days 7] [--output FILE]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database


def analyze_coin_learning(db: Database, days: int) -> dict:
    """Analyze how well coin scores predict performance."""
    results = {
        "coins_analyzed": 0,
        "correlation_positive": 0,
        "score_accuracy": 0,
        "details": [],
    }

    try:
        # Get all coins with scores
        with db._get_connection() as conn:
            cursor = conn.cursor()

            # Get coin scores
            cursor.execute("SELECT coin, score, total_trades, win_rate, total_pnl FROM coin_scores")
            coins = cursor.fetchall()

            if not coins:
                results["message"] = "No coin data available"
                return results

            score_performance_pairs = []

            for coin, score, trades, win_rate, pnl in coins:
                if trades and trades >= 5:
                    results["coins_analyzed"] += 1

                    # Calculate expected vs actual
                    expected_good = score > 55 if score else False
                    actual_good = (win_rate or 0) > 50 and (pnl or 0) > 0

                    if expected_good == actual_good:
                        results["correlation_positive"] += 1

                    score_performance_pairs.append({
                        "coin": coin,
                        "score": score,
                        "win_rate": win_rate,
                        "pnl": pnl,
                        "trades": trades,
                        "expected_good": expected_good,
                        "actual_good": actual_good,
                        "correct": expected_good == actual_good,
                    })

            if results["coins_analyzed"] > 0:
                results["score_accuracy"] = (
                    results["correlation_positive"] / results["coins_analyzed"] * 100
                )

            # Top and bottom performers
            sorted_by_pnl = sorted(score_performance_pairs, key=lambda x: x["pnl"] or 0, reverse=True)
            results["top_performers"] = sorted_by_pnl[:3]
            results["bottom_performers"] = sorted_by_pnl[-3:]
            results["details"] = score_performance_pairs

    except Exception as e:
        results["error"] = str(e)

    return results


def analyze_pattern_learning(db: Database, days: int) -> dict:
    """Analyze how well pattern confidence predicts outcomes."""
    results = {
        "patterns_analyzed": 0,
        "confidence_accuracy": 0,
        "high_confidence_win_rate": 0,
        "low_confidence_win_rate": 0,
        "details": [],
    }

    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()

            # Get patterns
            cursor.execute("""
                SELECT pattern_id, name, confidence, usage_count, win_rate, is_active
                FROM trading_patterns
            """)
            patterns = cursor.fetchall()

            if not patterns:
                results["message"] = "No pattern data available"
                return results

            high_conf_patterns = []
            low_conf_patterns = []

            for pattern_id, name, conf, usage, win_rate, active in patterns:
                if usage and usage >= 3:
                    results["patterns_analyzed"] += 1

                    pattern_data = {
                        "pattern_id": pattern_id,
                        "name": name,
                        "confidence": conf,
                        "usage": usage,
                        "win_rate": win_rate,
                        "is_active": active,
                    }
                    results["details"].append(pattern_data)

                    if conf and conf >= 0.6:
                        high_conf_patterns.append(win_rate or 0)
                    elif conf and conf < 0.4:
                        low_conf_patterns.append(win_rate or 0)

            if high_conf_patterns:
                results["high_confidence_win_rate"] = sum(high_conf_patterns) / len(high_conf_patterns)

            if low_conf_patterns:
                results["low_confidence_win_rate"] = sum(low_conf_patterns) / len(low_conf_patterns)

            # Confidence accuracy: high conf should have higher win rate
            if high_conf_patterns and low_conf_patterns:
                results["confidence_accuracy"] = (
                    100 if results["high_confidence_win_rate"] > results["low_confidence_win_rate"] else 0
                )

    except Exception as e:
        results["error"] = str(e)

    return results


def analyze_adaptation_effectiveness(db: Database, days: int) -> dict:
    """Analyze whether adaptations improved performance."""
    results = {
        "total_adaptations": 0,
        "measured_adaptations": 0,
        "effective_rate": 0,
        "harmful_rate": 0,
        "by_type": defaultdict(lambda: {"count": 0, "effective": 0, "harmful": 0}),
        "details": [],
    }

    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()

            # Get adaptations
            cursor.execute("""
                SELECT adaptation_id, action, target, confidence, effectiveness_rating,
                       win_rate_before, win_rate_after, pnl_before, pnl_after, applied_at
                FROM adaptations
                ORDER BY applied_at DESC
            """)
            adaptations = cursor.fetchall()

            results["total_adaptations"] = len(adaptations)

            effective_count = 0
            harmful_count = 0

            for row in adaptations:
                (adapt_id, action, target, conf, rating,
                 wr_before, wr_after, pnl_before, pnl_after, applied_at) = row

                adaptation_data = {
                    "id": adapt_id,
                    "action": action,
                    "target": target,
                    "confidence": conf,
                    "rating": rating,
                    "win_rate_change": (wr_after or 0) - (wr_before or 0) if wr_after and wr_before else None,
                    "pnl_change": (pnl_after or 0) - (pnl_before or 0) if pnl_after and pnl_before else None,
                }
                results["details"].append(adaptation_data)

                if rating and rating != "pending":
                    results["measured_adaptations"] += 1

                    # Track by type
                    action_type = action or "unknown"
                    results["by_type"][action_type]["count"] += 1

                    if rating in ["effective", "highly_effective"]:
                        effective_count += 1
                        results["by_type"][action_type]["effective"] += 1
                    elif rating == "harmful":
                        harmful_count += 1
                        results["by_type"][action_type]["harmful"] += 1

            if results["measured_adaptations"] > 0:
                results["effective_rate"] = effective_count / results["measured_adaptations"] * 100
                results["harmful_rate"] = harmful_count / results["measured_adaptations"] * 100

            # Convert defaultdict to regular dict
            results["by_type"] = dict(results["by_type"])

    except Exception as e:
        results["error"] = str(e)

    return results


def analyze_learning_velocity(db: Database, days: int) -> dict:
    """Analyze the rate of learning over time."""
    results = {
        "total_trades": 0,
        "total_reflections": 0,
        "total_insights": 0,
        "total_adaptations": 0,
        "insight_rate": 0,
        "adaptation_rate": 0,
        "daily_breakdown": [],
    }

    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()

            # Get trade count
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()

            cursor.execute("""
                SELECT COUNT(*) FROM trade_journal
                WHERE exit_time >= ?
            """, (cutoff,))
            results["total_trades"] = cursor.fetchone()[0] or 0

            # Get reflection count
            cursor.execute("""
                SELECT COUNT(*) FROM reflections
                WHERE created_at >= ?
            """, (cutoff,))
            results["total_reflections"] = cursor.fetchone()[0] or 0

            # Get insight count
            cursor.execute("""
                SELECT COUNT(*) FROM insights
                WHERE created_at >= ?
            """, (cutoff,))
            results["total_insights"] = cursor.fetchone()[0] or 0

            # Get adaptation count
            cursor.execute("""
                SELECT COUNT(*) FROM adaptations
                WHERE applied_at >= ?
            """, (cutoff,))
            results["total_adaptations"] = cursor.fetchone()[0] or 0

            # Calculate rates
            if results["total_trades"] > 0:
                results["insight_rate"] = results["total_insights"] / results["total_trades"]
                results["adaptation_rate"] = results["total_adaptations"] / results["total_trades"]

            # Daily breakdown
            for d in range(days):
                day_start = (datetime.now() - timedelta(days=d+1)).replace(
                    hour=0, minute=0, second=0
                ).isoformat()
                day_end = (datetime.now() - timedelta(days=d)).replace(
                    hour=0, minute=0, second=0
                ).isoformat()

                cursor.execute("""
                    SELECT COUNT(*) FROM trade_journal
                    WHERE exit_time >= ? AND exit_time < ?
                """, (day_start, day_end))
                day_trades = cursor.fetchone()[0] or 0

                cursor.execute("""
                    SELECT COUNT(*) FROM adaptations
                    WHERE applied_at >= ? AND applied_at < ?
                """, (day_start, day_end))
                day_adaptations = cursor.fetchone()[0] or 0

                results["daily_breakdown"].append({
                    "day": d + 1,
                    "date": (datetime.now() - timedelta(days=d+1)).strftime("%Y-%m-%d"),
                    "trades": day_trades,
                    "adaptations": day_adaptations,
                })

    except Exception as e:
        results["error"] = str(e)

    return results


def print_analysis(
    coin_results: dict,
    pattern_results: dict,
    adaptation_results: dict,
    velocity_results: dict,
) -> None:
    """Print formatted analysis results."""
    print("=" * 70)
    print("              LEARNING ANALYSIS REPORT")
    print("=" * 70)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Coin Learning
    print("-" * 70)
    print("COIN SCORE LEARNING")
    print("-" * 70)
    print(f"Coins analyzed: {coin_results.get('coins_analyzed', 0)}")
    print(f"Score accuracy: {coin_results.get('score_accuracy', 0):.1f}%")

    if coin_results.get("top_performers"):
        print("\nTop Performers:")
        for p in coin_results["top_performers"][:3]:
            print(f"  {p['coin']}: Score={p.get('score', 'N/A')}, "
                  f"WinRate={p.get('win_rate', 0):.1f}%, P&L=${p.get('pnl', 0):.2f}")

    if coin_results.get("bottom_performers"):
        print("\nBottom Performers:")
        for p in coin_results["bottom_performers"][-3:]:
            print(f"  {p['coin']}: Score={p.get('score', 'N/A')}, "
                  f"WinRate={p.get('win_rate', 0):.1f}%, P&L=${p.get('pnl', 0):.2f}")
    print()

    # Pattern Learning
    print("-" * 70)
    print("PATTERN CONFIDENCE LEARNING")
    print("-" * 70)
    print(f"Patterns analyzed: {pattern_results.get('patterns_analyzed', 0)}")
    print(f"High confidence win rate: {pattern_results.get('high_confidence_win_rate', 0):.1f}%")
    print(f"Low confidence win rate: {pattern_results.get('low_confidence_win_rate', 0):.1f}%")
    print(f"Confidence predicts outcomes: {'Yes' if pattern_results.get('confidence_accuracy', 0) > 50 else 'No'}")
    print()

    # Adaptation Effectiveness
    print("-" * 70)
    print("ADAPTATION EFFECTIVENESS")
    print("-" * 70)
    print(f"Total adaptations: {adaptation_results.get('total_adaptations', 0)}")
    print(f"Measured: {adaptation_results.get('measured_adaptations', 0)}")
    print(f"Effective rate: {adaptation_results.get('effective_rate', 0):.1f}%")
    print(f"Harmful rate: {adaptation_results.get('harmful_rate', 0):.1f}%")

    if adaptation_results.get("by_type"):
        print("\nBy Type:")
        for action, stats in adaptation_results["by_type"].items():
            print(f"  {action}: {stats['count']} total, "
                  f"{stats['effective']} effective, {stats['harmful']} harmful")
    print()

    # Learning Velocity
    print("-" * 70)
    print("LEARNING VELOCITY")
    print("-" * 70)
    print(f"Total trades: {velocity_results.get('total_trades', 0)}")
    print(f"Total reflections: {velocity_results.get('total_reflections', 0)}")
    print(f"Total insights: {velocity_results.get('total_insights', 0)}")
    print(f"Total adaptations: {velocity_results.get('total_adaptations', 0)}")
    print(f"Insight rate: {velocity_results.get('insight_rate', 0):.2%} per trade")
    print(f"Adaptation rate: {velocity_results.get('adaptation_rate', 0):.2%} per trade")

    if velocity_results.get("daily_breakdown"):
        print("\nDaily Activity (last 7 days):")
        for day in velocity_results["daily_breakdown"][:7]:
            print(f"  {day['date']}: {day['trades']} trades, {day['adaptations']} adaptations")

    print()
    print("=" * 70)

    # Overall Assessment
    score_ok = coin_results.get("score_accuracy", 0) >= 50
    pattern_ok = pattern_results.get("high_confidence_win_rate", 0) >= pattern_results.get("low_confidence_win_rate", 0)
    adapt_ok = adaptation_results.get("harmful_rate", 100) < 30
    velocity_ok = velocity_results.get("total_trades", 0) > 0

    passed = sum([score_ok, pattern_ok, adapt_ok, velocity_ok])
    total = 4

    print(f"ASSESSMENT: {passed}/{total} checks passed")
    if passed >= 3:
        print("Learning system is functioning well")
    elif passed >= 2:
        print("Learning system needs attention")
    else:
        print("Learning system may have issues")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Analyze Learning Effectiveness")
    parser.add_argument("--days", type=int, default=7, help="Days to analyze")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--db", help="Database path (default: data/trading_bot.db)")
    args = parser.parse_args()

    db_path = args.db or "data/trading_bot.db"

    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        sys.exit(1)

    print(f"Analyzing {args.days} days of learning data...")
    print(f"Database: {db_path}")
    print()

    db = Database(db_path=db_path)

    coin_results = analyze_coin_learning(db, args.days)
    pattern_results = analyze_pattern_learning(db, args.days)
    adaptation_results = analyze_adaptation_effectiveness(db, args.days)
    velocity_results = analyze_learning_velocity(db, args.days)

    if args.output:
        output = {
            "timestamp": datetime.now().isoformat(),
            "days_analyzed": args.days,
            "coin_learning": coin_results,
            "pattern_learning": pattern_results,
            "adaptation_effectiveness": adaptation_results,
            "learning_velocity": velocity_results,
        }
        Path(args.output).write_text(json.dumps(output, indent=2, default=str))
        print(f"Results saved to {args.output}")
    else:
        print_analysis(coin_results, pattern_results, adaptation_results, velocity_results)


if __name__ == "__main__":
    main()
