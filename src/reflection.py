"""
Deep Reflection Engine - LLM-powered periodic analysis.

TASK-131: Analyzes recent trading performance and generates insights
using qwen2.5:14b. Runs hourly or after every 10 trades.

This is the "thinking" layer where the bot reflects on what's working
and what isn't, identifying patterns that can improve performance.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.database import Database
from src.journal import JournalEntry, TradeJournal
from src.knowledge import KnowledgeBrain
from src.llm_interface import LLMInterface
from src.models.reflection import (
    CoinAnalysis,
    ExitAnalysis,
    Insight,
    PatternAnalysis,
    ReflectionResult,
    RegimeAnalysis,
    TimeAnalysis,
)

# Import for type hint only - avoid circular import
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.adaptation import AdaptationEngine

logger = logging.getLogger(__name__)


# LLM prompts
REFLECTION_SYSTEM_PROMPT = """You are the Reflection Engine for an autonomous trading bot.
Your job is to analyze recent trading performance and generate actionable insights.

You will receive performance data broken down by coin, pattern, time, and market regime.

Your output must be valid JSON with this structure:
{
    "summary": "Brief 2-3 sentence summary of overall performance",
    "insights": [
        {
            "insight_type": "coin|pattern|time|regime|exit|general",
            "category": "opportunity|problem|observation",
            "title": "Short title (under 50 chars)",
            "description": "Detailed explanation of the insight",
            "evidence": {"metric": value},
            "suggested_action": "Specific action to take (or null)",
            "confidence": 0.0-1.0
        }
    ]
}

Focus on:
- Patterns with statistical significance (5+ trades minimum)
- Actionable insights that can improve performance
- Both problems (things to stop) and opportunities (things to do more)
- Be specific with numbers and evidence

