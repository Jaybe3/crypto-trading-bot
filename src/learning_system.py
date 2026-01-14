"""Trade analysis and learning creation.

This is the CORE of the self-learning system. After each trade closes,
the LLM analyzes the outcome and creates learnings that improve future decisions.

The learning loop:
1. Trade closes (win or loss)
2. LLM analyzes what happened and why
3. Learning is extracted and stored
4. Future decisions are informed by accumulated learnings
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.database import Database
from src.llm_interface import LLMInterface

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Learning:
    """A learning extracted from a trade analysis."""
    id: Optional[int]
    trade_id: int
    what_happened: str
    why_outcome: str
    pattern: str
    lesson: str
    confidence: float
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'trade_id': self.trade_id,
            'what_happened': self.what_happened,
            'why_outcome': self.why_outcome,
            'pattern': self.pattern,
            'lesson': self.lesson,
            'confidence': self.confidence,
            'created_at': self.created_at
        }

    def to_text(self) -> str:
        """Convert to readable text for LLM context."""
        return f"[Confidence: {self.confidence:.0%}] {self.lesson}"


class LearningSystem:
    """Analyzes trades and creates learnings.

    This is the HEART of the self-learning trading bot. Every closed trade
    is an opportunity to learn and improve.

    The system:
    1. Takes a closed trade
    2. Sends details to LLM for analysis
    3. Extracts structured learning
    4. Stores in database for future reference
    """

    def __init__(self, db: Database = None, llm: LLMInterface = None):
        """Initialize the learning system.

        Args:
            db: Database instance. Creates new one if not provided.
            llm: LLMInterface instance. Creates new one if not provided.
        """
        self.db = db or Database()
        self.llm = llm  # Can be None if LLM unavailable
        logger.info("LearningSystem initialized")

    def get_closed_trade(self, trade_id: int) -> Optional[Dict[str, Any]]:
        """Get a closed trade by ID.

        Args:
            trade_id: The trade ID to look up.

        Returns:
            Trade dictionary or None if not found.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, coin_name, entry_price, exit_price, size_usd,
                       pnl_usd, pnl_pct, entry_reason, exit_reason,
                       opened_at, closed_at, duration_seconds
                FROM closed_trades
                WHERE id = ?
            """, (trade_id,))

            row = cursor.fetchone()
            if row is None:
                return None

            columns = ['id', 'coin_name', 'entry_price', 'exit_price', 'size_usd',
                      'pnl_usd', 'pnl_pct', 'entry_reason', 'exit_reason',
                      'opened_at', 'closed_at', 'duration_seconds']

            return dict(zip(columns, row))

    def get_market_context(self, coin: str) -> Dict[str, Any]:
        """Get current market context for a coin.

        Args:
            coin: Cryptocurrency name.

        Returns:
            Dict with market data context.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT price_usd, change_24h, last_updated
                FROM market_data
                WHERE coin = ?
            """, (coin,))

            row = cursor.fetchone()
            if row:
                return {
                    'current_price': row[0],
                    'change_24h': row[1] or 0,
                    'last_updated': row[2]
                }
            return {}

    def build_analysis_prompt(self, trade: Dict[str, Any]) -> str:
        """Build the prompt for trade analysis.

        Args:
            trade: Trade dictionary with all details.

        Returns:
            Formatted prompt string.
        """
        # Get market context
        market = self.get_market_context(trade['coin_name'])

        pnl_status = "PROFIT" if trade['pnl_usd'] >= 0 else "LOSS"
        duration_mins = trade.get('duration_seconds', 0) / 60

        prompt = f"""You are analyzing a completed cryptocurrency trade to learn from the outcome.

=== TRADE DETAILS ===
Coin: {trade['coin_name'].upper()}
Entry Price: ${trade['entry_price']:,.2f}
Exit Price: ${trade['exit_price']:,.2f}
Position Size: ${trade['size_usd']:,.2f}
Result: {pnl_status}
P&L: ${trade['pnl_usd']:+,.2f} ({trade['pnl_pct']:+.2f}%)
Entry Reason: {trade.get('entry_reason', 'Not specified')}
Exit Reason: {trade.get('exit_reason', 'Not specified')}
Duration: {duration_mins:.1f} minutes

=== MARKET CONTEXT ===
Current Price: ${market.get('current_price', 0):,.2f}
24h Change: {market.get('change_24h', 0):+.2f}%

