# TASK-021: Autonomous Monitoring Agent

## Overview
Build a self-monitoring system that uses the LLM to detect issues, bugs, and inefficiencies autonomously. The bot should catch its own problems without human prompting.

## Goal
**Bot catches its own bugs autonomously.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  autonomous_monitor.py                       │
├─────────────────────────────────────────────────────────────┤
│  1. Collect Data    →  Query all database tables            │
│  2. Build Report    →  Aggregate metrics and patterns       │
│  3. LLM Analysis    →  Send to LLM with critical prompt     │
│  4. Parse Findings  →  Extract issues with severity         │
│  5. Store Alerts    →  Save to monitoring_alerts table      │
│  6. Report          →  Log summary and exit                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### New Table: `monitoring_alerts`

```sql
CREATE TABLE IF NOT EXISTS monitoring_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,           -- 'bug', 'inefficiency', 'pattern', 'performance', 'missing_feature'
    severity TEXT NOT NULL,             -- 'critical', 'high', 'medium', 'low', 'info'
    title TEXT NOT NULL,                -- Short description
    description TEXT NOT NULL,          -- Full explanation
    evidence TEXT,                       -- Supporting data/queries
    recommendation TEXT,                 -- Suggested fix
    status TEXT DEFAULT 'open',         -- 'open', 'acknowledged', 'fixed', 'wontfix'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP,
    fixed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alerts_severity ON monitoring_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON monitoring_alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON monitoring_alerts(created_at);
```

---

## Data Collection

### 1. Trade Patterns
```python
def collect_trade_patterns(hours=24):
    """Collect trade distribution and patterns."""
    return {
        'total_trades': count,
        'trades_by_coin': {'bitcoin': 5, 'ethereum': 3, ...},
        'trades_by_tier': {1: 10, 2: 8, 3: 2},
        'trades_by_hour': {0: 2, 1: 3, ...},  # Hour of day
        'avg_trade_size': 50.0,
        'size_distribution': {'<$20': 5, '$20-50': 10, ...},
        'avg_duration_seconds': 120,
        'win_rate': 0.45,
        'avg_win_pnl': 1.0,
        'avg_loss_pnl': -5.0
    }
```

### 2. Rule Effectiveness
```python
def collect_rule_stats():
    """Collect rule usage and effectiveness."""
    return {
        'total_rules': 5,
        'rules_by_status': {'active': 2, 'testing': 3},
        'rule_details': [
            {
                'id': 1,
                'text': 'Buy on momentum...',
                'success_count': 5,
                'failure_count': 3,
                'success_rate': 0.625,
                'last_used': '2026-01-14 10:00:00'
            },
            ...
        ],
        'unused_rules': [...],  # Rules never applied
        'rules_never_succeeded': [...]
    }
```

### 3. Win/Loss Analysis
```python
def collect_winloss_patterns():
    """Analyze win/loss patterns."""
    return {
        'overall_win_rate': 0.45,
        'win_rate_by_tier': {1: 0.50, 2: 0.40, 3: 0.35},
        'win_rate_by_coin': {'bitcoin': 0.60, 'dogecoin': 0.20},
        'win_rate_by_hour': {9: 0.55, 10: 0.40, ...},
        'streak_analysis': {
            'current_streak': -3,  # Negative = losing
            'max_win_streak': 5,
            'max_loss_streak': 8
        },
        'pnl_by_exit_reason': {
            'take_profit': {'count': 10, 'total_pnl': 10.0},
            'stop_loss': {'count': 15, 'total_pnl': -75.0}
        }
    }
```

### 4. Account Health
```python
def collect_account_health():
    """Track account state over time."""
    return {
        'current_balance': 995.0,
        'starting_balance': 1000.0,
        'total_pnl': -5.0,
        'pnl_trend': 'declining',  # or 'improving', 'stable'
        'daily_pnl_history': [
            {'date': '2026-01-13', 'pnl': 2.0},
            {'date': '2026-01-14', 'pnl': -7.0}
        ],
        'exposure_utilization': 0.85,  # % of max exposure used
        'trades_near_limits': 5,  # Trades rejected for limits
        'balance_volatility': 0.02  # Std dev of balance changes
    }
```

### 5. System Metrics
```python
def collect_system_metrics():
    """Collect system health data."""
    return {
        'uptime_hours': 48,
        'total_cycles': 5760,
        'cycles_with_errors': 12,
        'error_rate': 0.002,
        'error_types': {
            'llm_timeout': 5,
            'market_data_failed': 3,
            'database_error': 0
        },
        'avg_cycle_duration': 3.5,
        'llm_response_times': {'avg': 2.1, 'max': 15.0, 'p95': 4.0},
        'market_data_staleness': 0,  # Seconds since last update
        'cooldown_effectiveness': {
            'rejections': 15,
            'unique_coins_traded': 12
        }
    }
```

