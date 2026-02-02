# Risk Disclosure

This document provides honest disclosure of risks associated with this trading system. These are not hypothetical—they are real risks that must be understood and accepted.

---

## Trading Risks

### Market Risk
**What:** Cryptocurrency prices can move against positions rapidly and significantly.

**Mitigation:**
- Tier-specific stop-losses (3%/5%/7%)
- Maximum 10% total exposure at any time
- Maximum 2% per individual trade

**Residual Risk:** Stop-losses can gap in fast markets. Flash crashes can exceed loss limits.

### Liquidity Risk
**What:** Some coins may not have sufficient volume to exit positions at expected prices.

**Mitigation:**
- Volume filtering excludes illiquid coins
- Tier 3 (high volatility) has smallest position limits
- Blue chips (Tier 1) get largest allocations

**Residual Risk:** Market-wide liquidity crises affect all coins simultaneously.

### Model Risk
**What:** The LLM may make poor decisions, learn wrong patterns, or create harmful rules.

**Mitigation:**
- All trades logged with reasoning (auditable)
- Rules require testing period before promotion
- Human can review and disable rules
- Conservative position sizing limits damage from bad decisions

**Residual Risk:** Subtle systematic errors may not be caught until significant losses accumulate.

---

## Technical Risks

### System Failure
**What:** Bot crashes, loses connectivity, or fails to execute trades.

**Mitigation:**
- Supervisor auto-restarts on crash
- Persistent state survives restarts
- Autonomous monitor detects issues
- All state in database (recoverable)

**Residual Risk:** Extended outages could leave positions unmanaged during adverse moves.

### Data Integrity
**What:** Corrupted data could lead to incorrect decisions or lost records.

**Mitigation:**
- SQLite ACID compliance
- Database can be backed up (single file)
- All trades logged to activity_log

**Residual Risk:** SQLite not designed for high concurrency. Consider PostgreSQL for Phase 2.

### API Dependency
**What:** CoinGecko API could change, rate-limit, or become unavailable.

**Mitigation:**
- Free tier has generous limits
- Bot handles API errors gracefully
- Falls back to HOLD if data unavailable

**Residual Risk:** Prolonged API outage would halt trading entirely.

### LLM Dependency
**What:** Ollama server could fail or produce unexpected outputs.

**Mitigation:**
- Runs locally (no external dependency)
- Bot defaults to HOLD if LLM unavailable
- Response parsing handles malformed outputs

**Residual Risk:** LLM quality depends on hardware. Slow responses on underpowered machines.

---

## Operational Risks

### Single Operator
**What:** Currently only one person can operate and troubleshoot the system.

**Mitigation:**
- Comprehensive documentation (this initiative)
- Runbooks for common operations
- Autonomous monitor reduces need for human intervention

**Residual Risk:** Extended operator unavailability could leave issues unresolved.

### Configuration Errors
**What:** Incorrect settings could bypass risk controls or cause unintended behavior.

**Mitigation:**
- Risk limits are hardcoded, not configurable
- Configuration validated on startup
- Logs capture all configuration

**Residual Risk:** Code changes could inadvertently modify risk parameters.

---

## Learning System Risks

### Overfitting
**What:** System learns patterns specific to recent conditions that don't generalize.

**Mitigation:**
- Rules require multiple confirming trades
- Testing period before promotion
- Rules can be demoted if performance degrades

**Residual Risk:** Market regime changes may invalidate learned patterns.

### Feedback Loops
**What:** Bot's own trades could influence the patterns it learns from.

**Mitigation:**
- Position sizes too small to move markets
- 45-coin universe spreads impact
- Cooldowns prevent concentrated trading

**Residual Risk:** In illiquid Tier 3 coins, bot could theoretically influence prices.

### Rule Accumulation
**What:** Too many rules could create conflicting signals or analysis paralysis.

**Mitigation:**
- Rules have limited lifespan if unused
- Can manually prune rules
- LLM considers rule relevance

**Residual Risk:** No automatic rule pruning currently implemented.

---

## Financial Risks

### Capital Loss
**What:** Trading capital can be lost partially or entirely.

**Reality Check:**
- Paper trading has no real financial risk
- Phase 2 with real money: only risk capital you can afford to lose
- This is speculation, not investment

### Opportunity Cost
**What:** Capital deployed here cannot be used elsewhere.

**Consideration:** Compare expected returns to alternatives (index funds, staking, etc.)

---

## Regulatory Risks

### Tax Implications
**What:** Cryptocurrency trades may be taxable events.

**Status:**
- Paper trading: No tax implications
- Real trading: Consult tax professional
- Bot does not currently export tax-ready reports

### Regulatory Changes
**What:** Cryptocurrency regulation is evolving and uncertain.

**Consideration:** Regulatory changes could impact ability to trade or require compliance changes.

---

## Summary

This system has meaningful risk mitigations but is not risk-free. The conservative position sizing and stop-losses limit but do not eliminate potential losses.

**Before Real Money Trading:**
- Prove profitability in paper trading
- Understand all risks above
- Only use capital you can afford to lose completely
- Have plan for monitoring and intervention

---

*Last Updated: February 2026*
