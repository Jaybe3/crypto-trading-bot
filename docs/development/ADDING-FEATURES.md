# Adding Features Guide

**Last Updated:** February 3, 2026
**Phase:** 2 Complete

Guide for adding new features to the trading bot.

---

## Feature Development Workflow

### 1. Create Task Spec

Before coding, create a task specification in `docs/specs/tasks/`:

```markdown
# TASK-XXX: Feature Name

## Overview
Brief description of what this feature does.

## Requirements
- [ ] Requirement 1
- [ ] Requirement 2

## Technical Approach
How will this be implemented?

## Files to Modify
- `src/component.py` - Add X
- `tests/test_component.py` - Add tests

## Testing
How will this be tested?

## Acceptance Criteria
When is this done?
```

### 2. Create Branch

```bash
git checkout -b feature/TASK-XXX-feature-name
```

### 3. Implement

Follow patterns in this guide.

### 4. Test

```bash
pytest tests/ -v
```

### 5. Document

Update relevant documentation.

### 6. Commit

```bash
git add .
git commit -m "TASK-XXX: Brief description"
```

---

## Common Feature Types

### Adding a New Metric

**Example:** Add "average hold time" metric

1. **Add to data model** (`src/models/quick_update.py`):
```python
@dataclass
class TradeResult:
    # ... existing fields
    duration_seconds: int = 0  # NEW
```

2. **Calculate in QuickUpdate** (`src/quick_update.py`):
```python
def process_trade_close(self, trade: TradeResult) -> QuickUpdateResult:
    # ... existing logic

    # NEW: Track hold time
    if trade.duration_seconds > 0:
        self._update_avg_hold_time(trade.coin, trade.duration_seconds)
```

3. **Store in database** (`src/database.py`):
```python
# Add column if needed
def _init_tables(self):
    # In coin_scores table
    """
    avg_hold_time_seconds REAL DEFAULT 0
    """
```

4. **Expose in Knowledge** (`src/knowledge.py`):
```python
def get_knowledge_context(self):
    return {
        # ... existing
        "avg_hold_times": self._get_avg_hold_times()  # NEW
    }
```

5. **Add tests**:
```python
def test_hold_time_tracked(scorer):
    trade = create_trade_result(duration_seconds=3600)
    scorer.process_trade_result(trade)

    score = scorer.get_coin_score(trade.coin)
    assert score.avg_hold_time > 0
```

---

### Adding a New Adaptation Type

**Example:** Add "PAUSE_COIN" adaptation (temporary halt)

1. **Define action** (`src/models/adaptation.py`):
```python
class AdaptationAction(Enum):
    BLACKLIST = "BLACKLIST"
    FAVOR = "FAVOR"
    REDUCE = "REDUCE"
    PAUSE_COIN = "PAUSE_COIN"  # NEW
```

2. **Handle in AdaptationEngine** (`src/adaptation.py`):
```python
def apply_adaptation(self, adaptation: Adaptation) -> AdaptationRecord:
    if adaptation.action == AdaptationAction.PAUSE_COIN:
        return self._apply_pause_coin(adaptation)
    # ... existing actions

def _apply_pause_coin(self, adaptation: Adaptation) -> AdaptationRecord:
    """Temporarily pause trading on a coin"""
    self.knowledge.pause_coin(
        adaptation.target,
        duration_minutes=adaptation.params.get("duration", 60)
    )
    return AdaptationRecord(
        action="PAUSE_COIN",
        target=adaptation.target,
        reason=adaptation.reason,
        # ... other fields
    )
```

3. **Support in KnowledgeBrain** (`src/knowledge.py`):
```python
def pause_coin(self, coin: str, duration_minutes: int):
    """Temporarily pause trading on a coin"""
    expires_at = datetime.now() + timedelta(minutes=duration_minutes)
    self._paused_coins[coin] = expires_at
    self.db.save_coin_pause(coin, expires_at)

def is_coin_paused(self, coin: str) -> bool:
    if coin not in self._paused_coins:
        return False
    if datetime.now() > self._paused_coins[coin]:
        del self._paused_coins[coin]
        return False
    return True
```

4. **Use in Strategist** (`src/strategist.py`):
```python
def _filter_coins(self, coins: List[str]) -> List[str]:
    """Filter out blacklisted and paused coins"""
    return [
        c for c in coins
        if not self.knowledge.is_blacklisted(c)
        and not self.knowledge.is_coin_paused(c)  # NEW
    ]
```

