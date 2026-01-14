# Development Workflow

**Target Audience:** Claude Code and Developers

This document defines the **mandatory workflow** that prevents black boxes and ensures transparency.

---

## 🎯 Golden Rules

1. **NEVER code without specification**
2. **ALWAYS provide verification steps**
3. **ONE component at a time - fully verified before moving on**
4. **User must be able to verify EVERYTHING independently**
5. **If user can't verify it works, it's NOT done**

---

## 🔄 The Mandatory Workflow

### Phase 1: Specification (BEFORE any code)

**Create Implementation Specification:**

```markdown
## IMPLEMENTATION SPEC FOR: [Component Name]

### What I'm Building
[Clear description]

### APIs/Services Used
- Service: CoinGecko API
- Endpoint: https://api.coingecko.com/api/v3/simple/price
- Method: GET
- Parameters: ids=bitcoin&vs_currencies=usd

### Example Request
curl "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"

### Example Response
{"bitcoin":{"usd":45230}}

### Where Data is Stored
- Database: /data/trading_bot.db
- Table: market_data
- Schema:
  CREATE TABLE market_data (
    coin TEXT PRIMARY KEY,
    price_usd REAL,
    timestamp TIMESTAMP
  );

### How User Can Verify This Works
1. Run this curl command: [exact command]
2. Expected output: [show exact output]
3. Query database: sqlite3 /data/trading_bot.db "SELECT * FROM market_data;"
4. Expected result: [show what should appear]
5. Check dashboard at: http://localhost:8080/market-data

### Files I Will Create/Modify
- src/market_data.py (new file)
- src/database.py (modify - add market_data table)
- tests/test_market_data.py (new file)

### Files I Will NOT Touch
- src/risk_manager.py
- src/llm_interface.py
- [any other protected files]

### Dependencies
- Requires: Database to be set up first
- Blocks: LLM integration (needs market data)

### Questions/Uncertainties
[Any clarifications needed]
```

**Wait for user approval before coding.**

---

### Phase 2: Implementation

**While coding:**

1. **Make ONE small change**
   - Good: "Add function to fetch BTC price"
   - Bad: "Add market data fetching for all coins, store in database, and update dashboard"

2. **Test immediately**
   ```bash
   python -m pytest tests/test_market_data.py -v
   ```

3. **Verify independently**
   ```bash
   # Can the user see this working?
   curl [the API]
   sqlite3 /data/trading_bot.db "SELECT * FROM table;"
   ```

4. **Commit working code**
   ```bash
   git commit -m "[Component] What changed

   Details...
   
   Verification: Tested with [command]
   Result: [what happened]"
   ```

---

### Phase 3: Verification & Proof

**After implementation, provide:**

```markdown
## VERIFICATION REPORT FOR: [Component]

### What Was Built
[Brief summary]

### Verification Steps Completed

#### 1. API Test
Command run:
curl "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"

Actual output:
{"bitcoin":{"usd":45230}}

✅ API returns real data

#### 2. Database Test
Command run:
sqlite3 /data/trading_bot.db "SELECT * FROM market_data;"

Actual output:
bitcoin|45230|2026-01-13 10:30:00

✅ Data is stored correctly

#### 3. Code Test
Command run:
python -m pytest tests/test_market_data.py -v

Actual output:
test_fetch_bitcoin_price PASSED
test_store_price_in_db PASSED
All tests passed

✅ Tests pass

#### 4. Dashboard Test
Navigate to: http://localhost:8080/market-data

What I see:
[Screenshot or description]
- BTC: $45,230 (updated 5 sec ago)
- ETH: $2,450 (updated 5 sec ago)

✅ Dashboard shows live data

### Files Modified
- src/market_data.py (created)
- src/database.py (modified)
- tests/test_market_data.py (created)

### How User Can Verify Right Now
Run these exact commands:
1. curl "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
2. sqlite3 /data/trading_bot.db "SELECT * FROM market_data;"
3. Visit http://localhost:8080 in browser

### Issues Found
[None, or list any problems]

### Ready for User Approval
Yes / No
```

