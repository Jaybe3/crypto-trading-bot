# Guide for Claude Code

**How to work on this self-learning crypto trading bot**

---

## 🎯 What This Project Is

This is a **self-learning AI trading bot** that:
- Makes its own decisions
- Learns from every trade
- Creates its own rules
- Optimizes itself over time

**This is NOT:**
- A fixed-strategy bot
- A bot with pre-programmed indicators
- A simple trading script

**The learning system is the entire point.**

---

## 🚨 Critical Context: Why This Framework Exists

**Previous attempts failed because the bot became a BLACK BOX:**
- User couldn't verify if data was real
- User couldn't see if learning loop worked
- User couldn't trust anything

**This framework prevents that.**

Every component MUST be independently verifiable by the user.

---

## 📋 Your Workflow (MANDATORY)

### Before Writing ANY Code:

1. **Read these files in order:**
   ```
   1. PRD.md (requirements)
   2. DEVELOPMENT.md (workflow)
   3. TASKS.md (current task)
   4. .clinerules (code standards)
   5. VERIFICATION_CHECKLIST.md (how to verify)
   ```

2. **Find your current task in TASKS.md**
   - Look for status: ⬜ Not Started
   - Read ALL acceptance criteria
   - Understand what "done" means

3. **Create Implementation Specification**
   
   Follow this template EXACTLY:
   
   ```markdown
   ## IMPLEMENTATION SPEC FOR: [Task Name]
   
   ### What I'm Building
   [Clear description]
   
   ### APIs/Services Used
   - Service: [e.g., CoinGecko API]
   - Endpoint: [exact URL]
   - Method: [GET/POST]
   - Parameters: [what params]
   
   ### Example Request
   [Exact curl command user can run]
   
   ### Example Response
   [What the response looks like]
   
   ### Where Data is Stored
   - Database: /data/trading_bot.db
   - Table: [table name]
   - Schema: [CREATE TABLE statement]
   
   ### How User Can Verify This Works
   1. [Exact command to run]
   2. [Expected output]
   3. [Another command]
   4. [Expected output]
   
   ### Files I Will Create/Modify
   - [list all files]
   
   ### Files I Will NOT Touch
   - [list protected files]
   
   ### Questions/Uncertainties
   [Any clarifications needed]
   ```

4. **Wait for user approval**
   - Don't code until spec is approved
   - Answer any questions
   - Clarify uncertainties

---

### While Coding:

1. **Make ONE small change**
   - Good: "Add function to fetch BTC price"
   - Bad: "Build entire market data system"

2. **Test immediately**
   ```bash
   python -m pytest tests/test_market_data.py -v
   ```

3. **Verify it works**
   ```bash
   # Run the verification commands from your spec
   curl [...]
   sqlite3 /data/trading_bot.db [...]
   ```

4. **Commit working code**
   ```bash
   git commit -m "[Component] Brief description
   
   Details of what changed
   
   Verification: Ran [commands]
   Result: [what happened]
   
   Task: TASK-XXX"
   ```

---

### After Implementation:

1. **Provide Verification Report**
   
   Follow this template:
   
   ```markdown
   ## VERIFICATION REPORT FOR: [Task Name]
   
   ### What Was Built
   [Brief summary]
   
   ### Verification Steps Completed
   
   #### 1. [Test Name]
   Command run:
   [exact command]
   
   Actual output:
   [what you got]
   
   ✅ [Pass/Fail with reason]
   
   #### 2. [Next Test]
   ...
   
   ### Files Modified
   - [list with changes made]
   
   ### How User Can Verify Right Now
   Run these commands:
   1. [exact command]
   2. [exact command]
   
   ### Issues Found
   [None, or list problems]
   
   ### Ready for User Approval
   Yes / No
   ```

2. **Update documentation**
   - Mark task in TASKS.md as 🔵 Needs Verification
   - Add progress notes
   - Update any affected docs

3. **Wait for user verification**
   - User will run your verification commands
   - User will approve or request changes
   - Only then can you move to next task

---

## 🎯 Example: Complete Task Flow

### User Says:
"Start with TASK-003: Market Data Fetching"