### 6. Learning Quality
```python
def collect_learning_quality():
    """Analyze quality of learnings generated."""
    return {
        'total_learnings': 25,
        'learnings_last_24h': 5,
        'avg_confidence': 0.65,
        'learnings_by_outcome': {'win': 10, 'loss': 15},
        'rules_created_from_learnings': 3,
        'duplicate_patterns': 2,  # Similar learnings
        'actionable_learnings': 18  # Have clear patterns
    }
```

---

## LLM Prompt

```python
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

Respond with JSON array of findings:
[
    {
        "type": "bug|inefficiency|pattern|performance|missing_feature",
        "severity": "critical|high|medium|low|info",
        "title": "Short description",
        "description": "Full explanation of the issue",
        "evidence": "Specific data points that support this finding",
        "recommendation": "What should be done to fix this"
    }
]

If you find NO issues (unlikely), return an empty array [].
Be thorough - a good audit finds at least 3-5 issues."""

MONITOR_USER_PROMPT = """
## BOT MONITORING REPORT
Generated: {timestamp}
Analysis Period: Last {hours} hours

### TRADE PATTERNS
{trade_patterns}

### RULE EFFECTIVENESS
{rule_stats}

### WIN/LOSS ANALYSIS
{winloss_patterns}

### ACCOUNT HEALTH
{account_health}

### SYSTEM METRICS
{system_metrics}

### LEARNING QUALITY
{learning_quality}

---

Analyze this data critically. Find bugs, inefficiencies, and problems.
Remember: Your job is to find issues the developers missed.
"""
```

---

## Script Structure

```python
#!/usr/bin/env python3
"""Autonomous monitoring agent for the trading bot.

Collects bot performance data and uses LLM to identify issues,
bugs, and inefficiencies autonomously.

Usage:
    python scripts/autonomous_monitor.py [--hours 24] [--verbose]

Cron example (run hourly):
    0 * * * * cd /path/to/bot && python scripts/autonomous_monitor.py >> logs/monitor.log 2>&1
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, '/mnt/c/documents/crypto-trading-bot')

from src.database import Database
from src.llm_interface import LLMInterface


class AutonomousMonitor:
    """Self-monitoring agent that uses LLM to detect issues."""

    def __init__(self, db: Database = None, llm: LLMInterface = None):
        self.db = db or Database()
        self.llm = llm or LLMInterface(db=self.db)
        self.logger = logging.getLogger(__name__)

    def run(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Run full monitoring analysis.

        Args:
            hours: Hours of data to analyze.

        Returns:
            List of findings from LLM analysis.
        """
        # 1. Collect all data
        report = self.collect_all_data(hours)

        # 2. Send to LLM for analysis
        findings = self.analyze_with_llm(report)

        # 3. Store findings in database
        self.store_findings(findings)

        # 4. Log summary
        self.log_summary(findings)

        return findings

    def collect_all_data(self, hours: int) -> Dict[str, Any]:
        """Collect all monitoring data."""
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
        # Implementation here
        pass

    def collect_rule_stats(self) -> Dict[str, Any]:
        """Collect rule usage and effectiveness."""
        # Implementation here
        pass

    def collect_winloss_patterns(self, hours: int) -> Dict[str, Any]:
        """Analyze win/loss patterns."""
        # Implementation here
        pass

    def collect_account_health(self) -> Dict[str, Any]:
        """Track account state."""
        # Implementation here
        pass

    def collect_system_metrics(self, hours: int) -> Dict[str, Any]:
        """Collect system health data."""
        # Implementation here
        pass

    def collect_learning_quality(self, hours: int) -> Dict[str, Any]:
        """Analyze quality of learnings."""
        # Implementation here
        pass

    def analyze_with_llm(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Send report to LLM for critical analysis."""
        # Build prompt and get response
        # Parse JSON response into findings
        pass

    def store_findings(self, findings: List[Dict[str, Any]]) -> None:
        """Store findings in monitoring_alerts table."""
        for finding in findings:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO monitoring_alerts
                    (alert_type, severity, title, description, evidence, recommendation)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    finding['type'],
                    finding['severity'],
                    finding['title'],
                    finding['description'],
                    finding.get('evidence', ''),
                    finding.get('recommendation', '')
                ))
                conn.commit()

    def log_summary(self, findings: List[Dict[str, Any]]) -> None:
        """Log summary of findings."""
        by_severity = {}
        for f in findings:
            sev = f['severity']
            by_severity[sev] = by_severity.get(sev, 0) + 1

        self.logger.info(f"Monitoring complete: {len(findings)} findings")
        for sev, count in sorted(by_severity.items()):
            self.logger.info(f"  {sev}: {count}")


def main():
    parser = argparse.ArgumentParser(description='Autonomous bot monitor')
    parser.add_argument('--hours', type=int, default=24, help='Hours to analyze')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    monitor = AutonomousMonitor()
    findings = monitor.run(hours=args.hours)

    # Exit with code based on severity
    if any(f['severity'] == 'critical' for f in findings):
        sys.exit(2)
    elif any(f['severity'] == 'high' for f in findings):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
```