---

### Adding a New Dashboard Page

**Example:** Add "Patterns" page

1. **Add route** (`src/dashboard_v2.py`):
```python
@app.get("/patterns")
async def patterns_page(request: Request):
    """Pattern library page"""
    patterns = await get_patterns()
    return templates.TemplateResponse(
        "patterns.html",
        {"request": request, "patterns": patterns}
    )
```

2. **Add API endpoint**:
```python
@app.get("/api/patterns")
async def api_patterns():
    """Get all patterns with stats"""
    patterns = db.get_all_patterns()
    return {
        "patterns": [p.to_dict() for p in patterns],
        "total": len(patterns),
        "active": sum(1 for p in patterns if p.is_active)
    }
```

3. **Create template** (`templates/patterns.html`):
```html
{% extends "base.html" %}
{% block content %}
<h1>Pattern Library</h1>
<table>
    <tr>
        <th>Pattern</th>
        <th>Confidence</th>
        <th>Times Used</th>
        <th>Win Rate</th>
        <th>Status</th>
    </tr>
    {% for pattern in patterns %}
    <tr>
        <td>{{ pattern.description }}</td>
        <td>{{ pattern.confidence | round(2) }}</td>
        <td>{{ pattern.times_used }}</td>
        <td>{{ (pattern.win_rate * 100) | round(1) }}%</td>
        <td>{{ "Active" if pattern.is_active else "Inactive" }}</td>
    </tr>
    {% endfor %}
</table>
{% endblock %}
```

4. **Add navigation**:
```html
<!-- In base.html -->
<nav>
    <a href="/">Overview</a>
    <a href="/knowledge">Knowledge</a>
    <a href="/patterns">Patterns</a>  <!-- NEW -->
    <a href="/adaptations">Adaptations</a>
</nav>
```

---

### Adding a New Insight Type

**Example:** Add "correlation" insight

1. **Define insight type** (`src/models/reflection.py`):
```python
class InsightType(Enum):
    COIN = "coin"
    PATTERN = "pattern"
    TIME = "time"
    CORRELATION = "correlation"  # NEW
```

2. **Generate in Reflection** (`src/reflection.py`):
```python
async def _analyze_correlations(self, trades: List[Trade]) -> List[Insight]:
    """Analyze correlations between coins"""
    insights = []

    # Calculate correlation matrix
    correlations = self._calculate_correlations(trades)

    for (coin1, coin2), corr in correlations.items():
        if abs(corr) > 0.7:  # Strong correlation
            insights.append(Insight(
                insight_type=InsightType.CORRELATION,
                category="observation",
                title=f"{coin1}/{coin2} correlation",
                description=f"Strong {'positive' if corr > 0 else 'negative'} correlation ({corr:.2f})",
                evidence={"correlation": corr, "coins": [coin1, coin2]},
                confidence=abs(corr)
            ))

    return insights
```

3. **Handle in Adaptation** (`src/adaptation.py`):
```python
def _process_correlation_insight(self, insight: Insight) -> Optional[Adaptation]:
    """Convert correlation insight to adaptation"""
    corr = insight.evidence["correlation"]
    coins = insight.evidence["coins"]

    if corr > 0.8:
        # Suggest reducing simultaneous positions
        return Adaptation(
            action=AdaptationAction.CREATE_RULE,
            target=f"correlation_{coins[0]}_{coins[1]}",
            reason=f"High correlation between {coins[0]} and {coins[1]}",
            params={
                "type": "correlation",
                "coins": coins,
                "max_simultaneous": 1
            }
        )
    return None
```

---

### Adding Exchange Integration

**Example:** Add Binance live trading

1. **Create exchange client** (`src/exchanges/binance.py`):
```python
from binance.client import Client

class BinanceClient:
    def __init__(self, api_key: str, api_secret: str):
        self.client = Client(api_key, api_secret)

    async def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float
    ) -> dict:
        """Place market order"""
        return self.client.create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=quantity
        )

    async def get_balance(self, asset: str) -> float:
        """Get balance for asset"""
        account = self.client.get_account()
        for balance in account["balances"]:
            if balance["asset"] == asset:
                return float(balance["free"])
        return 0.0
```

