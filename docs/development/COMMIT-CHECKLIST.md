# Pre-Commit Checklist

## Before Every Commit

### Code
- [ ] Code runs without errors
- [ ] Tests pass (or documented why skipped)
- [ ] No hardcoded secrets

### Integration
- [ ] New component imported and called from main.py?
- [ ] Changed interfaces updated downstream?

### Documentation
- [ ] SYSTEM-STATE.md updated (if architecture changed)
- [ ] Task file updated (if task-related)
- [ ] README updated (if user-facing)

### The Big Question
- [ ] Would a new developer understand what's running after this commit?

If no → update docs before committing.
