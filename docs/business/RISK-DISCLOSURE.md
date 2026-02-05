# Risk Disclosure

**Last Updated:** February 3, 2026
**Phase:** 2 Complete

This document provides honest disclosure of risks associated with this trading system. These are not hypothetical—they are real risks that must be understood and accepted.

---

## Trading Risks

### Market Risk
**What:** Cryptocurrency prices can move against positions rapidly and significantly.

**Mitigation:**
- Default stop-loss on all positions (2%)
- Maximum position size limits
- Maximum total exposure cap

**Residual Risk:** Stop-losses can gap in fast markets. Flash crashes can exceed loss limits.

### Liquidity Risk
**What:** Some coins may not have sufficient volume to exit positions at expected prices.

**Mitigation:**
- WebSocket provides real-time liquidity data
- Position sizes scaled to coin tier
- Paper trading simulates instant fills (real trading may slip)

**Residual Risk:** Market-wide liquidity crises affect all coins simultaneously.

### Model Risk
**What:** The LLM may make poor decisions, learn wrong patterns, or create harmful rules.

**Mitigation:**
- All trades logged with reasoning (auditable)
- Patterns require testing period
- Confidence scoring deactivates poor patterns
- Adaptations tracked with effectiveness measurement
- Rollback capability for harmful adaptations

**Residual Risk:** Subtle systematic errors may not be caught until significant losses accumulate.

---

## Learning System Risks

### Overfitting
**What:** System learns patterns specific to recent conditions that don't generalize.

**Mitigation:**
- Patterns require multiple confirming trades
- Confidence decays over time without reinforcement
- Reflection considers diverse timeframes

**Residual Risk:** Market regime changes may invalidate all learned patterns.

### Feedback Loops
**What:** Learning from own trades could reinforce bad behavior.

**Mitigation:**
- Position sizes too small to move markets
- 20-coin universe spreads impact
- Effectiveness tracking detects degradation

**Residual Risk:** Subtle feedback effects in illiquid coins.

### Adaptation Errors
**What:** Adaptations may harm rather than help performance.

**Mitigation:**
- All adaptations logged with before/after metrics
- Effectiveness measured after sufficient trades
- Automatic rollback for harmful adaptations
- Manual override capability

**Residual Risk:** Damage done before ineffective adaptation is detected.

### Learning Stagnation
**What:** System may stop learning useful patterns.

**Mitigation:**
- Reflection runs hourly regardless of trade count
- Insight generation prompts exploration
- Pattern library allows new pattern creation

**Residual Risk:** If market changes faster than learning, system may always lag.

---

## Technical Risks

### System Failure
**What:** Bot crashes, loses connectivity, or fails to execute trades.

**Mitigation:**
- Persistent state survives restarts
- Automatic WebSocket reconnection
- All positions stored in database
- Dashboard shows system health

**Residual Risk:** Extended outages could leave positions unmanaged during adverse moves.

### WebSocket Disconnection
**What:** Loss of real-time market data.

**Mitigation:**
- Automatic reconnection with exponential backoff
- Conditions expire (won't trigger on stale data)
- Dashboard shows connection status

**Residual Risk:** During reconnection, may miss trading opportunities or exit signals.

### LLM Failure
**What:** Ollama server unavailable or producing bad outputs.

**Mitigation:**
- System defaults to HOLD if LLM unavailable
- JSON parsing validates LLM responses
- Existing conditions remain active
- Quick Update runs without LLM

**Residual Risk:** Extended LLM outage prevents new condition generation.

### Data Integrity
**What:** Corrupted data could lead to incorrect decisions or lost records.

**Mitigation:**
- SQLite ACID compliance
- All state persistently stored
- Database can be backed up (single file)

**Residual Risk:** SQLite not designed for high concurrency. Single point of failure.

---

## Operational Risks

### Single Operator
**What:** Currently only one person can operate and troubleshoot the system.

**Mitigation:**
- Comprehensive documentation (16 documents)
- Runbooks for common operations
- Troubleshooting guide
- Dashboard for monitoring

**Residual Risk:** Extended operator unavailability could leave issues unresolved.

### Configuration Errors
**What:** Incorrect settings could bypass risk controls or cause unintended behavior.

**Mitigation:**
- Risk limits are code constants (not configurable)
- Configuration validated on startup
- Logs capture all configuration

**Residual Risk:** Code changes could inadvertently modify risk parameters.

### Monitoring Gaps
**What:** Issues may go unnoticed if not actively monitoring.

**Mitigation:**
- Dashboard shows real-time status
- Key metrics displayed prominently
- API for external monitoring integration

**Residual Risk:** No push notifications currently (must check dashboard).

---

## Financial Risks

### Capital Loss
**What:** Trading capital can be lost partially or entirely.

**Reality Check:**
- Paper trading has no real financial risk
- Phase 3 with real money: only risk capital you can afford to lose
- This is speculation, not investment

### Opportunity Cost
**What:** Capital deployed here cannot be used elsewhere.

**Consideration:** Compare expected returns to alternatives (index funds, staking, etc.)

### Hidden Costs
**What:** Real trading will have costs not present in paper trading.

**Costs to consider:**
- Exchange trading fees (0.1% typical)
- Spread (difference between bid/ask)
- Slippage (price moves between order and fill)
- Withdrawal fees

---

## Regulatory Risks

### Tax Implications
**What:** Cryptocurrency trades may be taxable events.

**Status:**
- Paper trading: No tax implications
- Real trading: Consult tax professional
- Trade export available for records

### Regulatory Changes
**What:** Cryptocurrency regulation is evolving and uncertain.

**Consideration:** Regulatory changes could impact ability to trade or require compliance changes.

---

## Phase 2 Specific Risks

### Learning System Novelty
**What:** The autonomous learning system is new and unproven at scale.

**Mitigation:**
- Extensive paper trading validation
- Effectiveness tracking on all adaptations
- Conservative approach (require high confidence)
- Rollback capability

**Residual Risk:** Unknown unknowns in a novel system design.

### Adaptation Frequency
**What:** Too many adaptations could create instability.

**Mitigation:**
- Minimum trades required before adaptation
- Confidence thresholds for actions
- Rate limiting on adaptations (implicit)

**Residual Risk:** Rapid market changes could trigger many adaptations.

---

## Risk Summary

| Category | Severity | Mitigation Quality |
|----------|----------|-------------------|
| Market | High | Moderate (stop-loss, limits) |
| Learning | Medium | Good (tracking, rollback) |
| Technical | Medium | Good (persistence, auto-recovery) |
| Operational | Low | Good (documentation) |
| Financial | High | Good (paper trading first) |
| Regulatory | Low | Limited (awareness only) |

---

## Before Real Money Trading

1. **Complete Phase 2.5 validation** with extended paper trading
2. **Verify learning effectiveness** with measurable improvement
3. **Understand all risks** documented here
4. **Only use capital you can afford to lose completely**
5. **Have monitoring and intervention plan ready**
6. **Start with small capital** and scale gradually

---

## Acknowledgment

By using this system for real money trading (Phase 3+), you acknowledge:
- Trading cryptocurrencies involves substantial risk of loss
- Past performance (paper trading) does not guarantee future results
- The learning system may not perform as expected in all market conditions
- You are solely responsible for your trading decisions and outcomes

---

*This risk disclosure is provided for transparency and informed decision-making. It is not legal or financial advice.*
