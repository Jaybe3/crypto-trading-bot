#!/usr/bin/env python3
"""
Trade Data Export Script (TASK-152).

Exports trade data in various formats for analysis.

Usage:
    python scripts/export_trades.py [--db PATH] [--output FILE] [--format csv|json] [--days 7]
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database


def export_trades_csv(db: Database, output_path: str, days: int = 7) -> int:
    """
    Export trades to CSV format.

    Args:
        db: Database instance.
        output_path: Path for output CSV file.
        days: Number of days to export.

    Returns:
        Number of trades exported.
    """
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    with db._get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                trade_id, coin, direction, entry_price, exit_price,
                position_size_usd, pnl_usd, pnl_pct, entry_time, exit_time,
                exit_reason, pattern_id, strategy_id, duration_seconds,
                btc_price_at_entry, btc_trend_at_entry
            FROM trade_journal
            WHERE exit_time >= ?
            ORDER BY exit_time ASC
        """, (cutoff,))

        trades = cursor.fetchall()

    if not trades:
        print(f"No trades found in the last {days} days")
        return 0

    # Write CSV
    headers = [
        "trade_id", "coin", "direction", "entry_price", "exit_price",
        "position_size_usd", "pnl_usd", "pnl_pct", "entry_time", "exit_time",
        "exit_reason", "pattern_id", "strategy_id", "duration_seconds",
        "btc_price_at_entry", "btc_trend_at_entry"
    ]

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for trade in trades:
            writer.writerow(trade)

    return len(trades)


