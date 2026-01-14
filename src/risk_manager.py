"""Risk management and trade validation.

Enforces all risk rules to protect the account from excessive losses.
Rules are NON-NEGOTIABLE - they cannot be overridden by the LLM.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional

from src.database import Database
from src.coin_config import get_tier, get_tier_config, TIERS
from src.volatility import VolatilityCalculator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Risk parameters - NON-NEGOTIABLE
MAX_TRADE_PERCENT = 0.02      # 2% max per trade
MAX_EXPOSURE_PERCENT = 0.10   # 10% max total exposure
MIN_BALANCE = 900.0           # Minimum balance to maintain
STOP_LOSS_PERCENT = 0.10      # 10% stop loss
TAKE_PROFIT_USD = 1.0         # $1 take profit per trade


@dataclass
class TradeValidation:
    """Result of trade validation check."""
    valid: bool
    reason: str
    max_allowed_size: float


class RiskManager:
    """Enforces risk management rules for all trades.

    All rules are NON-NEGOTIABLE and cannot be overridden.
    """

    def __init__(self, db: Database = None):
        """Initialize with database connection.

        Args:
            db: Database instance. If None, creates new connection.
        """
        self.db = db or Database()

        # Store risk parameters as instance variables for inspection
        self.max_trade_percent = MAX_TRADE_PERCENT
        self.max_exposure_percent = MAX_EXPOSURE_PERCENT
        self.min_balance = MIN_BALANCE
        self.stop_loss_percent = STOP_LOSS_PERCENT
        self.take_profit_usd = TAKE_PROFIT_USD

        logger.info("RiskManager initialized with NON-NEGOTIABLE rules:")
        logger.info(f"  Max trade: {self.max_trade_percent*100}% of balance")
        logger.info(f"  Max exposure: {self.max_exposure_percent*100}% of balance")
        logger.info(f"  Min balance: ${self.min_balance}")
        logger.info(f"  Stop loss: {self.stop_loss_percent*100}%")
        logger.info(f"  Take profit: ${self.take_profit_usd}")

    def get_risk_parameters(self) -> Dict[str, float]:
        """Get current risk parameters.

        Returns:
            Dictionary with all risk parameters.
        """
        return {
            'max_trade_percent': self.max_trade_percent,
            'max_exposure_percent': self.max_exposure_percent,
            'min_balance': self.min_balance,
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_usd': self.take_profit_usd
        }

    def get_account_state(self) -> Dict[str, Any]:
        """Get current account state from database.

        Returns:
            Account state dictionary.
        """
        return self.db.get_account_state()

    def get_available_for_trading(self) -> float:
        """Calculate how much USD is available for new trades.

        This accounts for:
        - Current balance
        - Amount already in positions
        - Minimum balance requirement
        - Maximum exposure limit

        Returns:
            USD amount available for trading.
        """
        state = self.get_account_state()
        balance = state.get('balance', 0)
        in_positions = state.get('in_positions', 0)

        # Calculate limits
        max_exposure_usd = balance * self.max_exposure_percent
        exposure_remaining = max_exposure_usd - in_positions

        # Must maintain minimum balance
        above_minimum = balance - self.min_balance

        # Available is the smaller of exposure remaining and above minimum
        available = min(exposure_remaining, above_minimum)

        # Cannot be negative
        return max(0, available)

    def calculate_max_trade_size(self) -> float:
        """Calculate maximum size for a single trade.

        Returns:
            Maximum USD for one trade.
        """
        state = self.get_account_state()
        balance = state.get('balance', 0)

        # Max per trade is 2% of balance
        max_per_trade = balance * self.max_trade_percent

        # But also limited by available for trading
        available = self.get_available_for_trading()

        return min(max_per_trade, available)

    def validate_trade(self, coin: str, size_usd: float, action: str = "BUY") -> TradeValidation:
        """Validate a proposed trade against all risk rules.

        Args:
            coin: Cryptocurrency name (e.g., 'bitcoin').
            size_usd: Size of trade in USD.
            action: Trade action ('BUY' or 'SELL').

        Returns:
            TradeValidation with valid flag, reason, and max allowed size.
        """
        state = self.get_account_state()
        balance = state.get('balance', 0)
        in_positions = state.get('in_positions', 0)
        available_balance = state.get('available_balance', balance)

        max_allowed = self.calculate_max_trade_size()

        # Rule 1: Check minimum balance would be maintained
        if action == "BUY":
            balance_after = balance - size_usd
            if balance_after < self.min_balance:
                return TradeValidation(
                    valid=False,
                    reason=f"Trade would put balance (${balance_after:.2f}) below minimum (${self.min_balance})",
                    max_allowed_size=max_allowed
                )

        # Rule 2: Check max trade size (2% of balance)
        max_trade_usd = balance * self.max_trade_percent
        if size_usd > max_trade_usd:
            return TradeValidation(
                valid=False,
                reason=f"Trade size (${size_usd:.2f}) exceeds max per trade (${max_trade_usd:.2f}, {self.max_trade_percent*100}% of balance)",
                max_allowed_size=max_allowed
            )

        # Rule 3: Check max total exposure (10% of balance)
        if action == "BUY":
            exposure_after = in_positions + size_usd
            max_exposure_usd = balance * self.max_exposure_percent
            if exposure_after > max_exposure_usd:
                return TradeValidation(
                    valid=False,
                    reason=f"Total exposure (${exposure_after:.2f}) would exceed max (${max_exposure_usd:.2f}, {self.max_exposure_percent*100}% of balance)",
                    max_allowed_size=max_allowed
                )

        # Rule 4: Check we have available balance
        if action == "BUY" and size_usd > available_balance:
            return TradeValidation(
                valid=False,
                reason=f"Trade size (${size_usd:.2f}) exceeds available balance (${available_balance:.2f})",
                max_allowed_size=max_allowed
            )

        # All rules passed
        return TradeValidation(
            valid=True,
            reason="Trade passes all risk checks",
            max_allowed_size=max_allowed
        )

    def calculate_stop_loss(self, entry_price: float) -> float:
        """Calculate stop loss price for a trade.

        Stop loss is set at -10% from entry price.

        Args:
            entry_price: Entry price in USD.

        Returns:
            Stop loss price in USD.
        """
        return entry_price * (1 - self.stop_loss_percent)

    def calculate_take_profit(self, entry_price: float, size_usd: float) -> float:
        """Calculate take profit price for a trade.

        Take profit is set to achieve +$1 profit.

        Formula: take_profit = entry_price * (1 + profit_usd / size_usd)

        Args:
            entry_price: Entry price in USD.
            size_usd: Trade size in USD.

        Returns:
            Take profit price in USD.
        """
        profit_percent = self.take_profit_usd / size_usd
        return entry_price * (1 + profit_percent)

    def check_stop_loss(self, entry_price: float, current_price: float) -> bool:
        """Check if stop loss has been triggered.

        Args:
            entry_price: Entry price in USD.
            current_price: Current price in USD.

        Returns:
            True if stop loss triggered (should exit).
        """
        stop_loss_price = self.calculate_stop_loss(entry_price)
        return current_price <= stop_loss_price

    def check_take_profit(self, entry_price: float, current_price: float, size_usd: float) -> bool:
        """Check if take profit has been reached.

        Args:
            entry_price: Entry price in USD.
            current_price: Current price in USD.
            size_usd: Trade size in USD.

        Returns:
            True if take profit reached (should exit).
        """
        take_profit_price = self.calculate_take_profit(entry_price, size_usd)
        return current_price >= take_profit_price

    def should_exit_trade(self, entry_price: float, current_price: float, size_usd: float) -> Dict[str, Any]:
        """Check if a trade should be exited.

        Args:
            entry_price: Entry price in USD.
            current_price: Current price in USD.
            size_usd: Trade size in USD.

        Returns:
            Dictionary with 'should_exit', 'reason', 'pnl_usd', 'pnl_pct'.
        """
        # Calculate current P&L
        price_change_pct = (current_price - entry_price) / entry_price
        pnl_usd = size_usd * price_change_pct
        pnl_pct = price_change_pct * 100

        # Check stop loss
        if self.check_stop_loss(entry_price, current_price):
            return {
                'should_exit': True,
                'reason': 'stop_loss',
                'pnl_usd': pnl_usd,
                'pnl_pct': pnl_pct
            }

        # Check take profit
        if self.check_take_profit(entry_price, current_price, size_usd):
            return {
                'should_exit': True,
                'reason': 'take_profit',
                'pnl_usd': pnl_usd,
                'pnl_pct': pnl_pct
            }

        # No exit triggered
        return {
            'should_exit': False,
            'reason': 'none',
            'pnl_usd': pnl_usd,
            'pnl_pct': pnl_pct
        }

    def log_risk_check(self, coin: str, size_usd: float, validation: TradeValidation) -> None:
        """Log a risk check to the activity log.

        Args:
            coin: Cryptocurrency name.
            size_usd: Proposed trade size.
            validation: Validation result.
        """
        activity_type = "risk_check_passed" if validation.valid else "risk_check_failed"
        description = f"Risk check for {coin} ${size_usd:.2f}: {validation.reason}"

        self.db.log_activity(
            activity_type=activity_type,
            description=description,
            details=f"max_allowed: ${validation.max_allowed_size:.2f}"
        )

    # =========================================================================
    # TIER-BASED RISK MANAGEMENT
    # =========================================================================

    def get_tier_limits(self, coin: str) -> Dict[str, Any]:
        """Get tier-specific position limits for a coin.

        Args:
            coin: Coin ID (e.g., 'bitcoin').

        Returns:
            Dict with tier-specific limits:
            - tier: Tier number (1, 2, or 3)
            - tier_name: Human-readable tier name
            - max_position_pct: Max % of balance for this tier
            - max_position_usd: Max USD for this tier (calculated)
            - stop_loss_pct: Stop loss % for this tier
            - take_profit_usd: Take profit amount
            - max_concurrent: Max positions in this tier
        """
        tier = get_tier(coin)
        config = get_tier_config(coin)
        state = self.get_account_state()
        balance = state.get('balance', 0)

        return {
            'tier': tier,
            'tier_name': config.name,
            'max_position_pct': config.max_position_pct,
            'max_position_usd': balance * config.max_position_pct,
            'stop_loss_pct': config.stop_loss_pct,
            'take_profit_usd': config.take_profit_usd,
            'max_concurrent': config.max_concurrent
        }

    def count_positions_in_tier(self, tier: int) -> int:
        """Count open positions in a specific tier.

        Args:
            tier: Tier number (1, 2, or 3).

        Returns:
            Number of open positions in that tier.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT coin_name FROM open_trades")
            open_coins = [row[0] for row in cursor.fetchall()]

        return sum(1 for coin in open_coins if get_tier(coin) == tier)

    def validate_trade_with_tier(self, coin: str, size_usd: float, action: str = "BUY") -> TradeValidation:
        """Validate a trade with tier-specific rules.

        This extends validate_trade with tier-based limits:
        - Tier-specific position size limits
        - Per-tier concurrent position limits

        Args:
            coin: Coin ID.
            size_usd: Trade size in USD.
            action: 'BUY' or 'SELL'.

        Returns:
            TradeValidation result.
        """
        # First run standard validation
        base_validation = self.validate_trade(coin, size_usd, action)
        if not base_validation.valid:
            return base_validation

        # Get tier-specific limits
        tier_limits = self.get_tier_limits(coin)
        tier = tier_limits['tier']
        config = get_tier_config(coin)

        # Check tier-specific position size
        if size_usd > tier_limits['max_position_usd']:
            return TradeValidation(
                valid=False,
                reason=f"Trade ${size_usd:.2f} exceeds {tier_limits['tier_name']} max ${tier_limits['max_position_usd']:.2f} ({config.max_position_pct:.0%})",
                max_allowed_size=tier_limits['max_position_usd']
            )

        # Check tier concurrent position limit
        if action == "BUY":
            current_in_tier = self.count_positions_in_tier(tier)
            if current_in_tier >= config.max_concurrent:
                return TradeValidation(
                    valid=False,
                    reason=f"Already have {current_in_tier}/{config.max_concurrent} positions in {tier_limits['tier_name']} tier",
                    max_allowed_size=0
                )

        return TradeValidation(
            valid=True,
            reason=f"Trade passes all checks (Tier {tier}: {tier_limits['tier_name']})",
            max_allowed_size=tier_limits['max_position_usd']
        )

    def calculate_tier_stop_loss(self, coin: str, entry_price: float) -> float:
        """Calculate tier-specific stop loss price.

        Uses tier-specific stop loss percentage.

        Args:
            coin: Coin ID.
            entry_price: Entry price in USD.

        Returns:
            Stop loss price in USD.
        """
        config = get_tier_config(coin)
        return entry_price * (1 - config.stop_loss_pct)

    def calculate_tier_take_profit(self, coin: str, entry_price: float, size_usd: float) -> float:
        """Calculate tier-specific take profit price.

        Uses consistent $1 take profit across all tiers.

        Args:
            coin: Coin ID.
            entry_price: Entry price in USD.
            size_usd: Trade size in USD.

        Returns:
            Take profit price in USD.
        """
        config = get_tier_config(coin)
        profit_percent = config.take_profit_usd / size_usd
        return entry_price * (1 + profit_percent)

    def should_exit_trade_with_tier(
        self, coin: str, entry_price: float, current_price: float, size_usd: float
    ) -> Dict[str, Any]:
        """Check if a trade should exit using tier-specific rules.

        Args:
            coin: Coin ID.
            entry_price: Entry price in USD.
            current_price: Current price in USD.
            size_usd: Trade size in USD.

        Returns:
            Dict with should_exit, reason, pnl_usd, pnl_pct.
        """
        config = get_tier_config(coin)

        # Calculate P&L
        price_change_pct = (current_price - entry_price) / entry_price
        pnl_usd = size_usd * price_change_pct
        pnl_pct = price_change_pct * 100

        # Check tier-specific stop loss
        stop_loss_price = self.calculate_tier_stop_loss(coin, entry_price)
        if current_price <= stop_loss_price:
            return {
                'should_exit': True,
                'reason': 'stop_loss',
                'pnl_usd': pnl_usd,
                'pnl_pct': pnl_pct,
                'tier': get_tier(coin)
            }

        # Check take profit ($1)
        take_profit_price = self.calculate_tier_take_profit(coin, entry_price, size_usd)
        if current_price >= take_profit_price:
            return {
                'should_exit': True,
                'reason': 'take_profit',
                'pnl_usd': pnl_usd,
                'pnl_pct': pnl_pct,
                'tier': get_tier(coin)
            }

        return {
            'should_exit': False,
            'reason': 'none',
            'pnl_usd': pnl_usd,
            'pnl_pct': pnl_pct,
            'tier': get_tier(coin)
        }

    def get_tier_summary(self) -> Dict[int, Dict[str, Any]]:
        """Get summary of positions and limits by tier.

        Returns:
            Dict mapping tier number to summary stats.
        """
        result = {}
        state = self.get_account_state()
        balance = state.get('balance', 0)

        for tier, config in TIERS.items():
            positions = self.count_positions_in_tier(tier)
            result[tier] = {
                'name': config.name,
                'positions': positions,
                'max_positions': config.max_concurrent,
                'slots_available': config.max_concurrent - positions,
                'max_position_usd': balance * config.max_position_pct,
                'stop_loss_pct': config.stop_loss_pct
            }

        return result

    # =========================================================================
    # VOLATILITY-BASED RISK ADJUSTMENT
    # =========================================================================

    def get_volatility_adjusted_limits(self, coin: str) -> Dict[str, Any]:
        """Get position limits adjusted for current volatility.

        Combines tier-based limits with volatility adjustments for
        smarter risk management in turbulent markets.

        Args:
            coin: Coin ID.

        Returns:
            Dict with tier limits plus volatility adjustments:
            - All tier_limits fields
            - volatility_score: Current volatility score (0-100)
            - volatility_multiplier: Position size multiplier
            - adjusted_max_position: Volatility-adjusted max position
            - position_reduction_pct: How much position is reduced
        """
        tier_limits = self.get_tier_limits(coin)
        base_position = tier_limits['max_position_usd']

        # Get volatility adjustment
        try:
            vc = VolatilityCalculator(db=self.db)
            adjusted, vol_info = vc.get_adjusted_position_size(coin, base_position)

            return {
                **tier_limits,
                'volatility_score': vol_info['volatility_score'],
                'volatility_multiplier': vol_info['multiplier'],
                'adjusted_max_position': adjusted,
                'position_reduction_pct': vol_info['reduction_pct']
            }
        except Exception as e:
            logger.warning(f"Volatility calculation failed for {coin}: {e}")
            # Fall back to tier limits without adjustment
            return {
                **tier_limits,
                'volatility_score': 50,  # Assume normal
                'volatility_multiplier': 1.0,
                'adjusted_max_position': base_position,
                'position_reduction_pct': 0
            }

    def calculate_volatility_stop_loss(self, coin: str, entry_price: float) -> float:
        """Calculate volatility-adjusted stop-loss price.

        Uses ATR-based calculation scaled by tier for more responsive
        stop-losses that adapt to market conditions.

        Args:
            coin: Coin ID.
            entry_price: Entry price in USD.

        Returns:
            Stop-loss price in USD.
        """
        try:
            vc = VolatilityCalculator(db=self.db)
            stop_price, _ = vc.calculate_dynamic_stop_loss(coin, entry_price)
            return stop_price
        except Exception as e:
            logger.warning(f"Volatility stop-loss calculation failed for {coin}: {e}")
            # Fall back to tier-based stop-loss
            return self.calculate_tier_stop_loss(coin, entry_price)

    def should_exit_trade_with_volatility(
        self, coin: str, entry_price: float, current_price: float, size_usd: float
    ) -> Dict[str, Any]:
        """Check if trade should exit using volatility-adjusted stop-loss.

        Args:
            coin: Coin ID.
            entry_price: Entry price in USD.
            current_price: Current price in USD.
            size_usd: Trade size in USD.

        Returns:
            Dict with should_exit, reason, pnl_usd, pnl_pct, volatility_score.
        """
        config = get_tier_config(coin)

        # Calculate P&L
        price_change_pct = (current_price - entry_price) / entry_price
        pnl_usd = size_usd * price_change_pct
        pnl_pct = price_change_pct * 100

        # Get volatility info
        try:
            vc = VolatilityCalculator(db=self.db)
            vol_score = vc.calculate_volatility_score(coin)
        except Exception:
            vol_score = 50

        # Check volatility-adjusted stop loss
        stop_loss_price = self.calculate_volatility_stop_loss(coin, entry_price)
        if current_price <= stop_loss_price:
            return {
                'should_exit': True,
                'reason': 'stop_loss',
                'pnl_usd': pnl_usd,
                'pnl_pct': pnl_pct,
                'tier': get_tier(coin),
                'volatility_score': vol_score
            }

        # Check take profit ($1 - consistent across tiers)
        take_profit_price = self.calculate_tier_take_profit(coin, entry_price, size_usd)
        if current_price >= take_profit_price:
            return {
                'should_exit': True,
                'reason': 'take_profit',
                'pnl_usd': pnl_usd,
                'pnl_pct': pnl_pct,
                'tier': get_tier(coin),
                'volatility_score': vol_score
            }

        return {
            'should_exit': False,
            'reason': 'none',
            'pnl_usd': pnl_usd,
            'pnl_pct': pnl_pct,
            'tier': get_tier(coin),
            'volatility_score': vol_score
        }


def get_risk_summary(db: Database = None) -> Dict[str, Any]:
    """Get a summary of current risk status.

    Args:
        db: Database instance.

    Returns:
        Dictionary with risk summary.
    """
    rm = RiskManager(db=db)
    state = rm.get_account_state()

    balance = state.get('balance', 0)
    in_positions = state.get('in_positions', 0)

    return {
        'balance': balance,
        'in_positions': in_positions,
        'exposure_percent': (in_positions / balance * 100) if balance > 0 else 0,
        'available_for_trading': rm.get_available_for_trading(),
        'max_single_trade': rm.calculate_max_trade_size(),
        'above_minimum': balance > rm.min_balance,
        'risk_parameters': rm.get_risk_parameters()
    }
