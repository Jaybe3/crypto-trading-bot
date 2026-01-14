# TASK-017: Performance Monitoring

## Overview
Implement comprehensive performance monitoring to track bot health, trading metrics, and system alerts. Enables real-time visibility into bot performance and early detection of issues.

## Current State
- Basic account state in database
- Dashboard shows trades and P&L
- No aggregated performance metrics
- No alerting system
- No external monitoring endpoint

## Target State
- Real-time performance metrics calculated and displayed
- Alert system for critical issues
- `/metrics` endpoint for external monitoring (Prometheus-compatible)
- Performance summary command for quick checks
- Historical performance tracking

---

## Key Metrics

### Trading Performance
| Metric | Description | Calculation |
|--------|-------------|-------------|
| `total_trades` | Total closed trades | COUNT(closed_trades) |
| `win_rate` | Percentage of profitable trades | wins / total_trades * 100 |
| `total_pnl` | Total profit/loss in USD | SUM(pnl_usd) |
| `avg_pnl_per_trade` | Average P&L per trade | total_pnl / total_trades |
| `best_trade` | Largest single win | MAX(pnl_usd) |
| `worst_trade` | Largest single loss | MIN(pnl_usd) |
| `profit_factor` | Gross profit / gross loss | sum(wins) / abs(sum(losses)) |

### Activity Metrics
| Metric | Description | Calculation |
|--------|-------------|-------------|
| `trades_today` | Trades closed today | COUNT WHERE closed_at = today |
| `trades_per_hour` | Average trading frequency | trades_24h / 24 |
| `open_positions` | Current open trades | COUNT(open_trades) |
| `exposure_pct` | % of balance in positions | in_positions / balance * 100 |

### Learning Metrics
| Metric | Description | Calculation |
|--------|-------------|-------------|
| `total_learnings` | Total learnings generated | COUNT(learnings) |
| `learnings_today` | Learnings created today | COUNT WHERE today |
| `active_rules` | Rules in active status | COUNT WHERE status='active' |
| `testing_rules` | Rules being tested | COUNT WHERE status='testing' |
| `rule_success_rate` | Avg success rate of active rules | AVG(success_rate) |

### System Health
| Metric | Description | Threshold |
|--------|-------------|-----------|
| `last_trade_age` | Time since last trade | Alert if > 6 hours |
| `last_price_update` | Time since price fetch | Alert if > 5 minutes |
| `api_errors_1h` | API errors in last hour | Alert if > 10 |
| `balance` | Current account balance | Alert if < $950 |
| `daily_pnl` | Today's P&L | Alert if < -$20 |

---

## Implementation

### 1. New Module: `src/metrics.py`

