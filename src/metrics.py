"""Performance metrics calculation and monitoring.

Provides real-time performance metrics, alerts, and
Prometheus-compatible endpoint for external monitoring.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from src.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Represents a monitoring alert."""
    level: AlertLevel
    metric: str
    message: str
    value: Any
    threshold: Any
    timestamp: datetime


class MetricsCollector:
    """Collects and calculates performance metrics.

    Provides comprehensive metrics for trading performance,
    activity monitoring, learning system health, and alerts.
    """

    # Alert thresholds
    THRESHOLDS = {
        'min_balance': 950.0,           # Alert if balance drops below
        'max_daily_loss': -20.0,        # Alert if daily P&L below
        'max_trade_gap_hours': 6,       # Alert if no trades for X hours
        'max_price_age_minutes': 5,     # Alert if prices stale
        'max_api_errors_hourly': 10,    # Alert if too many API errors
        'min_win_rate': 40.0,           # Warning if win rate below
    }

    def __init__(self, db: Database = None):
        """Initialize with database connection.

        Args:
            db: Database instance. Creates new one if not provided.
        """
        self.db = db or Database()
        self._alerts: List[Alert] = []

    def get_trading_metrics(self) -> Dict[str, Any]:
        """Calculate trading performance metrics.

        Returns:
            Dict with trading stats (win rate, P&L, profit factor, etc.)
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Total trades and win/loss counts
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN pnl_usd <= 0 THEN 1 ELSE 0 END) as losses,
                    SUM(pnl_usd) as total_pnl,
                    AVG(pnl_usd) as avg_pnl,
                    MAX(pnl_usd) as best_trade,
                    MIN(pnl_usd) as worst_trade,
                    SUM(CASE WHEN pnl_usd > 0 THEN pnl_usd ELSE 0 END) as gross_profit,
                    SUM(CASE WHEN pnl_usd < 0 THEN pnl_usd ELSE 0 END) as gross_loss
                FROM closed_trades
            """)
            row = cursor.fetchone()

            total = row[0] or 0
            wins = row[1] or 0
            losses = row[2] or 0
            total_pnl = row[3] or 0
            avg_pnl = row[4] or 0
            best_trade = row[5] or 0
            worst_trade = row[6] or 0
            gross_profit = row[7] or 0
            gross_loss = abs(row[8] or 0)

            win_rate = (wins / total * 100) if total > 0 else 0
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

            return {
                'total_trades': total,
                'wins': wins,
                'losses': losses,
                'win_rate': round(win_rate, 1),
                'total_pnl': round(total_pnl, 2),
                'avg_pnl_per_trade': round(avg_pnl, 2),
                'best_trade': round(best_trade, 2),
                'worst_trade': round(worst_trade, 2),
                'profit_factor': round(profit_factor, 2),
                'gross_profit': round(gross_profit, 2),
                'gross_loss': round(gross_loss, 2)
            }

    def get_activity_metrics(self) -> Dict[str, Any]:
        """Calculate activity and exposure metrics.

        Returns:
            Dict with activity stats (trades today, exposure, last trade, etc.)
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Trades today
            cursor.execute("""
                SELECT COUNT(*) FROM closed_trades
                WHERE date(closed_at) = date('now')
            """)
            trades_today = cursor.fetchone()[0]

            # Trades in last 24 hours
            cursor.execute("""
                SELECT COUNT(*) FROM closed_trades
                WHERE closed_at > datetime('now', '-24 hours')
            """)
            trades_24h = cursor.fetchone()[0]

            # Open positions
            cursor.execute("SELECT COUNT(*) FROM open_trades")
            open_positions = cursor.fetchone()[0]

            # Last trade time
            cursor.execute("""
                SELECT MAX(closed_at) FROM closed_trades
            """)
            last_trade = cursor.fetchone()[0]

            # Last price update
            cursor.execute("""
                SELECT MAX(last_updated) FROM market_data
            """)
            last_price = cursor.fetchone()[0]

        # Get account state
        state = self.db.get_account_state()
        balance = state.get('balance', 0)
        in_positions = state.get('in_positions', 0)
        exposure_pct = (in_positions / balance * 100) if balance > 0 else 0

        # Calculate hours since last trade
        hours_since_trade = None
        if last_trade:
            try:
                last_dt = datetime.fromisoformat(last_trade.replace('Z', '+00:00'))
                hours_since_trade = (datetime.now() - last_dt.replace(tzinfo=None)).total_seconds() / 3600
            except Exception:
                pass

        return {
            'trades_today': trades_today,
            'trades_24h': trades_24h,
            'trades_per_hour': round(trades_24h / 24, 2) if trades_24h else 0,
            'open_positions': open_positions,
            'exposure_pct': round(exposure_pct, 1),
            'last_trade_time': last_trade,
            'hours_since_trade': round(hours_since_trade, 1) if hours_since_trade else None,
            'last_price_update': last_price
        }

    def get_learning_metrics(self) -> Dict[str, Any]:
        """Calculate learning system metrics.

        Returns:
            Dict with learning stats (learnings count, rules, success rate)
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Total learnings
            cursor.execute("SELECT COUNT(*) FROM learnings")
            total_learnings = cursor.fetchone()[0]

            # Learnings today
            cursor.execute("""
                SELECT COUNT(*) FROM learnings
                WHERE date(created_at) = date('now')
            """)
            learnings_today = cursor.fetchone()[0]

            # Rules by status
            cursor.execute("""
                SELECT status, COUNT(*) FROM trading_rules
                GROUP BY status
            """)
            rules_by_status = {row[0]: row[1] for row in cursor.fetchall()}

            # Average success rate of active rules
            cursor.execute("""
                SELECT AVG(
                    CAST(success_count AS FLOAT) /
                    NULLIF(success_count + failure_count, 0)
                ) FROM trading_rules
                WHERE status = 'active'
            """)
            avg_success = cursor.fetchone()[0]

        return {
            'total_learnings': total_learnings,
            'learnings_today': learnings_today,
            'active_rules': rules_by_status.get('active', 0),
            'testing_rules': rules_by_status.get('testing', 0),
            'rejected_rules': rules_by_status.get('rejected', 0),
            'rule_success_rate': round((avg_success or 0) * 100, 1)
        }

    def get_system_health(self) -> Dict[str, Any]:
        """Check system health metrics.

        Returns:
            Dict with health stats (balance, errors, price freshness)
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # API errors in last hour
            cursor.execute("""
                SELECT COUNT(*) FROM activity_log
                WHERE activity_type = 'error'
                AND created_at > datetime('now', '-1 hour')
            """)
            api_errors_1h = cursor.fetchone()[0]

            # Price data freshness
            cursor.execute("""
                SELECT
                    (julianday('now') - julianday(MAX(last_updated))) * 24 * 60
                FROM market_data
            """)
            price_age_minutes = cursor.fetchone()[0] or 999

        state = self.db.get_account_state()

        return {
            'balance': state.get('balance', 0),
            'daily_pnl': state.get('daily_pnl', 0),
            'api_errors_1h': api_errors_1h,
            'price_age_minutes': round(price_age_minutes, 1),
            'database_ok': True  # If we got here, DB is working
        }

    def check_alerts(self) -> List[Alert]:
        """Check all metrics against thresholds and generate alerts.

        Returns:
            List of Alert objects for any threshold violations.
        """
        self._alerts = []

        health = self.get_system_health()
        activity = self.get_activity_metrics()
        trading = self.get_trading_metrics()

        # Balance alert
        if health['balance'] < self.THRESHOLDS['min_balance']:
            self._alerts.append(Alert(
                level=AlertLevel.CRITICAL,
                metric='balance',
                message=f"Balance ${health['balance']:.2f} below minimum ${self.THRESHOLDS['min_balance']}",
                value=health['balance'],
                threshold=self.THRESHOLDS['min_balance'],
                timestamp=datetime.now()
            ))

        # Daily loss alert
        if health['daily_pnl'] < self.THRESHOLDS['max_daily_loss']:
            self._alerts.append(Alert(
                level=AlertLevel.WARNING,
                metric='daily_pnl',
                message=f"Daily P&L ${health['daily_pnl']:.2f} exceeds max loss ${self.THRESHOLDS['max_daily_loss']}",
                value=health['daily_pnl'],
                threshold=self.THRESHOLDS['max_daily_loss'],
                timestamp=datetime.now()
            ))

        # Trade gap alert (only if we've had at least one trade)
        hours = activity.get('hours_since_trade')
        if hours and hours > self.THRESHOLDS['max_trade_gap_hours']:
            self._alerts.append(Alert(
                level=AlertLevel.WARNING,
                metric='trade_gap',
                message=f"No trades for {hours:.1f} hours (threshold: {self.THRESHOLDS['max_trade_gap_hours']}h)",
                value=hours,
                threshold=self.THRESHOLDS['max_trade_gap_hours'],
                timestamp=datetime.now()
            ))

        # Stale prices alert
        if health['price_age_minutes'] > self.THRESHOLDS['max_price_age_minutes']:
            self._alerts.append(Alert(
                level=AlertLevel.CRITICAL,
                metric='price_freshness',
                message=f"Price data {health['price_age_minutes']:.1f} min old (threshold: {self.THRESHOLDS['max_price_age_minutes']} min)",
                value=health['price_age_minutes'],
                threshold=self.THRESHOLDS['max_price_age_minutes'],
                timestamp=datetime.now()
            ))

        # API errors alert
        if health['api_errors_1h'] > self.THRESHOLDS['max_api_errors_hourly']:
            self._alerts.append(Alert(
                level=AlertLevel.WARNING,
                metric='api_errors',
                message=f"{health['api_errors_1h']} API errors in last hour (threshold: {self.THRESHOLDS['max_api_errors_hourly']})",
                value=health['api_errors_1h'],
                threshold=self.THRESHOLDS['max_api_errors_hourly'],
                timestamp=datetime.now()
            ))

        # Win rate warning (only if enough trades)
        if trading['total_trades'] >= 10 and trading['win_rate'] < self.THRESHOLDS['min_win_rate']:
            self._alerts.append(Alert(
                level=AlertLevel.INFO,
                metric='win_rate',
                message=f"Win rate {trading['win_rate']:.1f}% below {self.THRESHOLDS['min_win_rate']}%",
                value=trading['win_rate'],
                threshold=self.THRESHOLDS['min_win_rate'],
                timestamp=datetime.now()
            ))

        return self._alerts

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics in one call.

        Returns:
            Dict with trading, activity, learning, health metrics and alerts.
        """
        return {
            'trading': self.get_trading_metrics(),
            'activity': self.get_activity_metrics(),
            'learning': self.get_learning_metrics(),
            'health': self.get_system_health(),
            'alerts': [
                {
                    'level': a.level.value,
                    'metric': a.metric,
                    'message': a.message
                }
                for a in self.check_alerts()
            ],
            'timestamp': datetime.now().isoformat()
        }

    def format_prometheus(self) -> str:
        """Format metrics in Prometheus exposition format.

        Returns:
            String in Prometheus text format for scraping.
        """
        lines = []
        metrics = self.get_all_metrics()

        # Trading metrics
        t = metrics['trading']
        lines.append("# HELP cryptobot_trades_total Total number of closed trades")
        lines.append("# TYPE cryptobot_trades_total counter")
        lines.append(f"cryptobot_trades_total {t['total_trades']}")

        lines.append("# HELP cryptobot_win_rate Win rate percentage")
        lines.append("# TYPE cryptobot_win_rate gauge")
        lines.append(f"cryptobot_win_rate {t['win_rate']}")

        lines.append("# HELP cryptobot_pnl_total Total profit/loss in USD")
        lines.append("# TYPE cryptobot_pnl_total gauge")
        lines.append(f"cryptobot_pnl_total {t['total_pnl']}")

        lines.append("# HELP cryptobot_profit_factor Profit factor ratio")
        lines.append("# TYPE cryptobot_profit_factor gauge")
        lines.append(f"cryptobot_profit_factor {t['profit_factor']}")

        lines.append("# HELP cryptobot_avg_pnl Average PnL per trade")
        lines.append("# TYPE cryptobot_avg_pnl gauge")
        lines.append(f"cryptobot_avg_pnl {t['avg_pnl_per_trade']}")

        # Activity metrics
        a = metrics['activity']
        lines.append("# HELP cryptobot_open_positions Number of open positions")
        lines.append("# TYPE cryptobot_open_positions gauge")
        lines.append(f"cryptobot_open_positions {a['open_positions']}")

        lines.append("# HELP cryptobot_exposure_pct Exposure percentage")
        lines.append("# TYPE cryptobot_exposure_pct gauge")
        lines.append(f"cryptobot_exposure_pct {a['exposure_pct']}")

        lines.append("# HELP cryptobot_trades_24h Trades in last 24 hours")
        lines.append("# TYPE cryptobot_trades_24h gauge")
        lines.append(f"cryptobot_trades_24h {a['trades_24h']}")

        lines.append("# HELP cryptobot_trades_per_hour Average trades per hour")
        lines.append("# TYPE cryptobot_trades_per_hour gauge")
        lines.append(f"cryptobot_trades_per_hour {a['trades_per_hour']}")

        # Health metrics
        h = metrics['health']
        lines.append("# HELP cryptobot_balance Account balance in USD")
        lines.append("# TYPE cryptobot_balance gauge")
        lines.append(f"cryptobot_balance {h['balance']}")

        lines.append("# HELP cryptobot_daily_pnl Daily PnL in USD")
        lines.append("# TYPE cryptobot_daily_pnl gauge")
        lines.append(f"cryptobot_daily_pnl {h['daily_pnl']}")

        lines.append("# HELP cryptobot_api_errors_1h API errors in last hour")
        lines.append("# TYPE cryptobot_api_errors_1h gauge")
        lines.append(f"cryptobot_api_errors_1h {h['api_errors_1h']}")

        lines.append("# HELP cryptobot_price_age_minutes Age of price data in minutes")
        lines.append("# TYPE cryptobot_price_age_minutes gauge")
        lines.append(f"cryptobot_price_age_minutes {h['price_age_minutes']}")

        # Learning metrics
        l = metrics['learning']
        lines.append("# HELP cryptobot_learnings_total Total learnings")
        lines.append("# TYPE cryptobot_learnings_total counter")
        lines.append(f"cryptobot_learnings_total {l['total_learnings']}")

        lines.append("# HELP cryptobot_active_rules Active trading rules")
        lines.append("# TYPE cryptobot_active_rules gauge")
        lines.append(f"cryptobot_active_rules {l['active_rules']}")

        lines.append("# HELP cryptobot_testing_rules Testing trading rules")
        lines.append("# TYPE cryptobot_testing_rules gauge")
        lines.append(f"cryptobot_testing_rules {l['testing_rules']}")

        # Alert count
        lines.append("# HELP cryptobot_alerts_active Number of active alerts")
        lines.append("# TYPE cryptobot_alerts_active gauge")
        lines.append(f"cryptobot_alerts_active {len(metrics['alerts'])}")

        return "\n".join(lines)

    def print_summary(self) -> str:
        """Generate human-readable performance summary.

        Returns:
            Formatted string with performance summary.
        """
        metrics = self.get_all_metrics()
        t = metrics['trading']
        a = metrics['activity']
        l = metrics['learning']
        h = metrics['health']

        lines = [
            "=" * 50,
            "  CRYPTO TRADING BOT - PERFORMANCE SUMMARY",
            "=" * 50,
            "",
            "ACCOUNT STATUS",
            "-" * 30,
            f"  Balance:        ${h['balance']:.2f}",
            f"  Daily P&L:      ${h['daily_pnl']:.2f}",
            f"  Total P&L:      ${t['total_pnl']:.2f}",
            f"  Open Positions: {a['open_positions']}",
            f"  Exposure:       {a['exposure_pct']:.1f}%",
            "",
            "TRADING PERFORMANCE",
            "-" * 30,
            f"  Total Trades:   {t['total_trades']}",
            f"  Win Rate:       {t['win_rate']:.1f}%",
            f"  Profit Factor:  {t['profit_factor']:.2f}",
            f"  Avg Trade:      ${t['avg_pnl_per_trade']:.2f}",
            f"  Best Trade:     ${t['best_trade']:.2f}",
            f"  Worst Trade:    ${t['worst_trade']:.2f}",
            "",
            "ACTIVITY (24h)",
            "-" * 30,
            f"  Trades Today:   {a['trades_today']}",
            f"  Trades/Hour:    {a['trades_per_hour']:.2f}",
        ]

        if a.get('hours_since_trade'):
            lines.append(f"  Last Trade:     {a['hours_since_trade']:.1f}h ago")
        else:
            lines.append("  Last Trade:     No trades yet")

        lines.extend([
            "",
            "LEARNING SYSTEM",
            "-" * 30,
            f"  Total Learnings: {l['total_learnings']}",
            f"  Today:           {l['learnings_today']}",
            f"  Active Rules:    {l['active_rules']}",
            f"  Testing Rules:   {l['testing_rules']}",
            "",
        ])

        # Add alerts section
        alerts = metrics['alerts']
        lines.append("ALERTS")
        lines.append("-" * 30)
        if alerts:
            for alert in alerts:
                if alert['level'] == 'critical':
                    icon = "[!!!]"
                elif alert['level'] == 'warning':
                    icon = "[!]"
                else:
                    icon = "[i]"
                lines.append(f"  {icon} {alert['message']}")
        else:
            lines.append("  No active alerts")

        lines.extend([
            "",
            "=" * 50,
            f"  Generated: {metrics['timestamp']}",
            "=" * 50,
        ])

        return "\n".join(lines)


# Convenience function for command-line use
def print_performance_summary():
    """Print performance summary to console."""
    mc = MetricsCollector()
    print(mc.print_summary())


# Test when run directly
if __name__ == "__main__":
    print_performance_summary()