### You Respond:
```
I'll work on TASK-003. First, let me create the implementation specification.

## IMPLEMENTATION SPEC FOR: Market Data Fetching (CoinGecko)

### What I'm Building
A module to fetch real-time cryptocurrency prices from CoinGecko's public API.
Will fetch BTC, ETH, XRP prices and store in database.

### API Used
- Service: CoinGecko API (free tier, no auth)
- Endpoint: https://api.coingecko.com/api/v3/simple/price
- Method: GET
- Parameters: ids=bitcoin,ethereum,ripple&vs_currencies=usd&include_24hr_change=true

### Example Request
curl "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"

### Example Response
{
  "bitcoin": {
    "usd": 45230,
    "usd_24h_change": 2.3
  }
}

### Where Data Stored
- Database: /data/trading_bot.db
- Table: market_data
- Schema:
  CREATE TABLE market_data (
    coin TEXT PRIMARY KEY,
    price_usd REAL NOT NULL,
    change_24h REAL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

### How User Can Verify
1. Run: curl "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
2. Expected: {"bitcoin":{"usd":45230}}
3. Run: sqlite3 /data/trading_bot.db "SELECT * FROM market_data WHERE coin='bitcoin';"
4. Expected: Same price as curl command
5. Check dashboard at http://localhost:8080
6. Expected: Shows same BTC price

### Files I Will Create
- src/market_data.py (new)
- tests/test_market_data.py (new)

### Files I Will Modify
- src/database.py (add market_data table)

### Files I Will NOT Touch
- src/risk_manager.py
- src/llm_interface.py
- src/trading_engine.py

### Dependencies
- Requires TASK-002 (Database Setup) to be complete

Does this specification look good? Should I proceed with implementation?
```

### User Approves

### You Implement
- Write src/market_data.py
- Write tests
- Update database schema
- Test everything

### You Provide Verification Report
```
## VERIFICATION REPORT FOR: Market Data Fetching

### What Was Built
Implemented MarketDataFetcher class that fetches BTC, ETH, XRP prices
from CoinGecko API and stores them in database.

### Verification Steps Completed

#### 1. API Returns Real Data
Command run:
curl "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"

Actual output:
{"bitcoin":{"usd":45230}}

✅ API returns real market data

#### 2. Python Module Fetches Data
Command run:
python -c "from src.market_data import MarketDataFetcher; mdf = MarketDataFetcher(); print(mdf.fetch_prices())"

Actual output:
{'bitcoin': {'usd': 45230, 'usd_24h_change': 2.3}}

✅ Python module works

#### 3. Data Stored in Database
Command run:
sqlite3 /data/trading_bot.db "SELECT * FROM market_data;"

Actual output:
bitcoin|45230|2.3|2026-01-13 10:30:00

✅ Data is stored

#### 4. Tests Pass
Command run:
pytest tests/test_market_data.py -v

Actual output:
test_fetch_single_coin PASSED
test_fetch_multiple_coins PASSED
test_store_in_database PASSED
All 3 tests passed

✅ All tests pass

### Files Modified
- src/market_data.py (created - 85 lines)
- src/database.py (modified - added market_data table)
- tests/test_market_data.py (created - 45 lines)

### How User Can Verify Right Now
1. curl "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
2. sqlite3 /data/trading_bot.db "SELECT * FROM market_data WHERE coin='bitcoin';"
3. Compare prices - they should match

### Issues Found
None. All functionality works as expected.

### Ready for User Approval
Yes. User can verify using the commands above.
```

### User Verifies and Approves

### You Move to Next Task
```
TASK-003 is complete and verified. 

Looking at TASKS.md, the next task is TASK-004: LLM Connection Test.

Should I create the implementation spec for TASK-004?
```

---

## 🚫 What NOT to Do

### DON'T: Build Without Specification
```
❌ User: "Add market data"
❌ You: [immediately starts coding]
```

### DON'T: Use Fake Data
```python
❌ def fetch_price():
❌     return 45000  # fake
```

### DON'T: Skip Verification
```
❌ You: "I've added market data fetching. It should work."
❌ [Doesn't provide verification steps]
```

### DON'T: Build Multiple Things at Once
```
❌ You: "I've built market data, database, LLM connection, 
❌       and the dashboard all in one go."
```

### DON'T: Touch Files You Shouldn't
```
❌ [Working on market data but modifies risk_manager.py]
```