=== YOUR TASK ===
Analyze this trade and provide insights that can improve future trading decisions.
Focus on patterns that could help identify similar opportunities or avoid similar mistakes.

Respond in JSON format:
{{
  "what_happened": "Brief factual description of what occurred in this trade",
  "why_outcome": "Analysis of WHY the trade succeeded or failed",
  "pattern": "Any pattern you observe (e.g., 'entered during high momentum', 'stop loss too tight')",
  "lesson": "A specific, actionable lesson for future trades (be concrete, not vague)",
  "confidence": 0.0 to 1.0 (how confident you are in this lesson being repeatable)
}}

Be specific and actionable. Avoid vague statements like "be careful" or "do more research".
Good lessons are like: "When 24h change exceeds 5%, momentum trades have higher success rate"
"""
        return prompt

    def analyze_trade(self, trade_id: int) -> Optional[Learning]:
        """Analyze a closed trade and create a learning.

        This is the CORE function of the learning system.

        Args:
            trade_id: ID of the closed trade to analyze.

        Returns:
            Learning object if successful, None if failed.
        """
        logger.info(f"Analyzing trade #{trade_id}...")

        # Check if LLM is available
        if self.llm is None:
            logger.warning("LLM not available - cannot analyze trade")
            self.db.log_activity(
                "learning_skipped",
                f"Trade #{trade_id} not analyzed - LLM unavailable"
            )
            return None

        # Get trade details
        trade = self.get_closed_trade(trade_id)
        if trade is None:
            logger.error(f"Trade #{trade_id} not found in closed_trades")
            return None

        # Check if already analyzed
        existing = self.get_learning_for_trade(trade_id)
        if existing:
            logger.info(f"Trade #{trade_id} already has a learning")
            return existing

        # Build prompt and query LLM
        prompt = self.build_analysis_prompt(trade)

        system_prompt = """You are an expert cryptocurrency trading analyst.
