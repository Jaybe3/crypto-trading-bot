# Verification Checklist

**How to verify EVERYTHING is working and using real data**

This checklist helps you independently verify that every component works correctly and is not a black box.

---

## ✅ Verification Checklist

### 1. Market Data is REAL

**What to verify:** Bot is fetching real cryptocurrency prices, not fake/simulated data

**How to verify:**

```bash
# Step 1: Check CoinGecko website manually
Visit: https://www.coingecko.com/en/coins/bitcoin
Note the current BTC price (e.g., $45,230)

# Step 2: Check API directly
curl "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"

# You should see:
{"bitcoin":{"usd":45230}}

# Step 3: Check what bot sees
sqlite3 /data/trading_bot.db "SELECT * FROM market_data WHERE coin='bitcoin';"

# Should show same price:
bitcoin|45230|2026-01-13 10:30:00

# Step 4: Check dashboard
Visit http://localhost:8080
Look at "Current Market Data" section

# All four sources should show THE SAME price:
✓ CoinGecko website
✓ API direct call
✓ Database
✓ Dashboard
```

**If they don't match:** Data is fake or stale. Component is broken.

---

### 2. Database Has Real Data

**What to verify:** Trades, learnings, and rules are actually being stored

**How to verify:**

```bash
# Check all tables exist
sqlite3 /data/trading_bot.db ".tables"

# Should show:
account_state    closed_trades    open_trades      trading_rules
activity_log     learnings

# Check there's data in tables
sqlite3 /data/trading_bot.db "SELECT COUNT(*) FROM open_trades;"
sqlite3 /data/trading_bot.db "SELECT COUNT(*) FROM closed_trades;"
sqlite3 /data/trading_bot.db "SELECT COUNT(*) FROM learnings;"
sqlite3 /data/trading_bot.db "SELECT COUNT(*) FROM trading_rules;"

# Should show numbers > 0 (after bot has run)

# View actual data
sqlite3 /data/trading_bot.db "SELECT * FROM open_trades;"
sqlite3 /data/trading_bot.db "SELECT * FROM closed_trades LIMIT 5;"
sqlite3 /data/trading_bot.db "SELECT * FROM learnings ORDER BY created_at DESC LIMIT 5;"
sqlite3 /data/trading_bot.db "SELECT * FROM trading_rules;"

# Should see actual readable data
```

**If tables are empty:** Bot isn't storing data. Component is broken.

---

### 3. LLM is Actually Responding

**What to verify:** Local LLM is connected and generating real responses

**How to verify:**

```bash
# Test LLM directly (bypassing bot)
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:7b",
    "messages": [
      {"role": "user", "content": "What is the capital of France? Answer in one sentence."}
    ],
    "stream": false
  }'

# Should get actual response like:
{"message":{"content":"The capital of France is Paris."}}

# Check bot's logs to see LLM calls
cat logs/bot.log | grep "LLM"

# Should show:
[2026-01-13 10:30:00] LLM query sent: [prompt]
[2026-01-13 10:30:05] LLM response: [response]

# Check dashboard "LLM Thinking" section
Visit http://localhost:8080
Look for "LLM Current Thinking"

# Should show:
- Most recent prompt sent to LLM
- LLM's actual response
- Decision made
- Reasoning
```

**If no response or gibberish:** LLM connection is broken.

---

### 4. Trades are Being Recorded

**What to verify:** When bot makes trades, they appear in database

**How to verify:**

```bash
# Before any trades
sqlite3 /data/trading_bot.db "SELECT COUNT(*) FROM open_trades;"
# Should show: 0

# Let bot run for 5 minutes
# (It should make at least one trade)

# After bot runs
sqlite3 /data/trading_bot.db "SELECT COUNT(*) FROM open_trades;"
# Should show: 1 or more

# View the trade
sqlite3 /data/trading_bot.db "SELECT * FROM open_trades;"

# Should show something like:
1|bitcoin|45000|20|45050|1.00|0.11|40500|45020|Volume spike pattern|2026-01-13 10:30:00

# Check dashboard
Visit http://localhost:8080

# "Open Trades" section should show the same trade
```

**If count stays 0:** Bot isn't making trades. Check risk manager or LLM decision logic.

---

### 5. Stop Loss / Take Profit Work

**What to verify:** Positions automatically close at -10% or +$1

**How to verify:**