IMPORTANT: Respond with JSON only - no other text."""


class ReflectionEngine:
    """Periodic LLM-powered analysis and insight generation.

    Runs hourly or after every 10 trades to:
    - Analyze recent trading performance
    - Identify patterns (winning/losing coins, times, regimes)
    - Generate LLM-powered insights
    - Produce adaptation recommendations

    Example:
        >>> engine = ReflectionEngine(journal, knowledge, llm, db)
        >>> await engine.start()  # Runs in background
        >>> # Or manually trigger
        >>> result = await engine.reflect()
    """

    # Trigger thresholds
    REFLECTION_INTERVAL_HOURS = 1
    REFLECTION_TRADE_COUNT = 10
    MIN_TRADES_FOR_REFLECTION = 5

    # Analysis window
    ANALYSIS_HOURS = 24

    def __init__(
        self,
        journal: TradeJournal,
        knowledge: KnowledgeBrain,
        llm: LLMInterface,
        db: Optional[Database] = None,
        adaptation_engine: Optional["AdaptationEngine"] = None,
    ):
        """Initialize ReflectionEngine.

        Args:
            journal: TradeJournal for accessing trade history.
            knowledge: KnowledgeBrain for context.
            llm: LLMInterface for insight generation.
            db: Optional Database for logging reflections.
            adaptation_engine: Optional AdaptationEngine for applying insights.
        """
        self.journal = journal
        self.knowledge = knowledge
        self.llm = llm
        self.db = db
        self.adaptation_engine = adaptation_engine

        # State
        self.last_reflection_time: Optional[datetime] = None
        self.trades_since_reflection: int = 0
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

        # Stats
        self.reflections_completed: int = 0
        self.insights_generated: int = 0
        self.adaptations_applied: int = 0

        logger.info("ReflectionEngine initialized")

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def start(self) -> None:
        """Start background reflection loop."""
        if self._running:
            logger.warning("ReflectionEngine already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            f"ReflectionEngine started (interval={self.REFLECTION_INTERVAL_HOURS}h, "
            f"trade_trigger={self.REFLECTION_TRADE_COUNT})"
        )

    async def stop(self) -> None:
        """Stop the reflection loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("ReflectionEngine stopped")

    async def _run_loop(self) -> None:
        """Background loop that checks for reflection triggers."""
        while self._running:
            try:
                if self.should_reflect():
                    await self.reflect()

                # Check every minute
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in reflection loop: {e}")
                await asyncio.sleep(60)

    def on_trade_close(self) -> None:
        """Called by QuickUpdate to track trade count."""
        self.trades_since_reflection += 1
        logger.debug(f"Trades since reflection: {self.trades_since_reflection}")

    def should_reflect(self) -> bool:
        """Check if reflection should run now."""
        # Time-based trigger
        if self.last_reflection_time:
            hours_since = (datetime.now() - self.last_reflection_time).total_seconds() / 3600
            if hours_since >= self.REFLECTION_INTERVAL_HOURS:
                logger.info(f"Time trigger: {hours_since:.1f}h since last reflection")
                return True

        # Trade count trigger
        if self.trades_since_reflection >= self.REFLECTION_TRADE_COUNT:
            logger.info(f"Trade trigger: {self.trades_since_reflection} trades since last reflection")
            return True

        # First reflection (no history) - need minimum trades
        if self.last_reflection_time is None:
            if self.trades_since_reflection >= self.MIN_TRADES_FOR_REFLECTION:
                logger.info(f"Initial reflection: {self.trades_since_reflection} trades available")
                return True

        return False

    # =========================================================================
    # Core Reflection
    # =========================================================================

    async def reflect(self) -> ReflectionResult:
        """Run a full reflection cycle.

        Returns:
            ReflectionResult with analyses and insights.
        """
        start_time = time.perf_counter()
        logger.info("Starting deep reflection...")

        # Get recent trades
        trades = self.journal.get_recent(hours=self.ANALYSIS_HOURS, status="closed")

        if not trades:
            logger.warning("No trades to analyze")
            return self._empty_result()

        # Calculate period
        period_start = min(t.entry_time for t in trades)
        period_end = max(t.exit_time or t.entry_time for t in trades)
        period_hours = (period_end - period_start).total_seconds() / 3600

        # Overall stats
        wins = sum(1 for t in trades if t.pnl_usd and t.pnl_usd > 0)
        losses = len(trades) - wins
        total_pnl = sum(t.pnl_usd or 0 for t in trades)
        win_rate = wins / len(trades) if trades else 0

        # Run quantitative analyses
        analysis_start = time.perf_counter()

        coin_analyses = self._analyze_by_coin(trades)
        pattern_analyses = self._analyze_by_pattern(trades)
        time_analysis = self._analyze_by_time(trades)
        regime_analysis = self._analyze_by_regime(trades)
        exit_analysis = self._analyze_exits(trades)

        analysis_time_ms = (time.perf_counter() - analysis_start) * 1000

        # Generate LLM insights
        llm_start = time.perf_counter()

        insights, summary = await self._generate_insights(
            trades=trades,
            coin_analyses=coin_analyses,
            pattern_analyses=pattern_analyses,
            time_analysis=time_analysis,
            regime_analysis=regime_analysis,
            exit_analysis=exit_analysis,
            period_hours=period_hours,
            total_pnl=total_pnl,
            win_rate=win_rate,
        )

        llm_time_ms = (time.perf_counter() - llm_start) * 1000
        total_time_ms = (time.perf_counter() - start_time) * 1000

        # Apply adaptations (TASK-133)
        adaptations = []
        if self.adaptation_engine and insights:
            adaptations = self.adaptation_engine.apply_insights(insights)
            self.adaptations_applied += len(adaptations)
            if adaptations:
                logger.info(f"Applied {len(adaptations)} adaptations from insights")
                for a in adaptations:
                    logger.info(f"  Adaptation: {a}")

        # Build result
        result = ReflectionResult(
            timestamp=datetime.now(),
            trades_analyzed=len(trades),
            period_hours=period_hours,
            total_pnl=total_pnl,
            win_rate=win_rate,
            wins=wins,
            losses=losses,
            coin_analyses=coin_analyses,
            pattern_analyses=pattern_analyses,
            time_analysis=time_analysis,
            regime_analysis=regime_analysis,
            exit_analysis=exit_analysis,
            insights=insights,
            summary=summary,
            analysis_time_ms=analysis_time_ms,
            llm_time_ms=llm_time_ms,
            total_time_ms=total_time_ms,
            adaptations=adaptations,
        )

        # Update state
        self.last_reflection_time = datetime.now()
        self.trades_since_reflection = 0
        self.reflections_completed += 1
        self.insights_generated += len(insights)

        # Log reflection
        self._log_reflection(result)

        logger.info(f"Reflection complete: {result}")
        for insight in insights:
            logger.info(f"  Insight: {insight}")

        return result

    def _empty_result(self) -> ReflectionResult:
        """Return an empty result when no trades to analyze."""
        return ReflectionResult(
            timestamp=datetime.now(),
            trades_analyzed=0,
            period_hours=0,
            total_pnl=0,
            win_rate=0,
            wins=0,
            losses=0,
            coin_analyses=[],
            pattern_analyses=[],
            time_analysis=None,
            regime_analysis=None,
            exit_analysis=None,
            insights=[],
            summary="No trades to analyze.",
        )

    # =========================================================================
    # Quantitative Analysis
    # =========================================================================

    def _analyze_by_coin(self, trades: List[JournalEntry]) -> List[CoinAnalysis]:
        """Analyze performance by coin."""
        coin_trades: Dict[str, List[JournalEntry]] = defaultdict(list)
        for t in trades:
            coin_trades[t.coin].append(t)

        analyses = []
        for coin, coin_list in coin_trades.items():
            pnls = [t.pnl_usd or 0 for t in coin_list]
            winners = [p for p in pnls if p > 0]
            losers = [p for p in pnls if p <= 0]

            # Calculate trend (comparing first half to second half)
            if len(coin_list) >= 4:
                mid = len(coin_list) // 2
                first_half_pnl = sum(t.pnl_usd or 0 for t in coin_list[:mid])
                second_half_pnl = sum(t.pnl_usd or 0 for t in coin_list[mid:])
                if second_half_pnl > first_half_pnl * 1.2:
                    trend = "improving"
                elif second_half_pnl < first_half_pnl * 0.8:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"

            analyses.append(CoinAnalysis(
                coin=coin,
                total_trades=len(coin_list),
                wins=len(winners),
                losses=len(losers),
                win_rate=len(winners) / len(coin_list) if coin_list else 0,
                total_pnl=sum(pnls),
                avg_pnl=sum(pnls) / len(pnls) if pnls else 0,
                avg_winner=sum(winners) / len(winners) if winners else 0,
                avg_loser=sum(losers) / len(losers) if losers else 0,
                best_trade=max(pnls) if pnls else 0,
                worst_trade=min(pnls) if pnls else 0,
                trend=trend,
            ))

        # Sort by total P&L
        analyses.sort(key=lambda x: x.total_pnl, reverse=True)
        return analyses

    def _analyze_by_pattern(self, trades: List[JournalEntry]) -> List[PatternAnalysis]:
        """Analyze performance by pattern/strategy."""
        pattern_trades: Dict[str, List[JournalEntry]] = defaultdict(list)

        for t in trades:
            key = t.pattern_id or t.strategy_id or "unknown"
            pattern_trades[key].append(t)

        analyses = []
        for pattern_id, pattern_list in pattern_trades.items():
            pnls = [t.pnl_usd or 0 for t in pattern_list]
            wins = sum(1 for p in pnls if p > 0)

            # Get pattern description from library if available
            description = pattern_id
            confidence = 0.5
            if self.knowledge and pattern_id != "unknown":
                patterns = self.knowledge.get_active_patterns()
                for p in patterns:
                    if p.pattern_id == pattern_id:
                        description = p.description
                        confidence = p.confidence
                        break

            analyses.append(PatternAnalysis(
                pattern_id=pattern_id,
                description=description,
                total_trades=len(pattern_list),
                wins=wins,
                losses=len(pattern_list) - wins,
                win_rate=wins / len(pattern_list) if pattern_list else 0,
                total_pnl=sum(pnls),
                avg_pnl=sum(pnls) / len(pnls) if pnls else 0,
                confidence=confidence,
            ))

        analyses.sort(key=lambda x: x.total_pnl, reverse=True)
        return analyses

    def _analyze_by_time(self, trades: List[JournalEntry]) -> TimeAnalysis:
        """Analyze performance by time of day and day of week."""
        hour_trades: Dict[int, List[JournalEntry]] = defaultdict(list)
        day_trades: Dict[int, List[JournalEntry]] = defaultdict(list)

        for t in trades:
            hour_trades[t.hour_of_day].append(t)
            day_trades[t.day_of_week].append(t)

        # Calculate win rates by hour
        hour_win_rates = {}
        hour_trade_counts = {}
        for hour, hour_list in hour_trades.items():
            wins = sum(1 for t in hour_list if t.pnl_usd and t.pnl_usd > 0)
            hour_win_rates[hour] = wins / len(hour_list) if hour_list else 0
            hour_trade_counts[hour] = len(hour_list)

        # Calculate win rates by day
        day_win_rates = {}
        day_trade_counts = {}
        for day, day_list in day_trades.items():
            wins = sum(1 for t in day_list if t.pnl_usd and t.pnl_usd > 0)
            day_win_rates[day] = wins / len(day_list) if day_list else 0
            day_trade_counts[day] = len(day_list)

        # Find best/worst hours (with minimum 2 trades)
        valid_hours = {h: r for h, r in hour_win_rates.items() if hour_trade_counts.get(h, 0) >= 2}
        best_hours = sorted(valid_hours.keys(), key=lambda h: valid_hours[h], reverse=True)[:3]
        worst_hours = sorted(valid_hours.keys(), key=lambda h: valid_hours[h])[:3]

        # Find best/worst days (with minimum 2 trades)
        valid_days = {d: r for d, r in day_win_rates.items() if day_trade_counts.get(d, 0) >= 2}
        best_days = sorted(valid_days.keys(), key=lambda d: valid_days[d], reverse=True)[:2]
        worst_days = sorted(valid_days.keys(), key=lambda d: valid_days[d])[:2]

        # Weekend vs weekday
        weekend_trades = [t for t in trades if t.day_of_week >= 5]
        weekday_trades = [t for t in trades if t.day_of_week < 5]

        weekend_wins = sum(1 for t in weekend_trades if t.pnl_usd and t.pnl_usd > 0)
        weekday_wins = sum(1 for t in weekday_trades if t.pnl_usd and t.pnl_usd > 0)

        return TimeAnalysis(
            best_hours=best_hours,
            worst_hours=worst_hours,
            hour_win_rates=hour_win_rates,
            hour_trade_counts=hour_trade_counts,
            best_days=best_days,
            worst_days=worst_days,
            day_win_rates=day_win_rates,
            day_trade_counts=day_trade_counts,
            weekend_trades=len(weekend_trades),
            weekend_win_rate=weekend_wins / len(weekend_trades) if weekend_trades else 0,
            weekday_win_rate=weekday_wins / len(weekday_trades) if weekday_trades else 0,
        )

    def _analyze_by_regime(self, trades: List[JournalEntry]) -> RegimeAnalysis:
        """Analyze performance by market regime."""
        btc_up = [t for t in trades if t.btc_trend == "up"]
        btc_down = [t for t in trades if t.btc_trend == "down"]
        btc_sideways = [t for t in trades if t.btc_trend in ("sideways", None)]

        def calc_stats(trade_list):
            if not trade_list:
                return 0, 0, 0
            wins = sum(1 for t in trade_list if t.pnl_usd and t.pnl_usd > 0)
            pnl = sum(t.pnl_usd or 0 for t in trade_list)
            return len(trade_list), wins / len(trade_list), pnl

        up_count, up_wr, up_pnl = calc_stats(btc_up)
        down_count, down_wr, down_pnl = calc_stats(btc_down)
        side_count, side_wr, side_pnl = calc_stats(btc_sideways)

        # Determine best/worst regime
        regimes = [
            ("btc_up", up_wr, up_count),
            ("btc_down", down_wr, down_count),
            ("btc_sideways", side_wr, side_count),
        ]
        valid_regimes = [(r, wr, c) for r, wr, c in regimes if c >= 2]

        if valid_regimes:
            best_regime = max(valid_regimes, key=lambda x: x[1])[0]
            worst_regime = min(valid_regimes, key=lambda x: x[1])[0]
        else:
            best_regime = "unknown"
            worst_regime = "unknown"

        return RegimeAnalysis(
            btc_up_trades=up_count,
            btc_up_win_rate=up_wr,
            btc_up_pnl=up_pnl,
            btc_down_trades=down_count,
            btc_down_win_rate=down_wr,
            btc_down_pnl=down_pnl,
            btc_sideways_trades=side_count,
            btc_sideways_win_rate=side_wr,
            btc_sideways_pnl=side_pnl,
            best_regime=best_regime,
            worst_regime=worst_regime,
        )

    def _analyze_exits(self, trades: List[JournalEntry]) -> ExitAnalysis:
        """Analyze exit performance."""
        stop_losses = [t for t in trades if t.exit_reason == "stop_loss"]
        take_profits = [t for t in trades if t.exit_reason == "take_profit"]
        manual = [t for t in trades if t.exit_reason == "manual"]

        total = len(trades)

        # Average P&L by exit type
        sl_pnls = [t.pnl_usd or 0 for t in stop_losses]
        tp_pnls = [t.pnl_usd or 0 for t in take_profits]

        # Early exits (trades with missed_profit > 0)
        early_exits = [t for t in trades if t.missed_profit_usd and t.missed_profit_usd > 1.0]
        missed_profits = [t.missed_profit_usd or 0 for t in early_exits]

        return ExitAnalysis(
            stop_loss_count=len(stop_losses),
            take_profit_count=len(take_profits),
            manual_count=len(manual),
            total_exits=total,
            stop_loss_rate=len(stop_losses) / total if total else 0,
            take_profit_rate=len(take_profits) / total if total else 0,
            avg_stop_loss_pnl=sum(sl_pnls) / len(sl_pnls) if sl_pnls else 0,
            avg_take_profit_pnl=sum(tp_pnls) / len(tp_pnls) if tp_pnls else 0,
            early_exits=len(early_exits),
            avg_missed_profit=sum(missed_profits) / len(missed_profits) if missed_profits else 0,
        )

    # =========================================================================
    # LLM Insight Generation
    # =========================================================================

    async def _generate_insights(
        self,
        trades: List[JournalEntry],
        coin_analyses: List[CoinAnalysis],
        pattern_analyses: List[PatternAnalysis],
        time_analysis: TimeAnalysis,
        regime_analysis: RegimeAnalysis,
        exit_analysis: ExitAnalysis,
        period_hours: float,
        total_pnl: float,
        win_rate: float,
    ) -> tuple[List[Insight], str]:
        """Use LLM to generate insights from analyses."""
        # Build prompt
        prompt = self._build_reflection_prompt(
            trades=trades,
            coin_analyses=coin_analyses,
            pattern_analyses=pattern_analyses,
            time_analysis=time_analysis,
            regime_analysis=regime_analysis,
            exit_analysis=exit_analysis,
            period_hours=period_hours,
            total_pnl=total_pnl,
            win_rate=win_rate,
        )

        # Query LLM
        try:
            response = self.llm.query(prompt, REFLECTION_SYSTEM_PROMPT)

            if not response:
                logger.warning("LLM returned empty response")
                return [], "Unable to generate insights."

            # Parse response
            insights, summary = self._parse_llm_response(response)
            return insights, summary

        except Exception as e:
            logger.error(f"LLM insight generation failed: {e}")
            return [], f"Insight generation failed: {e}"

    def _build_reflection_prompt(
        self,
        trades: List[JournalEntry],
        coin_analyses: List[CoinAnalysis],
        pattern_analyses: List[PatternAnalysis],
        time_analysis: TimeAnalysis,
        regime_analysis: RegimeAnalysis,
        exit_analysis: ExitAnalysis,
        period_hours: float,
        total_pnl: float,
        win_rate: float,
    ) -> str:
        """Build the reflection prompt for LLM."""
        wins = sum(1 for t in trades if t.pnl_usd and t.pnl_usd > 0)

        # Format coin analysis
        coin_lines = []
        for c in coin_analyses[:10]:
            status = ""
            if c.win_rate >= 0.6 and c.total_pnl > 0:
                status = " [STRONG]"
            elif c.win_rate < 0.3 and c.total_pnl < 0:
                status = " [WEAK]"
            coin_lines.append(
                f"  {c.coin}: {c.total_trades} trades, {c.win_rate:.0%} win rate, "
                f"${c.total_pnl:+.2f} P&L, trend: {c.trend}{status}"
            )
        coin_text = "\n".join(coin_lines) if coin_lines else "  No coin data"

        # Format pattern analysis
        pattern_lines = []
        for p in pattern_analyses[:5]:
            pattern_lines.append(
                f"  {p.pattern_id}: {p.total_trades} trades, {p.win_rate:.0%} win rate, "
                f"${p.total_pnl:+.2f} P&L"
            )
        pattern_text = "\n".join(pattern_lines) if pattern_lines else "  No pattern data"

        # Format time analysis
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        best_hours_str = ", ".join(f"{h}:00" for h in time_analysis.best_hours) if time_analysis.best_hours else "N/A"
        worst_hours_str = ", ".join(f"{h}:00" for h in time_analysis.worst_hours) if time_analysis.worst_hours else "N/A"
        best_days_str = ", ".join(day_names[d] for d in time_analysis.best_days) if time_analysis.best_days else "N/A"
        worst_days_str = ", ".join(day_names[d] for d in time_analysis.worst_days) if time_analysis.worst_days else "N/A"

        return f"""Analyze this trading performance and generate actionable insights:

PERIOD: {period_hours:.1f} hours
OVERALL: {len(trades)} trades, {wins} wins ({win_rate:.0%}), ${total_pnl:+.2f} P&L

PERFORMANCE BY COIN:
{coin_text}

PERFORMANCE BY PATTERN/STRATEGY:
{pattern_text}

PERFORMANCE BY TIME:
  Best hours (UTC): {best_hours_str}
  Worst hours (UTC): {worst_hours_str}
  Best days: {best_days_str}
  Worst days: {worst_days_str}
  Weekend win rate: {time_analysis.weekend_win_rate:.0%} ({time_analysis.weekend_trades} trades)
  Weekday win rate: {time_analysis.weekday_win_rate:.0%}

PERFORMANCE BY MARKET REGIME:
  BTC Up: {regime_analysis.btc_up_win_rate:.0%} win rate ({regime_analysis.btc_up_trades} trades), ${regime_analysis.btc_up_pnl:+.2f}
  BTC Down: {regime_analysis.btc_down_win_rate:.0%} win rate ({regime_analysis.btc_down_trades} trades), ${regime_analysis.btc_down_pnl:+.2f}
  BTC Sideways: {regime_analysis.btc_sideways_win_rate:.0%} win rate ({regime_analysis.btc_sideways_trades} trades), ${regime_analysis.btc_sideways_pnl:+.2f}
  Best regime: {regime_analysis.best_regime}
  Worst regime: {regime_analysis.worst_regime}

EXIT ANALYSIS:
  Stop-loss rate: {exit_analysis.stop_loss_rate:.0%} ({exit_analysis.stop_loss_count} trades), avg ${exit_analysis.avg_stop_loss_pnl:.2f}
  Take-profit rate: {exit_analysis.take_profit_rate:.0%} ({exit_analysis.take_profit_count} trades), avg ${exit_analysis.avg_take_profit_pnl:.2f}
  Early exits (missed profit): {exit_analysis.early_exits} trades, avg ${exit_analysis.avg_missed_profit:.2f} missed

Generate 3-7 specific, actionable insights. Focus on patterns with 5+ trades.
For underperforming coins (<30% win rate, 5+ trades), suggest blacklisting.
For overperforming coins (>60% win rate, 5+ trades), suggest favoring.

Respond with JSON only."""

    def _parse_llm_response(self, response: str) -> tuple[List[Insight], str]:
        """Parse LLM response into insights."""
        try:
            # Clean response
            clean = response.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]

            data = json.loads(clean.strip())

            summary = data.get("summary", "No summary provided.")
            insights = []

            for i_data in data.get("insights", []):
                try:
                    insight = Insight.from_dict(i_data)
                    insights.append(insight)
                except Exception as e:
                    logger.warning(f"Failed to parse insight: {e}")
                    continue

            return insights, summary

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response: {response[:500]}")
            return [], "Failed to parse insights."

    # =========================================================================
    # Persistence
    # =========================================================================

    def _log_reflection(self, result: ReflectionResult) -> None:
        """Save reflection to database."""
        if not self.db:
            return

        try:
            self.db.log_reflection(
                trades_analyzed=result.trades_analyzed,
                period_hours=result.period_hours,
                insights=json.dumps([i.to_dict() for i in result.insights]),
                summary=result.summary,
                total_time_ms=result.total_time_ms,
            )
        except Exception as e:
            logger.error(f"Failed to log reflection: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get ReflectionEngine statistics."""
        return {
            "reflections_completed": self.reflections_completed,
            "insights_generated": self.insights_generated,
            "adaptations_applied": self.adaptations_applied,
            "last_reflection": self.last_reflection_time.isoformat() if self.last_reflection_time else None,
            "trades_since_reflection": self.trades_since_reflection,
            "is_running": self._running,
        }

    def get_health(self) -> Dict[str, Any]:
        """Get component health status for monitoring.

        Returns:
            Dict with status (healthy/degraded/failed), last_activity, error_count, metrics.
        """
        now = datetime.now()

        # Check time since last reflection
        if self.last_reflection_time:
            time_since = (now - self.last_reflection_time).total_seconds() / 3600
        else:
            time_since = None

        # Determine health status
        if not self._running:
            status = "stopped"
        elif time_since is None:
            # Never ran, but might be waiting for enough trades
            status = "healthy" if self.trades_since_reflection < self.MIN_TRADES_FOR_REFLECTION else "degraded"
        elif time_since > self.REFLECTION_INTERVAL_HOURS * 2:
            status = "degraded"  # Should have run by now
        else:
            status = "healthy"

        return {
            "status": status,
            "last_activity": self.last_reflection_time.isoformat() if self.last_reflection_time else None,
            "error_count": 0,
            "metrics": {
                "reflections_completed": self.reflections_completed,
                "insights_generated": self.insights_generated,
                "adaptations_applied": self.adaptations_applied,
                "trades_since_reflection": self.trades_since_reflection,
                "hours_since_reflection": round(time_since, 2) if time_since else None,
                "is_running": self._running,
            }
        }


# Allow running directly for testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("=" * 60)
    print("ReflectionEngine Test")
    print("=" * 60)
    print("\nNote: This requires trades in the journal to analyze.")
    print("Run the full trading system first to generate data.")