```python
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

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    level: AlertLevel
    metric: str
    message: str
    value: Any
    threshold: Any
    timestamp: datetime


class MetricsCollector:
    """Collects and calculates performance metrics."""

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
        self.db = db or Database()
        self._alerts: List[Alert] = []

    def get_trading_metrics(self) -> Dict[str, Any]:
        """Calculate trading performance metrics."""
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
        """Calculate activity and exposure metrics."""
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
            except:
                pass

        return {
            'trades_today': trades_today,
            'trades_24h': trades_24h,
            'trades_per_hour': round(trades_24h / 24, 2),
            'open_positions': open_positions,
            'exposure_pct': round(exposure_pct, 1),
            'last_trade_time': last_trade,
            'hours_since_trade': round(hours_since_trade, 1) if hours_since_trade else None,
            'last_price_update': last_price
        }

    def get_learning_metrics(self) -> Dict[str, Any]:
        """Calculate learning system metrics."""
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
        """Check system health metrics."""
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
        """Check all metrics against thresholds and generate alerts."""
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

        # Trade gap alert
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
        """Get all metrics in one call."""
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
        """Format metrics in Prometheus exposition format."""
        lines = []
        metrics = self.get_all_metrics()

        # Trading metrics
        t = metrics['trading']
        lines.append(f"# HELP cryptobot_trades_total Total number of closed trades")
        lines.append(f"# TYPE cryptobot_trades_total counter")
        lines.append(f"cryptobot_trades_total {t['total_trades']}")

        lines.append(f"# HELP cryptobot_win_rate Win rate percentage")
        lines.append(f"# TYPE cryptobot_win_rate gauge")
        lines.append(f"cryptobot_win_rate {t['win_rate']}")

        lines.append(f"# HELP cryptobot_pnl_total Total profit/loss in USD")
        lines.append(f"# TYPE cryptobot_pnl_total gauge")
        lines.append(f"cryptobot_pnl_total {t['total_pnl']}")

        lines.append(f"# HELP cryptobot_profit_factor Profit factor ratio")
        lines.append(f"# TYPE cryptobot_profit_factor gauge")
        lines.append(f"cryptobot_profit_factor {t['profit_factor']}")

        # Activity metrics
        a = metrics['activity']
        lines.append(f"# HELP cryptobot_open_positions Number of open positions")
        lines.append(f"# TYPE cryptobot_open_positions gauge")
        lines.append(f"cryptobot_open_positions {a['open_positions']}")

        lines.append(f"# HELP cryptobot_exposure_pct Exposure percentage")
        lines.append(f"# TYPE cryptobot_exposure_pct gauge")
        lines.append(f"cryptobot_exposure_pct {a['exposure_pct']}")

        lines.append(f"# HELP cryptobot_trades_24h Trades in last 24 hours")
        lines.append(f"# TYPE cryptobot_trades_24h gauge")
        lines.append(f"cryptobot_trades_24h {a['trades_24h']}")

        # Health metrics
        h = metrics['health']
        lines.append(f"# HELP cryptobot_balance Account balance in USD")
        lines.append(f"# TYPE cryptobot_balance gauge")
        lines.append(f"cryptobot_balance {h['balance']}")

        lines.append(f"# HELP cryptobot_daily_pnl Daily PnL in USD")
        lines.append(f"# TYPE cryptobot_daily_pnl gauge")
        lines.append(f"cryptobot_daily_pnl {h['daily_pnl']}")

        lines.append(f"# HELP cryptobot_api_errors_1h API errors in last hour")
        lines.append(f"# TYPE cryptobot_api_errors_1h gauge")
        lines.append(f"cryptobot_api_errors_1h {h['api_errors_1h']}")

        # Learning metrics
        l = metrics['learning']
        lines.append(f"# HELP cryptobot_learnings_total Total learnings")
        lines.append(f"# TYPE cryptobot_learnings_total counter")
        lines.append(f"cryptobot_learnings_total {l['total_learnings']}")

        lines.append(f"# HELP cryptobot_active_rules Active trading rules")
        lines.append(f"# TYPE cryptobot_active_rules gauge")
        lines.append(f"cryptobot_active_rules {l['active_rules']}")

        # Alert count
        lines.append(f"# HELP cryptobot_alerts_active Number of active alerts")
        lines.append(f"# TYPE cryptobot_alerts_active gauge")
        lines.append(f"cryptobot_alerts_active {len(metrics['alerts'])}")

        return "\n".join(lines)

    def print_summary(self) -> str:
        """Generate human-readable performance summary."""
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
            f"  Last Trade:     {a.get('hours_since_trade', 'N/A')}h ago" if a.get('hours_since_trade') else "  Last Trade:     No trades yet",
            "",
            "LEARNING SYSTEM",
            "-" * 30,
            f"  Total Learnings: {l['total_learnings']}",
            f"  Today:           {l['learnings_today']}",
            f"  Active Rules:    {l['active_rules']}",
            f"  Testing Rules:   {l['testing_rules']}",
            "",
        ]

        # Add alerts section
        alerts = metrics['alerts']
        if alerts:
            lines.extend([
                "ALERTS",
                "-" * 30,
            ])
            for alert in alerts:
                icon = "!!!" if alert['level'] == 'critical' else "!" if alert['level'] == 'warning' else "i"
                lines.append(f"  [{icon}] {alert['message']}")
            lines.append("")
        else:
            lines.extend([
                "ALERTS",
                "-" * 30,
                "  No active alerts",
                "",
            ])

        lines.extend([
            "=" * 50,
            f"  Generated: {metrics['timestamp']}",
            "=" * 50,
        ])

        return "\n".join(lines)
```

### 2. Dashboard Integration

Add `/api/metrics` and `/metrics` endpoints to `src/dashboard.py`:

