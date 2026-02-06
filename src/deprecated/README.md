# Deprecated Modules

These modules are Phase 1 code that is no longer integrated into the system.
They query Phase 1 tables (closed_trades, open_trades, learnings, trading_rules,
activity_log) that are not used by the Phase 2 trading system.

Moved here during audit on 2026-02-05.

| File | Original Purpose | Why Deprecated |
|------|-----------------|----------------|
| metrics.py | Performance metrics and alerts | Queries Phase 1 tables, not imported by anything |
| daily_summary.py | Daily trading summary | Queries Phase 1 tables, not imported by anything |
