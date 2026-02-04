# RECOMMENDATIONS

**Generated:** February 3, 2026
**Auditor:** Claude Code (Automated)

This document provides prioritized recommendations for addressing audit findings.

---

## PRIORITY 1: CRITICAL (Fix Immediately)

### R-001: Update Documentation References

**Addresses:** I-001 (23 files reference main.py)

**Action:** Replace all references to `main.py` with `main.py`

**Files to Update:**

```bash
# Run this command to find and list all occurrences:
grep -r "main_v2\.py" --include="*.md" docs/ tasks/ *.md
```

**Estimated Changes:**
| File | Changes Needed |
|------|----------------|
| docs/operations/RUNBOOK.md | ~12 replacements |
| docs/development/SETUP.md | ~8 replacements |
| docs/architecture/SYSTEM-OVERVIEW.md | ~4 replacements |
| docs/operations/TROUBLESHOOTING.md | ~3 replacements |
| docs/operations/DASHBOARD-GUIDE.md | ~2 replacements |
| docs/operations/PAPER-TRADING-GUIDE.md | ~2 replacements |
| docs/architecture/COMPONENT-REFERENCE.md | ~2 replacements |
| docs/PRE-RUN-CHECKLIST.md | ~2 replacements |
| + 15 task files | ~1 each |

**Verification:**
```bash
# After fixing, this should return no results:
grep -r "main_v2\.py" --include="*.md" docs/ tasks/ *.md
```

---

### R-002: Fix or Remove Broken Tests

**Addresses:** I-002 (92 test failures/errors)

**Action:** Categorize and handle each test failure appropriately

**Step 1: Remove/Skip Deprecated Tests**
```python
# Add to test files for deprecated components:
import pytest

pytestmark = pytest.mark.skip(reason="Testing deprecated component")
```

**Files to Mark Deprecated:**
- `tests/test_trading_engine.py` - 36 errors
- `tests/test_learning_system.py` - 7 errors

**Step 2: Fix Strategist Tests**
The 13 failing tests in `test_strategist.py` need investigation:
- Check if mock interfaces match current implementation
- Update test fixtures if needed
- Verify TradeCondition creation matches new validation

**Step 3: Fix Knowledge Integration Tests**
The 20 errors in `test_knowledge_integration.py`:
- Check import paths
- Update mock objects
- Verify integration interfaces

**Target:** 525+ tests passing, 0 failures, 0 errors

---

## PRIORITY 2: HIGH (Fix Before Paper Trading)

### R-003: Archive Deprecated Files

**Addresses:** I-003 (8 deprecated files, ~2150 lines)

**Action:** Move deprecated files to archive directory

```bash
# Create archive
mkdir -p archive/phase1

# Move deprecated files
mv src/main_legacy.py archive/phase1/
mv src/dashboard.py archive/phase1/
mv src/trading_engine.py archive/phase1/
mv src/learning_system.py archive/phase1/
mv src/market_data.py archive/phase1/
mv src/risk_manager.py archive/phase1/
mv src/metrics.py archive/phase1/
mv src/volatility.py archive/phase1/

# Update git
git add -A
git commit -m "Archive Phase 1 deprecated files"
```

**Alternative:** Delete files completely if rollback not needed:
```bash
rm src/main_legacy.py src/dashboard.py src/trading_engine.py \
   src/learning_system.py src/market_data.py src/risk_manager.py \
   src/metrics.py src/volatility.py
```

---

### R-004: Address Analysis Module

**Addresses:** I-004 (analysis module not integrated)

**Options:**

**Option A: Remove Unused Module**
```bash
rm -rf src/analysis/
```

**Option B: Integrate Module**
- Connect `analysis/performance.py` to dashboard
- Use `analysis/learning.py` in reflection reports
- Document intended usage

**Recommendation:** Option A (Remove) - unless there's a specific plan to use these files.

---

### R-005: Handle Deprecated Test Files

**Addresses:** I-005 (tests for deprecated components)

**Action:** Either remove or mark as deprecated

**Option A: Remove Test Files**
```bash
rm tests/test_trading_engine.py
rm tests/test_learning_system.py
rm tests/test_dashboard.py  # if deprecated
rm tests/test_risk_manager.py  # if deprecated
```

**Option B: Mark as Skipped**
```python
# At top of each deprecated test file:
import pytest
pytestmark = pytest.mark.skip(reason="Tests deprecated Phase 1 component")
```

---

## PRIORITY 3: MEDIUM (Fix During Stabilization)

### R-006: Align Exchange Configuration

**Addresses:** I-006 (Binance symbols with Bybit exchange)

**Options:**

**Option A: Update Symbols for Bybit**
- Bybit uses same format (BTCUSDT)
- May already be compatible
- Verify symbol mapping works

**Option B: Document Symbol Translation**
- Add symbol mapping table to documentation
- Ensure market_feed.py handles translation

