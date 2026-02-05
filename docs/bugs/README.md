# Bug Tracking

## Structure

- `../../audit_results/COMPLETE-BUG-LIST.md` - Master list of all known bugs
- `FIXED/` - Documentation of fixed bugs
- `OPEN/` - Documentation of open bugs (complex bugs needing detailed tracking)

## Bug ID Format

- `RT-XXX` - Runtime bugs (data flow, integration, database)
- `DASH-XXX` - Dashboard bugs (UI, API endpoints)
- `LEARN-XXX` - Learning system bugs (reflection, adaptation)
- `PHASE3-XXX` - Phase 3 technical indicator bugs

## Severity Levels

| Severity | Description | Response Time |
|----------|-------------|---------------|
| CRITICAL | System doesn't work as intended | Immediate |
| HIGH | Major functionality broken | Within 1 day |
| MEDIUM | Functionality impaired | Within 1 week |
| LOW | Cosmetic / tech debt | As time permits |

## Bug Documentation Format

Each bug should have:
1. ID (RT-XXX, DASH-XXX, etc.)
2. Severity (CRITICAL, HIGH, MEDIUM, LOW)
3. Description
4. Evidence (queries, logs, screenshots)
5. Root Cause
6. Fix Applied
7. Verification Steps
8. Regression Test Added

See `FIXED/TEMPLATE.md` for the full template.

## Current Status (2026-02-05)

| Severity | Open | Fixed |
|----------|------|-------|
| CRITICAL | 3 | 0 |
| HIGH | 6 | 0 |
| MEDIUM | 5 | 0 |
| LOW | 2 | 0 |

**Total: 16 bugs identified**

See `../../audit_results/COMPLETE-BUG-LIST.md` for the full list with evidence.

## Process

### When a bug is found:
1. Add to COMPLETE-BUG-LIST.md with evidence
2. Assign ID based on category
3. Determine severity
4. If complex, create detailed doc in OPEN/

### When a bug is fixed:
1. Create doc in FIXED/ using template
2. Include verification evidence
3. Reference git commit
4. Update COMPLETE-BUG-LIST.md status
5. Add regression test

### Verification Requirements
Every fix must include:
- Before/after audit output
- Specific test that would catch regression
- Evidence that fix works (query results, API responses, etc.)
