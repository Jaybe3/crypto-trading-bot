# Pre-Change Checklist

Run this checklist BEFORE making any code changes.

## 1. Run Full Audit
```bash
./scripts/audit.sh
```
Save the output. This is your baseline.

## 2. Verify Tests Pass
```bash
python3 -m pytest tests/ -q
```
If any tests fail, DO NOT proceed. Fix them first or document why they're expected to fail.

## 3. Check Git Status
```bash
git status
```
Ensure working directory is clean or changes are intentional.

## 4. Document What You're Changing

Before writing code, document:
- What bug/feature you're addressing (ID)
- What files you expect to modify
- What the expected outcome is

Example:
```
Fixing: RT-009 (Knowledge API endpoints broken)
Files: src/dashboard_v2.py
Expected: /api/knowledge/coins returns HTTP 200
```

## 5. Create Pre-Wave Checkpoint
```bash
git add -A && git commit -m "PRE-WAVE-X: Checkpoint before [description]"
```

---

## After Changes

### 6. Run Audit Again
```bash
./scripts/audit.sh
```

Compare to baseline:
- All previously passing checks should still pass
- New checks related to your fix should now pass
- No new failures introduced

### 7. Run Specific Tests
```bash
python3 -m pytest tests/ -v -k "test_name"
```

### 8. Verify the Fix
Run the specific verification for your bug fix:
```bash
# Example for RT-009
curl http://localhost:8080/api/knowledge/coins
# Should return HTTP 200 with data
```

### 9. Check for Regressions
```bash
python3 -m pytest tests/ -q
```
All tests must pass.

---

## Commit with Evidence

Include in commit message:
- Bug ID fixed
- Before/after audit results
- Verification steps performed

Example:
```
Fix RT-009: Knowledge API endpoints

Before: /api/knowledge/coins returned HTTP 500
After: /api/knowledge/coins returns HTTP 200 with coin data

Changes:
- dashboard_v2.py: Fixed method call from get_all_coins() to get_all_coin_scores()

Verification:
- curl test passes
- audit.sh shows knowledge endpoints PASS
- All existing tests pass

Audit: PASSED (no regressions)
```

---

## Quick Reference

| Step | Command | Must Pass? |
|------|---------|------------|
| Baseline audit | `./scripts/audit.sh` | Record it |
| Tests pass | `pytest tests/ -q` | YES |
| Git clean | `git status` | Aware |
| Post-change audit | `./scripts/audit.sh` | No regressions |
| Fix verification | [specific to bug] | YES |
| All tests | `pytest tests/ -q` | YES |
