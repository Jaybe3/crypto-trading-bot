# TASK-015: Volatility-Based Risk Adjustment

## Overview
Implement dynamic risk adjustment based on real-time market volatility. Position sizes and stop-losses will automatically adapt to current market conditions, providing smarter risk management beyond static tier-based rules.

## Current State
- Risk parameters are static per tier (3%, 5%, 7% stop-loss)
- Position sizes based only on tier and balance
- No consideration of current market volatility
- Same risk approach in calm vs turbulent markets

## Target State
- Rolling volatility calculated for each coin (24h, 7d)
- Position sizes scaled inversely to volatility
- Stop-loss distances based on ATR (Average True Range)
- Risk automatically tightens in volatile markets

---

## Volatility Metrics

### 1. Price Volatility (Standard Deviation of Returns)
```
volatility_24h = std_dev(hourly_returns, 24 periods)
volatility_7d = std_dev(daily_returns, 7 periods)
```

### 2. ATR (Average True Range)
```
True Range = max(high - low, |high - prev_close|, |low - prev_close|)
ATR = moving_average(True Range, 14 periods)
```

Since CoinGecko free tier doesn't provide OHLC, we'll use:
- **Proxy ATR**: Based on 24h price change magnitude
- **Historical Volatility**: From stored price snapshots

### 3. Volatility Score (0-100)
Normalize volatility into a score for easy comparison:
```
vol_score = min(100, (coin_volatility / market_avg_volatility) * 50)
```
- Score < 30: Low volatility
- Score 30-70: Normal volatility
- Score > 70: High volatility

---

## Position Size Adjustment

### Formula
```python
base_position = tier_max_position_pct * balance
volatility_multiplier = get_volatility_multiplier(vol_score)
adjusted_position = base_position * volatility_multiplier
```

### Volatility Multiplier Table
| Volatility Score | Multiplier | Effect |
|------------------|------------|--------|
| 0-20 (Very Low) | 1.2 | +20% position |
| 20-40 (Low) | 1.0 | No change |
| 40-60 (Normal) | 0.9 | -10% position |
| 60-80 (High) | 0.7 | -30% position |
| 80-100 (Extreme) | 0.5 | -50% position |

### Example
- Tier 3 coin (10% max = $100 on $1000 balance)
- Volatility score: 75 (High)
- Multiplier: 0.7
- Adjusted position: $100 × 0.7 = $70

---

## Dynamic Stop-Loss

### ATR-Based Stop-Loss
Instead of fixed percentage, use ATR multiples:
```python
stop_loss_distance = ATR * atr_multiplier
stop_loss_price = entry_price * (1 - stop_loss_distance)
```

### ATR Multiplier by Tier
| Tier | ATR Multiplier | Rationale |
|------|----------------|-----------|
| 1 | 1.5x ATR | Tighter for blue chips |
| 2 | 2.0x ATR | Moderate for established |
| 3 | 2.5x ATR | Wider for volatile coins |

### Minimum/Maximum Bounds
- **Minimum stop-loss**: 2% (prevent too tight)
- **Maximum stop-loss**: 15% (prevent unlimited risk)

---

## Implementation

### 1. Database Schema Update

Add `price_history` table for volatility calculation:

```sql
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coin TEXT NOT NULL,
    price_usd REAL NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_price_history_coin_time
ON price_history(coin, timestamp DESC);

-- Add volatility columns to market_data
ALTER TABLE market_data ADD COLUMN volatility_24h REAL;
ALTER TABLE market_data ADD COLUMN volatility_score INTEGER;
```

### 2. New Module: `src/volatility.py`

