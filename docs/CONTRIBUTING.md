# Contributing Guidelines

## Definition of Done

A task is COMPLETE only when ALL are true:

- [ ] Code implemented (not stub/placeholder)
- [ ] Code integrated (called from main.py)
- [ ] Tests pass (or manual verification documented)
- [ ] SYSTEM-STATE.md updated (if architecture changed)
- [ ] Task file completion notes added

If ANY is false → task is IN PROGRESS, not COMPLETE.

---

## Documentation Rules

### Single Source of Truth

`docs/SYSTEM-STATE.md` is authoritative for what runs in production.

### No Documentation Drift

If you find docs that contradict SYSTEM-STATE.md:
1. Stop current work
2. Determine which is correct
3. Update the incorrect document
4. Note the fix in task completion

---

## Deployment Rules

### Production Changes

Any change to production requires:
1. Update SYSTEM-STATE.md
2. Update tasks/INDEX.md
3. Note in task file

### Deprecated Code

When deprecating:
1. Rename with `_legacy` or `_deprecated` suffix
2. Add to SYSTEM-STATE.md deprecated table
3. Keep 30 days minimum
4. Delete only after verification