def export_trades_json(db: Database, output_path: str, days: int = 7) -> dict:
    """
    Export trades to JSON format with metadata.

    Args:
        db: Database instance.
        output_path: Path for output JSON file.
        days: Number of days to export.

    Returns:
        Export metadata dictionary.
    """
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    with db._get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                trade_id, coin, direction, entry_price, exit_price,
                position_size_usd, pnl_usd, pnl_pct, entry_time, exit_time,
                exit_reason, pattern_id, strategy_id, duration_seconds,
                btc_price_at_entry, btc_trend_at_entry
            FROM trade_journal
            WHERE exit_time >= ?
            ORDER BY exit_time ASC
        """, (cutoff,))

        rows = cursor.fetchall()

    trades = []
    for row in rows:
        trades.append({
            "trade_id": row[0],
            "coin": row[1],
            "direction": row[2],
            "entry_price": row[3],
            "exit_price": row[4],
            "position_size_usd": row[5],
            "pnl_usd": row[6],
            "pnl_pct": row[7],
            "entry_time": row[8],
            "exit_time": row[9],
            "exit_reason": row[10],
            "pattern_id": row[11],
            "strategy_id": row[12],
            "duration_seconds": row[13],
            "btc_price_at_entry": row[14],
            "btc_trend_at_entry": row[15],
        })

    output = {
        "metadata": {
            "exported_at": datetime.now().isoformat(),
            "days_exported": days,
            "cutoff_date": cutoff,
            "total_trades": len(trades),
        },
        "trades": trades,
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    return output["metadata"]


def export_full_dataset(db: Database, output_dir: str, days: int = 7) -> dict:
    """
    Export complete dataset: trades, patterns, rules, adaptations.

    Args:
        db: Database instance.
        output_dir: Directory for output files.
        days: Number of days to export.

    Returns:
        Dictionary with export statistics.
    """
    os.makedirs(output_dir, exist_ok=True)
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    stats = {
        "trades": 0,
        "patterns": 0,
        "rules": 0,
        "adaptations": 0,
        "coin_scores": 0,
        "insights": 0,
    }

    with db._get_connection() as conn:
        cursor = conn.cursor()

        # Export trades
        cursor.execute("""
            SELECT * FROM trade_journal
            WHERE exit_time >= ?
            ORDER BY exit_time ASC
        """, (cutoff,))
        trades = cursor.fetchall()
        trade_cols = [desc[0] for desc in cursor.description]
        stats["trades"] = len(trades)

        with open(os.path.join(output_dir, "trades.json"), "w") as f:
            json.dump({
                "columns": trade_cols,
                "data": [dict(zip(trade_cols, row)) for row in trades]
            }, f, indent=2, default=str)

        # Export patterns
        cursor.execute("SELECT * FROM trading_patterns")
        patterns = cursor.fetchall()
        pattern_cols = [desc[0] for desc in cursor.description]
        stats["patterns"] = len(patterns)

        with open(os.path.join(output_dir, "patterns.json"), "w") as f:
            json.dump({
                "columns": pattern_cols,
                "data": [dict(zip(pattern_cols, row)) for row in patterns]
            }, f, indent=2, default=str)

        # Export rules
        cursor.execute("SELECT * FROM regime_rules")
        rules = cursor.fetchall()
        rule_cols = [desc[0] for desc in cursor.description]
        stats["rules"] = len(rules)

        with open(os.path.join(output_dir, "rules.json"), "w") as f:
            json.dump({
                "columns": rule_cols,
                "data": [dict(zip(rule_cols, row)) for row in rules]
            }, f, indent=2, default=str)

        # Export adaptations
        cursor.execute("""
            SELECT * FROM adaptations
            WHERE applied_at >= ?
        """, (cutoff,))
        adaptations = cursor.fetchall()
        adapt_cols = [desc[0] for desc in cursor.description]
        stats["adaptations"] = len(adaptations)

        with open(os.path.join(output_dir, "adaptations.json"), "w") as f:
            json.dump({
                "columns": adapt_cols,
                "data": [dict(zip(adapt_cols, row)) for row in adaptations]
            }, f, indent=2, default=str)

        # Export coin scores
        cursor.execute("SELECT * FROM coin_scores")
        scores = cursor.fetchall()
        score_cols = [desc[0] for desc in cursor.description]
        stats["coin_scores"] = len(scores)

        with open(os.path.join(output_dir, "coin_scores.json"), "w") as f:
            json.dump({
                "columns": score_cols,
                "data": [dict(zip(score_cols, row)) for row in scores]
            }, f, indent=2, default=str)

        # Export insights
        cursor.execute("""
            SELECT * FROM insights
            WHERE created_at >= ?
        """, (cutoff,))
        insights = cursor.fetchall()
        insight_cols = [desc[0] for desc in cursor.description]
        stats["insights"] = len(insights)

        with open(os.path.join(output_dir, "insights.json"), "w") as f:
            json.dump({
                "columns": insight_cols,
                "data": [dict(zip(insight_cols, row)) for row in insights]
            }, f, indent=2, default=str)

    # Write manifest
    manifest = {
        "exported_at": datetime.now().isoformat(),
        "days": days,
        "cutoff": cutoff,
        "files": [
            "trades.json",
            "patterns.json",
            "rules.json",
            "adaptations.json",
            "coin_scores.json",
            "insights.json",
        ],
        "stats": stats,
    }

    with open(os.path.join(output_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Export Trade Data")
    parser.add_argument("--db", default="data/trading_bot.db", help="Database path")
    parser.add_argument("--output", "-o", help="Output file/directory")
    parser.add_argument("--format", choices=["csv", "json", "full"], default="csv",
                       help="Export format")
    parser.add_argument("--days", type=int, default=7, help="Days to export")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"ERROR: Database not found at {args.db}")
        sys.exit(1)

    db = Database(db_path=args.db)

    if args.format == "csv":
        output = args.output or "reports/trades.csv"
        count = export_trades_csv(db, output, args.days)
        print(f"Exported {count} trades to {output}")

    elif args.format == "json":
        output = args.output or "reports/trades.json"
        meta = export_trades_json(db, output, args.days)
        print(f"Exported {meta['total_trades']} trades to {output}")

    elif args.format == "full":
        output = args.output or "reports/data_export"
        stats = export_full_dataset(db, output, args.days)
        print(f"Full dataset exported to {output}/")
        print(f"  Trades: {stats['trades']}")
        print(f"  Patterns: {stats['patterns']}")
        print(f"  Rules: {stats['rules']}")
        print(f"  Adaptations: {stats['adaptations']}")
        print(f"  Coin Scores: {stats['coin_scores']}")
        print(f"  Insights: {stats['insights']}")


if __name__ == "__main__":
    main()