```bash
# Find an open trade
sqlite3 /data/trading_bot.db "SELECT id, coin_name, entry_price, stop_loss_price, take_profit_price FROM open_trades;"

# Example output:
1|bitcoin|45000|40500|45022.50

# This means:
# Entry: $45,000
# Stop loss: $40,500 (45000 * 0.90 = 10% loss)
# Take profit: $45,022.50 (entry + $1 profit on $20 position)

# Wait for price to move (or simulate)
# If BTC price reaches $45,022.50 or $40,500, position should close

# Check closed_trades
sqlite3 /data/trading_bot.db "SELECT * FROM closed_trades ORDER BY closed_at DESC LIMIT 1;"

# Should show:
1|bitcoin|45000|45022.50|20|1.00|0.05|Volume spike|Take profit reached|2026-01-13 10:30:00|2026-01-13 10:32:00|120

# This shows:
# - Closed at take profit price
# - Made $1 profit
# - Duration: 120 seconds (2 minutes)
```

**If positions don't close:** Stop loss/take profit logic is broken.

---

### 6. Learnings are Created

**What to verify:** After each trade closes, LLM analyzes it and creates a learning

**How to verify:**

```bash
# Check learnings before a trade closes
sqlite3 /data/trading_bot.db "SELECT COUNT(*) FROM learnings;"
# Note the count (e.g., 5)

# Wait for a trade to close
# (Either stop loss or take profit hits)

# Check learnings again (within 30 seconds)
sqlite3 /data/trading_bot.db "SELECT COUNT(*) FROM learnings;"
# Should be one more (e.g., 6)

# Read the new learning
sqlite3 /data/trading_bot.db "SELECT learning_text FROM learnings ORDER BY created_at DESC LIMIT 1;"

# Should show LLM's analysis like:
"This trade succeeded because the volume spike pattern indicated momentum. 
The 24h price change of +2.3% confirmed the upward trend. 
Pattern: Volume increases >50% with positive price action often lead to quick profits.
Lesson: Continue to monitor volume as a leading indicator."

# Check dashboard
Visit http://localhost:8080/learnings

# Should show the new learning
```

**If no learnings created:** Learning system is broken. LLM is not analyzing trades.

---

### 7. Rules are Being Created

**What to verify:** When LLM identifies patterns, it creates trading rules

**How to verify:**

```bash
# Check rules before
sqlite3 /data/trading_bot.db "SELECT COUNT(*) FROM trading_rules;"
# Note the count

# Let bot run and make several successful trades with similar patterns
# (This takes time - expect 1+ hours)

# Check rules after
sqlite3 /data/trading_bot.db "SELECT COUNT(*) FROM trading_rules;"
# Should have increased

# View the rules
sqlite3 /data/trading_bot.db "SELECT rule_text, status, success_count, failure_count FROM trading_rules;"

# Should show something like:
Buy when volume increases >50% and 24h change is positive|testing|3|1
Exit positions within 2 minutes to lock in quick profits|testing|2|0

# Check dashboard
Visit http://localhost:8080/rules

# Should show rules with their status and success rates
```

**If no rules created:** Rule creation logic is broken or LLM isn't identifying patterns.

---

### 8. Rules are Being Used

**What to verify:** Active rules are actually influencing trading decisions

**How to verify:**

```bash
# Find an active rule
sqlite3 /data/trading_bot.db "SELECT id, rule_text FROM trading_rules WHERE status='active';"

# Example:
1|Buy when volume increases >50% and 24h change is positive

# Check recent trade
sqlite3 /data/trading_bot.db "SELECT entry_reason FROM open_trades ORDER BY opened_at DESC LIMIT 1;"

# Should mention the rule:
"Applying rule #1: Volume increase of 65% with +2.3% price change"

# Check logs
cat logs/bot.log | grep "rule"

# Should show:
[2026-01-13 10:30:00] Evaluating active rules: 3 rules found
[2026-01-13 10:30:00] Rule #1 matched: Buy when volume increases >50%
[2026-01-13 10:30:00] Applying rule #1 to trading decision
```

**If rules aren't mentioned:** Rules aren't being used in decisions.

---

### 9. Risk Limits are Enforced

**What to verify:** Bot respects 2% per trade and 10% total exposure limits

**How to verify:**

```bash
# Check account balance
sqlite3 /data/trading_bot.db "SELECT balance FROM account_state ORDER BY timestamp DESC LIMIT 1;"
# Example: 1000

# This means:
# Max per trade: $20 (2% of $1,000)
# Max total exposure: $100 (10% of $1,000)

# Check all open positions
sqlite3 /data/trading_bot.db "SELECT size_usd FROM open_trades;"

# Each should be ≤ $20:
20
18
20

# Check total
sqlite3 /data/trading_bot.db "SELECT SUM(size_usd) FROM open_trades;"

# Should be ≤ $100:
58

# Try to force an invalid trade (in Python REPL)
python -c "
from src.risk_manager import RiskManager
rm = RiskManager()
result = rm.validate_trade(size_usd=25, account_balance=1000, open_positions_total=0)
print(result.valid, result.reason)
"

# Should output:
False Trade size exceeds maximum allowed
```

