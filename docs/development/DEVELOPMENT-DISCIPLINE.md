# DEVELOPMENT DISCIPLINE FRAMEWORK

**Purpose:** Prevent the failure modes that got us here. Make rigorous verification the default, not the exception.

---

## THE THREE RULES

Every action in this project follows three rules, in this order:

1. **Verify before you act.** Never fix something based on an assumption. Read the code. Run the check. Confirm the assumption is true.
2. **Challenge before you deliver.** Before calling anything done, ask: "What could go wrong? What am I assuming? What haven't I checked?"
3. **Prove before you claim.** "Done" means showing evidence, not saying a word. A passing test. A grep output. A screenshot. No proof, not done.

---

## FOR CLAUDE CODE: THE PROMPT FRAMEWORK

Every Claude Code prompt must contain these 5 sections. No exceptions.

### Section 1: CONTEXT (What exists right now)
Tell Claude Code what the current state is. What files exist, what's broken, what was tried before. Don't let it guess.

```
## CONTEXT
- File X exists at path Y
- It currently does Z (which is wrong because...)
- Previous attempt did A but failed because B
- Related files: [list]
```

### Section 2: TASK (What to do)
Specific, unambiguous instructions. Not "fix the dashboard" but "in src/dashboard_v2.py, change line 14 from `import main_v2` to `import main`."

### Section 3: VERIFICATION REQUIREMENTS (Prove it works)
Every task must include verification steps that Claude Code must run and include in its output.

```
## VERIFICATION
Before implementing:
- [ ] Read [file] lines [X-Y] to confirm [assumption]
- [ ] Run `grep -n "[pattern]" [file]` to verify [thing]

After implementing:
- [ ] Run test suite: `python -m pytest tests/test_[relevant].py -v`
- [ ] Show the diff of every file changed
- [ ] Run `python -c "from src.X import Y"` to verify imports work
```

### Section 4: DEFINITION OF DONE
Explicit checklist. Task is not complete until every box is checked.

```
## DONE MEANS
- [ ] Code change implemented
- [ ] All verification checks pass (output included)
- [ ] Tests pass (output included)
- [ ] No new warnings or errors introduced
- [ ] Related documentation updated (if applicable)
- [ ] Diff of every changed file shown
```

### Section 5: IMPORTANT CONSTRAINTS
Guardrails that prevent scope creep and corner-cutting.

```
## IMPORTANT
- Do NOT modify any file not listed in TASK
- Do NOT skip verification steps
- If any verification step fails, STOP and report - do not guess a fix
- If you discover a new issue while working, document it but do not fix it
- Task is NOT DONE until all DONE MEANS boxes are checked with evidence
```

---

## FOR THIS PROJECT (Claude.ai): THE REVIEW PROTOCOL

### Before drafting a Claude Code prompt:
1. **State what I know** - What's the current state based on evidence?
2. **State what I'm assuming** - What haven't I verified?
3. **Challenge the assumptions** - For each assumption, what happens if it's wrong?
4. **Add verification steps** - Turn each assumption into a check

### Before approving Claude Code output:
1. **Read the evidence** - Did it actually show test output? Diffs? Grep results?
2. **Check for gaps** - Did it skip any verification steps?
3. **Spot-check claims** - If it says "all tests pass," did it show the output?
4. **Ask "what changed?"** - Get a list of every file modified and why

### After any wave of changes:
1. **Run a mini-audit** - Verify the changes didn't break anything else
2. **Update docs** - If code changed, docs change in the same wave
3. **Update SYSTEM-STATE.md** - Single source of truth stays current

---

## THE CHALLENGE CHECKLIST

Before ANY deliverable leaves this project (prompt, plan, assessment), run through:

| Question | If the answer is "I don't know" |
|----------|-------------------------------|
| What exactly will this change? | Stop. Read the code first. |
| What could go wrong with this change? | Stop. Think through failure modes. |
| What am I assuming about the current state? | Stop. Add verification step. |
| Has this assumption been verified with evidence? | Stop. Run the check first. |
| If this fix is wrong, what breaks? | Stop. Add a rollback plan. |
| How will we know this worked? | Stop. Add a test or verification. |
| What else touches the same code/data? | Stop. Check for side effects. |
| Did I read the actual file, or am I working from memory? | Stop. Read the actual file. |

---

## ANTI-PATTERNS TO CATCH

These are the specific failure modes from our history. If you see any of these, stop.

| Anti-Pattern | What It Looks Like | What To Do Instead |
|-------------|--------------------|--------------------|
| **"COMPLETE" without proof** | "Task done ✅" with no test output | Demand evidence. Show the passing test. |
| **Fix-and-pray** | Changing code without verifying assumptions | Run verification BEFORE the fix |
| **Skipped test** | `@pytest.mark.skip("known bug")` | Fix the bug. Don't skip the test. |
| **Assumption cascade** | Fix A assumes B, B assumes C, nobody checked C | Verify from the bottom up |
| **Doc drift** | Code changes without doc updates | Code and docs change in the same commit |
| **Scope creep** | "While I was in there, I also changed..." | One task per prompt. New issues get new tasks. |
| **Optimistic reading** | "All chains verified COMPLETE" when they crash | Claims require runtime proof, not just code reading |
| **Percentage theater** | "100% audit" that covered 18% | Define scope upfront, track completion honestly |