---

## 🚨 Checkpoint System

**Each component has a checkpoint:**

| # | Component | Verify | Status |
|---|-----------|--------|--------|
| 1 | Market Data Fetching | curl + data visible | ⬜ Not Started |
| 2 | Database Setup | Can query tables | ⬜ Not Started |
| 3 | LLM Connection | Gets real responses | ⬜ Not Started |
| 4 | Paper Trading Logic | Trades appear in DB | ⬜ Not Started |
| 5 | Risk Management | Limits are enforced | ⬜ Not Started |
| 6 | Learning Analysis | Learnings created | ⬜ Not Started |
| 7 | Rule Creation | Rules stored & used | ⬜ Not Started |
| 8 | Dashboard | All data visible live | ⬜ Not Started |

**Cannot proceed to next checkpoint until current one passes verification.**

---

## 📋 Example: Market Data Component

### SPEC (Before Coding):

```markdown
## IMPLEMENTATION SPEC: Market Data Fetching

### What I'm Building
Module to fetch real-time cryptocurrency prices from CoinGecko API

### API Used
- CoinGecko API (free tier, no auth required)
- Endpoint: /api/v3/simple/price
- Rate limit: 10-50 calls/minute (safe)

### Example
curl "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true"

Response:
{
  "bitcoin": {"usd": 45230, "usd_24h_change": 2.3},
  "ethereum": {"usd": 2450, "usd_24h_change": 1.8}
}

### Storage
Database: /data/trading_bot.db
Table: market_data
Fields: coin, price_usd, change_24h, last_updated

### Verification
1. Run curl command - should get real prices
2. Run Python script - should store in database
3. Query database - should see latest prices
4. Dashboard - should display prices

### Dependencies
None (this is first component)
```

**User approves ✅**

### IMPLEMENTATION:

```python
# src/market_data.py
import requests
import sqlite3
from datetime import datetime

class MarketDataFetcher:
    def __init__(self, db_path="/data/trading_bot.db"):
        self.db_path = db_path
        self.base_url = "https://api.coingecko.com/api/v3"
    
    def fetch_prices(self, coins=["bitcoin", "ethereum"]):
        """Fetch current prices for specified coins."""
        url = f"{self.base_url}/simple/price"
        params = {
            "ids": ",".join(coins),
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def store_prices(self, price_data):
        """Store prices in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for coin, data in price_data.items():
            cursor.execute("""
                INSERT OR REPLACE INTO market_data 
                (coin, price_usd, change_24h, last_updated)
                VALUES (?, ?, ?, ?)
            """, (coin, data['usd'], data.get('usd_24h_change', 0), datetime.now()))
        
        conn.commit()
        conn.close()
```

Test immediately:
```bash
python -m pytest tests/test_market_data.py -v
```

### VERIFICATION:

```markdown
## VERIFICATION REPORT: Market Data Fetching

#### 1. API Test (REAL DATA)
$ curl "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
{"bitcoin":{"usd":45230}}

✅ Returns real market data

#### 2. Python Script Test
$ python -c "from src.market_data import MarketDataFetcher; mdf = MarketDataFetcher(); print(mdf.fetch_prices())"
{'bitcoin': {'usd': 45230, 'usd_24h_change': 2.3}}

✅ Script fetches real data

#### 3. Database Test
$ sqlite3 /data/trading_bot.db "SELECT * FROM market_data;"
bitcoin|45230|2.3|2026-01-13 10:30:00

✅ Data stored in database

#### 4. User Can Verify Right Now
Run: curl "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
Compare to: sqlite3 /data/trading_bot.db "SELECT * FROM market_data WHERE coin='bitcoin';"
Prices should match

✅ Ready for approval
```

**User verifies independently ✅**

**User approves moving to next component ✅**

---