**Verification:**
```python
# Test symbol compatibility
from src.market_feed import MarketFeed
feed = MarketFeed()
# Connect and verify coin subscriptions work
```

---

### R-007: Integrate or Remove daily_summary.py

**Addresses:** I-007 (daily_summary.py not integrated)

**Options:**

**Option A: Integrate**
- Add to main.py scheduler
- Call daily at midnight
- Output to logs/daily_summary/

**Option B: Remove**
```bash
rm src/daily_summary.py
```

---

### R-008: Fix Coin Count Documentation

**Addresses:** I-008 (README says 45, config has 20)

**Action:** Update README.md line 12

**From:**
```markdown
- **45-Coin Universe** across 3 risk tiers
```

**To:**
```markdown
- **20-Coin Universe** across 3 risk tiers
```

---

### R-009: Fix Exchange Documentation

**Addresses:** I-009 (docs say Binance, system uses Bybit)

**Action:** Update docs/architecture/SYSTEM-OVERVIEW.md

**From:**
```markdown
WebSocket connection to Binance
```

**To:**
```markdown
WebSocket connection to Bybit (Binance fallback available)
```

---

### R-010: Fix Strategist Tests

**Addresses:** I-010 (13 Strategist test failures)

**Investigation Steps:**
1. Run with verbose output: `pytest tests/test_strategist.py -v --tb=long`
2. Check if TradeCondition mock matches new validation rules
3. Verify trigger price validation (0.1-0.3% rule)
4. Update test fixtures if interface changed

**Key Tests to Fix:**
- `test_calculate_take_profit_long` - Math validation
- `test_generate_conditions` - Full generation flow
- `test_callback_notification` - Event handling

---

## PRIORITY 4: LOW (Fix When Convenient)

### R-011: Fix Knowledge Integration Tests

**Addresses:** I-011 (20 test errors)

**Investigation:**
```bash
pytest tests/test_knowledge_integration.py -v --tb=long 2>&1 | head -100
```

**Common Causes:**
- Import errors
- Mock object mismatches
- Interface changes not reflected in tests

---

### R-012: Fix PHASE-2-INDEX Location

**Addresses:** I-012 (missing file reference)

**Action:** Update any links to correct path

**From:** `docs/specs/PHASE-2-INDEX.md`
**To:** `docs/architecture/PHASE-2-INDEX.md`

---

### R-013: Standardize Date Formats

**Addresses:** I-013 (mixed date formats)

**Standard:** Use "February 3, 2026" format (human readable)

**Files to Check:**
- All docs/*.md headers
- Task file headers

---

### R-014: Document Sniper State Path

**Addresses:** I-014 (sniper state file path)

**Action:** Add to COMPONENT-REFERENCE.md

```markdown
### Sniper State File
- **Location:** `data/sniper_state.json`
- **Contents:** Active conditions, open positions
- **Persistence:** Saved on shutdown, loaded on startup
```

---

## IMPLEMENTATION ORDER

### Phase 1: Critical (Before Any Production Use)
1. R-001: Update main.py references in docs
2. R-002: Fix/skip broken tests

### Phase 2: High (Before Paper Trading Validation)
3. R-003: Archive deprecated files
4. R-004: Remove unused analysis module
5. R-005: Handle deprecated tests

### Phase 3: Medium (During Stabilization)
6. R-006: Verify exchange configuration
7. R-007: Decide on daily_summary.py
8. R-008: Fix coin count in README
9. R-009: Fix exchange in docs
10. R-010: Fix Strategist tests

### Phase 4: Low (Ongoing Cleanup)
11. R-011: Fix knowledge integration tests
12. R-012: Fix PHASE-2-INDEX location
13. R-013: Standardize dates
14. R-014: Document sniper state

---

## QUICK WINS (Can Do Now)

These can be done with simple find-and-replace:

```bash
# R-001: Fix main.py references
find docs/ tasks/ -name "*.md" -exec sed -i 's/main_v2\.py/main.py/g' {} \;

# R-008: Fix coin count (manual edit README.md)

# R-009: Fix exchange reference (manual edit SYSTEM-OVERVIEW.md)
```

---

## VERIFICATION CHECKLIST

After implementing recommendations:

- [ ] `grep -r "main_v2\.py" docs/ tasks/` returns nothing
- [ ] `pytest tests/` shows 0 failures, 0 errors
- [ ] No deprecated files in src/ (or clearly marked)
- [ ] README coin count matches config
- [ ] Documentation matches actual system behavior
- [ ] All links in docs resolve correctly

---

## ESTIMATED EFFORT

| Priority | Recommendations | Estimated Effort |
|----------|-----------------|------------------|
| Critical | R-001, R-002 | 2-4 hours |
| High | R-003, R-004, R-005 | 1-2 hours |
| Medium | R-006 to R-010 | 2-4 hours |
| Low | R-011 to R-014 | 1-2 hours |

**Total:** 6-12 hours of cleanup work

---

*This concludes the audit recommendations. Prioritize Critical and High items before running paper trading validation.*
