"""Web dashboard for monitoring the trading bot.

Displays real-time market data, account state, and trade information.
All data comes directly from the database - no simulation.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

from flask import Flask, render_template_string, jsonify

# Add parent directory to path for imports when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import Database
from src.market_data import format_price
from src.coin_config import get_tier
from src.volatility import VolatilityCalculator
from src.metrics import MetricsCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Dashboard HTML template
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Crypto Trading Bot - Dashboard</title>
    <meta http-equiv="refresh" content="5">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
            min-height: 100vh;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            background: #16213e;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .header h1 {
            color: #00d9ff;
            font-size: 1.5em;
        }
        .status {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #00ff88;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
        }
        .card h2 {
            color: #00d9ff;
            font-size: 1.1em;
            margin-bottom: 15px;
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
        }
        .price-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #333;
        }
        .price-row:last-child {
            border-bottom: none;
        }
        .coin-name {
            font-weight: bold;
            text-transform: uppercase;
        }
        .price {
            font-family: 'Courier New', monospace;
            font-size: 1.1em;
        }
        .change {
            font-size: 0.9em;
            padding: 2px 8px;
            border-radius: 4px;
        }
        .change.positive {
            color: #00ff88;
            background: rgba(0, 255, 136, 0.1);
        }
        .change.negative {
            color: #ff4757;
            background: rgba(255, 71, 87, 0.1);
        }
        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
        }
        .stat-label {
            color: #888;
        }
        .stat-value {
            font-family: 'Courier New', monospace;
            font-weight: bold;
        }
        .stat-value.profit {
            color: #00ff88;
        }
        .stat-value.loss {
            color: #ff4757;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th, td {
            padding: 12px 8px;
            text-align: left;
            border-bottom: 1px solid #333;
        }
        th {
            color: #888;
            font-weight: normal;
            font-size: 0.85em;
            text-transform: uppercase;
        }
        td {
            font-family: 'Courier New', monospace;
        }
        .empty-message {
            color: #666;
            text-align: center;
            padding: 30px;
            font-style: italic;
        }
        .footer {
            text-align: center;
            color: #666;
            padding: 20px;
            font-size: 0.85em;
        }
        .refresh-note {
            color: #00d9ff;
        }
        /* Learnings styles */
        .learning-item {
            padding: 12px;
            border-bottom: 1px solid #333;
            margin-bottom: 8px;
        }
        .learning-item:last-child {
            border-bottom: none;
        }
        .learning-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .learning-coin {
            font-weight: bold;
            color: #00d9ff;
            text-transform: uppercase;
        }
        .confidence {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.85em;
        }
        .confidence.high { background: rgba(0, 255, 136, 0.2); color: #00ff88; }
        .confidence.medium { background: rgba(255, 193, 7, 0.2); color: #ffc107; }
        .confidence.low { background: rgba(255, 71, 87, 0.2); color: #ff4757; }
        .learning-lesson {
            color: #eee;
            line-height: 1.4;
        }
        .learning-pattern {
            color: #888;
            font-size: 0.85em;
            margin-top: 6px;
            font-style: italic;
        }
        /* Rules styles */
        .rules-section-title {
            font-size: 0.9em;
            margin: 15px 0 10px 0;
            padding-bottom: 5px;
            border-bottom: 1px solid #333;
        }
        .rules-section-title.active { color: #00ff88; }
        .rules-section-title.testing { color: #ffc107; }
        .rule-item {
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.03);
        }
        .rule-item.active { border-left: 3px solid #00ff88; }
        .rule-item.testing { border-left: 3px solid #ffc107; }
        .rule-text {
            color: #eee;
            margin-bottom: 6px;
        }
        .rule-stats {
            font-size: 0.85em;
            color: #888;
        }
        .success-rate {
            color: #00ff88;
            margin-right: 10px;
        }
        /* Tier badges */
        .tier-badge {
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.7em;
            font-weight: bold;
            margin-left: 6px;
        }
        .tier-1 { background: #ffd700; color: #000; }
        .tier-2 { background: #c0c0c0; color: #000; }
        .tier-3 { background: #cd7f32; color: #fff; }
        /* Market data grid for many coins */
        .market-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 8px;
            max-height: 400px;
            overflow-y: auto;
        }
        .market-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 4px;
        }
        .market-item .coin-info {
            display: flex;
            align-items: center;
        }
        .market-item .stats {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        /* Volatility score badge */
        .vol-badge {
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 0.7em;
            font-weight: bold;
        }
        .vol-low { background: #00ff88; color: #000; }
        .vol-normal { background: #ffc107; color: #000; }
        .vol-high { background: #ff4757; color: #fff; }
        /* Performance metrics */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        .metric-box {
            text-align: center;
            padding: 10px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 6px;
        }
        .metric-value {
            font-size: 1.5em;
            font-weight: bold;
            font-family: 'Courier New', monospace;
        }
        .metric-label {
            font-size: 0.8em;
            color: #888;
            margin-top: 4px;
        }
        /* Alerts */
        .alert-box {
            padding: 8px 12px;
            border-radius: 4px;
            margin-top: 10px;
            font-size: 0.9em;
        }
        .alert-critical { background: rgba(255, 71, 87, 0.2); border-left: 3px solid #ff4757; }
        .alert-warning { background: rgba(255, 193, 7, 0.2); border-left: 3px solid #ffc107; }
        .alert-info { background: rgba(0, 217, 255, 0.2); border-left: 3px solid #00d9ff; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Crypto Trading Bot</h1>
        <div class="status">
            <div class="status-dot"></div>
            <span>Live</span>
            <span style="color: #666; margin-left: 20px;">
                Last update: {{ last_update }}
            </span>
        </div>
    </div>

    <div class="grid">
        <!-- Market Data Card -->
        <div class="card">
            <h2>Market Data ({{ market_data|length }} coins)</h2>
            {% if market_data %}
            <div class="market-grid">
                {% for coin, data in market_data.items()|sort(attribute='1.tier') %}
                <div class="market-item">
                    <div class="coin-info">
                        <span class="coin-name">{{ coin[:8] }}</span>
                        <span class="tier-badge tier-{{ data.tier }}">T{{ data.tier }}</span>
                    </div>
                    <div class="stats">
                        <span class="vol-badge vol-{{ 'low' if data.vol_score < 30 else 'high' if data.vol_score > 70 else 'normal' }}">
                            V{{ data.vol_score }}
                        </span>
                        <span class="change {{ 'positive' if data.change_24h >= 0 else 'negative' }}">
                            {{ "%.1f"|format(data.change_24h) }}%
                        </span>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
                <div class="empty-message">No market data yet. Run market data fetcher.</div>
            {% endif %}
        </div>

        <!-- Account State Card -->
        <div class="card">
            <h2>Account State</h2>
            <div class="stat-row">
                <span class="stat-label">Balance</span>
                <span class="stat-value">${{ "%.2f"|format(account.balance) }}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Available</span>
                <span class="stat-value">${{ "%.2f"|format(account.available_balance) }}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">In Positions</span>
                <span class="stat-value">${{ "%.2f"|format(account.in_positions) }}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Total P&L</span>
                <span class="stat-value {{ 'profit' if account.total_pnl >= 0 else 'loss' }}">
                    ${{ "%.2f"|format(account.total_pnl) }}
                </span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Daily P&L</span>
                <span class="stat-value {{ 'profit' if account.daily_pnl >= 0 else 'loss' }}">
                    ${{ "%.2f"|format(account.daily_pnl) }}
                </span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Trades Today</span>
                <span class="stat-value">{{ account.trade_count_today }}</span>
            </div>
        </div>

        <!-- Performance Metrics Card -->
        <div class="card">
            <h2>Performance Metrics</h2>
            <div class="metrics-grid">
                <div class="metric-box">
                    <div class="metric-value {{ 'profit' if metrics.trading.win_rate >= 50 else 'loss' }}">{{ metrics.trading.win_rate }}%</div>
                    <div class="metric-label">Win Rate</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value">{{ metrics.trading.profit_factor }}x</div>
                    <div class="metric-label">Profit Factor</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value">{{ metrics.trading.total_trades }}</div>
                    <div class="metric-label">Total Trades</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value">{{ metrics.activity.trades_per_hour }}/hr</div>
                    <div class="metric-label">Trade Rate</div>
                </div>
            </div>
            {% if metrics.alerts %}
            <div style="margin-top: 15px;">
                <h3 style="font-size: 0.9em; color: #ff4757; margin-bottom: 8px;">Active Alerts</h3>
                {% for alert in metrics.alerts %}
                <div class="alert-box alert-{{ alert.level }}">
                    {{ alert.message }}
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </div>
    </div>

    <!-- Open Trades -->
    <div class="card" style="margin-bottom: 20px;">
        <h2>Open Trades</h2>
        {% if open_trades %}
        <table>
            <thead>
                <tr>
                    <th>Coin</th>
                    <th>Entry Price</th>
                    <th>Size</th>
                    <th>Current</th>
                    <th>P&L</th>
                    <th>Stop Loss</th>
                    <th>Take Profit</th>
                </tr>
            </thead>
            <tbody>
                {% for trade in open_trades %}
                <tr>
                    <td style="text-transform: uppercase;">{{ trade.coin_name }}</td>
                    <td>${{ "%.2f"|format(trade.entry_price) }}</td>
                    <td>${{ "%.2f"|format(trade.size_usd) }}</td>
                    <td>${{ "%.2f"|format(trade.current_price or trade.entry_price) }}</td>
                    <td class="{{ 'profit' if (trade.unrealized_pnl or 0) >= 0 else 'loss' }}">
                        ${{ "%.2f"|format(trade.unrealized_pnl or 0) }}
                    </td>
                    <td>${{ "%.2f"|format(trade.stop_loss_price) }}</td>
                    <td>${{ "%.2f"|format(trade.take_profit_price) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-message">No open trades</div>
        {% endif %}
    </div>

    <!-- Closed Trades -->
    <div class="card">
        <h2>Recent Closed Trades (Last 10)</h2>
        {% if closed_trades %}
        <table>
            <thead>
                <tr>
                    <th>Coin</th>
                    <th>Entry</th>
                    <th>Exit</th>
                    <th>Size</th>
                    <th>P&L</th>
                    <th>Duration</th>
                    <th>Closed</th>
                </tr>
            </thead>
            <tbody>
                {% for trade in closed_trades %}
                <tr>
                    <td style="text-transform: uppercase;">{{ trade.coin_name }}</td>
                    <td>${{ "%.2f"|format(trade.entry_price) }}</td>
                    <td>${{ "%.2f"|format(trade.exit_price) }}</td>
                    <td>${{ "%.2f"|format(trade.size_usd) }}</td>
                    <td class="{{ 'profit' if trade.pnl_usd >= 0 else 'loss' }}">
                        ${{ "%.2f"|format(trade.pnl_usd) }} ({{ "%.1f"|format(trade.pnl_pct) }}%)
                    </td>
                    <td>{{ trade.duration_seconds or 0 }}s</td>
                    <td>{{ trade.closed_at }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-message">No closed trades yet</div>
        {% endif %}
    </div>

    <!-- Learnings and Rules Grid -->
    <div class="grid" style="margin-top: 20px;">
        <!-- Learnings Card -->
        <div class="card">
            <h2>Recent Learnings</h2>
            {% if learnings %}
            <div class="learnings-list">
                {% for learning in learnings %}
                <div class="learning-item">
                    <div class="learning-header">
                        <span class="learning-coin">{{ learning.coin_name }}</span>
                        <span class="confidence {{ 'high' if learning.confidence >= 0.7 else 'medium' if learning.confidence >= 0.5 else 'low' }}">
                            {{ "%.0f"|format(learning.confidence * 100) }}%
                        </span>
                    </div>
                    <div class="learning-lesson">{{ learning.lesson }}</div>
                    {% if learning.pattern %}
                    <div class="learning-pattern">Pattern: {{ learning.pattern }}</div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="empty-message">No learnings yet. Complete some trades first.</div>
            {% endif %}
        </div>

        <!-- Trading Rules Card -->
        <div class="card">
            <h2>Trading Rules</h2>

            <!-- Active Rules -->
            {% if rules.active %}
            <h3 class="rules-section-title active">Active Rules ({{ rules.active|length }})</h3>
            {% for rule in rules.active %}
            <div class="rule-item active">
                <div class="rule-text">{{ rule.rule_text }}</div>
                <div class="rule-stats">
                    <span class="success-rate">{{ "%.0f"|format(rule.success_rate * 100) }}% success</span>
                    <span class="trade-count">({{ rule.total_trades }} trades)</span>
                </div>
            </div>
            {% endfor %}
            {% endif %}

            <!-- Testing Rules -->
            {% if rules.testing %}
            <h3 class="rules-section-title testing">Testing Rules ({{ rules.testing|length }})</h3>
            {% for rule in rules.testing %}
            <div class="rule-item testing">
                <div class="rule-text">{{ rule.rule_text }}</div>
                <div class="rule-stats">
                    <span class="trade-count">{{ rule.total_trades }}/10 trades</span>
                </div>
            </div>
            {% endfor %}
            {% endif %}

            {% if not rules.active and not rules.testing %}
            <div class="empty-message">No rules yet. Rules emerge from high-confidence learnings.</div>
            {% endif %}
        </div>
    </div>

    <div class="footer">
        <p>Data refreshes every <span class="refresh-note">5 seconds</span></p>
        <p style="margin-top: 10px;">
            All data is REAL and comes directly from the database.
            Verify with: <code>python3 -c "from src.database import Database; print(Database().get_account_state())"</code>
        </p>
    </div>
</body>
</html>
"""


