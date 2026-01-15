#!/usr/bin/env python3
"""Autonomous monitoring agent for the trading bot.

Collects bot performance data and uses LLM to identify issues,
bugs, and inefficiencies autonomously.

Usage:
    python scripts/autonomous_monitor.py [--hours 24] [--verbose] [--dry-run]

Cron example (run hourly):
    0 * * * * cd /mnt/c/documents/crypto-trading-bot && python3 scripts/autonomous_monitor.py >> logs/monitor.log 2>&1
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import Database
from src.llm_interface import LLMInterface
from src.coin_config import get_tier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# LLM PROMPTS
# =============================================================================

MONITOR_SYSTEM_PROMPT = """You are a trading bot auditor performing a critical analysis.

Your job is to find problems, bugs, inefficiencies, and issues that the developers
might have missed. Be skeptical and critical. Look for:

1. **BUGS & LOGIC ERRORS**
   - Rules that never fire or always fire
   - Patterns that don't make sense
   - Inconsistent behavior
   - Data that doesn't add up

2. **INEFFICIENCIES**
   - Wasted opportunities
   - Poor timing patterns
   - Suboptimal rule usage
   - Unused features

3. **PERFORMANCE ISSUES**
   - Slow operations
   - High error rates
   - Resource problems
   - Bottlenecks

4. **MISSING FUNCTIONALITY**
   - Gaps in the system
   - Features that should exist
   - Incomplete implementations
   - Edge cases not handled

5. **UNEXPECTED PATTERNS**
   - Anomalies in the data
   - Suspicious correlations
   - Statistical outliers
   - Things that "smell wrong"

IMPORTANT: Find problems I DIDN'T tell you to look for. Be creative and critical.
Think like a skeptical code reviewer who assumes there are bugs.

Respond with a JSON array of findings. Each finding must have these fields:
- "type": one of "bug", "inefficiency", "pattern", "performance", "missing_feature"
- "severity": one of "critical", "high", "medium", "low", "info"
- "title": short description (under 80 chars)
- "description": full explanation
- "evidence": specific data points that support this finding
- "recommendation": what should be done to fix this

Example response:
[
    {
        "type": "bug",
        "severity": "high",
        "title": "Rule success rate doesn't match trade outcomes",
        "description": "Rule #3 shows 80% success but actual trades using it have 20% win rate",
        "evidence": "Rule stats: 8/10 success. Trades with rule: 2/10 wins.",
        "recommendation": "Audit rule tracking - may not be recording outcomes correctly"
    }
]