Your job is to analyze completed trades and extract actionable learnings.
Always respond with valid JSON. Be specific and concrete in your analysis."""

        logger.info(f"Querying LLM for trade #{trade_id} analysis...")
        result = self.llm.query_json(prompt, system_prompt)

        if result is None:
            logger.error(f"Failed to get LLM analysis for trade #{trade_id}")
            self.db.log_activity(
                "learning_failed",
                f"LLM analysis failed for trade #{trade_id}"
            )
            return None

        # Validate response
        required_fields = ['what_happened', 'why_outcome', 'pattern', 'lesson', 'confidence']
        for field in required_fields:
            if field not in result:
                logger.error(f"LLM response missing field: {field}")
                return None

        # Store learning in database
        learning_text = json.dumps(result)
        confidence = float(result.get('confidence', 0.5))

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO learnings (
                    trade_id, learning_text, pattern_observed, confidence_level, created_at
                ) VALUES (?, ?, ?, ?, datetime('now'))
            """, (trade_id, learning_text, result.get('pattern', ''), confidence))

            learning_id = cursor.lastrowid
            conn.commit()

        # Log the learning creation
        self.db.log_activity(
            "learning_created",
            f"Trade #{trade_id}: {result['lesson'][:100]}...",
            f"confidence={confidence:.2f}, pattern={result.get('pattern', '')[:50]}"
        )

        logger.info(f"Learning #{learning_id} created for trade #{trade_id}")
        logger.info(f"Lesson: {result['lesson']}")

        return Learning(
            id=learning_id,
            trade_id=trade_id,
            what_happened=result['what_happened'],
            why_outcome=result['why_outcome'],
            pattern=result['pattern'],
            lesson=result['lesson'],
            confidence=confidence
        )

    def get_learning_for_trade(self, trade_id: int) -> Optional[Learning]:
        """Get existing learning for a trade.

        Args:
            trade_id: The trade ID to look up.

        Returns:
            Learning object or None if not found.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, trade_id, learning_text, confidence_level, created_at
                FROM learnings
                WHERE trade_id = ?
            """, (trade_id,))

            row = cursor.fetchone()
            if row is None:
                return None

            # Parse learning text
            try:
                data = json.loads(row[2])
            except json.JSONDecodeError:
                data = {'lesson': row[2]}

            return Learning(
                id=row[0],
                trade_id=row[1],
                what_happened=data.get('what_happened', ''),
                why_outcome=data.get('why_outcome', ''),
                pattern=data.get('pattern', ''),
                lesson=data.get('lesson', ''),
                confidence=row[3],
                created_at=row[4]
            )

    def get_learnings_for_decision(self, limit: int = 10) -> List[Learning]:
        """Get recent high-confidence learnings to inform decisions.

        Returns learnings sorted by confidence (highest first).

        Args:
            limit: Maximum number of learnings to return.

        Returns:
            List of Learning objects.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, trade_id, learning_text, confidence_level, created_at
                FROM learnings
                WHERE confidence_level >= 0.5
                ORDER BY confidence_level DESC, created_at DESC
                LIMIT ?
            """, (limit,))

            learnings = []
            for row in cursor.fetchall():
                try:
                    data = json.loads(row[2])
                except json.JSONDecodeError:
                    data = {'lesson': row[2]}

                learnings.append(Learning(
                    id=row[0],
                    trade_id=row[1],
                    what_happened=data.get('what_happened', ''),
                    why_outcome=data.get('why_outcome', ''),
                    pattern=data.get('pattern', ''),
                    lesson=data.get('lesson', ''),
                    confidence=row[3],
                    created_at=row[4]
                ))

            return learnings

    def get_learnings_by_coin(self, coin: str) -> List[Learning]:
        """Get learnings related to a specific coin.

        Args:
            coin: Cryptocurrency name.

        Returns:
            List of Learning objects for that coin.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, l.trade_id, l.learning_text, l.confidence_level, l.created_at
                FROM learnings l
                JOIN closed_trades c ON l.trade_id = c.id
                WHERE c.coin_name = ?
                ORDER BY l.confidence_level DESC
            """, (coin,))

            learnings = []
            for row in cursor.fetchall():
                try:
                    data = json.loads(row[2])
                except json.JSONDecodeError:
                    data = {'lesson': row[2]}

                learnings.append(Learning(
                    id=row[0],
                    trade_id=row[1],
                    what_happened=data.get('what_happened', ''),
                    why_outcome=data.get('why_outcome', ''),
                    pattern=data.get('pattern', ''),
                    lesson=data.get('lesson', ''),
                    confidence=row[3],
                    created_at=row[4]
                ))

            return learnings

    def get_all_learnings(self, limit: int = 50) -> List[Learning]:
        """Get all learnings for review.

        Args:
            limit: Maximum number of learnings to return.

        Returns:
            List of Learning objects.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, trade_id, learning_text, confidence_level, created_at
                FROM learnings
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

            learnings = []
            for row in cursor.fetchall():
                try:
                    data = json.loads(row[2])
                except json.JSONDecodeError:
                    data = {'lesson': row[2]}

                learnings.append(Learning(
                    id=row[0],
                    trade_id=row[1],
                    what_happened=data.get('what_happened', ''),
                    why_outcome=data.get('why_outcome', ''),
                    pattern=data.get('pattern', ''),
                    lesson=data.get('lesson', ''),
                    confidence=row[3],
                    created_at=row[4]
                ))

            return learnings

    def get_unanalyzed_trades(self) -> List[int]:
        """Get trade IDs that haven't been analyzed yet.

        Returns:
            List of trade IDs without learnings.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.id
                FROM closed_trades c
                LEFT JOIN learnings l ON c.id = l.trade_id
                WHERE l.id IS NULL
                ORDER BY c.closed_at DESC
            """)

            return [row[0] for row in cursor.fetchall()]

    def analyze_all_pending(self) -> List[Learning]:
        """Analyze all closed trades that haven't been analyzed.

        Returns:
            List of newly created Learning objects.
        """
        pending = self.get_unanalyzed_trades()
        logger.info(f"Found {len(pending)} unanalyzed trades")

        learnings = []
        for trade_id in pending:
            learning = self.analyze_trade(trade_id)
            if learning:
                learnings.append(learning)

        return learnings

    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary statistics about learnings.

        Returns:
            Dict with learning statistics.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Total learnings
            cursor.execute("SELECT COUNT(*) FROM learnings")
            total = cursor.fetchone()[0]

            # Average confidence
            cursor.execute("SELECT AVG(confidence_level) FROM learnings")
            avg_confidence = cursor.fetchone()[0] or 0

            # High confidence learnings
            cursor.execute("SELECT COUNT(*) FROM learnings WHERE confidence_level >= 0.7")
            high_confidence = cursor.fetchone()[0]

            # Unanalyzed trades
            unanalyzed = len(self.get_unanalyzed_trades())

            return {
                'total_learnings': total,
                'average_confidence': avg_confidence,
                'high_confidence_count': high_confidence,
                'unanalyzed_trades': unanalyzed
            }


def get_learnings_as_text(db: Database = None, limit: int = 10) -> List[str]:
    """Get learnings formatted as text for LLM context.

    This is a convenience function for the trading decision prompt.

    Args:
        db: Database instance.
        limit: Maximum number of learnings.

    Returns:
        List of learning text strings.
    """
    ls = LearningSystem(db=db, llm=None)
    learnings = ls.get_learnings_for_decision(limit=limit)
    return [l.to_text() for l in learnings]


# =============================================================================
# RULE CREATION FROM PATTERNS
# =============================================================================

# Rule creation configuration - adjustable thresholds
MIN_CONFIDENCE_FOR_RULE = 0.7  # Minimum learning confidence to create a rule
RULE_TEST_TRADES = 10          # Number of trades before evaluating rule
RULE_PROMOTE_THRESHOLD = 0.6   # Success rate to promote to active
RULE_REJECT_THRESHOLD = 0.4    # Success rate to reject rule


@dataclass
class TradingRule:
    """A trading rule created from a high-confidence learning."""
    id: Optional[int]
    rule_text: str              # The actionable rule
    source_learning_id: int     # Which learning created this (traceability)
    source_pattern: str         # The pattern it's based on
    trigger_condition: str      # When the rule applies
    expected_action: str        # BUY/SELL/HOLD/WAIT
    status: str                 # "testing", "active", "rejected"
    success_count: int
    failure_count: int
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'rule_text': self.rule_text,
            'source_learning_id': self.source_learning_id,
            'source_pattern': self.source_pattern,
            'trigger_condition': self.trigger_condition,
            'expected_action': self.expected_action,
            'status': self.status,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'created_at': self.created_at
        }

    def success_rate(self) -> float:
        """Calculate current success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total

    def total_trades(self) -> int:
        """Get total trades using this rule."""
        return self.success_count + self.failure_count

    def to_text(self) -> str:
        """Convert to readable text for LLM context."""
        rate = self.success_rate()
        return f"[{self.status.upper()}] {self.rule_text} (Success: {rate:.0%})"