### DON'T: Move Forward Without Approval
```
❌ You: [Completes TASK-003, immediately starts TASK-004 
❌       without waiting for user to verify TASK-003]
```

---

## ✅ What TO Do

### DO: Follow the Workflow
1. Read docs
2. Create spec
3. Get approval
4. Implement one thing
5. Verify it works
6. Provide verification report
7. Wait for user approval
8. Move to next task

### DO: Use Real Data
```python
✓ def fetch_price(coin):
✓     response = requests.get(f"{API_URL}?ids={coin}")
✓     return response.json()[coin]['usd']
```

### DO: Provide Verification Steps
```
✓ You: "Market data fetching is complete.
✓ 
✓ To verify:
✓ 1. Run: curl [exact command]
✓ 2. Run: sqlite3 [exact query]
✓ 3. Prices should match
✓ 
✓ I've tested all these steps."
```

### DO: Build One Thing at a Time
```
✓ You: "I've completed the market data fetching.
✓       It's tested and verified.
✓       Ready to move to database setup?"
```

### DO: Stay Focused
```
✓ [Working on market data]
✓ [Only modifies market_data.py and related files]
✓ [Doesn't touch unrelated code]
```

### DO: Wait for Approval
```
✓ You: [Completes TASK-003]
✓ You: [Provides verification report]
✓ You: [Waits for user to verify]
✓ User: "Verified. Looks good."
✓ You: "Great! Moving to TASK-004..."
```

---

## 🎯 Key Principles

### 1. Transparency
Everything must be verifiable. No black boxes.

User must be able to:
- See raw API responses
- Query database directly
- Read LLM prompts and responses
- Verify all data is real

### 2. Incremental Progress
One small piece at a time.

Each piece must be:
- Fully functional
- Fully tested
- Fully verified
- Approved by user

### 3. Real Data Only
No fake, simulated, or placeholder data.

All data must be:
- From real APIs
- Verifiable by user
- Matchable to external sources

### 4. Documentation
Everything must be documented.

User must be able to:
- Understand what each component does
- Verify each component works
- See the status of all tasks
- Track all changes

---

## 🚨 Special Notes

### About the Learning System

This is THE most important part of the project.

The bot must:
- Actually learn from trades
- Actually create rules
- Actually apply those rules
- Actually improve over time

This is not optional. This is the project.

### About Risk Management

Risk limits are NON-NEGOTIABLE:
- Max 2% per trade
- Max 10% total exposure
- Auto stop loss at -10%
- Auto take profit at +$1

These cannot be bypassed. Ever.

### About Phase 2

DO NOT BUILD Phase 2 features:
- No wallet integration
- No real trading
- No admin UI
- Nothing from Phase 2

Phase 1 must prove the concept works first.

---

## 📚 Resources

### When You're Stuck

1. Re-read PRD.md for requirements
2. Re-read DEVELOPMENT.md for workflow
3. Check TASKS.md for similar completed tasks
4. Review VERIFICATION_CHECKLIST.md
5. Ask user for clarification

### When User Reports a Problem

1. Ask user to run verification commands
2. Check logs: `cat logs/bot.log`
3. Query database to see actual data
4. Identify which component is failing
5. Fix that specific component
6. Verify fix works
7. Provide verification steps to user

---

## 🎓 Success Indicators

### You're Doing It Right When:

- ✅ User can verify everything independently
- ✅ All data in dashboard matches database
- ✅ All data in database matches APIs
- ✅ Each task is fully complete before moving on
- ✅ No components are black boxes
- ✅ User understands what each part does

### You Need to Adjust When:

- ❌ User asks "how do I know this is real?"
- ❌ User can't run verification commands
- ❌ Dashboard shows placeholder data
- ❌ Database is empty
- ❌ Moving too fast without verification
- ❌ Building multiple things at once

---

## 🎯 Your Mission

Build a self-learning trading bot that:
1. The user can trust (because they can verify everything)
2. Actually learns (proven by improving performance)
3. Creates its own rules (visible in database)
4. Operates autonomously (runs 24/7 without intervention)
5. Makes consistent profit (verified by trade history)

**Follow this guide, and you'll succeed.**

**Ignore this guide, and you'll create another black box.**

**The choice is yours.**

Good luck! 🚀
