"""Tests for rule creation from learnings (TASK-009).

Tests the RuleManager class which creates actionable trading rules
from high-confidence learnings.
"""

import os
import tempfile
import pytest

from src.database import Database
from src.learning_system import (
    Learning, TradingRule, RuleManager,
    MIN_CONFIDENCE_FOR_RULE, RULE_TEST_TRADES,
    RULE_PROMOTE_THRESHOLD, RULE_REJECT_THRESHOLD
)


class TestTradingRule:
    """Test TradingRule dataclass."""

    def test_rule_creation(self):
        """Test creating a TradingRule."""
        rule = TradingRule(
            id=1,
            rule_text="When 24h change > 5%, BUY",
            source_learning_id=1,
            source_pattern="momentum trading",
            trigger_condition="high momentum",
            expected_action="BUY",
            status="testing",
            success_count=0,
            failure_count=0
        )
        assert rule.id == 1
        assert rule.rule_text == "When 24h change > 5%, BUY"
        assert rule.status == "testing"

    def test_success_rate_zero_trades(self):
        """Test success rate with no trades."""
        rule = TradingRule(
            id=1, rule_text="Test", source_learning_id=1,
            source_pattern="", trigger_condition="",
            expected_action="HOLD", status="testing",
            success_count=0, failure_count=0
        )
        assert rule.success_rate() == 0.0

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        rule = TradingRule(
            id=1, rule_text="Test", source_learning_id=1,
            source_pattern="", trigger_condition="",
            expected_action="HOLD", status="testing",
            success_count=7, failure_count=3
        )
        assert rule.success_rate() == 0.7

    def test_total_trades(self):
        """Test total trades calculation."""
        rule = TradingRule(
            id=1, rule_text="Test", source_learning_id=1,
            source_pattern="", trigger_condition="",
            expected_action="HOLD", status="testing",
            success_count=5, failure_count=5
        )
        assert rule.total_trades() == 10

    def test_to_dict(self):
        """Test conversion to dict."""
        rule = TradingRule(
            id=1, rule_text="Test rule", source_learning_id=1,
            source_pattern="pattern", trigger_condition="trigger",
            expected_action="BUY", status="active",
            success_count=8, failure_count=2
        )
        d = rule.to_dict()
        assert d['id'] == 1
        assert d['rule_text'] == "Test rule"
        assert d['status'] == "active"

    def test_to_text(self):
        """Test conversion to readable text."""
        rule = TradingRule(
            id=1, rule_text="When momentum > 5%, BUY", source_learning_id=1,
            source_pattern="", trigger_condition="",
            expected_action="BUY", status="active",
            success_count=7, failure_count=3
        )
        text = rule.to_text()
        assert "[ACTIVE]" in text
        assert "When momentum > 5%, BUY" in text
        assert "70%" in text


class TestRuleManager:
    """Test RuleManager functionality."""

    def setup_method(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rules.db")
        self.db = Database(db_path=self.db_path)
        self.rm = RuleManager(db=self.db, llm=None)

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_init_default(self):
        """Test default initialization."""
        rm = RuleManager(db=self.db)
        assert rm.db is not None
        assert rm.min_confidence == MIN_CONFIDENCE_FOR_RULE

    def test_skip_low_confidence_learning(self):
        """Test that low confidence learnings are skipped."""
        learning = Learning(
            id=1, trade_id=1,
            what_happened="Test trade",
            why_outcome="Testing",
            pattern="test pattern",
            lesson="Test lesson",
            confidence=0.5  # Below MIN_CONFIDENCE_FOR_RULE (0.7)
        )

        result = self.rm.create_rule_from_learning(learning)
        assert result is None

    def test_skip_without_llm(self):
        """Test that rule creation fails without LLM."""
        learning = Learning(
            id=1, trade_id=1,
            what_happened="Test trade",
            why_outcome="Testing",
            pattern="test pattern",
            lesson="Test lesson",
            confidence=0.9  # High enough
        )

        # RuleManager has no LLM
        result = self.rm.create_rule_from_learning(learning)
        assert result is None

    def test_get_active_rules_empty(self):
        """Test getting active rules when none exist."""
        rules = self.rm.get_active_rules()
        assert rules == []

    def test_get_testing_rules_empty(self):
        """Test getting testing rules when none exist."""
        rules = self.rm.get_testing_rules()
        assert rules == []

    def test_get_all_rules_empty(self):
        """Test getting all rules when none exist."""
        rules = self.rm.get_all_rules()
        assert rules == []


class TestRuleRecordOutcome:
    """Test recording outcomes for rules."""

    def setup_method(self):
        """Create a temporary database with a test rule."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rules.db")
        self.db = Database(db_path=self.db_path)
        self.rm = RuleManager(db=self.db, llm=None)

        # Insert a test rule directly
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trading_rules (
                    rule_text, rule_type, status,
                    success_count, failure_count, created_at
                ) VALUES (
                    'When momentum > 5%, BUY',
                    'high momentum',
                    'testing',
                    0, 0,
                    datetime('now')
                )
            """)
            self.rule_id = cursor.lastrowid
            conn.commit()

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_record_success(self):
        """Test recording a successful trade."""
        self.rm.record_rule_outcome(self.rule_id, success=True)

        rules = self.rm.get_testing_rules()
        assert len(rules) == 1
        assert rules[0].success_count == 1
        assert rules[0].failure_count == 0

    def test_record_failure(self):
        """Test recording a failed trade."""
        self.rm.record_rule_outcome(self.rule_id, success=False)

        rules = self.rm.get_testing_rules()
        assert len(rules) == 1
        assert rules[0].success_count == 0
        assert rules[0].failure_count == 1

    def test_record_multiple_outcomes(self):
        """Test recording multiple outcomes."""
        for _ in range(3):
            self.rm.record_rule_outcome(self.rule_id, success=True)
        for _ in range(2):
            self.rm.record_rule_outcome(self.rule_id, success=False)

        rules = self.rm.get_testing_rules()
        assert len(rules) == 1
        assert rules[0].success_count == 3
        assert rules[0].failure_count == 2
        assert rules[0].success_rate() == 0.6