## 🔍 Verification Commands Reference

### Check Market Data is Real
```bash
# Compare API to what bot sees
curl "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
# vs
sqlite3 /data/trading_bot.db "SELECT * FROM market_data WHERE coin='bitcoin';"
# Prices should match
```

### Check Database Has Real Data
```bash
# View all trades
sqlite3 /data/trading_bot.db "SELECT * FROM closed_trades;"

# View learnings
sqlite3 /data/trading_bot.db "SELECT * FROM learnings ORDER BY created_at DESC;"

# View rules
sqlite3 /data/trading_bot.db "SELECT * FROM trading_rules WHERE status='active';"
```

### Check LLM is Really Responding
```bash
# Test LLM directly
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:7b",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "stream": false
  }'
# Should get actual response
```

### Check Dashboard is Live
```bash
# Visit http://localhost:8080
# Open browser dev tools (F12)
# Watch Network tab
# Should see requests every 5 seconds
# Should see data updating
```

---

## 🚫 Common Mistakes to Avoid

### ❌ DON'T DO THIS:

**Building without specification:**
```
User: "Add market data fetching"
Claude: [immediately writes code]
```

**Not providing verification:**
```
Claude: "I've added market data fetching. It should work."
```

**Making multiple changes at once:**
```
Claude: "I've added market data, set up the database, 
connected the LLM, and built the dashboard"
```

**Using fake/simulated data:**
```python
def fetch_price():
    return random.randint(40000, 50000)  # ❌ NO!
```

### ✅ DO THIS:

**Specification first:**
```
User: "Add market data fetching"
Claude: "I'll create a specification first. Here's what I propose:
- API: CoinGecko
- Endpoint: /simple/price
- Example: [shows curl command]
- Storage: [shows table]
- Verification: [shows how user can verify]

Does this look good?"
```

**Always provide verification:**
```
Claude: "Market data fetching is complete. 

To verify it works:
1. Run: curl [exact command]
2. You should see: [exact output]
3. Query database: [exact command]
4. You should see: [exact output]

I've tested all these steps and can confirm they work."
```

**One change at a time:**
```
Claude: "I've added the market data fetching function.
It's tested and working. 

Verification:
- API call: ✅
- Data stored: ✅
- User can verify: ✅

Ready to move to next component (database setup)?"
```

**Always use real data:**
```python
def fetch_price(coin):
    response = requests.get(f"{API_URL}?ids={coin}")
    return response.json()[coin]['usd']  # ✅ YES!
```

---

## 📝 Task Completion Checklist

Before marking ANY task complete:

```
Technical Completion:
[ ] Code written
[ ] Tests pass
[ ] No errors in logs

Verification (CRITICAL):
[ ] User can run verification commands
[ ] Verification commands work
[ ] Results match expected output
[ ] Dashboard shows data (if applicable)
[ ] Database can be queried directly

Documentation:
[ ] Spec was created and approved
[ ] Verification report provided
[ ] TASKS.md updated
[ ] CHANGELOG.md updated

User Approval:
[ ] User has verified independently
[ ] User approves moving forward
```

**If ANY checkbox is unchecked, task is NOT complete.**

---

## 🎯 Success Indicators

**You're doing it right when:**
- ✅ User can verify everything independently
- ✅ No black boxes
- ✅ Dashboard shows real, live data
- ✅ Database has real data
- ✅ API calls return real responses
- ✅ Each component works before moving to next

**You need to adjust when:**
- ❌ User asks "how do I know this is real?"
- ❌ User can't verify something works
- ❌ Dashboard shows placeholder data
- ❌ Database is empty or has fake data
- ❌ Moving too fast without verification

---

## Remember

**This project failed before because it became a black box.**

**This workflow prevents that by:**
1. Forcing specification before code
2. Requiring verification at every step
3. Making everything independently verifiable
4. Building one piece at a time
5. User approval at each checkpoint

**Follow this workflow religiously.**