class DashboardData:
    """Fetches data from database for dashboard display."""

    def __init__(self, db: Database = None):
        """Initialize with database connection."""
        self.db = db or Database()

    def get_market_data(self) -> Dict[str, Dict[str, float]]:
        """Get current market prices from database with tier and volatility info."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT coin, price_usd, change_24h, last_updated
                FROM market_data
                ORDER BY coin
            """)

            result = {}
            for row in cursor.fetchall():
                coin_id = row[0]
                result[coin_id] = {
                    'price_usd': row[1],
                    'change_24h': row[2] or 0,
                    'last_updated': row[3],
                    'tier': get_tier(coin_id),
                    'vol_score': 50  # Default, will be updated below
                }

        # Add volatility scores
        try:
            vc = VolatilityCalculator(db=self.db)
            for coin_id in result.keys():
                try:
                    result[coin_id]['vol_score'] = vc.calculate_volatility_score(coin_id)
                except Exception:
                    pass  # Keep default of 50
        except Exception as e:
            logger.warning(f"Failed to get volatility scores: {e}")

        return result

    def get_account_state(self) -> Dict[str, Any]:
        """Get current account state."""
        state = self.db.get_account_state()
        # Ensure all expected fields exist with defaults
        return {
            'balance': state.get('balance', 0),
            'available_balance': state.get('available_balance', 0),
            'in_positions': state.get('in_positions', 0),
            'total_pnl': state.get('total_pnl', 0),
            'daily_pnl': state.get('daily_pnl', 0),
            'trade_count_today': state.get('trade_count_today', 0)
        }

    def get_open_trades(self) -> List[Dict[str, Any]]:
        """Get all open trades."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, coin_name, entry_price, size_usd, current_price,
                       unrealized_pnl, unrealized_pnl_pct, stop_loss_price,
                       take_profit_price, entry_reason, opened_at
                FROM open_trades
                ORDER BY opened_at DESC
            """)

            columns = ['id', 'coin_name', 'entry_price', 'size_usd', 'current_price',
                      'unrealized_pnl', 'unrealized_pnl_pct', 'stop_loss_price',
                      'take_profit_price', 'entry_reason', 'opened_at']

            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_closed_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent closed trades."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, coin_name, entry_price, exit_price, size_usd,
                       pnl_usd, pnl_pct, entry_reason, exit_reason,
                       opened_at, closed_at, duration_seconds
                FROM closed_trades
                ORDER BY closed_at DESC
                LIMIT ?
            """, (limit,))

            columns = ['id', 'coin_name', 'entry_price', 'exit_price', 'size_usd',
                      'pnl_usd', 'pnl_pct', 'entry_reason', 'exit_reason',
                      'opened_at', 'closed_at', 'duration_seconds']

            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_learnings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent learnings for display."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, l.trade_id, l.learning_text, l.confidence_level,
                       l.created_at, c.coin_name, c.pnl_usd
                FROM learnings l
                LEFT JOIN closed_trades c ON l.trade_id = c.id
                ORDER BY l.created_at DESC
                LIMIT ?
            """, (limit,))

            learnings = []
            for row in cursor.fetchall():
                try:
                    data = json.loads(row[2])
                except (json.JSONDecodeError, TypeError):
                    data = {'lesson': row[2] or ''}

                learnings.append({
                    'id': row[0],
                    'trade_id': row[1],
                    'lesson': data.get('lesson', ''),
                    'pattern': data.get('pattern', ''),
                    'confidence': row[3] or 0,
                    'created_at': row[4],
                    'coin_name': row[5] or 'unknown',
                    'trade_pnl': row[6] or 0
                })
            return learnings

    def get_trading_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get trading rules grouped by status."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, rule_text, status, success_count, failure_count, created_at
                FROM trading_rules
                ORDER BY
                    CASE status
                        WHEN 'active' THEN 1
                        WHEN 'testing' THEN 2
                        ELSE 3
                    END,
                    created_at DESC
            """)

            rules = {'active': [], 'testing': [], 'rejected': []}
            for row in cursor.fetchall():
                total = (row[3] or 0) + (row[4] or 0)
                success_rate = (row[3] or 0) / total if total > 0 else 0

                rule = {
                    'id': row[0],
                    'rule_text': row[1],
                    'status': row[2],
                    'success_count': row[3] or 0,
                    'failure_count': row[4] or 0,
                    'success_rate': success_rate,
                    'total_trades': total,
                    'created_at': row[5]
                }
                if row[2] in rules:
                    rules[row[2]].append(rule)
            return rules


# Create dashboard data fetcher
dashboard_data = DashboardData()


@app.route('/')
def index():
    """Main dashboard page."""
    try:
        # Get performance metrics
        mc = MetricsCollector(db=dashboard_data.db)
        metrics = mc.get_all_metrics()

        data = {
            'market_data': dashboard_data.get_market_data(),
            'account': dashboard_data.get_account_state(),
            'open_trades': dashboard_data.get_open_trades(),
            'closed_trades': dashboard_data.get_closed_trades(),
            'learnings': dashboard_data.get_learnings(),
            'rules': dashboard_data.get_trading_rules(),
            'metrics': metrics,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        return render_template_string(DASHBOARD_TEMPLATE, **data)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return f"<h1>Dashboard Error</h1><p>{e}</p>", 500


@app.route('/api/status')
def api_status():
    """JSON API endpoint for dashboard data."""
    try:
        return jsonify({
            'status': 'running',
            'market_data': dashboard_data.get_market_data(),
            'account': dashboard_data.get_account_state(),
            'open_trades': dashboard_data.get_open_trades(),
            'closed_trades': dashboard_data.get_closed_trades(),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/metrics')
def api_metrics():
    """JSON API endpoint for performance metrics."""
    try:
        mc = MetricsCollector(db=dashboard_data.db)
        return jsonify(mc.get_all_metrics())
    except Exception as e:
        logger.error(f"Metrics API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/metrics')
def prometheus_metrics():
    """Prometheus-compatible metrics endpoint.

    Returns metrics in Prometheus exposition format for external monitoring.
    Can be scraped by Prometheus or other monitoring systems.
    """
    try:
        mc = MetricsCollector(db=dashboard_data.db)
        return mc.format_prometheus(), 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception as e:
        logger.error(f"Prometheus metrics error: {e}")
        return f"# Error: {e}", 500, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/api/alerts')
def api_alerts():
    """JSON API endpoint for active alerts."""
    try:
        mc = MetricsCollector(db=dashboard_data.db)
        alerts = mc.check_alerts()
        return jsonify({
            'alerts': [
                {
                    'level': a.level.value,
                    'metric': a.metric,
                    'message': a.message,
                    'value': a.value,
                    'threshold': a.threshold
                }
                for a in alerts
            ],
            'count': len(alerts),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Alerts API error: {e}")
        return jsonify({'error': str(e)}), 500


def run_dashboard(host: str = '0.0.0.0', port: int = 8080, debug: bool = False):
    """Run the dashboard server.

    Args:
        host: Host to bind to (default: 0.0.0.0 for all interfaces).
        port: Port to listen on (default: 8080).
        debug: Enable Flask debug mode.
    """
    logger.info(f"Starting dashboard at http://{host}:{port}")
    logger.info("Press Ctrl+C to stop")
    app.run(host=host, port=port, debug=debug)


# Allow running directly
if __name__ == "__main__":
    print("=" * 60)
    print("Crypto Trading Bot - Dashboard")
    print("=" * 60)
    print()
    print("Starting dashboard server on 0.0.0.0:8080...")
    print("Access at: http://localhost:8080 (or your WSL IP from Windows)")
    print()
    print("All data displayed is REAL from the database.")
    print("Press Ctrl+C to stop.")
    print()

    run_dashboard(debug=False)
