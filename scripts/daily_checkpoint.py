#!/usr/bin/env python3
"""
Daily Checkpoint Script for Paper Trading Validation.

Collects metrics from the running system and generates a daily report.

Usage:
    python scripts/daily_checkpoint.py [--output FILE]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Install with: pip install requests")
    sys.exit(1)


DASHBOARD_URL = "http://localhost:8080"


def fetch_api(endpoint: str) -> dict:
    """Fetch data from dashboard API."""
    try:
        response = requests.get(f"{DASHBOARD_URL}{endpoint}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"WARNING: Failed to fetch {endpoint}: {e}")
        return {}


def get_system_health() -> dict:
    """Get system health status."""
    return fetch_api("/api/health")


def get_loop_stats() -> dict:
    """Get learning loop statistics."""
    return fetch_api("/api/loop-stats")


def get_profitability() -> dict:
    """Get profitability snapshot."""
    return fetch_api("/api/profitability/snapshot")


def get_effectiveness() -> dict:
    """Get effectiveness summary."""
    return fetch_api("/api/adaptations/effectiveness")


def get_conditions() -> dict:
    """Get active conditions."""
    return fetch_api("/api/conditions")


def get_positions() -> dict:
    """Get open positions."""
    return fetch_api("/api/positions")


def get_knowledge_stats() -> dict:
    """Get knowledge brain statistics."""
    coins = fetch_api("/api/knowledge/coins")
    patterns = fetch_api("/api/knowledge/patterns")
    rules = fetch_api("/api/knowledge/rules")
    blacklist = fetch_api("/api/knowledge/blacklist")

    return {
        "total_coins": coins.get("count", 0),
        "total_patterns": patterns.get("count", 0),
        "active_patterns": len([p for p in patterns.get("patterns", []) if p.get("is_active", True)]),
        "total_rules": rules.get("count", 0),
        "blacklisted_coins": blacklist.get("count", 0),
    }


def determine_decision(health: dict, stats: dict, profit: dict, effectiveness: dict) -> str:
    """Determine go/no-go decision based on metrics."""
    issues = []

    # Check health
    overall = health.get("overall", "unknown")
    if overall == "failed":
        return "ABORT", ["System health: FAILED"]
    if overall == "degraded":
        issues.append("System health degraded")

    # Check P&L
    total_pnl = profit.get("total_pnl", 0)
    if total_pnl < -1000:
        return "PAUSE", [f"P&L below -$1000: ${total_pnl:.2f}"]
    if total_pnl < -500:
        issues.append(f"P&L concerning: ${total_pnl:.2f}")

    # Check effectiveness
    harmful = effectiveness.get("harmful", 0)
    total_measured = sum([
        effectiveness.get("highly_effective", 0),
        effectiveness.get("effective", 0),
        effectiveness.get("neutral", 0),
        effectiveness.get("ineffective", 0),
        harmful,
    ])
    if total_measured > 0 and (harmful / total_measured) > 0.5:
        return "PAUSE", [f">{50}% adaptations harmful"]
    if total_measured > 0 and (harmful / total_measured) > 0.2:
        issues.append(f"High harmful adaptation rate: {harmful}/{total_measured}")

    # Check activity
    trades = stats.get("total_trades", 0)
    uptime = stats.get("uptime_hours", 0)
    if uptime > 24 and trades == 0:
        issues.append("No trades in 24+ hours")

    if issues:
        return "INVESTIGATE", issues
    return "CONTINUE", []


def generate_report(output_file: str = None) -> str:
    """Generate daily checkpoint report."""
    print("Collecting metrics from dashboard...")
    print(f"Dashboard URL: {DASHBOARD_URL}")
    print()

    # Fetch all data
    health = get_system_health()
    stats = get_loop_stats()
    profit = get_profitability()
    effectiveness = get_effectiveness()
    conditions = get_conditions()
    positions = get_positions()
    knowledge = get_knowledge_stats()

    # Determine decision
    decision, reasons = determine_decision(health, stats, profit, effectiveness)

    # Format report
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    uptime_hours = stats.get("uptime_hours", 0)
    uptime_h = int(uptime_hours)
    uptime_m = int((uptime_hours - uptime_h) * 60)

    report = f"""
================================================================================
                    DAILY CHECKPOINT REPORT
================================================================================
Date/Time: {today}
Decision:  {decision}
{f"Reasons:   {', '.join(reasons)}" if reasons else ""}

--------------------------------------------------------------------------------
SYSTEM HEALTH
--------------------------------------------------------------------------------
Overall Status:    {health.get("overall", "unknown").upper()}
Uptime:            {uptime_h}h {uptime_m}m
Components:
"""

    for name, comp in health.get("components", {}).items():
        status = comp.get("status", "unknown") if isinstance(comp, dict) else comp
        report += f"  - {name}: {status}\n"

    report += f"""
--------------------------------------------------------------------------------
TRADING ACTIVITY
--------------------------------------------------------------------------------
Total Trades:      {stats.get("total_trades", 0)}
Active Conditions: {conditions.get("count", 0)}
Open Positions:    {positions.get("count", 0)}

--------------------------------------------------------------------------------
PERFORMANCE
--------------------------------------------------------------------------------
Win Rate:          {profit.get("win_rate", 0):.1f}%
Total P&L:         ${profit.get("total_pnl", 0):.2f}
Profit Factor:     {profit.get("profit_factor", 0):.2f}
Sharpe Ratio:      {profit.get("sharpe_ratio", 0):.2f}
Max Drawdown:      {profit.get("max_drawdown_pct", 0):.1f}%

--------------------------------------------------------------------------------
LEARNING
--------------------------------------------------------------------------------
Reflections:       {stats.get("total_reflections", 0)}
Insights:          {stats.get("total_insights", 0)}
Adaptations:       {stats.get("total_adaptations", 0)}

Knowledge Brain:
  - Coins tracked:     {knowledge.get("total_coins", 0)}
  - Blacklisted:       {knowledge.get("blacklisted_coins", 0)}
  - Patterns (active): {knowledge.get("active_patterns", 0)}
  - Regime Rules:      {knowledge.get("total_rules", 0)}

--------------------------------------------------------------------------------
EFFECTIVENESS
--------------------------------------------------------------------------------
Highly Effective:  {effectiveness.get("highly_effective", 0)}
Effective:         {effectiveness.get("effective", 0)}
Neutral:           {effectiveness.get("neutral", 0)}
Ineffective:       {effectiveness.get("ineffective", 0)}
Harmful:           {effectiveness.get("harmful", 0)}
Pending:           {effectiveness.get("pending", 0)}

================================================================================
"""

    print(report)

    # Save to file if specified
    if output_file:
        Path(output_file).write_text(report)
        print(f"Report saved to: {output_file}")

    return decision


def main():
    parser = argparse.ArgumentParser(description="Daily Checkpoint for Paper Trading")
    parser.add_argument("--output", "-o", help="Output file for report")
    parser.add_argument("--json", action="store_true", help="Output raw JSON data")
    args = parser.parse_args()

    if args.json:
        data = {
            "timestamp": datetime.now().isoformat(),
            "health": get_system_health(),
            "stats": get_loop_stats(),
            "profitability": get_profitability(),
            "effectiveness": get_effectiveness(),
            "knowledge": get_knowledge_stats(),
        }
        print(json.dumps(data, indent=2))
    else:
        decision = generate_report(args.output)
        sys.exit(0 if decision == "CONTINUE" else 1)


if __name__ == "__main__":
    main()
