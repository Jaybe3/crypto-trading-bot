# ADR-001: Database as Single Source of Truth

## Status
PROPOSED (pending implementation)

## Context
The system has three data stores (Sniper memory, JSON file, database) that have drifted out of sync, causing RT-001 through RT-005.

Evidence of current drift (2026-02-05):
- account_state (DB): $1,000 balance
- sniper_state (JSON): $9,930 balance
- Sniper memory: $9,935 balance
- Profitability (from trade_journal): $10,757 balance

This makes the system unreliable and confusing for users.

## Decision
Database will be the single source of truth for all persistent state.

## Consequences

### Positive
- All API endpoints return consistent data
- Bot restart preserves all state
- Single place to query for debugging
- Audit trail in database
- Historical analysis possible

### Negative
- More database writes (performance impact)
- Sniper must handle database failures gracefully
- Migration required for existing data

### Implementation Plan
1. Add `update_account_state()` calls after every trade
2. Modify API endpoints to read from database
3. Keep JSON file as backup/recovery only
4. Add data consistency checks to audit script

## Alternatives Considered

### 1. Sniper memory as source of truth
**Rejected** - Lost on restart, no persistence

### 2. JSON file as source of truth
**Rejected** - No query capability, hard to analyze

### 3. Event sourcing
**Rejected** - Too complex for current needs, would require significant rewrite

### 4. Keep current multi-source approach with sync
**Rejected** - Sync adds complexity and failure modes

## Migration Strategy

1. Fix RT-001: Add `update_account_state()` calls
2. Verify data flows to database correctly
3. Update API endpoints one at a time
4. Add consistency checks
5. Deprecate JSON file (keep for emergency recovery)

## Related Issues
- RT-001: update_account_state() never called
- RT-002: open_trades/closed_trades unused
- RT-003: Data disagreement
- RT-004: API endpoints read different sources
- RT-005: Three disconnected data stores