class RuleManager:
    """Creates and manages trading rules from learnings.

    Rules are the second layer of intelligence:
    1. Learnings are insights from individual trades
    2. Rules are actionable guidelines created from strong patterns

    Rule Lifecycle:
    - Created from high-confidence learning (confidence >= 0.7)
    - Status: "testing" - being validated over multiple trades
    - After 10 trades: promoted to "active" (>=60%) or "rejected" (<40%)
    """

    def __init__(self, db: Database = None, llm: LLMInterface = None):
        """Initialize rule manager.

        Args:
            db: Database instance.
            llm: LLMInterface for rule formulation.
        """
        self.db = db or Database()
        self.llm = llm
        self.min_confidence = MIN_CONFIDENCE_FOR_RULE
        logger.info(f"RuleManager initialized (min_confidence={self.min_confidence})")

    def create_rule_from_learning(self, learning: Learning) -> Optional[TradingRule]:
        """Create a trading rule from a high-confidence learning.

        Args:
            learning: The learning to convert to a rule.

        Returns:
            TradingRule if created, None if skipped or failed.
        """
        # Check confidence threshold
        if learning.confidence < self.min_confidence:
            logger.info(f"Learning #{learning.id} confidence {learning.confidence:.0%} below threshold {self.min_confidence:.0%}")
            return None

        # Check if similar rule already exists
        if self._rule_exists_for_learning(learning.id):
            logger.info(f"Rule already exists for learning #{learning.id}")
            return None

        # Check if LLM available
        if self.llm is None:
            logger.warning("LLM not available - cannot create rule")
            return None

        logger.info(f"Creating rule from learning #{learning.id} (confidence: {learning.confidence:.0%})")

        # Ask LLM to formulate actionable rule
        rule_data = self._formulate_rule(learning)
        if rule_data is None:
            logger.error("Failed to formulate rule from learning")
            return None

        # Store in database
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trading_rules (
                    rule_text, rule_type, status,
                    success_count, failure_count, created_at
                ) VALUES (?, ?, 'testing', 0, 0, datetime('now'))
            """, (rule_data['rule_text'], learning.pattern or 'learned'))

            rule_id = cursor.lastrowid
            conn.commit()

        # Log creation
        self.db.log_activity(
            "rule_created",
            f"Rule #{rule_id} from learning #{learning.id}: {rule_data['rule_text'][:80]}...",
            f"trigger={rule_data.get('trigger_condition', '')[:50]}"
        )

        logger.info(f"Rule #{rule_id} created: {rule_data['rule_text'][:60]}...")

        return TradingRule(
            id=rule_id,
            rule_text=rule_data['rule_text'],
            source_learning_id=learning.id,
            source_pattern=learning.pattern,
            trigger_condition=rule_data.get('trigger_condition', ''),
            expected_action=rule_data.get('expected_action', 'HOLD'),
            status='testing',
            success_count=0,
            failure_count=0
        )

    def _formulate_rule(self, learning: Learning) -> Optional[Dict[str, Any]]:
        """Ask LLM to formulate an actionable rule from a learning.

        Args:
            learning: The learning to convert.

        Returns:
            Dict with rule_text, trigger_condition, expected_action.
        """
        prompt = f"""You are converting a trading lesson into an actionable rule.