```python
"""Volatility calculation and risk adjustment.

Calculates rolling volatility metrics and provides
dynamic position sizing and stop-loss recommendations.
"""

import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from src.database import Database
from src.coin_config import get_tier, get_tier_config


# Volatility multiplier thresholds
VOLATILITY_MULTIPLIERS = [
    (20, 1.2),   # Very low volatility: +20%
    (40, 1.0),   # Low volatility: no change
    (60, 0.9),   # Normal volatility: -10%
    (80, 0.7),   # High volatility: -30%
    (100, 0.5),  # Extreme volatility: -50%
]

# ATR multipliers by tier
ATR_MULTIPLIERS = {
    1: 1.5,  # Blue chips: tighter stops
    2: 2.0,  # Established: moderate
    3: 2.5,  # High volatility: wider stops
}

# Stop-loss bounds
MIN_STOP_LOSS_PCT = 0.02  # 2% minimum
MAX_STOP_LOSS_PCT = 0.15  # 15% maximum


class VolatilityCalculator:
    """Calculates volatility metrics for risk adjustment."""

    def __init__(self, db: Database = None):
        self.db = db or Database()
        self._ensure_tables()

    def _ensure_tables(self):
        """Create price_history table if not exists."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coin TEXT NOT NULL,
                    price_usd REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_history_coin_time
                ON price_history(coin, timestamp DESC)
            """)
            conn.commit()

    def record_price(self, coin: str, price: float) -> None:
        """Record a price snapshot for volatility calculation."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO price_history (coin, price_usd)
                VALUES (?, ?)
            """, (coin, price))
            conn.commit()

    def record_all_prices(self, prices: Dict[str, float]) -> int:
        """Record prices for all coins."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            for coin, price in prices.items():
                cursor.execute("""
                    INSERT INTO price_history (coin, price_usd)
                    VALUES (?, ?)
                """, (coin, price))
            conn.commit()
        return len(prices)

    def get_price_history(
        self, coin: str, hours: int = 24
    ) -> List[Tuple[float, str]]:
        """Get price history for a coin."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT price_usd, timestamp
                FROM price_history
                WHERE coin = ?
                AND timestamp > datetime('now', ?)
                ORDER BY timestamp ASC
            """, (coin, f'-{hours} hours'))
            return [(row[0], row[1]) for row in cursor.fetchall()]

    def calculate_volatility(self, coin: str, hours: int = 24) -> float:
        """Calculate volatility as standard deviation of returns.

        Returns:
            Volatility as a decimal (e.g., 0.05 = 5%)
        """
        history = self.get_price_history(coin, hours)

        if len(history) < 2:
            # Not enough data, return tier default
            config = get_tier_config(coin)
            return config.stop_loss_pct

        # Calculate returns
        prices = [h[0] for h in history]
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)

        if not returns:
            config = get_tier_config(coin)
            return config.stop_loss_pct

        # Standard deviation of returns
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)

        # Annualize (optional, for comparison)
        # For hourly data over 24h, multiply by sqrt(24)
        return std_dev

    def calculate_volatility_score(self, coin: str) -> int:
        """Calculate normalized volatility score (0-100).

        Score interpretation:
        - 0-30: Low volatility
        - 30-70: Normal volatility
        - 70-100: High volatility
        """
        vol = self.calculate_volatility(coin, hours=24)

        # Use 24h change as additional signal
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT change_24h FROM market_data WHERE coin = ?",
                (coin,)
            )
            row = cursor.fetchone()
            change_24h = abs(row[0]) if row and row[0] else 0

        # Combine volatility and 24h change
        # Higher change = higher score
        base_score = min(100, vol * 1000)  # Scale volatility
        change_score = min(50, change_24h * 5)  # 10% change = 50 points

        combined = (base_score * 0.6) + (change_score * 0.4)
        return min(100, int(combined))

    def get_volatility_multiplier(self, vol_score: int) -> float:
        """Get position size multiplier based on volatility score."""
        for threshold, multiplier in VOLATILITY_MULTIPLIERS:
            if vol_score <= threshold:
                return multiplier
        return 0.5  # Default to most conservative

    def calculate_dynamic_stop_loss(
        self, coin: str, entry_price: float
    ) -> Tuple[float, float]:
        """Calculate dynamic stop-loss based on volatility.

        Returns:
            Tuple of (stop_loss_price, stop_loss_pct)
        """
        tier = get_tier(coin)
        tier_config = get_tier_config(coin)
        atr_mult = ATR_MULTIPLIERS.get(tier, 2.0)

        # Calculate volatility-based stop distance
        vol = self.calculate_volatility(coin, hours=24)
        stop_distance = vol * atr_mult

        # Apply bounds
        stop_pct = max(MIN_STOP_LOSS_PCT, min(MAX_STOP_LOSS_PCT, stop_distance))

        # Ensure at least tier minimum
        stop_pct = max(stop_pct, tier_config.stop_loss_pct * 0.5)

        stop_price = entry_price * (1 - stop_pct)
        return stop_price, stop_pct

    def get_adjusted_position_size(
        self, coin: str, base_position: float
    ) -> Tuple[float, Dict]:
        """Get volatility-adjusted position size.

        Args:
            coin: Coin ID
            base_position: Base position size from tier config

        Returns:
            Tuple of (adjusted_size, adjustment_info)
        """
        vol_score = self.calculate_volatility_score(coin)
        multiplier = self.get_volatility_multiplier(vol_score)
        adjusted = base_position * multiplier

        return adjusted, {
            'volatility_score': vol_score,
            'multiplier': multiplier,
            'base_position': base_position,
            'adjusted_position': adjusted,
            'reduction_pct': (1 - multiplier) * 100
        }

    def cleanup_old_history(self, days: int = 7) -> int:
        """Remove price history older than specified days."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM price_history
                WHERE timestamp < datetime('now', ?)
            """, (f'-{days} days',))
            deleted = cursor.rowcount
            conn.commit()
        return deleted

    def get_volatility_summary(self) -> Dict[str, Dict]:
        """Get volatility summary for all tracked coins."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT coin FROM market_data")
            coins = [row[0] for row in cursor.fetchall()]

        summary = {}
        for coin in coins:
            vol_score = self.calculate_volatility_score(coin)
            multiplier = self.get_volatility_multiplier(vol_score)
            summary[coin] = {
                'volatility_score': vol_score,
                'multiplier': multiplier,
                'tier': get_tier(coin)
            }

        return summary
```

