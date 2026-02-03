"""
Trading System Configuration.

Central configuration for the autonomous trading bot.
"""

import os
from pathlib import Path

# =============================================================================
# Project Paths
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# =============================================================================
# Exchange Configuration
# =============================================================================

DEFAULT_EXCHANGE = os.getenv("TRADING_EXCHANGE", "bybit")

# =============================================================================
# Tradeable Coins
# =============================================================================

TRADEABLE_COINS = [
    # Tier 1 - Blue chips (high liquidity)
    "BTC", "ETH", "SOL", "BNB", "XRP",
    # Tier 2 - High volume
    "DOGE", "ADA", "AVAX", "LINK", "DOT",
    "MATIC", "UNI", "ATOM", "LTC", "ETC",
    # Tier 3 - More volatile
    "NEAR", "APT", "ARB", "OP", "INJ",
]

COIN_TIERS = {
    1: ["BTC", "ETH", "SOL", "BNB", "XRP"],
    2: ["DOGE", "ADA", "AVAX", "LINK", "DOT", "MATIC", "UNI", "ATOM", "LTC", "ETC"],
    3: ["NEAR", "APT", "ARB", "OP", "INJ"],
}

# =============================================================================
# Risk Management
# =============================================================================

MAX_POSITIONS = 5
MAX_POSITION_PER_COIN = 1
MAX_EXPOSURE_PCT = 0.10  # 10% of balance

DEFAULT_STOP_LOSS_PCT = 0.02    # 2%
DEFAULT_TAKE_PROFIT_PCT = 0.015  # 1.5%
DEFAULT_POSITION_SIZE_USD = 100.0

# =============================================================================
# Paper Trading
# =============================================================================

INITIAL_BALANCE = 10000.0

# =============================================================================
# Health Monitoring
# =============================================================================

STALE_DATA_THRESHOLD = 5  # seconds without tick = unhealthy
STATUS_LOG_INTERVAL = 60  # seconds between status logs

# =============================================================================
# Paths
# =============================================================================

DATABASE_PATH = str(DATA_DIR / "trading_bot.db")
SNIPER_STATE_PATH = str(DATA_DIR / "sniper_state.json")
