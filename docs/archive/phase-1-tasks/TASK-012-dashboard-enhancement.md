# TASK-012: Dashboard Enhancement - Learnings and Rules Views

## Overview
Add two new sections to the dashboard to display learnings extracted from trades and trading rules with their current status.

## Current State
- Dashboard (`src/dashboard.py`) displays: market data, account state, open trades, closed trades
- `learnings` table stores JSON with: what_happened, why_outcome, pattern, lesson, confidence
- `trading_rules` table stores: rule_text, status (testing/active/rejected), success/failure counts

## Implementation

### 1. Add Data Fetching Methods to DashboardData Class

```python
# In src/dashboard.py, add to DashboardData class:

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
            except:
                data = {'lesson': row[2]}

            learnings.append({
                'id': row[0],
                'trade_id': row[1],
                'lesson': data.get('lesson', ''),
                'pattern': data.get('pattern', ''),
                'confidence': row[3],
                'created_at': row[4],
                'coin_name': row[5],
                'trade_pnl': row[6]
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
            rules[row[2]].append(rule)
        return rules
```

### 2. Update index() Route
Add learnings and rules to the data dict passed to template:

```python
data = {
    'market_data': dashboard_data.get_market_data(),
    'account': dashboard_data.get_account_state(),
    'open_trades': dashboard_data.get_open_trades(),
    'closed_trades': dashboard_data.get_closed_trades(),
    'learnings': dashboard_data.get_learnings(),      # NEW
    'rules': dashboard_data.get_trading_rules(),       # NEW
    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}
```

### 3. Add HTML/CSS for Learnings Section

```html
<!-- Learnings Card -->
<div class="card" style="margin-bottom: 20px;">
    <h2>Recent Learnings</h2>
    {% if learnings %}
    <div class="learnings-list">
        {% for learning in learnings %}
        <div class="learning-item">
            <div class="learning-header">
                <span class="learning-coin">{{ learning.coin_name|upper }}</span>
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
```

### 4. Add HTML/CSS for Rules Section

```html
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
    <div class="empty-message">No rules created yet. Rules emerge from high-confidence learnings.</div>
    {% endif %}
</div>
```

### 5. CSS Additions

```css
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
    margin-bottom: 8px;
}
.learning-coin {
    font-weight: bold;
    color: #00d9ff;
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
```

## Files to Modify
- `src/dashboard.py` - Add methods and update template

## Testing
1. Run dashboard: `python3 src/dashboard.py`
2. Verify learnings section displays (may be empty initially)
3. Verify rules section displays with proper grouping
4. Check CSS styling renders correctly
5. Confirm auto-refresh (5s) updates new data

## Dependencies
- Requires `json` import (already present)
- Uses existing `learnings` and `trading_rules` tables
