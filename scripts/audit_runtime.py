#!/usr/bin/env python3
"""
Comprehensive runtime audit script for crypto trading bot.

Usage: python scripts/audit_runtime.py [--db PATH] [--state PATH] [--api URL]

Performs multi-layer verification:
1. Database consistency
2. JSON state file consistency
3. API endpoint verification (if bot is running)
4. Cross-layer data agreement
5. Known bug detection
"""

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class AuditResult:
    """Result of a single audit check."""
    name: str
    passed: bool
    message: str
    severity: str = "info"  # info, warning, error, critical
    bug_id: Optional[str] = None


@dataclass
class AuditReport:
    """Complete audit report."""
    timestamp: datetime = field(default_factory=datetime.now)
    results: list = field(default_factory=list)

    @property
    def errors(self) -> list:
        return [r for r in self.results if r.severity == "error"]

    @property
    def warnings(self) -> list:
        return [r for r in self.results if r.severity == "warning"]

    @property
    def passed(self) -> list:
        return [r for r in self.results if r.passed]

    @property
    def failed(self) -> list:
        return [r for r in self.results if not r.passed]

    def add(self, result: AuditResult):
        self.results.append(result)

    def summary(self) -> str:
        lines = [
            "=" * 60,
            "AUDIT SUMMARY",
            "=" * 60,
            f"Time: {self.timestamp.isoformat()}",
            f"Total checks: {len(self.results)}",
            f"Passed: {len(self.passed)}",
            f"Failed: {len(self.failed)}",
            f"Warnings: {len(self.warnings)}",
            f"Errors: {len(self.errors)}",
            "",
        ]

        if self.failed:
            lines.append("FAILED CHECKS:")
            for r in self.failed:
                icon = "❌" if r.severity == "error" else "⚠️"
                bug = f" [{r.bug_id}]" if r.bug_id else ""
                lines.append(f"  {icon} {r.name}{bug}: {r.message}")
            lines.append("")

        if self.passed:
            lines.append("PASSED CHECKS:")
            for r in self.passed:
                lines.append(f"  ✅ {r.name}")

        return "\n".join(lines)