2. **Create exchange interface** (`src/exchanges/interface.py`):
```python
from abc import ABC, abstractmethod

class ExchangeInterface(ABC):
    @abstractmethod
    async def place_market_order(self, symbol: str, side: str, quantity: float) -> dict:
        pass

    @abstractmethod
    async def get_balance(self, asset: str) -> float:
        pass

class PaperExchange(ExchangeInterface):
    """Paper trading implementation"""

    def __init__(self, initial_balance: float = 10000):
        self.balance = initial_balance

    async def place_market_order(self, symbol: str, side: str, quantity: float) -> dict:
        # Simulate order
        return {"orderId": uuid.uuid4().hex, "status": "FILLED"}

    async def get_balance(self, asset: str) -> float:
        return self.balance
```

3. **Use in Sniper** (`src/sniper.py`):
```python
class Sniper:
    def __init__(self, exchange: ExchangeInterface, journal: TradeJournal):
        self.exchange = exchange
        self.journal = journal

    async def _execute_entry(self, condition: TradeCondition):
        """Execute trade entry"""
        # Calculate quantity
        quantity = condition.position_size_usd / self.feed.get_price(condition.coin)

        # Place order
        order = await self.exchange.place_market_order(
            symbol=f"{condition.coin}USDT",
            side="BUY" if condition.direction == "LONG" else "SELL",
            quantity=quantity
        )

        # Record position
        # ...
```

---

## Code Style Guidelines

### Imports

```python
# Standard library
import os
import json
from datetime import datetime
from typing import List, Dict, Optional

# Third party
import pytest
from dataclasses import dataclass

# Local
from src.database import Database
from src.models.knowledge import CoinScore
```

### Type Hints

```python
def process_trade(
    self,
    trade: TradeResult,
    context: Optional[Dict[str, Any]] = None
) -> QuickUpdateResult:
    """Process a closed trade.

    Args:
        trade: The trade result to process
        context: Optional additional context

    Returns:
        QuickUpdateResult with any adaptations triggered
    """
    pass
```

### Error Handling

```python
def get_coin_score(self, coin: str) -> Optional[CoinScore]:
    """Get score for a coin.

    Returns None if coin not found.
    """
    try:
        return self.db.get_coin_score(coin)
    except Exception as e:
        logger.error(f"Error getting coin score for {coin}: {e}")
        return None
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

class CoinScorer:
    def process_trade_result(self, trade: TradeResult):
        logger.debug(f"Processing trade {trade.trade_id} for {trade.coin}")

        # ... processing

        if adaptation:
            logger.info(f"Adaptation triggered: {adaptation}")
```

---

## Testing New Features

### Test-First Approach

1. Write test that fails
2. Implement feature
3. Verify test passes
4. Refactor if needed

### Test Checklist

- [ ] Unit tests for new methods
- [ ] Integration test if touching multiple components
- [ ] Edge cases (empty inputs, errors)
- [ ] Test with mock dependencies
- [ ] Test with real database (integration)

### Example Test Structure

```python
class TestNewFeature:
    """Tests for new feature X"""

    def setup_method(self):
        """Setup for each test"""
        self.db = Database(":memory:")
        self.component = Component(self.db)

    def test_basic_functionality(self):
        """Feature should do X when Y"""
        result = self.component.new_method(input)
        assert result == expected

    def test_edge_case_empty_input(self):
        """Feature should handle empty input"""
        result = self.component.new_method([])
        assert result is None

    def test_error_handling(self):
        """Feature should handle errors gracefully"""
        with pytest.raises(ValueError):
            self.component.new_method(invalid_input)
```

---

## Documentation Requirements

When adding a feature, update:

1. **Component Reference** (`docs/architecture/COMPONENT-REFERENCE.md`)
   - Add new methods/classes

2. **Data Model** (`docs/architecture/DATA-MODEL.md`)
   - Add new tables/columns

3. **Testing Guide** (`docs/development/TESTING-GUIDE.md`)
   - Add test examples

4. **Relevant Operations Docs**
   - If feature affects operations

---

## Related Documentation

- [COMPONENT-GUIDE.md](./COMPONENT-GUIDE.md) - Component details
- [TESTING-GUIDE.md](./TESTING-GUIDE.md) - Testing practices
- [../architecture/SYSTEM-OVERVIEW.md](../architecture/SYSTEM-OVERVIEW.md) - Architecture