LESSON: {learning.lesson}
PATTERN: {learning.pattern}
WHY IT HAPPENED: {learning.why_outcome}
CONFIDENCE: {learning.confidence:.0%}

Create a specific, actionable trading rule based on this lesson.
The rule should be in the format: "When [CONDITION], then [ACTION]"

Examples of good rules:
- "When 24h change > 5% and momentum is positive, BUY with increased position size"
- "When price drops 3% within 1 hour, WAIT for stabilization before buying"
- "When a coin hits take profit, avoid re-entering for at least 30 minutes"
- "When market volatility is low, use tighter stop losses"

Respond in JSON format:
{{
  "rule_text": "When [specific condition], then [specific action]",
  "trigger_condition": "Brief description of when this rule applies",
  "expected_action": "BUY or SELL or HOLD or WAIT",
  "confidence": 0.0 to 1.0
}}

Be specific and actionable. The rule must be clear enough to automate."""

        system_prompt = """You are an expert trading strategist.
Convert lessons into actionable trading rules.
Rules must be specific, measurable, and automatable.
Always respond with valid JSON."""

        result = self.llm.query_json(prompt, system_prompt)

        if result and 'rule_text' in result:
            return result
        return None

    def _rule_exists_for_learning(self, learning_id: int) -> bool:
        """Check if a rule was already created from this learning.

        Note: We track by pattern similarity since we don't store learning_id
        in the current schema. This prevents duplicate rules.
        """
        # For now, check by looking at recent rules
        # In a full implementation, we'd add source_learning_id to the schema
        return False  # Allow rule creation for now

    def get_active_rules(self) -> List[TradingRule]:
        """Get all active rules for trading decisions.

        Returns:
            List of active TradingRule objects.
        """
        return self._get_rules_by_status('active')

    def get_testing_rules(self) -> List[TradingRule]:
        """Get rules currently being tested.

        Returns:
            List of testing TradingRule objects.
        """
        return self._get_rules_by_status('testing')

    def get_all_rules(self) -> List[TradingRule]:
        """Get all rules regardless of status.

        Returns:
            List of all TradingRule objects.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, rule_text, rule_type, status,
                       success_count, failure_count, created_at
                FROM trading_rules
                ORDER BY created_at DESC
            """)

            rules = []
            for row in cursor.fetchall():
                rules.append(TradingRule(
                    id=row[0],
                    rule_text=row[1],
                    source_learning_id=0,  # Not stored in current schema
                    source_pattern=row[2] or '',
                    trigger_condition='',
                    expected_action='',
                    status=row[3],
                    success_count=row[4] or 0,
                    failure_count=row[5] or 0,
                    created_at=row[6]
                ))

            return rules

    def _get_rules_by_status(self, status: str) -> List[TradingRule]:
        """Get rules filtered by status.

        Args:
            status: Rule status to filter by.

        Returns:
            List of TradingRule objects.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, rule_text, rule_type, status,
                       success_count, failure_count, created_at
                FROM trading_rules
                WHERE status = ?
                ORDER BY success_count DESC
            """, (status,))

            rules = []
            for row in cursor.fetchall():
                rules.append(TradingRule(
                    id=row[0],
                    rule_text=row[1],
                    source_learning_id=0,
                    source_pattern=row[2] or '',
                    trigger_condition='',
                    expected_action='',
                    status=row[3],
                    success_count=row[4] or 0,
                    failure_count=row[5] or 0,
                    created_at=row[6]
                ))

            return rules

    def record_rule_outcome(self, rule_id: int, success: bool) -> None:
        """Record whether a trade using this rule succeeded or failed.

        This is called after EVERY trade that used a rule.

        Args:
            rule_id: The rule that was used.
            success: True if trade was profitable, False otherwise.
        """
        column = 'success_count' if success else 'failure_count'

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE trading_rules
                SET {column} = {column} + 1
                WHERE id = ?
            """, (rule_id,))
            conn.commit()

        outcome = "SUCCESS" if success else "FAILURE"
        logger.info(f"Rule #{rule_id} outcome recorded: {outcome}")

        # Immediately evaluate this rule
        self.evaluate_rule(rule_id)

    def evaluate_rule(self, rule_id: int) -> Optional[str]:
        """Evaluate a single rule and promote/reject if ready.

        Called after every trade for immediate feedback.

        Args:
            rule_id: The rule to evaluate.

        Returns:
            New status if changed, None if unchanged.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, success_count, failure_count
                FROM trading_rules
                WHERE id = ?
            """, (rule_id,))

            row = cursor.fetchone()
            if row is None:
                return None

            status, success, failure = row
            total = success + failure

            # Only evaluate rules in testing status with enough data
            if status != 'testing' or total < RULE_TEST_TRADES:
                return None

            success_rate = success / total

            # Determine new status
            if success_rate >= RULE_PROMOTE_THRESHOLD:
                new_status = 'active'
            elif success_rate < RULE_REJECT_THRESHOLD:
                new_status = 'rejected'
            else:
                return None  # Continue testing

            # Update status
            cursor.execute("""
                UPDATE trading_rules
                SET status = ?
                WHERE id = ?
            """, (new_status, rule_id))
            conn.commit()

            # Log the promotion/rejection
            self.db.log_activity(
                f"rule_{new_status}",
                f"Rule #{rule_id} {new_status.upper()} (success rate: {success_rate:.0%})",
                f"wins={success}, losses={failure}"
            )

            logger.info(f"Rule #{rule_id} status changed to {new_status} ({success_rate:.0%})")
            return new_status

    def evaluate_all_rules(self) -> List[Dict[str, Any]]:
        """Evaluate all testing rules.

        Returns:
            List of rules that changed status.
        """
        testing_rules = self.get_testing_rules()
        changes = []

        for rule in testing_rules:
            new_status = self.evaluate_rule(rule.id)
            if new_status:
                changes.append({
                    'rule_id': rule.id,
                    'old_status': 'testing',
                    'new_status': new_status,
                    'success_rate': rule.success_rate()
                })

        return changes

    def get_rule_summary(self) -> Dict[str, Any]:
        """Get summary statistics about rules.

        Returns:
            Dict with rule statistics.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Count by status
            cursor.execute("""
                SELECT status, COUNT(*)
                FROM trading_rules
                GROUP BY status
            """)
            status_counts = dict(cursor.fetchall())

            # Total rules
            total = sum(status_counts.values())

            # Average success rate of active rules
            cursor.execute("""
                SELECT AVG(CAST(success_count AS FLOAT) /
                           (success_count + failure_count + 0.001))
                FROM trading_rules
                WHERE status = 'active'
            """)
            avg_success = cursor.fetchone()[0] or 0

            return {
                'total_rules': total,
                'active_rules': status_counts.get('active', 0),
                'testing_rules': status_counts.get('testing', 0),
                'rejected_rules': status_counts.get('rejected', 0),
                'avg_active_success_rate': avg_success
            }


def get_rules_as_text(db: Database = None) -> List[str]:
    """Get active rules formatted as text for LLM context.

    Args:
        db: Database instance.

    Returns:
        List of rule text strings.
    """
    rm = RuleManager(db=db, llm=None)
    rules = rm.get_active_rules()
    return [r.to_text() for r in rules]
