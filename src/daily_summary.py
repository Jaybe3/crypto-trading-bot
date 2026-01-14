"""Daily summary report generation.

Generates comprehensive daily reports showing:
- Trading performance (P&L, win rate)
- Learnings extracted from trades
- Rule status changes
- Key metrics and trends
"""

import json
import logging
import os
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path for imports when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailySummary:
    """Generates daily trading summary reports."""

    def __init__(self, db: Database = None):
        """Initialize with database connection."""
        self.db = db or Database()

    def get_today_trades(self) -> List[Dict[str, Any]]:
        """Get all trades closed today."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, coin_name, entry_price, exit_price, size_usd,
                       pnl_usd, pnl_pct, entry_reason, exit_reason,
                       duration_seconds, closed_at
                FROM closed_trades
                WHERE date(closed_at) = date('now')
                ORDER BY closed_at DESC
            """)

            columns = ['id', 'coin_name', 'entry_price', 'exit_price', 'size_usd',
                      'pnl_usd', 'pnl_pct', 'entry_reason', 'exit_reason',
                      'duration_seconds', 'closed_at']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_today_learnings(self) -> List[Dict[str, Any]]:
        """Get learnings created today."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, l.trade_id, l.learning_text, l.confidence_level,
                       c.coin_name, c.pnl_usd
                FROM learnings l
                LEFT JOIN closed_trades c ON l.trade_id = c.id
                WHERE date(l.created_at) = date('now')
                ORDER BY l.confidence_level DESC
            """)

            learnings = []
            for row in cursor.fetchall():
                try:
                    data = json.loads(row[2])
                except (json.JSONDecodeError, TypeError):
                    data = {'lesson': row[2] or ''}

                learnings.append({
                    'id': row[0],
                    'trade_id': row[1],
                    'lesson': data.get('lesson', ''),
                    'pattern': data.get('pattern', ''),
                    'confidence': row[3] or 0,
                    'coin': row[4] or 'unknown',
                    'trade_pnl': row[5] or 0
                })
            return learnings

    def get_rule_changes(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get rules created or status-changed today."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # New rules created today
            cursor.execute("""
                SELECT id, rule_text, status, success_count, failure_count
                FROM trading_rules
                WHERE date(created_at) = date('now')
            """)
            new_rules = [dict(zip(['id', 'rule_text', 'status', 'success', 'failure'], row))
                        for row in cursor.fetchall()]

            # Get activity log for rule promotions/rejections today
            cursor.execute("""
                SELECT description, details, created_at
                FROM activity_log
                WHERE activity_type IN ('rule_active', 'rule_rejected')
                AND date(created_at) = date('now')
                ORDER BY created_at DESC
            """)
            status_changes = [dict(zip(['description', 'details', 'time'], row))
                            for row in cursor.fetchall()]

            return {
                'new_rules': new_rules,
                'status_changes': status_changes
            }

    def calculate_stats(self, trades: List[Dict]) -> Dict[str, Any]:
        """Calculate performance statistics from trades."""
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'best_trade': None,
                'worst_trade': None,
                'avg_duration_mins': 0
            }

        wins = [t for t in trades if t['pnl_usd'] > 0]
        losses = [t for t in trades if t['pnl_usd'] <= 0]
        total_pnl = sum(t['pnl_usd'] for t in trades)
        durations = [t['duration_seconds'] or 0 for t in trades]

        best = max(trades, key=lambda t: t['pnl_usd'])
        worst = min(trades, key=lambda t: t['pnl_usd'])

        return {
            'total_trades': len(trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(trades) if trades else 0,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / len(trades),
            'best_trade': {
                'coin': best['coin_name'],
                'pnl': best['pnl_usd'],
                'pnl_pct': best['pnl_pct']
            },
            'worst_trade': {
                'coin': worst['coin_name'],
                'pnl': worst['pnl_usd'],
                'pnl_pct': worst['pnl_pct']
            },
            'avg_duration_mins': sum(durations) / len(durations) / 60 if durations else 0
        }

    def generate_summary(self) -> Dict[str, Any]:
        """Generate complete daily summary."""
        trades = self.get_today_trades()
        learnings = self.get_today_learnings()
        rule_changes = self.get_rule_changes()
        stats = self.calculate_stats(trades)
        account = self.db.get_account_state()

        return {
            'date': date.today().isoformat(),
            'generated_at': datetime.now().isoformat(),
            'account': {
                'balance': account.get('balance', 0),
                'daily_pnl': account.get('daily_pnl', 0),
                'total_pnl': account.get('total_pnl', 0)
            },
            'stats': stats,
            'trades': trades,
            'learnings': learnings,
            'rules': rule_changes
        }

    def format_text_report(self, summary: Dict = None) -> str:
        """Format summary as readable text report."""
        if summary is None:
            summary = self.generate_summary()

        stats = summary['stats']
        account = summary['account']

        lines = [
            "=" * 60,
            f"DAILY TRADING SUMMARY - {summary['date']}",
            "=" * 60,
            "",
            "ACCOUNT STATUS",
            "-" * 40,
            f"  Balance:     ${account['balance']:,.2f}",
            f"  Daily P&L:   ${account['daily_pnl']:+,.2f}",
            f"  Total P&L:   ${account['total_pnl']:+,.2f}",
            "",
            "TRADING PERFORMANCE",
            "-" * 40,
            f"  Trades:      {stats['total_trades']}",
            f"  Wins/Losses: {stats['winning_trades']}/{stats['losing_trades']}",
            f"  Win Rate:    {stats['win_rate']:.1%}",
            f"  Total P&L:   ${stats['total_pnl']:+,.2f}",
            f"  Avg P&L:     ${stats['avg_pnl']:+,.2f}",
            f"  Avg Duration: {stats['avg_duration_mins']:.1f} mins",
        ]

        if stats['best_trade']:
            lines.extend([
                "",
                f"  Best Trade:  {stats['best_trade']['coin'].upper()} "
                f"${stats['best_trade']['pnl']:+,.2f} ({stats['best_trade']['pnl_pct']:+.1f}%)",
                f"  Worst Trade: {stats['worst_trade']['coin'].upper()} "
                f"${stats['worst_trade']['pnl']:+,.2f} ({stats['worst_trade']['pnl_pct']:+.1f}%)",
            ])

        # Learnings section
        lines.extend(["", "LEARNINGS GAINED", "-" * 40])
        if summary['learnings']:
            for i, l in enumerate(summary['learnings'][:5], 1):
                conf = f"[{l['confidence']:.0%}]"
                lesson_text = l['lesson'][:55] + "..." if len(l['lesson']) > 55 else l['lesson']
                lines.append(f"  {i}. {conf} {lesson_text}")
        else:
            lines.append("  No new learnings today")

        # Rules section
        lines.extend(["", "RULE CHANGES", "-" * 40])
        rules = summary['rules']
        if rules['new_rules']:
            lines.append(f"  New rules created: {len(rules['new_rules'])}")
        if rules['status_changes']:
            for change in rules['status_changes']:
                lines.append(f"  - {change['description']}")
        if not rules['new_rules'] and not rules['status_changes']:
            lines.append("  No rule changes today")

        lines.extend([
            "",
            "=" * 60,
            f"Generated at {summary['generated_at'][:19]}",
            "=" * 60
        ])

        return "\n".join(lines)

    def save_report(self, output_dir: str = None) -> str:
        """Save daily report to file.

        Args:
            output_dir: Directory to save reports. Defaults to data/reports/

        Returns:
            Path to the saved text report file.
        """
        if output_dir is None:
            project_root = Path(__file__).parent.parent
            output_dir = project_root / "data" / "reports"

        summary = self.generate_summary()
        report_text = self.format_text_report(summary)

        # Create reports directory
        reports_dir = Path(output_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Save text report
        filename = f"daily_summary_{summary['date']}.txt"
        filepath = reports_dir / filename
        filepath.write_text(report_text)

        # Save JSON version too
        json_filename = f"daily_summary_{summary['date']}.json"
        json_filepath = reports_dir / json_filename
        json_filepath.write_text(json.dumps(summary, indent=2, default=str))

        logger.info(f"Daily summary saved to {filepath}")
        return str(filepath)


def print_daily_summary():
    """Print today's summary to console."""
    ds = DailySummary()
    print(ds.format_text_report())


if __name__ == "__main__":
    print("=" * 60)
    print("Generating Daily Summary Report...")
    print("=" * 60)
    print()
    print_daily_summary()
