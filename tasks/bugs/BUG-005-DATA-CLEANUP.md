# BUG-005-DATA-CLEANUP: Database reset (fresh start)

**Severity:** N/A (data maintenance)
**Date:** 2026-02-05
**Status:** COMPLETE

## Rationale
Database contained 951 trades generated while multiple critical bugs were active:
- BUG-002/003/004: Schema mismatches crashed learning analysis
- BUG-005: 701 trades had corrupted timestamps (epoch 1969)
- Learning pipeline produced 0 insights from analyzed trades
- Only 2/20 coins had scores despite 211 closed trades

Data had no analytical value. Fresh start with fixed code preferred.

## Actions
1. Backed up old database to data/trading_bot.db.pre-audit-backup (2.6MB)
2. Backed up old sniper state to data/sniper_state.json.pre-audit-backup
3. Deleted database and sniper state
4. Verified system recreates database with all 23 tables on startup

## Verification
- Backups exist and preserved
- New database created with 23 tables
- Test suite passes (835 passed, 1 skipped)

## Backup Contents (for reference)
Old database contained:
- 951 total trades in trade_journal
- 714 orphaned "open" trades (never closed)
- 98 trades with corrupted timestamps (1969-12-31)
- 2 coins in coin_scores (BTC, SOL only)