---

## LIVING VERIFICATION: SYSTEM HEALTH CHECKS

Create a script that runs automatically and catches drift before it becomes a crisis.

```bash
# scripts/verify_system.sh - Run after every wave of changes

echo "=== IMPORT CHECK ==="
python -c "
import importlib, sys
modules = ['src.main', 'src.strategist', 'src.dashboard_v2', 'src.quick_update',
           'src.coin_scorer', 'src.analysis.learning', 'src.technical.manager']
for mod in modules:
    try:
        importlib.import_module(mod)
        print(f'  OK: {mod}')
    except Exception as e:
        print(f'  FAIL: {mod} - {e}')
"

echo ""
echo "=== TEST SUITE ==="
python -m pytest tests/ -q --tb=no 2>&1 | tail -5

echo ""
echo "=== DATABASE SCHEMA VS QUERIES ==="
# Check that every table queried in code exists in database.py
python -c "
import re, subprocess
# Extract tables from CREATE TABLE statements
with open('src/database.py') as f:
    creates = set(re.findall(r'CREATE TABLE IF NOT EXISTS (\w+)', f.read()))
# Extract tables from SELECT/INSERT/UPDATE/DELETE statements
result = subprocess.run(['grep', '-rn', 'FROM\|INTO\|UPDATE', 'src/'],
                       capture_output=True, text=True)
queried = set(re.findall(r'(?:FROM|INTO|UPDATE)\s+(\w+)', result.stdout))
missing = queried - creates - {'sqlite_master', 'pragma'}
if missing:
    print(f'  FAIL: Tables queried but not defined: {missing}')
else:
    print(f'  OK: All {len(queried)} queried tables exist in schema')
"

echo ""
echo "=== CONFIG CONSISTENCY ==="
# Check SYMBOL_MAP only exists once
echo -n "  SYMBOL_MAP definitions: "
grep -rn "SYMBOL_MAP\s*=" src/ | wc -l

echo ""
echo "=== DOC DRIFT CHECK ==="
# Check for known drift indicators
echo -n "  'Binance' in docs (should be 0): "
grep -rl "Binance" docs/ 2>/dev/null | wc -l
echo -n "  '45 coins' in docs (should be 0): "
grep -rl "45 coins" docs/ 2>/dev/null | wc -l
```

This script runs in 10 seconds. Run it after every Claude Code session.

---

## HANDOFF PROTOCOL: Claude.ai ↔ Claude Code

The division of labor is critical. Mixing planning and execution is how things broke.

| Claude.ai (this project) | Claude Code |
|---------------------------|-------------|
| Think, plan, design | Execute, implement, test |
| Draft prompts | Run prompts |
| Review output evidence | Produce output evidence |
| Make architectural decisions | Follow architectural decisions |
| Approve or reject | Report results honestly |

**The handoff flow:**

```
Claude.ai drafts prompt
    → User reviews/approves prompt
        → User gives prompt to Claude Code
            → Claude Code executes and returns evidence
                → User pastes results back to Claude.ai
                    → Claude.ai reviews evidence against expectations
                        → If gaps found, new prompt drafted
                        → If all checks pass, move to next task
```

**Critical rule:** Claude Code never decides architecture. If it encounters a design question during implementation, it stops and reports back. It does not guess.

---

## MEMORY UPDATES

These rules should be stored in project memory so every conversation starts with them:

1. Verify before act. Challenge before deliver. Prove before claim.
2. Every Claude Code prompt needs: CONTEXT, TASK, VERIFICATION, DONE MEANS, CONSTRAINTS.
3. "Done" requires evidence (test output, diffs, grep results). No evidence = not done.
4. Never fix based on assumptions. If unsure, run a check first.
5. New issues found during a fix get documented separately, not fixed inline.
6. Code changes and doc updates happen in the same wave.
7. Run verify_system.sh after every wave.

---

## ROLLBACK PROTOCOL

Every wave of changes must be recoverable.

**Before each wave:**
```bash
git add -A && git commit -m "PRE-WAVE-[N]: Checkpoint before [description]"
```

**If a wave breaks things:**
```bash
git diff HEAD  # See what changed
git stash      # Save current state
git checkout .  # Revert to pre-wave checkpoint
# Investigate what went wrong before trying again
```

**Rule:** Never start Wave N+1 until Wave N is committed, tested, and verified. Each wave is an atomic unit - either all of its fixes land or none of them do.

---

## HOW THIS WOULD HAVE PREVENTED OUR MISTAKES

| What Happened | Which Rule Prevents It |
|--------------|----------------------|
| Phase 3 built but never connected | DONE MEANS: "Integration test passes" |
| FAVORED test skipped instead of bug fixed | Anti-pattern: "Skipped test" |
| 18% audit called "comprehensive" | Anti-pattern: "Percentage theater" |
| Fix plans with unverified assumptions | Rule: "Verify before you act" |
| Dashboard data mismatch not caught | Living verification: system health check |
| Documentation describing wrong system | Rule: "Code and docs change together" |
| "All chains COMPLETE" when they crash | Anti-pattern: "Optimistic reading" |
| Config fallbacks silently overriding settings | Challenge checklist: "What else touches this?" |