**If limits aren't enforced:** Risk manager is broken. CRITICAL ISSUE.

---

### 10. Dashboard Shows Live Data

**What to verify:** Dashboard updates in real-time with accurate information

**How to verify:**

```bash
# Open dashboard
Visit http://localhost:8080

# Open browser developer tools (F12)
# Go to Network tab

# Watch for requests every 5 seconds
# Should see: GET /api/status every 5 seconds

# Check data updates:
1. Note current BTC price on dashboard
2. Query database:
   sqlite3 /data/trading_bot.db "SELECT price_usd FROM market_data WHERE coin='bitcoin';"
3. Prices should match

# Wait 5 seconds
# Dashboard should refresh with new data
# Query database again
# New prices should match

# Check all sections update:
- Bot status ✓
- Market data ✓
- Account balance ✓
- Open trades ✓
- Closed trades ✓
- Learnings count ✓
- Rules count ✓
```

**If dashboard doesn't update:** Dashboard refresh logic is broken.

---

## 🎯 Quick Verification Script

Save this as `verify.sh` and run it:

```bash
#!/bin/bash

echo "=== VERIFICATION SCRIPT ==="
echo ""

echo "1. Checking market data..."
curl -s "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
echo ""
sqlite3 /data/trading_bot.db "SELECT coin, price_usd FROM market_data WHERE coin='bitcoin';"
echo ""

echo "2. Checking database tables..."
sqlite3 /data/trading_bot.db ".tables"
echo ""

echo "3. Checking data counts..."
echo "Open trades: $(sqlite3 /data/trading_bot.db 'SELECT COUNT(*) FROM open_trades;')"
echo "Closed trades: $(sqlite3 /data/trading_bot.db 'SELECT COUNT(*) FROM closed_trades;')"
echo "Learnings: $(sqlite3 /data/trading_bot.db 'SELECT COUNT(*) FROM learnings;')"
echo "Rules: $(sqlite3 /data/trading_bot.db 'SELECT COUNT(*) FROM trading_rules;')"
echo ""

echo "4. Checking LLM connection..."
curl -s -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder:7b","messages":[{"role":"user","content":"Say hello"}],"stream":false}' \
  | grep -o '"content":"[^"]*"'
echo ""

echo "5. Checking dashboard..."
curl -s http://localhost:8080 > /dev/null && echo "Dashboard is accessible ✓" || echo "Dashboard is NOT accessible ✗"
echo ""

echo "=== VERIFICATION COMPLETE ==="
```

Make it executable:
```bash
chmod +x verify.sh
./verify.sh
```

---

## 🚨 What to Do If Verification Fails

### Market Data Mismatch
→ Check API key (if required)
→ Check internet connection
→ Check if CoinGecko is rate limiting
→ Review market_data.py code

### Database Empty
→ Check if database file exists: `ls -la /data/trading_bot.db`
→ Check if bot is running: `ps aux | grep python`
→ Check logs: `cat logs/bot.log`
→ Review database.py code

### LLM Not Responding
→ Check if OpenWebUI is running: visit http://localhost:3000
→ Check if model is loaded: look for qwen2.5-coder:7b
→ Check logs for errors: `cat logs/bot.log | grep "LLM"`
→ Review llm_interface.py code

### No Trades
→ Check if bot is running
→ Check if risk manager is too restrictive
→ Check if LLM is returning HOLD too often
→ Check logs: `cat logs/bot.log`

### Dashboard Not Updating
→ Check if dashboard server is running: `ps aux | grep dashboard`
→ Check if port 8080 is available: `lsof -i :8080`
→ Check browser console for errors (F12)
→ Review dashboard.py code

---

## ✅ All Components Verified

When ALL items on this checklist pass:
- ✅ Market data is real
- ✅ Database has data
- ✅ LLM responds
- ✅ Trades are recorded
- ✅ Stop loss/take profit work
- ✅ Learnings are created
- ✅ Rules are created
- ✅ Rules are used
- ✅ Risk limits enforced
- ✅ Dashboard shows live data

**Then you can trust the system is working correctly.**

---

**Remember: If you can't verify it, don't trust it.**

This checklist ensures there are NO black boxes.
