# Claude Code Prompt Template

Use this template for all Claude Code tasks to ensure consistent quality and regression prevention.

---

## TEMPLATE

```
# [TASK TITLE]

## MANDATORY FIRST STEP
Read `docs/development/DEVELOPMENT-DISCIPLINE.md` in full before doing anything else.

## CONTEXT
[What exists currently, what's broken, relevant bug IDs]

Example:
- Bug RT-009: Knowledge API endpoints return HTTP 500
- Root cause: dashboard_v2.py calls get_all_coins() but KnowledgeBrain has get_all_coin_scores()
- Files involved: src/dashboard_v2.py, src/knowledge.py

## PRE-CHANGE VERIFICATION
Run and save output:
```bash
./scripts/audit.sh > /tmp/audit_before.txt 2>&1
cat /tmp/audit_before.txt
```

## TASK
[Specific work to be done]

Example:
1. In src/dashboard_v2.py line 272, change `get_all_coins()` to `get_all_coin_scores()`
2. In src/dashboard_v2.py line 284, change `get_coin(coin)` to `get_coin_score(coin)`
3. Update `_format_coin()` to handle CoinScore objects

## POST-CHANGE VERIFICATION
Run and compare to baseline:
```bash
./scripts/audit.sh > /tmp/audit_after.txt 2>&1
diff /tmp/audit_before.txt /tmp/audit_after.txt || true
cat /tmp/audit_after.txt
```

Additional verification:
```bash
curl http://localhost:8080/api/knowledge/coins
# Should return HTTP 200 with coin data
```

## DONE MEANS
- [ ] Pre-change audit saved
- [ ] [Specific task criteria - e.g., "get_all_coins replaced with get_all_coin_scores"]
- [ ] [Specific task criteria - e.g., "API returns HTTP 200"]
- [ ] Post-change audit shows no regressions
- [ ] All existing tests still pass
- [ ] New tests added for this change (if applicable)
- [ ] Git commit made with bug ID in message

## CONSTRAINTS
- Read development framework FIRST
- Run audit BEFORE and AFTER
- Fix ONLY the specified issues
- Document any new issues found but don't fix them
- Show diffs for all changes
- Do NOT modify files not listed in TASK
```

---

## USAGE

1. Copy the template
2. Fill in [TASK TITLE], [CONTEXT], and [TASK] sections
3. Add specific verification steps for the task
4. Add specific DONE MEANS criteria
5. Give to Claude Code

---

## EXAMPLE: Fixing RT-009

```
# Fix RT-009: Knowledge API Endpoints Broken

## MANDATORY FIRST STEP
Read `docs/development/DEVELOPMENT-DISCIPLINE.md` in full before doing anything else.

## CONTEXT
- Bug RT-009: 5 knowledge API endpoints return HTTP 500
- Root cause: dashboard_v2.py calls methods that don't exist in KnowledgeBrain
  - Calls get_all_coins() → Should be get_all_coin_scores()
  - Calls get_coin() → Should be get_coin_score()
- Evidence: curl http://localhost:8080/api/knowledge/coins returns "Internal Server Error"
- Files: src/dashboard_v2.py (lines 266-330), src/knowledge.py

## PRE-CHANGE VERIFICATION
```bash
./scripts/audit.sh > /tmp/audit_before.txt 2>&1
cat /tmp/audit_before.txt
```

## TASK
1. In src/dashboard_v2.py:
   - Line 272: Change `get_all_coins()` to `get_all_coin_scores()`
   - Line 284: Change `get_coin(coin)` to `get_coin_score(coin)`

2. Verify _format_coin() handles CoinScore correctly (it should - check first)

## POST-CHANGE VERIFICATION
```bash
./scripts/audit.sh > /tmp/audit_after.txt 2>&1
diff /tmp/audit_before.txt /tmp/audit_after.txt || true
cat /tmp/audit_after.txt

# Test the endpoints
curl -s http://localhost:8080/api/knowledge/coins | head -20
curl -s http://localhost:8080/api/knowledge/patterns | head -20
```

## DONE MEANS
- [ ] Pre-change audit saved
- [ ] get_all_coins() → get_all_coin_scores() in dashboard_v2.py
- [ ] get_coin() → get_coin_score() in dashboard_v2.py
- [ ] /api/knowledge/coins returns HTTP 200
- [ ] /api/knowledge/patterns returns HTTP 200
- [ ] Post-change audit shows no regressions
- [ ] All existing tests pass
- [ ] Git commit with "Fix RT-009" in message

## CONSTRAINTS
- Read development framework FIRST
- Run audit BEFORE and AFTER
- Fix ONLY RT-009 - do not fix other bugs found
- Document any new issues but don't fix them
- Show diffs for dashboard_v2.py
```

---

## CHECKLIST BEFORE SENDING PROMPT

- [ ] Included MANDATORY FIRST STEP
- [ ] CONTEXT has specific bug IDs and evidence
- [ ] TASK has specific file:line references
- [ ] PRE-CHANGE VERIFICATION included
- [ ] POST-CHANGE VERIFICATION included
- [ ] DONE MEANS has checkboxes for each criterion
- [ ] CONSTRAINTS section included