---

## Implementation Plan

### Step 1: Database Schema
Add `monitoring_alerts` table to `database.py`.

### Step 2: Data Collection Methods
Implement all `collect_*` methods with proper SQL queries.

### Step 3: LLM Integration
- Create monitoring-specific prompts
- Handle JSON parsing of findings
- Implement retry logic

### Step 4: Alert Storage
- Store findings with proper categorization
- Avoid duplicate alerts (check for similar recent alerts)

### Step 5: CLI Interface
- Argument parsing (--hours, --verbose, --dry-run)
- Proper exit codes for cron
- Logging to file

### Step 6: Testing
- Run manually and verify output
- Check alerts stored correctly
- Verify LLM analysis quality

---

## Files Changed

| File | Changes |
|------|---------|
| `src/database.py` | Add `monitoring_alerts` table |
| `scripts/autonomous_monitor.py` | New file - main script |
| `TASKS.md` | Update task status |

---

## Cron Setup (After Implementation)

```bash
# Add to crontab (run hourly)
crontab -e

# Add line:
0 * * * * cd /mnt/c/documents/crypto-trading-bot && python3 scripts/autonomous_monitor.py >> logs/monitor.log 2>&1
```

---

## Verification

### Test 1: Manual Run
```bash
python3 scripts/autonomous_monitor.py --hours 24 --verbose
```

### Test 2: Check Alerts Stored
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('data/trading_bot.db')
cursor = conn.cursor()
cursor.execute('SELECT severity, title FROM monitoring_alerts ORDER BY created_at DESC LIMIT 10')
for row in cursor.fetchall():
    print(f'[{row[0]}] {row[1]}')
"
```

### Test 3: View Full Report
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('data/trading_bot.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT alert_type, severity, title, description, recommendation
    FROM monitoring_alerts
    WHERE created_at > datetime('now', '-1 hour')
''')
for row in cursor.fetchall():
    print(f'\\n[{row[1].upper()}] {row[0]}: {row[2]}')
    print(f'  {row[3]}')
    print(f'  Recommendation: {row[4]}')
"
```

---

## Success Criteria

- [ ] Script runs without errors
- [ ] All 6 data collection categories work
- [ ] LLM returns valid JSON findings
- [ ] Findings stored in database
- [ ] Exit codes work for cron (0=ok, 1=high, 2=critical)
- [ ] Can run multiple times without issues
- [ ] Finds at least 1 real issue on first run

---

## Example Output

```
$ python3 scripts/autonomous_monitor.py --hours 24

2026-01-14 18:00:00 - INFO - Starting autonomous monitoring...
2026-01-14 18:00:00 - INFO - Collecting trade patterns...
2026-01-14 18:00:00 - INFO - Collecting rule stats...
2026-01-14 18:00:01 - INFO - Collecting win/loss patterns...
2026-01-14 18:00:01 - INFO - Collecting account health...
2026-01-14 18:00:01 - INFO - Collecting system metrics...
2026-01-14 18:00:01 - INFO - Collecting learning quality...
2026-01-14 18:00:02 - INFO - Sending to LLM for analysis...
2026-01-14 18:00:15 - INFO - LLM analysis complete
2026-01-14 18:00:15 - INFO - Storing 5 findings...
2026-01-14 18:00:15 - INFO -
========================================
MONITORING COMPLETE
========================================
Total findings: 5
  critical: 0
  high: 1
  medium: 2
  low: 2

HIGH SEVERITY:
  - [inefficiency] Win rate drops significantly at night (22:00-06:00)

MEDIUM SEVERITY:
  - [pattern] Rule #3 has 0% success rate after 10 uses
  - [bug] Cooldown not preventing repeated trades on DOGE

LOW SEVERITY:
  - [info] 15% of learnings have duplicate patterns
  - [performance] LLM response time increasing (avg 4.2s)
========================================
```
