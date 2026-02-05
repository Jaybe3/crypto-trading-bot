# New Issues Found During Fix Waves

Issues discovered during implementation that were NOT in the original 64-issue audit.
These get documented here, not fixed inline.

| Date | Found During | File | Description | Severity |
|------|-------------|------|-------------|----------|
| 2026-02-04 | Wave 2 Group D | docs/architecture/AUTONOMOUS-TRADER-SPEC.md:817 | References deleted coins.json in file tree | LOW |
| 2026-02-05 | Wave 5 Part 1 | tests/test_quick_update.py:TestPerformance | Flaky timing test - fails in full suite but passes in isolation | LOW |
