"""
Strategist Component - LLM-powered trade condition generator.

The Strategist periodically analyzes market conditions and generates
TradeCondition objects for the Sniper to watch and execute.

Key responsibilities:
- Runs every 2-5 minutes (configurable)
- Reads market data from MarketFeed
- Reads knowledge from Knowledge Brain (when available)
- Uses qwen2.5:14b to generate specific trade conditions
- Outputs conditions for Sniper to execute
- Does NOT execute trades directly

Example:
    >>> strategist = Strategist(llm, market_feed)
    >>> strategist.subscribe_conditions(sniper.set_conditions)
    >>> await strategist.start()
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Callable, List, Optional, Dict, Any

from src.database import Database
from src.llm_interface import LLMInterface
from src.market_feed import MarketFeed
from src.models.trade_condition import TradeCondition

logger = logging.getLogger(__name__)


# Configuration defaults
DEFAULT_INTERVAL_SECONDS = 180  # 3 minutes
DEFAULT_CONDITION_TTL_MINUTES = 5
DEFAULT_MAX_CONDITIONS = 3
DEFAULT_MIN_POSITION_SIZE = 20.0
DEFAULT_MAX_POSITION_SIZE = 100.0


class Strategist:
    """LLM-powered strategy generator.

    Runs periodically to analyze market conditions and generate trade conditions
    for the Sniper to watch. Uses qwen2.5:14b for reasoning.

    Attributes:
        llm: LLM interface for generating conditions.
        market: MarketFeed for real-time prices.
        db: Database for logging conditions.
        interval: Seconds between strategy generations.
        active_conditions: Currently active trade conditions.
    """

    def __init__(
        self,
        llm: LLMInterface,
        market_feed: MarketFeed,
        knowledge: Optional[Any] = None,  # KnowledgeBrain when available
        coin_scorer: Optional[Any] = None,  # CoinScorer for position modifiers
        pattern_library: Optional[Any] = None,  # PatternLibrary for pattern context
        db: Optional[Database] = None,
        interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
        condition_ttl_minutes: int = DEFAULT_CONDITION_TTL_MINUTES,
        max_conditions: int = DEFAULT_MAX_CONDITIONS,
    ):
        """Initialize the Strategist.

        Args:
            llm: LLM interface for querying the model.
            market_feed: MarketFeed instance for price data.
            knowledge: Optional KnowledgeBrain for learned rules/patterns.
            coin_scorer: Optional CoinScorer for position modifiers and blacklist.
            pattern_library: Optional PatternLibrary for pattern context.
            db: Optional Database instance (creates new if not provided).
            interval_seconds: Seconds between condition generation (default: 180).
            condition_ttl_minutes: Minutes until conditions expire (default: 5).
            max_conditions: Maximum conditions per generation cycle (default: 3).
        """
        self.llm = llm
        self.market = market_feed
        self.knowledge = knowledge
        self.coin_scorer = coin_scorer  # TASK-121: for position modifiers and blacklist
        self.pattern_library = pattern_library  # TASK-122: for pattern context
        self.db = db or Database()
        self.interval = interval_seconds
        self.condition_ttl = condition_ttl_minutes
        self.max_conditions = max_conditions

        # State
        self.active_conditions: List[TradeCondition] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Callbacks
        self._condition_callbacks: List[Callable[[List[TradeCondition]], None]] = []

        # Stats
        self.generation_count = 0
        self.conditions_generated = 0
        self.last_generation_time: Optional[datetime] = None

        logger.info(
            f"Strategist initialized: interval={interval_seconds}s, "
            f"ttl={condition_ttl_minutes}min, max={max_conditions}"
        )

    def subscribe_conditions(
        self, callback: Callable[[List[TradeCondition]], None]
    ) -> None:
        """Register callback for when new conditions are generated.

        Args:
            callback: Function to call with new conditions list.
        """
        self._condition_callbacks.append(callback)
        logger.debug(f"Added condition callback, total: {len(self._condition_callbacks)}")

    def unsubscribe_conditions(
        self, callback: Callable[[List[TradeCondition]], None]
    ) -> None:
        """Remove a condition callback.

        Args:
            callback: Previously registered callback to remove.
        """
        if callback in self._condition_callbacks:
            self._condition_callbacks.remove(callback)

    async def start(self) -> None:
        """Start the periodic strategist loop."""
        if self._running:
            logger.warning("Strategist already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Strategist started, generating every {self.interval}s")

    async def stop(self) -> None:
        """Stop the strategist loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Strategist stopped")

    async def _run_loop(self) -> None:
        """Main loop that generates conditions periodically."""
        while self._running:
            try:
                # Generate new conditions
                conditions = await self.generate_conditions()

                # Notify callbacks
                self._notify_callbacks(conditions)

                # Wait for next cycle
                await asyncio.sleep(self.interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in strategist loop: {e}")
                # Wait before retrying on error
                await asyncio.sleep(30)

    async def generate_conditions(self) -> List[TradeCondition]:
        """Generate trade conditions based on current market state.

        Returns:
            List of TradeCondition objects for Sniper to watch.
        """
        logger.info("Generating trade conditions...")
        self.generation_count += 1

        # Clean up expired conditions first
        self._remove_expired_conditions()
        self.db.delete_expired_conditions()

        # TASK-123: Check regime rules first
        self._active_rule_actions = self._check_regime_rules()
        if "NO_TRADE" in self._active_rule_actions:
            logger.info("NO_TRADE regime rule triggered - skipping generation")
            self.db.log_activity(
                activity_type="strategist",
                description="Skipped generation due to NO_TRADE regime rule",
                details=json.dumps({"triggered_actions": self._active_rule_actions})
            )
            return []

        # Build context for LLM
        context = self._build_context()

        if not context.get("market_state", {}).get("prices"):
            logger.warning("No price data available, skipping generation")
            return []

        # Build and send prompt
        prompt = self._build_prompt(context)
        system_prompt = self._get_system_prompt()

        try:
            response = self.llm.query(prompt, system_prompt)

            if response is None:
                logger.error("LLM returned None response")
                return []

            # Parse response into conditions
            conditions = self._parse_response(response)

            # Validate and store conditions
            valid_conditions = []
            for condition in conditions[: self.max_conditions]:
                if self._validate_condition(condition):
                    valid_conditions.append(condition)
                    self.db.save_condition(condition.to_dict())

            # Update active conditions
            self.active_conditions = valid_conditions
            self.conditions_generated += len(valid_conditions)
            self.last_generation_time = datetime.now()

            logger.info(f"Generated {len(valid_conditions)} conditions")
            for c in valid_conditions:
                logger.info(f"  {c}")

            # Log activity
            self.db.log_activity(
                activity_type="strategist",
                description=f"Generated {len(valid_conditions)} conditions",
                details=json.dumps({
                    "conditions": [c.to_dict() for c in valid_conditions],
                    "context_summary": {
                        "coins_analyzed": len(context.get("market_state", {}).get("prices", {})),
                        "knowledge_rules": len(context.get("knowledge", {}).get("active_rules", [])),
                    }
                })
            )

            return valid_conditions

        except Exception as e:
            logger.error(f"Error generating conditions: {e}")
            self.db.log_activity(
                activity_type="error",
                description="Strategist generation failed",
                details=str(e)
            )
            return []

    def get_active_conditions(self) -> List[TradeCondition]:
        """Get currently active (non-expired) conditions.

        Returns:
            List of active TradeCondition objects.
        """
        self._remove_expired_conditions()
        return self.active_conditions.copy()

    def _build_context(self) -> Dict[str, Any]:
        """Build context dictionary for LLM prompt.

        Returns:
            Context dict with market state, knowledge, and account info.
        """
        # Get market data
        prices = self.market.get_all_prices()
        market_state = {
            "prices": {},
            "changes_24h": {},
        }

        for coin, tick in prices.items():
            market_state["prices"][coin] = tick.price
            market_state["changes_24h"][coin] = tick.change_24h

        # Get knowledge (simplified until Knowledge Brain is ready)
        knowledge = self._get_knowledge()

        # Get account state
        account = self.db.get_account_state()

        # Get recent performance
        recent_performance = self._get_recent_performance()

        return {
            "market_state": market_state,
            "knowledge": knowledge,
            "account": {
                "balance_usd": account.get("balance", 1000),
                "available_balance": account.get("available_balance", 1000),
                "open_positions": [],  # TODO: Get from Sniper
                "recent_pnl_24h": account.get("daily_pnl", 0),
            },
            "recent_performance": recent_performance,
        }

    def _get_knowledge(self) -> Dict[str, Any]:
        """Get comprehensive trading knowledge for prompt.

        Returns:
            Knowledge dict with full context for LLM.
        """
        if self.knowledge:
            # Get coin performance summaries
            coin_summaries = []
            for score in self.knowledge.get_all_coin_scores()[:10]:
                status = self._get_coin_status_label(score)
                summary = {
                    "coin": score.coin,
                    "status": status,
                    "trades": score.total_trades,
                    "win_rate": f"{score.win_rate:.0%}",
                    "pnl": f"${score.total_pnl:.2f}",
                    "trend": score.trend,
                }
                coin_summaries.append(summary)

            # Get active regime rules with descriptions
            active_rules = []
            for rule in self.knowledge.get_active_rules():
                active_rules.append({
                    "description": rule.description,
                    "action": rule.action,
                    "times_triggered": rule.times_triggered,
                })

            # Get bad coins (poor performers not yet blacklisted)
            bad_coins = self.knowledge.get_bad_coins()

            return {
                "good_coins": self.knowledge.get_good_coins(),
                "avoid_coins": self.knowledge.get_blacklisted_coins() + bad_coins,
                "blacklisted": self.knowledge.get_blacklisted_coins(),
                "coin_summaries": coin_summaries,
                "active_rules": active_rules,
                "winning_patterns": [p.description for p in self.knowledge.get_winning_patterns()],
                "blacklist_count": len(self.knowledge.get_blacklisted_coins()),
            }

        # Simplified fallback when no knowledge brain
        return {
            "good_coins": [],
            "avoid_coins": [],
            "blacklisted": [],
            "coin_summaries": [],
            "active_rules": [],
            "winning_patterns": [],
            "blacklist_count": 0,
        }

    def _get_coin_status_label(self, score) -> str:
        """Get human-readable status label for a coin score."""
        if score.is_blacklisted:
            return "BLACKLISTED"
        if score.total_trades < 5:
            return "NEW"
        if score.win_rate >= 0.60 and score.total_pnl > 0:
            return "FAVORED"
        if score.win_rate < 0.45:
            return "REDUCED"
        return "NORMAL"

    def _get_market_state_for_rules(self) -> Dict[str, Any]:
        """Build market state dict for regime rule checking.

        Returns:
            Dict with conditions that rules can check against.
        """
        state = {}

        # BTC trend and price
        btc_tick = self.market.get_price("BTC")
        if btc_tick:
            state["btc_price"] = btc_tick.price
            state["btc_change_24h"] = btc_tick.change_24h
            # Determine trend
            if btc_tick.change_24h > 2:
                state["btc_trend"] = "up"
            elif btc_tick.change_24h < -2:
                state["btc_trend"] = "down"
            else:
                state["btc_trend"] = "sideways"

        # Time of day
        now = datetime.now()
        state["hour_of_day"] = now.hour
        state["day_of_week"] = now.weekday()
        state["is_weekend"] = now.weekday() >= 5

        # Session
        if 0 <= now.hour < 8:
            state["session"] = "asia"
        elif 8 <= now.hour < 14:
            state["session"] = "europe"
        elif 14 <= now.hour < 21:
            state["session"] = "us"
        else:
            state["session"] = "late_us"

        return state

    def _check_regime_rules(self) -> List[str]:
        """Check regime rules and return triggered actions.

        Returns:
            List of actions from triggered rules (e.g., ["NO_TRADE", "REDUCE_SIZE"]).
        """
        if not self.knowledge:
            return []

        market_state = self._get_market_state_for_rules()
        actions = self.knowledge.check_rules(market_state)

        if actions:
            logger.info(f"Regime rules triggered: {actions}")

        return actions

    def _calculate_final_position_size(
        self,
        base_size: float,
        coin: str,
        pattern_id: Optional[str] = None
    ) -> float:
        """Calculate final position size with all modifiers.

        Combines:
        - Coin score modifier (0.0 - 1.5)
        - Pattern confidence modifier (0.75 - 1.25)
        - Regime rule modifier (0.5 for REDUCE_SIZE)

        Args:
            base_size: Base position size in USD.
            coin: Coin symbol.
            pattern_id: Optional pattern ID if using a known pattern.

        Returns:
            Final position size in USD.
        """
        size = base_size

        # 1. Coin score modifier
        if self.coin_scorer:
            coin_modifier = self.coin_scorer.get_position_modifier(coin)
            if coin_modifier == 0.0:
                return 0.0  # Blacklisted
            size *= coin_modifier
            if coin_modifier != 1.0:
                logger.debug(f"Coin modifier for {coin}: {coin_modifier}")

        # 2. Pattern confidence modifier
        if pattern_id and self.pattern_library:
            pattern_modifier = self.pattern_library.get_position_modifier(pattern_id)
            size *= pattern_modifier
            if pattern_modifier != 1.0:
                logger.debug(f"Pattern modifier for {pattern_id}: {pattern_modifier}")

        # 3. Regime rule modifier
        if hasattr(self, '_active_rule_actions') and self._active_rule_actions:
            if "REDUCE_SIZE" in self._active_rule_actions:
                size *= 0.5
                logger.debug("Regime REDUCE_SIZE modifier: 0.5")

        # Enforce limits
        size = max(DEFAULT_MIN_POSITION_SIZE, min(DEFAULT_MAX_POSITION_SIZE, size))

        return round(size, 2)

    def _get_recent_performance(self) -> Dict[str, Any]:
        """Get recent trading performance metrics.

        Returns:
            Performance dict with win rate and trade counts.
        """
        # TODO: Calculate from trade journal when available
        return {
            "win_rate_24h": 0.50,
            "total_trades_24h": 0,
            "streak": 0,
        }

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the Strategist.

        Returns:
            System prompt string.
        """
        return """You are the Strategist for an autonomous trading bot. Your job is to set up trade conditions for the Sniper to watch and execute.

IMPORTANT RULES:
1. Only suggest coins that are NOT in the avoid list
2. Position size MUST be between $20 and $100 (NEVER exceed $100)
3. Stop-loss should be 1-3%
4. Take-profit should be 1-2%
5. You can suggest 0-3 conditions (0 if no good setups)
6. Each condition must have a clear, specific trigger price
7. Only suggest LONG trades (we don't support SHORT yet)

CRITICAL - TRIGGER PRICE RULES:
- Conditions expire in 5 minutes, so trigger prices MUST be very close to current price
- For ABOVE triggers: set trigger_price 0.1-0.3% ABOVE current price (e.g., if BTC is $76000, trigger at $76076-$76228)
- For BELOW triggers: set trigger_price 0.1-0.3% BELOW current price
- DO NOT set triggers more than 0.5% from current price - they will expire before triggering
- The trigger price is where you WANT to enter, not a distant target

OUTPUT FORMAT:
You MUST respond with valid JSON in exactly this format:
{
    "conditions": [
        {
            "coin": "SOL",
            "direction": "LONG",
            "trigger_price": 143.50,
            "trigger_condition": "ABOVE",
            "stop_loss_pct": 2.0,
            "take_profit_pct": 1.5,
            "position_size_usd": 50,
            "reasoning": "Brief explanation of why this trade",
            "strategy_id": "pattern_name"
        }
    ],
    "market_assessment": "Brief assessment of overall market conditions",
    "no_trade_reason": null
}

If no good setups exist, return:
{
    "conditions": [],
    "market_assessment": "Brief assessment",
    "no_trade_reason": "Why no trades are suggested"
}

Think about:
- Which coins show momentum or clear patterns?
- Trigger price MUST be within 0.1-0.3% of current price (conditions expire in 5 min)
- What's an appropriate position size given confidence?
- What stop-loss protects against downside while giving room to work?"""

    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """Build the LLM prompt with context.

        Args:
            context: Context dictionary from _build_context().

        Returns:
            Formatted prompt string.
        """
        market = context["market_state"]
        knowledge = context["knowledge"]
        account = context["account"]
        performance = context["recent_performance"]

        # Format prices nicely
        price_lines = []
        for coin, price in sorted(market["prices"].items()):
            change = market["changes_24h"].get(coin, 0)
            direction = "+" if change >= 0 else ""
            price_lines.append(f"  {coin}: ${price:,.2f} ({direction}{change:.1f}%)")

        prices_text = "\n".join(price_lines) if price_lines else "  No price data"

        # Format coin performance summaries
        coin_summary_text = "  No history yet"
        if knowledge.get("coin_summaries"):
            lines = []
            for cs in knowledge["coin_summaries"][:5]:
                lines.append(
                    f"  {cs['coin']}: {cs['status']} | {cs['trades']} trades | "
                    f"{cs['win_rate']} win | {cs['pnl']} P&L | {cs['trend']}"
                )
            if lines:
                coin_summary_text = "\n".join(lines)

        # Format regime rules
        rules_text = "  None active"
        if knowledge.get("active_rules"):
            rules = knowledge["active_rules"]
            rules_text = "\n".join(
                f"  - {r['description']} -> {r['action']}" for r in rules
            )

        # Build pattern section if pattern library available
        pattern_section = ""
        if self.pattern_library:
            pattern_context = self.pattern_library.get_pattern_context()
            if pattern_context["high_confidence"]:
                high_patterns = [
                    f"  - {p.description} ({p.confidence:.0%} conf, {p.win_rate:.0%} win rate)"
                    for p in pattern_context["high_confidence"][:5]
                ]
                pattern_section = f"""
HIGH-CONFIDENCE PATTERNS (consider using these):
{chr(10).join(high_patterns)}
"""

        # Format winning patterns
        patterns_list = "None identified"
        if knowledge.get("winning_patterns"):
            patterns_list = ", ".join(knowledge["winning_patterns"][:5])

        return f"""CURRENT MARKET STATE:
{prices_text}

COIN PERFORMANCE (your track record):
{coin_summary_text}

COINS TO FAVOR: {', '.join(knowledge['good_coins']) or 'None identified'}
COINS TO AVOID: {', '.join(knowledge['avoid_coins']) or 'None blacklisted'}

ACTIVE REGIME RULES:
{rules_text}

WINNING PATTERNS: {patterns_list}
{pattern_section}
ACCOUNT STATE:
- Balance: ${account['balance_usd']:,.2f}
- Available: ${account['available_balance']:,.2f}
- 24h P&L: ${account['recent_pnl_24h']:,.2f}

RECENT PERFORMANCE:
- Win rate (24h): {performance['win_rate_24h']*100:.0f}%
- Trades today: {performance['total_trades_24h']}

Based on this data, generate 0-3 specific trade conditions.
Set trigger prices that are realistic (near current prices).
If using a known pattern, include pattern_id in your response.
Respond with JSON only - no other text."""

    def _parse_response(self, response: str) -> List[TradeCondition]:
        """Parse LLM response into TradeCondition objects.

        Args:
            response: Raw LLM response string.

        Returns:
            List of TradeCondition objects (may be empty).
        """
        try:
            # Clean response - handle markdown code blocks
            clean = response.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]

            data = json.loads(clean.strip())

            conditions = []
            for cond_data in data.get("conditions", []):
                try:
                    # Set expiration time
                    valid_until = datetime.now() + timedelta(minutes=self.condition_ttl)

                    condition = TradeCondition(
                        coin=cond_data["coin"].upper(),
                        direction=cond_data.get("direction", "LONG"),
                        trigger_price=float(cond_data["trigger_price"]),
                        trigger_condition=cond_data.get("trigger_condition", "ABOVE"),
                        stop_loss_pct=float(cond_data.get("stop_loss_pct", 2.0)),
                        take_profit_pct=float(cond_data.get("take_profit_pct", 1.5)),
                        position_size_usd=float(cond_data.get("position_size_usd", 50)),
                        reasoning=cond_data.get("reasoning", ""),
                        strategy_id=cond_data.get("strategy_id", "llm_generated"),
                        valid_until=valid_until,
                    )
                    conditions.append(condition)

                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse condition: {e}")
                    continue

            # Log market assessment if present
            if data.get("market_assessment"):
                logger.info(f"Market assessment: {data['market_assessment']}")
            if data.get("no_trade_reason"):
                logger.info(f"No trade reason: {data['no_trade_reason']}")

            return conditions

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw response: {response[:500]}")
            return []

    def _validate_condition(self, condition: TradeCondition) -> bool:
        """Validate a trade condition.

        Args:
            condition: TradeCondition to validate.

        Returns:
            True if condition is valid.
        """
        # TASK-121: Check if coin is blacklisted
        if self.coin_scorer:
            from src.coin_scorer import CoinStatus
            status = self.coin_scorer.get_coin_status(condition.coin)
            if status == CoinStatus.BLACKLISTED:
                logger.info(f"Skipping {condition.coin}: BLACKLISTED")
                return False

            # Apply position modifier based on coin status
            modifier = self.coin_scorer.get_position_modifier(condition.coin)
            if modifier != 1.0:
                original_size = condition.position_size_usd
                condition.position_size_usd = original_size * modifier
                logger.info(
                    f"Adjusted {condition.coin} size: ${original_size:.0f} * "
                    f"{modifier} = ${condition.position_size_usd:.0f} ({status.value})"
                )

        # Check position size limits
        if condition.position_size_usd < DEFAULT_MIN_POSITION_SIZE:
            logger.warning(
                f"Position size ${condition.position_size_usd} below minimum "
                f"${DEFAULT_MIN_POSITION_SIZE}"
            )
            return False

        if condition.position_size_usd > DEFAULT_MAX_POSITION_SIZE:
            logger.warning(
                f"Position size ${condition.position_size_usd} exceeds maximum "
                f"${DEFAULT_MAX_POSITION_SIZE}"
            )
            return False

        # Check stop loss is reasonable
        if condition.stop_loss_pct <= 0 or condition.stop_loss_pct > 10:
            logger.warning(f"Invalid stop loss: {condition.stop_loss_pct}%")
            return False

        # Check take profit is reasonable
        if condition.take_profit_pct <= 0 or condition.take_profit_pct > 10:
            logger.warning(f"Invalid take profit: {condition.take_profit_pct}%")
            return False

        # Check trigger price is positive
        if condition.trigger_price <= 0:
            logger.warning(f"Invalid trigger price: {condition.trigger_price}")
            return False

        # Check coin has price data
        current_price = self.market.get_price(condition.coin)
        if current_price is None:
            logger.warning(f"No price data for {condition.coin}")
            return False

        # Check trigger price is reasonable (within 2% of current - conditions expire in 5 min)
        price_diff_pct = abs(condition.trigger_price - current_price.price) / current_price.price * 100
        if price_diff_pct > 2:
            logger.warning(
                f"Trigger price ${condition.trigger_price} is {price_diff_pct:.1f}% "
                f"away from current ${current_price.price} - too far for 5-min TTL"
            )
            return False

        return True

    def _remove_expired_conditions(self) -> None:
        """Remove expired conditions from active list."""
        before = len(self.active_conditions)
        self.active_conditions = [
            c for c in self.active_conditions if not c.is_expired()
        ]
        removed = before - len(self.active_conditions)
        if removed > 0:
            logger.debug(f"Removed {removed} expired conditions")

    def _notify_callbacks(self, conditions: List[TradeCondition]) -> None:
        """Notify all callbacks of new conditions.

        Args:
            conditions: List of new conditions.
        """
        for callback in self._condition_callbacks:
            try:
                callback(conditions)
            except Exception as e:
                logger.error(f"Error in condition callback: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get strategist statistics.

        Returns:
            Stats dictionary.
        """
        return {
            "generation_count": self.generation_count,
            "conditions_generated": self.conditions_generated,
            "active_conditions": len(self.active_conditions),
            "last_generation": self.last_generation_time.isoformat()
            if self.last_generation_time
            else None,
            "interval_seconds": self.interval,
            "is_running": self._running,
        }

    def get_health(self) -> Dict[str, Any]:
        """Get component health status for monitoring.

        Returns:
            Dict with status (healthy/degraded/failed), last_activity, error_count, metrics.
        """
        now = datetime.now()

        # Check time since last generation
        if self.last_generation_time:
            time_since_gen = (now - self.last_generation_time).total_seconds()
        else:
            time_since_gen = None

        # Determine health status
        if not self._running:
            status = "stopped"
        elif time_since_gen is None:
            status = "degraded"  # Never ran
        elif time_since_gen > self.interval * 3:
            status = "degraded"  # Should have run by now
        else:
            status = "healthy"

        return {
            "status": status,
            "last_activity": self.last_generation_time.isoformat()
            if self.last_generation_time
            else None,
            "error_count": 0,  # Could add error tracking in future
            "metrics": {
                "generation_count": self.generation_count,
                "conditions_generated": self.conditions_generated,
                "active_conditions": len(self.active_conditions),
                "interval_seconds": self.interval,
                "time_since_last_generation": round(time_since_gen, 1) if time_since_gen else None,
                "is_running": self._running,
            }
        }


# Allow running directly for testing
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    async def test_strategist():
        print("=" * 60)
        print("Strategist Test - Generating Trade Conditions")
        print("=" * 60)

        # Initialize components
        llm = LLMInterface()
        market = MarketFeed(["BTC", "ETH", "SOL", "XRP", "DOGE"])

        strategist = Strategist(
            llm=llm,
            market_feed=market,
            interval_seconds=120,
        )

        # Track conditions
        def on_conditions(conditions):
            print(f"\n[Callback] Received {len(conditions)} conditions")

        strategist.subscribe_conditions(on_conditions)

        # Connect to market feed
        print("\nConnecting to market feed...")
        await market.connect()

        # Wait for price data
        print("Waiting for prices...")
        await asyncio.sleep(5)

        # Check prices
        prices = market.get_all_prices()
        print(f"\nGot prices for {len(prices)} coins:")
        for coin, tick in list(prices.items())[:5]:
            print(f"  {coin}: ${tick.price:,.2f}")

        # Generate conditions
        print("\n" + "-" * 40)
        print("Generating conditions...")
        print("-" * 40)

        conditions = await strategist.generate_conditions()

        print(f"\nGenerated {len(conditions)} conditions:")
        for c in conditions:
            print(f"\n{c.direction} {c.coin}:")
            print(f"  Trigger: {c.trigger_condition} ${c.trigger_price:,.2f}")
            print(f"  Stop: {c.stop_loss_pct}% | Target: {c.take_profit_pct}%")
            print(f"  Size: ${c.position_size_usd}")
            print(f"  Reason: {c.reasoning}")
            print(f"  Valid until: {c.valid_until.strftime('%H:%M:%S')}")

        # Print stats
        print("\n" + "-" * 40)
        print("Stats:")
        stats = strategist.get_stats()
        for k, v in stats.items():
            print(f"  {k}: {v}")

    try:
        asyncio.run(test_strategist())
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(0)
