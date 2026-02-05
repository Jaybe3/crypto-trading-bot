# Bug RT-XXX: [Title]

## Summary
[One line description]

## Severity
[CRITICAL/HIGH/MEDIUM/LOW]

## Evidence (Before Fix)
[SQL queries, log output, or screenshots that prove the bug exists]

```sql
-- Example query showing the bug
SELECT * FROM table WHERE condition;
-- Result: [unexpected result]
```

```
# Log output or API response showing the bug
```

## Root Cause
[Why the bug happened - specific code location and logic error]

**Location:** `src/file.py:123`

**Problem:** [Describe what the code does wrong]

## Fix Applied
[What was changed, with file:line references]

**Files Changed:**
- `src/file.py:123-130` - [Description of change]
- `src/other.py:45` - [Description of change]

**Code Change:**
```python
# Before
old_code()

# After
new_code()
```

## Verification (After Fix)
[Commands to verify the fix worked]

```sql
-- Same query now returns expected result
SELECT * FROM table WHERE condition;
-- Result: [expected result]
```

```bash
# Verification command
./scripts/audit.sh | grep "related check"
# Output: PASS
```

## Regression Test Added
[Test that would catch this bug if reintroduced]

**Test Location:** `tests/test_xxx.py::test_xxx`

```python
def test_bug_rt_xxx_regression():
    """Ensure RT-XXX doesn't regress."""
    # Test code here
    assert expected_behavior
```

## Related Issues
- RT-YYY: [Related bug]
- DASH-ZZZ: [Related bug]

## Fixed In
**Commit:** `abc1234`
**Date:** YYYY-MM-DD
**Wave:** Wave-X