### 3. Update `src/risk_manager.py`

Add volatility-aware methods:

```python
from src.volatility import VolatilityCalculator

class RiskManager:
    def __init__(self, db: Database = None):
        # ... existing init ...
        self.volatility = VolatilityCalculator(db=self.db)

    def get_volatility_adjusted_limits(self, coin: str) -> Dict[str, Any]:
        """Get position limits adjusted for current volatility."""
        tier_limits = self.get_tier_limits(coin)
        base_position = tier_limits['max_position_usd']

        # Get volatility adjustment
        adjusted, vol_info = self.volatility.get_adjusted_position_size(
            coin, base_position
        )

        # Get dynamic stop-loss
        # (Need entry price, so return the percentage)
        vol_score = vol_info['volatility_score']

        return {
            **tier_limits,
            'volatility_score': vol_score,
            'volatility_multiplier': vol_info['multiplier'],
            'adjusted_max_position': adjusted,
            'position_reduction_pct': vol_info['reduction_pct']
        }

    def calculate_volatility_stop_loss(
        self, coin: str, entry_price: float
    ) -> float:
        """Calculate volatility-adjusted stop-loss price."""
        stop_price, _ = self.volatility.calculate_dynamic_stop_loss(
            coin, entry_price
        )
        return stop_price
```

### 4. Update `src/market_data.py`

Record prices for volatility calculation:

```python
def update_all_prices(self) -> Dict[str, Any]:
    # ... existing code ...

    # Record prices for volatility calculation
    from src.volatility import VolatilityCalculator
    vc = VolatilityCalculator(db=self.db)

    prices_to_record = {
        coin: data['price_usd']
        for coin, data in prices.items()
        if stats['updated'] > 0
    }
    vc.record_all_prices(prices_to_record)

    return stats
```

### 5. Update Dashboard

Add volatility column to market data display:
```html
<span class="vol-score vol-{{ 'low' if data.vol_score < 30 else 'high' if data.vol_score > 70 else 'normal' }}">
    V:{{ data.vol_score }}
</span>
```

---

## Acceptance Criteria

- [ ] Price history table created and populated
- [ ] Volatility calculated for all coins with sufficient data
- [ ] Volatility score (0-100) computed correctly
- [ ] Position sizes adjust based on volatility multiplier
- [ ] Stop-loss distances respect min/max bounds
- [ ] Dashboard shows volatility scores
- [ ] Old price history cleaned up (>7 days)
- [ ] Existing tier-based logic still works as fallback

---

## Testing Plan

### Step 1: Verify Price History Recording
```python
from src.volatility import VolatilityCalculator
vc = VolatilityCalculator()

# Record some prices
vc.record_price("bitcoin", 95000)
vc.record_price("bitcoin", 95500)

# Check history
history = vc.get_price_history("bitcoin", hours=1)
assert len(history) >= 2
```

### Step 2: Verify Volatility Calculation
```python
# Need data first, so run after a few cycles
vol = vc.calculate_volatility("bitcoin", hours=24)
print(f"Bitcoin 24h volatility: {vol:.4f}")

score = vc.calculate_volatility_score("bitcoin")
print(f"Bitcoin volatility score: {score}")
```

### Step 3: Verify Position Adjustment
```python
from src.risk_manager import RiskManager
rm = RiskManager()

# Compare base vs adjusted
base_limits = rm.get_tier_limits("pepe")
adj_limits = rm.get_volatility_adjusted_limits("pepe")

print(f"Base max position: ${base_limits['max_position_usd']:.2f}")
print(f"Adjusted max position: ${adj_limits['adjusted_max_position']:.2f}")
print(f"Volatility score: {adj_limits['volatility_score']}")
```

### Step 4: Verify Stop-Loss Calculation
```python
entry_price = 0.00001234
stop_price = rm.calculate_volatility_stop_loss("pepe", entry_price)
stop_pct = (entry_price - stop_price) / entry_price * 100

print(f"Entry: ${entry_price}")
print(f"Stop-loss: ${stop_price}")
print(f"Distance: {stop_pct:.1f}%")
```

---

## Files to Create/Modify

| File | Action | Changes |
|------|--------|---------|
| `src/volatility.py` | CREATE | Volatility calculation module |
| `src/risk_manager.py` | MODIFY | Add volatility-aware methods |
| `src/market_data.py` | MODIFY | Record prices for history |
| `src/dashboard.py` | MODIFY | Show volatility scores |
| `src/database.py` | MODIFY | Add price_history table |

---

## Rollback Plan

If volatility adjustment causes issues:
1. Set all volatility multipliers to 1.0 (no adjustment)
2. Fall back to tier-based stop-loss percentages
3. Price history recording can continue (no harm)
