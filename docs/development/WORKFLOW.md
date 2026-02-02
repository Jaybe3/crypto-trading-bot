# Development Workflow

This document explains how to work on the crypto trading bot project, whether you're Claude Code or a human developer.

---

## Quick Start

### Every Session
```
1. Read .clinerules
2. Read tasks/INDEX.md
3. Check tasks/active/ for in-progress work
4. Confirm with user what to work on
5. Begin (spec first if new work)
```

### Completing Work
```
1. Verify with runnable commands
2. Complete all task file sections
3. Move task to tasks/completed/{phase}/
4. Update tasks/INDEX.md
5. Get user approval
```

---

## Task Lifecycle

```
CREATE ──> SPECIFY ──> IMPLEMENT ──> VERIFY ──> DOCUMENT ──> CLOSE
   │          │            │           │           │           │
   │          │            │           │           │           │
 New task   Full spec    Code in    User runs  Complete    Move to
 from       approved     small      commands   all task    completed/
 template   by user      steps      confirms   sections    folder
```

### 1. CREATE

Create new task file from template:
```bash
cp tasks/templates/TASK-TEMPLATE.md tasks/active/TASK-XXX.md
```

Fill in:
- Title, Status (IN PROGRESS), Created date
- Objective (1-2 sentences)
- Background (why this exists)

### 2. SPECIFY

Complete the specification:
- Detailed requirements
- Acceptance criteria (checkboxes)
- Technical approach
- Files to create/modify

**STOP and get user approval before coding.**

### 3. IMPLEMENT

Build incrementally:
- One small change at a time
- Test each change before proceeding
- Commit working code frequently

### 4. VERIFY

Provide verification:
- Exact commands user can run
- Expected output
- How to confirm it's working

User must verify independently.

### 5. DOCUMENT

Complete task file:
- Files Created table
- Files Modified table
- Completion Notes (what actually happened)
- Any deviations from spec

### 6. CLOSE

Finalize:
```bash
mv tasks/active/TASK-XXX.md tasks/completed/phase-X-name/
```

Update `tasks/INDEX.md` with completion.

---

## Task File Template

See `tasks/templates/TASK-TEMPLATE.md` for the standard format.

Key sections:
- **Objective:** What this accomplishes (1-2 sentences)
- **Background:** Why this task exists
- **Specification:** Detailed requirements
- **Technical Approach:** How to implement
- **Files Created/Modified:** Tables tracking changes
- **Acceptance Criteria:** Checkboxes for completion
- **Verification:** Commands to prove it works
- **Completion Notes:** What actually happened

---

## Common Mistakes to Avoid

| Mistake | Consequence | Prevention |
|---------|-------------|------------|
| Coding without spec | Rework when requirements wrong | Always spec first |
| Large implementation steps | Hard to debug | Small, verifiable steps |
| Skipping verification | Bugs found later | User must run commands |
| Empty doc sections | Lost knowledge | Fill everything or mark N/A |
| Not updating INDEX | Inaccurate status | Always update on completion |

---

## Branching Strategy

For this project, work directly on main branch with frequent commits. Each commit should be a working state.

Commit message format:
```
[Component] Brief description

- Detail 1
- Detail 2

Task: TASK-XXX
```

---

## Testing

### Unit Tests
```bash
python -m pytest tests/ -v
```

### Manual Testing
Run verification commands from task file.

### Integration Testing
Start full system and observe behavior:
```bash
bash scripts/start.sh
# Watch logs
tail -f logs/bot.log
# Check dashboard
open http://localhost:8080
```

---

## Environment Setup

See `docs/development/SETUP.md` for environment setup instructions.

---

*Last Updated: February 2026*