class TestRuleEvaluation:
    """Test rule promotion/rejection logic."""

    def setup_method(self):
        """Create a temporary database with a test rule."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rules.db")
        self.db = Database(db_path=self.db_path)
        self.rm = RuleManager(db=self.db, llm=None)

        # Insert a test rule
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trading_rules (
                    rule_text, rule_type, status,
                    success_count, failure_count, created_at
                ) VALUES (
                    'When momentum > 5%, BUY',
                    'high momentum',
                    'testing',
                    0, 0,
                    datetime('now')
                )
            """)
            self.rule_id = cursor.lastrowid
            conn.commit()

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_no_evaluation_below_threshold(self):
        """Test that rules aren't evaluated until enough trades."""
        # Record 5 trades (below RULE_TEST_TRADES = 10)
        for _ in range(5):
            self.rm.record_rule_outcome(self.rule_id, success=True)

        rules = self.rm.get_testing_rules()
        assert len(rules) == 1
        assert rules[0].status == 'testing'

    def test_promote_to_active(self):
        """Test rule promotion to active status."""
        # Record 7 successes, 3 failures = 70% success rate
        for _ in range(7):
            self.rm.record_rule_outcome(self.rule_id, success=True)
        for _ in range(3):
            self.rm.record_rule_outcome(self.rule_id, success=False)

        # After 10 trades, rule should be evaluated and promoted
        active_rules = self.rm.get_active_rules()
        assert len(active_rules) == 1
        assert active_rules[0].id == self.rule_id
        assert active_rules[0].status == 'active'

    def test_reject_rule(self):
        """Test rule rejection."""
        # Record 3 successes, 7 failures = 30% success rate
        for _ in range(3):
            self.rm.record_rule_outcome(self.rule_id, success=True)
        for _ in range(7):
            self.rm.record_rule_outcome(self.rule_id, success=False)

        # After 10 trades, rule should be rejected
        testing_rules = self.rm.get_testing_rules()
        active_rules = self.rm.get_active_rules()

        assert len(testing_rules) == 0
        assert len(active_rules) == 0

        # Check it's in rejected status
        all_rules = self.rm.get_all_rules()
        assert len(all_rules) == 1
        assert all_rules[0].status == 'rejected'

    def test_continue_testing_in_middle(self):
        """Test that rules in middle range continue testing."""
        # Record 5 successes, 5 failures = 50% (between 40% and 60%)
        for _ in range(5):
            self.rm.record_rule_outcome(self.rule_id, success=True)
        for _ in range(5):
            self.rm.record_rule_outcome(self.rule_id, success=False)

        # Rule should still be in testing
        testing_rules = self.rm.get_testing_rules()
        assert len(testing_rules) == 1
        assert testing_rules[0].status == 'testing'


class TestRuleSummary:
    """Test rule summary statistics."""

    def setup_method(self):
        """Create a temporary database with various rules."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_rules.db")
        self.db = Database(db_path=self.db_path)
        self.rm = RuleManager(db=self.db, llm=None)

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_empty_summary(self):
        """Test summary with no rules."""
        summary = self.rm.get_rule_summary()
        assert summary['total_rules'] == 0
        assert summary['active_rules'] == 0
        assert summary['testing_rules'] == 0
        assert summary['rejected_rules'] == 0

    def test_summary_with_rules(self):
        """Test summary with various rules."""
        # Insert rules with different statuses
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trading_rules (rule_text, rule_type, status, success_count, failure_count, created_at)
                VALUES ('Rule 1', 'pattern', 'active', 8, 2, datetime('now'))
            """)
            cursor.execute("""
                INSERT INTO trading_rules (rule_text, rule_type, status, success_count, failure_count, created_at)
                VALUES ('Rule 2', 'pattern', 'testing', 3, 2, datetime('now'))
            """)
            cursor.execute("""
                INSERT INTO trading_rules (rule_text, rule_type, status, success_count, failure_count, created_at)
                VALUES ('Rule 3', 'pattern', 'rejected', 2, 8, datetime('now'))
            """)
            conn.commit()

        summary = self.rm.get_rule_summary()
        assert summary['total_rules'] == 3
        assert summary['active_rules'] == 1
        assert summary['testing_rules'] == 1
        assert summary['rejected_rules'] == 1


class TestConfigurableThresholds:
    """Test that thresholds are configurable."""

    def test_default_thresholds(self):
        """Verify default threshold values."""
        assert MIN_CONFIDENCE_FOR_RULE == 0.7
        assert RULE_TEST_TRADES == 10
        assert RULE_PROMOTE_THRESHOLD == 0.6
        assert RULE_REJECT_THRESHOLD == 0.4


def test_rule_manager_import():
    """Test that RuleManager can be imported."""
    from src.learning_system import RuleManager, TradingRule
    assert RuleManager is not None
    assert TradingRule is not None