If you find NO issues (unlikely), return an empty array [].
Be thorough - a good audit finds at least 3-5 issues."""


# =============================================================================
# AUTONOMOUS MONITOR CLASS
# =============================================================================

class AutonomousMonitor:
    """Self-monitoring agent that uses LLM to detect issues."""

    def __init__(self, db: Database = None, llm: LLMInterface = None):
        """Initialize the monitor.

        Args:
            db: Database instance (creates new if not provided).
            llm: LLM interface (creates new if not provided).
        """
        self.db = db or Database()
        self.llm = llm or LLMInterface(db=self.db)

    def run(self, hours: int = 24, dry_run: bool = False) -> List[Dict[str, Any]]:
        """Run full monitoring analysis.

        Args:
            hours: Hours of data to analyze.
            dry_run: If True, don't store findings in database.

        Returns:
            List of findings from LLM analysis.
        """
        logger.info(f"Starting autonomous monitoring (last {hours} hours)...")

        # 1. Collect all data
        logger.info("Collecting data...")
        report = self.collect_all_data(hours)

        # 2. Send to LLM for analysis
        logger.info("Sending to LLM for analysis...")
        findings = self.analyze_with_llm(report, hours)

        # 3. Store findings in database (unless dry run)
        if not dry_run and findings:
            logger.info(f"Storing {len(findings)} findings...")
            self.store_findings(findings)
        elif dry_run:
            logger.info("Dry run - not storing findings")

        # 4. Log summary
        self.log_summary(findings)

        return findings

    # =========================================================================
    # DATA COLLECTION METHODS
    # =========================================================================

    def collect_all_data(self, hours: int) -> Dict[str, Any]:
        """Collect all monitoring data.

        Args:
            hours: Hours of data to analyze.

        Returns:
            Comprehensive data report.
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'hours': hours,
            'trade_patterns': self.collect_trade_patterns(hours),
            'rule_stats': self.collect_rule_stats(),
            'winloss_patterns': self.collect_winloss_patterns(hours),
            'account_health': self.collect_account_health(),
            'system_metrics': self.collect_system_metrics(hours),
            'learning_quality': self.collect_learning_quality(hours)
        }

    def collect_trade_patterns(self, hours: int) -> Dict[str, Any]:
        """Collect trade distribution and patterns."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Total trades in period
            cursor.execute("""
                SELECT COUNT(*) FROM closed_trades
                WHERE closed_at > datetime('now', ? || ' hours')
            """, (f'-{hours}',))
            total_trades = cursor.fetchone()[0]

            # Trades by coin
            cursor.execute("""
                SELECT coin_name, COUNT(*) as cnt FROM closed_trades
                WHERE closed_at > datetime('now', ? || ' hours')
                GROUP BY coin_name ORDER BY cnt DESC
            """, (f'-{hours}',))
            trades_by_coin = {row[0]: row[1] for row in cursor.fetchall()}

            # Trades by tier
            trades_by_tier = {1: 0, 2: 0, 3: 0}
            for coin, count in trades_by_coin.items():
                tier = get_tier(coin)
                trades_by_tier[tier] += count

            # Trades by hour of day
            cursor.execute("""
                SELECT strftime('%H', closed_at) as hour, COUNT(*) FROM closed_trades
                WHERE closed_at > datetime('now', ? || ' hours')
                GROUP BY hour ORDER BY hour
            """, (f'-{hours}',))
            trades_by_hour = {int(row[0]): row[1] for row in cursor.fetchall()}

            # Trade sizes
            cursor.execute("""
                SELECT AVG(size_usd), MIN(size_usd), MAX(size_usd) FROM closed_trades
                WHERE closed_at > datetime('now', ? || ' hours')
            """, (f'-{hours}',))
            row = cursor.fetchone()
            avg_size = row[0] or 0
            min_size = row[1] or 0
            max_size = row[2] or 0

            # Duration stats
            cursor.execute("""
                SELECT AVG(duration_seconds), MIN(duration_seconds), MAX(duration_seconds)
                FROM closed_trades
                WHERE closed_at > datetime('now', ? || ' hours')
            """, (f'-{hours}',))
            row = cursor.fetchone()
            avg_duration = row[0] or 0
            min_duration = row[1] or 0
            max_duration = row[2] or 0

            # Win rate
            cursor.execute("""
                SELECT
                    COUNT(CASE WHEN pnl_usd > 0 THEN 1 END) as wins,
                    COUNT(CASE WHEN pnl_usd <= 0 THEN 1 END) as losses
                FROM closed_trades
                WHERE closed_at > datetime('now', ? || ' hours')
            """, (f'-{hours}',))
            row = cursor.fetchone()
            wins = row[0] or 0
            losses = row[1] or 0
            win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0

            # Average P&L
            cursor.execute("""
                SELECT
                    AVG(CASE WHEN pnl_usd > 0 THEN pnl_usd END) as avg_win,
                    AVG(CASE WHEN pnl_usd <= 0 THEN pnl_usd END) as avg_loss,
                    SUM(pnl_usd) as total_pnl
                FROM closed_trades
                WHERE closed_at > datetime('now', ? || ' hours')
            """, (f'-{hours}',))
            row = cursor.fetchone()
            avg_win = row[0] or 0
            avg_loss = row[1] or 0
            total_pnl = row[2] or 0

            # Open trades
            cursor.execute("SELECT COUNT(*) FROM open_trades")
            open_trades = cursor.fetchone()[0]

        return {
            'total_trades': total_trades,
            'open_trades': open_trades,
            'trades_by_coin': trades_by_coin,
            'trades_by_tier': trades_by_tier,
            'trades_by_hour': trades_by_hour,
            'avg_trade_size': round(avg_size, 2),
            'size_range': {'min': round(min_size, 2), 'max': round(max_size, 2)},
            'avg_duration_seconds': round(avg_duration, 1),
            'duration_range': {'min': min_duration, 'max': max_duration},
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 3),
            'avg_win_pnl': round(avg_win, 2),
            'avg_loss_pnl': round(avg_loss, 2),
            'total_pnl': round(total_pnl, 2)
        }

    def collect_rule_stats(self) -> Dict[str, Any]:
        """Collect rule usage and effectiveness."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # All rules
            cursor.execute("""
                SELECT id, rule_text, rule_type, status, success_count, failure_count, last_used
                FROM trading_rules
                ORDER BY id
            """)
            rules = []
            for row in cursor.fetchall():
                success = row[4] or 0
                failure = row[5] or 0
                total = success + failure
                rate = success / total if total > 0 else 0
                rules.append({
                    'id': row[0],
                    'text': row[1][:100] + '...' if len(row[1]) > 100 else row[1],
                    'type': row[2],
                    'status': row[3],
                    'success_count': success,
                    'failure_count': failure,
                    'total_uses': total,
                    'success_rate': round(rate, 3),
                    'last_used': row[6]
                })

            # Rules by status
            rules_by_status = {}
            for r in rules:
                status = r['status']
                rules_by_status[status] = rules_by_status.get(status, 0) + 1

            # Unused rules (never applied)
            unused = [r for r in rules if r['total_uses'] == 0]

            # Rules that never succeeded
            never_succeeded = [r for r in rules if r['total_uses'] > 0 and r['success_count'] == 0]

            # Rules with very low success rate (< 30% with 5+ uses)
            low_success = [r for r in rules if r['total_uses'] >= 5 and r['success_rate'] < 0.3]

        return {
            'total_rules': len(rules),
            'rules_by_status': rules_by_status,
            'rule_details': rules,
            'unused_rules': [r['id'] for r in unused],
            'rules_never_succeeded': [r['id'] for r in never_succeeded],
            'low_success_rules': [{'id': r['id'], 'rate': r['success_rate'], 'uses': r['total_uses']} for r in low_success]
        }

    def collect_winloss_patterns(self, hours: int) -> Dict[str, Any]:
        """Analyze win/loss patterns."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Win rate by coin
            cursor.execute("""
                SELECT coin_name,
                    COUNT(CASE WHEN pnl_usd > 0 THEN 1 END) as wins,
                    COUNT(*) as total
                FROM closed_trades
                WHERE closed_at > datetime('now', ? || ' hours')
                GROUP BY coin_name
            """, (f'-{hours}',))
            win_rate_by_coin = {}
            for row in cursor.fetchall():
                if row[2] > 0:
                    win_rate_by_coin[row[0]] = {
                        'wins': row[1],
                        'total': row[2],
                        'rate': round(row[1] / row[2], 3)
                    }

            # Win rate by hour
            cursor.execute("""
                SELECT strftime('%H', closed_at) as hour,
                    COUNT(CASE WHEN pnl_usd > 0 THEN 1 END) as wins,
                    COUNT(*) as total
                FROM closed_trades
                WHERE closed_at > datetime('now', ? || ' hours')
                GROUP BY hour
            """, (f'-{hours}',))
            win_rate_by_hour = {}
            for row in cursor.fetchall():
                if row[2] > 0:
                    win_rate_by_hour[int(row[0])] = round(row[1] / row[2], 3)

            # Win rate by exit reason
            cursor.execute("""
                SELECT exit_reason,
                    COUNT(*) as cnt,
                    SUM(pnl_usd) as total_pnl,
                    AVG(pnl_usd) as avg_pnl
                FROM closed_trades
                WHERE closed_at > datetime('now', ? || ' hours')
                GROUP BY exit_reason
            """, (f'-{hours}',))
            by_exit_reason = {}
            for row in cursor.fetchall():
                by_exit_reason[row[0]] = {
                    'count': row[1],
                    'total_pnl': round(row[2] or 0, 2),
                    'avg_pnl': round(row[3] or 0, 2)
                }

            # Streak analysis - get last 20 trades
            cursor.execute("""
                SELECT pnl_usd FROM closed_trades
                ORDER BY closed_at DESC LIMIT 20
            """)
            trades = [row[0] for row in cursor.fetchall()]

            current_streak = 0
            if trades:
                direction = 1 if trades[0] > 0 else -1
                for pnl in trades:
                    if (pnl > 0 and direction > 0) or (pnl <= 0 and direction < 0):
                        current_streak += direction
                    else:
                        break

            # Max streaks (from all trades)
            cursor.execute("SELECT pnl_usd FROM closed_trades ORDER BY closed_at")
            all_trades = [row[0] for row in cursor.fetchall()]

            max_win_streak = 0
            max_loss_streak = 0
            current_win = 0
            current_loss = 0
            for pnl in all_trades:
                if pnl > 0:
                    current_win += 1
                    current_loss = 0
                    max_win_streak = max(max_win_streak, current_win)
                else:
                    current_loss += 1
                    current_win = 0
                    max_loss_streak = max(max_loss_streak, current_loss)

        # Win rate by tier
        win_rate_by_tier = {1: {'wins': 0, 'total': 0}, 2: {'wins': 0, 'total': 0}, 3: {'wins': 0, 'total': 0}}
        for coin, stats in win_rate_by_coin.items():
            tier = get_tier(coin)
            win_rate_by_tier[tier]['wins'] += stats['wins']
            win_rate_by_tier[tier]['total'] += stats['total']

        for tier in win_rate_by_tier:
            t = win_rate_by_tier[tier]
            t['rate'] = round(t['wins'] / t['total'], 3) if t['total'] > 0 else 0

        return {
            'win_rate_by_coin': win_rate_by_coin,
            'win_rate_by_tier': win_rate_by_tier,
            'win_rate_by_hour': win_rate_by_hour,
            'by_exit_reason': by_exit_reason,
            'streak_analysis': {
                'current_streak': current_streak,
                'max_win_streak': max_win_streak,
                'max_loss_streak': max_loss_streak
            }
        }

    def collect_account_health(self) -> Dict[str, Any]:
        """Track account state."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Current state
            cursor.execute("SELECT * FROM account_state ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            current_balance = row[1] if row else 1000
            in_positions = row[3] if row else 0
            total_pnl = row[4] if row else 0

            # Starting balance (assumed 1000)
            starting_balance = 1000.0

            # Daily P&L history (last 7 days)
            cursor.execute("""
                SELECT date(closed_at) as day, SUM(pnl_usd) as daily_pnl
                FROM closed_trades
                WHERE closed_at > datetime('now', '-7 days')
                GROUP BY day ORDER BY day
            """)
            daily_pnl = [{'date': row[0], 'pnl': round(row[1], 2)} for row in cursor.fetchall()]

            # Trades rejected (from activity log)
            cursor.execute("""
                SELECT COUNT(*) FROM activity_log
                WHERE activity_type IN ('risk_check_failed', 'decision_rejected')
                AND created_at > datetime('now', '-24 hours')
            """)
            rejected_trades = cursor.fetchone()[0]

            # Determine trend
            if len(daily_pnl) >= 2:
                recent_avg = sum(d['pnl'] for d in daily_pnl[-3:]) / min(3, len(daily_pnl))
                if recent_avg > 1:
                    trend = 'improving'
                elif recent_avg < -1:
                    trend = 'declining'
                else:
                    trend = 'stable'
            else:
                trend = 'insufficient_data'

            # Exposure utilization
            max_exposure = current_balance * 0.10
            exposure_util = in_positions / max_exposure if max_exposure > 0 else 0

        return {
            'current_balance': round(current_balance, 2),
            'starting_balance': starting_balance,
            'total_pnl': round(total_pnl, 2),
            'pnl_percent': round((total_pnl / starting_balance) * 100, 2),
            'in_positions': round(in_positions, 2),
            'exposure_utilization': round(exposure_util, 2),
            'pnl_trend': trend,
            'daily_pnl_history': daily_pnl,
            'trades_rejected_24h': rejected_trades
        }

    def collect_system_metrics(self, hours: int) -> Dict[str, Any]:
        """Collect system health data."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Activity counts by type
            cursor.execute("""
                SELECT activity_type, COUNT(*) FROM activity_log
                WHERE created_at > datetime('now', ? || ' hours')
                GROUP BY activity_type
            """, (f'-{hours}',))
            activity_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # Error counts
            cursor.execute("""
                SELECT COUNT(*) FROM activity_log
                WHERE activity_type IN ('error', 'cycle_error', 'bot_error')
                AND created_at > datetime('now', ? || ' hours')
            """, (f'-{hours}',))
            error_count = cursor.fetchone()[0]

            # Cycle count (approximate from bot_started to now)
            cycles = activity_counts.get('llm_decision', 0)

            # Cooldown rejections
            cursor.execute("""
                SELECT COUNT(*) FROM activity_log
                WHERE activity_type = 'risk_check_failed'
                AND description LIKE '%cooldown%'
                AND created_at > datetime('now', ? || ' hours')
            """, (f'-{hours}',))
            cooldown_rejections = cursor.fetchone()[0]

            # Unique coins traded
            cursor.execute("""
                SELECT COUNT(DISTINCT coin_name) FROM closed_trades
                WHERE closed_at > datetime('now', ? || ' hours')
            """, (f'-{hours}',))
            unique_coins = cursor.fetchone()[0]

            # Current cooldowns
            cursor.execute("""
                SELECT COUNT(*) FROM coin_cooldowns
                WHERE expires_at > datetime('now')
            """)
            active_cooldowns = cursor.fetchone()[0]

            # Market data freshness
            cursor.execute("""
                SELECT MAX(last_updated) FROM market_data
            """)
            last_market_update = cursor.fetchone()[0]

        return {
            'cycles_estimated': cycles,
            'error_count': error_count,
            'error_rate': round(error_count / cycles, 4) if cycles > 0 else 0,
            'activity_counts': activity_counts,
            'cooldown_stats': {
                'rejections': cooldown_rejections,
                'unique_coins_traded': unique_coins,
                'active_cooldowns': active_cooldowns
            },
            'last_market_update': last_market_update
        }

    def collect_learning_quality(self, hours: int) -> Dict[str, Any]:
        """Analyze quality of learnings."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Total learnings
            cursor.execute("SELECT COUNT(*) FROM learnings")
            total_learnings = cursor.fetchone()[0]

            # Recent learnings
            cursor.execute("""
                SELECT COUNT(*) FROM learnings
                WHERE created_at > datetime('now', ? || ' hours')
            """, (f'-{hours}',))
            recent_learnings = cursor.fetchone()[0]

            # Average confidence
            cursor.execute("SELECT AVG(confidence_level) FROM learnings")
            avg_confidence = cursor.fetchone()[0] or 0

            # Learnings by trade outcome (join with closed_trades)
            cursor.execute("""
                SELECT
                    CASE WHEN ct.pnl_usd > 0 THEN 'win' ELSE 'loss' END as outcome,
                    COUNT(*) as cnt
                FROM learnings l
                LEFT JOIN closed_trades ct ON l.trade_id = ct.id
                WHERE ct.id IS NOT NULL
                GROUP BY outcome
            """)
            by_outcome = {row[0]: row[1] for row in cursor.fetchall()}

            # Rules created from learnings (rules with created_by = 'LLM')
            cursor.execute("""
                SELECT COUNT(*) FROM trading_rules WHERE created_by = 'LLM'
            """)
            rules_from_learnings = cursor.fetchone()[0]

            # Sample recent learnings for pattern check
            cursor.execute("""
                SELECT learning_text FROM learnings
                ORDER BY created_at DESC LIMIT 20
            """)
            recent_texts = [row[0] for row in cursor.fetchall()]

            # Simple duplicate detection (check for similar starts)
            duplicates = 0
            seen_starts = set()
            for text in recent_texts:
                start = text[:50].lower() if text else ""
                if start in seen_starts:
                    duplicates += 1
                seen_starts.add(start)

        return {
            'total_learnings': total_learnings,
            'learnings_last_period': recent_learnings,
            'avg_confidence': round(avg_confidence, 3),
            'by_outcome': by_outcome,
            'rules_created': rules_from_learnings,
            'potential_duplicates': duplicates,
            'sample_learnings': recent_texts[:5]
        }

    # =========================================================================
    # LLM ANALYSIS
    # =========================================================================

    def analyze_with_llm(self, report: Dict[str, Any], hours: int) -> List[Dict[str, Any]]:
        """Send report to LLM for critical analysis.

        Args:
            report: Collected data report.
            hours: Analysis period in hours.

        Returns:
            List of findings.
        """
        # Build the user prompt
        user_prompt = f"""
## BOT MONITORING REPORT
Generated: {report['timestamp']}
Analysis Period: Last {hours} hours

### TRADE PATTERNS
{json.dumps(report['trade_patterns'], indent=2)}

### RULE EFFECTIVENESS
{json.dumps(report['rule_stats'], indent=2)}

### WIN/LOSS ANALYSIS
{json.dumps(report['winloss_patterns'], indent=2)}

### ACCOUNT HEALTH
{json.dumps(report['account_health'], indent=2)}

### SYSTEM METRICS
{json.dumps(report['system_metrics'], indent=2)}

### LEARNING QUALITY
{json.dumps(report['learning_quality'], indent=2)}

---

Analyze this data critically. Find bugs, inefficiencies, and problems.
Remember: Your job is to find issues the developers missed.
Return a JSON array of findings.
"""

        # Query LLM
        response = self.llm.query_json(user_prompt, MONITOR_SYSTEM_PROMPT)

        if response is None:
            logger.error("LLM returned no response")
            return [{
                'type': 'performance',
                'severity': 'high',
                'title': 'LLM analysis failed',
                'description': 'The monitoring LLM query returned no response',
                'evidence': 'query_json returned None',
                'recommendation': 'Check LLM connectivity and try again'
            }]

        # Handle both list and dict responses
        if isinstance(response, list):
            findings = response
        elif isinstance(response, dict) and 'findings' in response:
            findings = response['findings']
        else:
            logger.warning(f"Unexpected LLM response format: {type(response)}")
            findings = [response] if isinstance(response, dict) else []

        # Validate findings
        valid_findings = []
        for f in findings:
            if isinstance(f, dict) and 'type' in f and 'severity' in f and 'title' in f:
                # Ensure all required fields exist
                f.setdefault('description', f.get('title', 'No description'))
                f.setdefault('evidence', '')
                f.setdefault('recommendation', '')
                valid_findings.append(f)

        logger.info(f"LLM returned {len(valid_findings)} valid findings")
        return valid_findings

    # =========================================================================
    # STORAGE AND REPORTING
    # =========================================================================

    def store_findings(self, findings: List[Dict[str, Any]]) -> None:
        """Store findings in monitoring_alerts table.

        Args:
            findings: List of findings to store.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            for finding in findings:
                # Check for duplicate (same title in last hour)
                cursor.execute("""
                    SELECT id FROM monitoring_alerts
                    WHERE title = ? AND created_at > datetime('now', '-1 hour')
                """, (finding['title'],))

                if cursor.fetchone():
                    logger.debug(f"Skipping duplicate alert: {finding['title']}")
                    continue

                cursor.execute("""
                    INSERT INTO monitoring_alerts
                    (alert_type, severity, title, description, evidence, recommendation)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    finding.get('type', 'unknown'),
                    finding.get('severity', 'info'),
                    finding.get('title', 'Untitled'),
                    finding.get('description', ''),
                    finding.get('evidence', ''),
                    finding.get('recommendation', '')
                ))

            conn.commit()

    def log_summary(self, findings: List[Dict[str, Any]]) -> None:
        """Log summary of findings.

        Args:
            findings: List of findings.
        """
        # Count by severity
        by_severity = {}
        for f in findings:
            sev = f.get('severity', 'unknown')
            by_severity[sev] = by_severity.get(sev, 0) + 1

        print("\n" + "=" * 50)
        print("MONITORING COMPLETE")
        print("=" * 50)
        print(f"Total findings: {len(findings)}")

        for sev in ['critical', 'high', 'medium', 'low', 'info']:
            if sev in by_severity:
                print(f"  {sev}: {by_severity[sev]}")

        # Show high+ severity details
        high_plus = [f for f in findings if f.get('severity') in ['critical', 'high']]
        if high_plus:
            print(f"\n{'='*50}")
            print("HIGH+ SEVERITY FINDINGS:")
            print("=" * 50)
            for f in high_plus:
                print(f"\n[{f.get('severity', '?').upper()}] {f.get('type', '?')}: {f.get('title', '?')}")
                print(f"  {f.get('description', '')[:200]}")
                if f.get('evidence'):
                    print(f"  Evidence: {f.get('evidence')[:150]}")
                if f.get('recommendation'):
                    print(f"  Fix: {f.get('recommendation')[:150]}")

        print("=" * 50 + "\n")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Autonomous monitoring agent for the trading bot'
    )
    parser.add_argument(
        '--hours', type=int, default=24,
        help='Hours of data to analyze (default: 24)'
    )
    parser.add_argument(
        '--verbose', action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Run analysis but do not store findings'
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run monitor
    monitor = AutonomousMonitor()
    findings = monitor.run(hours=args.hours, dry_run=args.dry_run)

    # Exit with code based on severity
    if any(f.get('severity') == 'critical' for f in findings):
        sys.exit(2)
    elif any(f.get('severity') == 'high' for f in findings):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