```python
from src.metrics import MetricsCollector

# Add to dashboard.py

@app.route('/api/metrics')
def api_metrics():
    """JSON API endpoint for all metrics."""
    try:
        mc = MetricsCollector(db=dashboard_data.db)
        return jsonify(mc.get_all_metrics())
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/metrics')
def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    try:
        mc = MetricsCollector(db=dashboard_data.db)
        return mc.format_prometheus(), 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        logger.error(f"Prometheus metrics error: {e}")
        return f"# Error: {e}", 500
```

### 3. Performance Summary Script

Create `scripts/performance.sh`:

```bash
#!/bin/bash
# Show performance summary

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"
python3 -c "
from src.metrics import MetricsCollector
mc = MetricsCollector()
print(mc.print_summary())
"
```

### 4. Dashboard UI Enhancement

Add performance metrics section to dashboard HTML:

```html
<!-- Performance Metrics Card -->
<div class="card">
    <h2>Performance Metrics</h2>
    <div class="metrics-grid">
        <div class="metric">
            <span class="metric-value">{{ metrics.trading.win_rate }}%</span>
            <span class="metric-label">Win Rate</span>
        </div>
        <div class="metric">
            <span class="metric-value">${{ metrics.trading.total_pnl }}</span>
            <span class="metric-label">Total P&L</span>
        </div>
        <div class="metric">
            <span class="metric-value">{{ metrics.trading.profit_factor }}x</span>
            <span class="metric-label">Profit Factor</span>
        </div>
        <div class="metric">
            <span class="metric-value">{{ metrics.activity.trades_per_hour }}/hr</span>
            <span class="metric-label">Trade Rate</span>
        </div>
    </div>

    <!-- Alerts Section -->
    {% if metrics.alerts %}
    <div class="alerts-section">
        <h3>Active Alerts</h3>
        {% for alert in metrics.alerts %}
        <div class="alert alert-{{ alert.level }}">
            {{ alert.message }}
        </div>
        {% endfor %}
    </div>
    {% endif %}
</div>
```

---

## Alert System

### Alert Levels
| Level | Color | Action |
|-------|-------|--------|
| INFO | Blue | Log only |
| WARNING | Yellow | Log + display |
| CRITICAL | Red | Log + display + (future: notify) |

### Default Thresholds
| Metric | Threshold | Level |
|--------|-----------|-------|
| Balance | < $950 | CRITICAL |
| Daily P&L | < -$20 | WARNING |
| Trade Gap | > 6 hours | WARNING |
| Price Age | > 5 minutes | CRITICAL |
| API Errors | > 10/hour | WARNING |
| Win Rate | < 40% | INFO |

---

## Usage

### Check Performance
```bash
# Quick summary
bash scripts/performance.sh

# Or directly
python3 -c "from src.metrics import MetricsCollector; print(MetricsCollector().print_summary())"
```

### API Endpoints
```bash
# JSON metrics
curl http://localhost:8080/api/metrics | jq

# Prometheus format
curl http://localhost:8080/metrics
```

### External Monitoring
Add to Prometheus config:
```yaml
scrape_configs:
  - job_name: 'cryptobot'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
```

---

## Acceptance Criteria

- [ ] MetricsCollector class calculates all metrics
- [ ] `/api/metrics` returns JSON with all metrics
- [ ] `/metrics` returns Prometheus-compatible format
- [ ] Alert system detects threshold violations
- [ ] Dashboard shows performance summary
- [ ] `scripts/performance.sh` prints summary
- [ ] Alerts display in dashboard

---

## Files to Create/Modify

| File | Action | Changes |
|------|--------|---------|
| `src/metrics.py` | CREATE | Metrics calculation module |
| `src/dashboard.py` | MODIFY | Add /api/metrics and /metrics endpoints |
| `scripts/performance.sh` | CREATE | Performance summary script |

---

## Testing Plan

1. **Metrics Calculation**
```python
from src.metrics import MetricsCollector
mc = MetricsCollector()
print(mc.get_all_metrics())
```

2. **Alert Detection**
```python
alerts = mc.check_alerts()
for a in alerts:
    print(f"[{a.level.value}] {a.message}")
```

3. **Prometheus Format**
```bash
curl http://localhost:8080/metrics
```

4. **Performance Summary**
```bash
bash scripts/performance.sh
```