class RuntimeAuditor:
    """Comprehensive runtime auditor."""

    def __init__(self, db_path: str, state_path: str, api_url: Optional[str] = None):
        self.db_path = db_path
        self.state_path = state_path
        self.api_url = api_url
        self.report = AuditReport()

        # Cached data
        self._db_data = {}
        self._json_data = {}
        self._api_data = {}

    def run_all(self) -> AuditReport:
        """Run all audit checks."""
        print("Starting comprehensive runtime audit...")
        print(f"  Database: {self.db_path}")
        print(f"  State file: {self.state_path}")
        print(f"  API URL: {self.api_url or 'not specified'}")
        print()

        # Load data sources
        self._load_database()
        self._load_json_state()
        if self.api_url:
            self._load_api_data()

        # Run checks
        self._check_database_integrity()
        self._check_known_bugs()
        self._check_cross_layer_consistency()
        self._check_data_flow()

        return self.report

    def _load_database(self):
        """Load data from database."""
        if not os.path.exists(self.db_path):
            self.report.add(AuditResult(
                name="Database exists",
                passed=False,
                message=f"Database not found at {self.db_path}",
                severity="critical"
            ))
            return

        self.report.add(AuditResult(
            name="Database exists",
            passed=True,
            message=f"Found at {self.db_path}"
        ))

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        try:
            # Account state
            cur.execute("SELECT balance, total_pnl FROM account_state LIMIT 1")
            row = cur.fetchone()
            self._db_data["account_balance"] = row[0] if row else None
            self._db_data["account_pnl"] = row[1] if row else None

            # Trade journal stats
            cur.execute("SELECT COUNT(*) FROM trade_journal")
            self._db_data["journal_total"] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM trade_journal WHERE exit_time IS NOT NULL")
            self._db_data["journal_closed"] = cur.fetchone()[0]

            cur.execute("SELECT COALESCE(SUM(pnl_usd), 0) FROM trade_journal WHERE exit_time IS NOT NULL")
            self._db_data["journal_pnl"] = cur.fetchone()[0]

            # Open/closed trades tables
            cur.execute("SELECT COUNT(*) FROM open_trades")
            self._db_data["open_trades_count"] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM closed_trades")
            self._db_data["closed_trades_count"] = cur.fetchone()[0]

            # Activity log
            cur.execute("SELECT COUNT(*) FROM activity_log")
            self._db_data["activity_count"] = cur.fetchone()[0]

            # Adaptations
            cur.execute("SELECT COUNT(*) FROM adaptations")
            self._db_data["adaptation_count"] = cur.fetchone()[0]

            # Table list
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            self._db_data["tables"] = [row[0] for row in cur.fetchall()]

        finally:
            conn.close()

    def _load_json_state(self):
        """Load data from JSON state file."""
        if not os.path.exists(self.state_path):
            self.report.add(AuditResult(
                name="State file exists",
                passed=False,
                message=f"State file not found at {self.state_path}",
                severity="warning"
            ))
            return

        self.report.add(AuditResult(
            name="State file exists",
            passed=True,
            message=f"Found at {self.state_path}"
        ))

        with open(self.state_path) as f:
            state = json.load(f)

        self._json_data["balance"] = state.get("balance")
        self._json_data["total_pnl"] = state.get("total_pnl", 0)
        self._json_data["open_positions"] = len(state.get("positions", {}))
        self._json_data["closed_positions"] = len(state.get("closed_positions", []))

    def _load_api_data(self):
        """Load data from API endpoints."""
        try:
            import requests

            # Status endpoint
            resp = requests.get(f"{self.api_url}/api/status", timeout=5)
            if resp.ok:
                data = resp.json()
                self._api_data["status"] = data
                self._api_data["balance"] = data.get("account", {}).get("balance")
                self._api_data["total_pnl"] = data.get("account", {}).get("total_pnl")

            # Profitability endpoint
            resp = requests.get(f"{self.api_url}/api/profitability/snapshot", timeout=5)
            if resp.ok:
                data = resp.json()
                self._api_data["profitability"] = data
                self._api_data["prof_balance"] = data.get("account_balance")
                self._api_data["prof_pnl"] = data.get("total_pnl")

            self.report.add(AuditResult(
                name="API accessible",
                passed=True,
                message=f"Connected to {self.api_url}"
            ))

        except Exception as e:
            self.report.add(AuditResult(
                name="API accessible",
                passed=False,
                message=f"Could not connect: {e}",
                severity="warning"
            ))

    def _check_database_integrity(self):
        """Check database structure and integrity."""
        if not self._db_data:
            return

        # Check expected tables exist
        expected_tables = [
            "account_state", "trade_journal", "activity_log",
            "coin_scores", "pattern_stats", "adaptations"
        ]

        missing = [t for t in expected_tables if t not in self._db_data.get("tables", [])]
        if missing:
            self.report.add(AuditResult(
                name="Required tables exist",
                passed=False,
                message=f"Missing tables: {missing}",
                severity="error"
            ))
        else:
            self.report.add(AuditResult(
                name="Required tables exist",
                passed=True,
                message=f"All {len(expected_tables)} required tables present"
            ))

    def _check_known_bugs(self):
        """Check for known runtime bugs."""
        # RT-001: update_account_state() never called
        db_balance = self._db_data.get("account_balance")
        if db_balance == 1000.0:
            self.report.add(AuditResult(
                name="RT-001: Account state updates",
                passed=False,
                message="account_state.balance stuck at initial $1000 - update_account_state() never called",
                severity="error",
                bug_id="RT-001"
            ))
        elif db_balance is not None:
            self.report.add(AuditResult(
                name="RT-001: Account state updates",
                passed=True,
                message=f"Account balance: ${db_balance:.2f}"
            ))

        # RT-002: open_trades/closed_trades tables empty
        open_count = self._db_data.get("open_trades_count", 0)
        closed_count = self._db_data.get("closed_trades_count", 0)
        journal_count = self._db_data.get("journal_total", 0)

        if open_count == 0 and closed_count == 0 and journal_count > 0:
            self.report.add(AuditResult(
                name="RT-002: Trade tables populated",
                passed=False,
                message=f"open_trades/closed_trades empty (0 rows) but trade_journal has {journal_count} entries",
                severity="warning",
                bug_id="RT-002"
            ))
        else:
            self.report.add(AuditResult(
                name="RT-002: Trade tables populated",
                passed=True,
                message=f"open_trades={open_count}, closed_trades={closed_count}"
            ))

    def _check_cross_layer_consistency(self):
        """Check data consistency across storage layers."""
        # Compare JSON vs Database balance
        db_balance = self._db_data.get("account_balance")
        json_balance = self._json_data.get("balance")

        if db_balance is not None and json_balance is not None:
            if abs(db_balance - json_balance) > 0.01:
                self.report.add(AuditResult(
                    name="RT-003: Balance consistency (DB vs JSON)",
                    passed=False,
                    message=f"Mismatch: DB=${db_balance:.2f}, JSON=${json_balance:.2f}",
                    severity="error",
                    bug_id="RT-003"
                ))
            else:
                self.report.add(AuditResult(
                    name="RT-003: Balance consistency (DB vs JSON)",
                    passed=True,
                    message=f"Both show ${json_balance:.2f}"
                ))

        # Compare JSON vs API (if available)
        if self._api_data.get("balance") and json_balance:
            api_balance = self._api_data["balance"]
            if abs(api_balance - json_balance) > 0.01:
                self.report.add(AuditResult(
                    name="RT-004: Balance consistency (JSON vs API)",
                    passed=False,
                    message=f"Mismatch: JSON=${json_balance:.2f}, API=${api_balance:.2f}",
                    severity="warning",
                    bug_id="RT-004"
                ))

        # Check P&L consistency
        db_pnl = self._db_data.get("journal_pnl", 0)
        json_pnl = self._json_data.get("total_pnl", 0)

        if abs(db_pnl - json_pnl) > 1.0:
            self.report.add(AuditResult(
                name="Total P&L consistency",
                passed=False,
                message=f"Mismatch: DB=${db_pnl:.2f}, JSON=${json_pnl:.2f}",
                severity="warning"
            ))

    def _check_data_flow(self):
        """Verify data flows are working."""
        # Check trade journal is being written
        journal_count = self._db_data.get("journal_total", 0)
        if journal_count > 0:
            self.report.add(AuditResult(
                name="Trade journal writes",
                passed=True,
                message=f"{journal_count} trades recorded"
            ))
        else:
            self.report.add(AuditResult(
                name="Trade journal writes",
                passed=False,
                message="No trades in journal",
                severity="warning"
            ))

        # Check activity log is being written
        activity_count = self._db_data.get("activity_count", 0)
        if activity_count > 0:
            self.report.add(AuditResult(
                name="Activity log writes",
                passed=True,
                message=f"{activity_count} activities logged"
            ))

        # Check adaptations are being recorded
        adaptation_count = self._db_data.get("adaptation_count", 0)
        if adaptation_count > 0:
            self.report.add(AuditResult(
                name="Adaptation recording",
                passed=True,
                message=f"{adaptation_count} adaptations recorded"
            ))


def main():
    parser = argparse.ArgumentParser(description="Runtime audit for crypto trading bot")
    parser.add_argument("--db", default="data/trading_bot.db", help="Database path")
    parser.add_argument("--state", default="data/sniper_state.json", help="State file path")
    parser.add_argument("--api", default=None, help="API URL (e.g., http://localhost:8000)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    auditor = RuntimeAuditor(args.db, args.state, args.api)
    report = auditor.run_all()

    if args.json:
        output = {
            "timestamp": report.timestamp.isoformat(),
            "summary": {
                "total": len(report.results),
                "passed": len(report.passed),
                "failed": len(report.failed),
                "warnings": len(report.warnings),
                "errors": len(report.errors)
            },
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "severity": r.severity,
                    "bug_id": r.bug_id
                }
                for r in report.results
            ]
        }
        print(json.dumps(output, indent=2))
    else:
        print(report.summary())

    # Exit code: 0 if no errors, 1 if errors
    sys.exit(0 if not report.errors else 1)


if __name__ == "__main__":
    main()
