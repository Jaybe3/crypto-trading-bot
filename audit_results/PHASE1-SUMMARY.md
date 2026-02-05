# Phase 1: Automated Tooling Summary

**Date:** 2026-02-04
**Auditor:** Claude Code

---

## Tool Execution Status

| Tool | Ran | Exit Code | Output File |
|------|-----|-----------|-------------|
| pylint (JSON) | ✅ | 30 | pylint.json |
| pylint (text) | ✅ | 30 | pylint.txt |
| flake8 | ✅ | 1 | flake8.txt |
| ruff | ✅ | 1 | ruff.json |
| mypy | ✅ | 2 | mypy.txt |
| bandit (JSON) | ✅ | 1 | bandit.json |
| bandit (text) | ✅ | 1 | bandit.txt |
| vulture | ✅ | 3 | vulture.txt |
| radon cc | ✅ | 0 | radon_complexity.txt |
| radon mi | ✅ | 0 | radon_maintainability.txt |
| black | ✅ | 1 | black.txt |
| isort | ✅ | 1 | isort.txt |
| pydocstyle | ✅ | 1 | pydocstyle.txt |
| interrogate | ✅ | 0 | interrogate.txt |
| pytest + coverage | ✅ | 1 | pytest.txt, coverage.json |

**Tools NOT installed/run:** pyright, safety, pip-audit, pipreqs, deptry, semgrep, pydeps, xenon

---

## Issue Counts

| Tool | Issues |
|------|--------|
| pylint | ~1600 lines |
| flake8 | 396 |
| mypy | 11 errors |
| bandit | ~25 (mostly Low severity) |
| vulture (dead code) | 206 lines |
| black (formatting) | Many files need reformatting |
| isort (imports) | Many files need reordering |
| pydocstyle | Many issues |

---

## Critical/High Severity Issues

### From Bandit (Security)
- No CRITICAL or HIGH severity issues found
- All issues are LOW severity (asserts in production code, ANSI color codes flagged as "passwords")

### From Mypy (Type Checking)
- Missing type stubs for `requests` library (11 errors)
- No actual type errors in business logic detected

### From Pylint
Key categories:
- `W1203`: f-string logging (many instances) - MEDIUM
- `W0621`: Redefining name from outer scope - LOW
- `W0611`: Unused imports - LOW
- `W0718`: Catching general Exception - MEDIUM
- `C0301`: Line too long - LOW

---

## Test Status

| Metric | Value |
|--------|-------|
| Total Tests | 908 |
| Passed | 871 |
| Failed | 17 |
| Errors | 18 |
| Skipped | 2 |
| Coverage | 64.0% |

**Note:** All 17 failures and 18 errors are in `tests/deprecated/` directory - deprecated tests for deprecated code.

---

## Code Quality Metrics

### Complexity (Radon)
- **Average Complexity:** A (3.6) - EXCELLENT
- **Total Blocks Analyzed:** 907
- No functions rated C, D, E, or F

### Docstring Coverage (Interrogate)
- Most files: 93-100%
- Lowest: `models/reflection.py` at 44%

---

## Dead Code (Vulture)

206 items flagged at 60% confidence. Notable:
- Unused methods in `database.py` (30+)
- Unused API endpoints in `dashboard.py` and `dashboard_v2.py`
- Unused functions in `analysis/performance.py`

---

## Known Issues from Audit Prompt

These were pre-identified and need verification:

1. **SYMBOL_MAP mismatch** - `funding.py` and `candle_fetcher.py` vs `settings.py`
2. **Phase 3 modules not imported** - `src/sentiment/`, `src/technical/` in main.py/strategist.py
3. **coin_scorer.py FAVORED demotion** - checks win_rate but not P&L
4. **config/coins.json vs settings.py** - says binance_us vs bybit
5. **SYSTEM-STATE.md contradiction** - says "NOT INCLUDED" but Phase 3 complete
6. **Duplicate code in main.py** - lines 937-973

---

## Files Summary

| Directory | Python Files |
|-----------|-------------|
| src/ | 53 |
| scripts/ | 7 |
| tests/ | 45 |

| Directory | Markdown Files |
|-----------|---------------|
| docs/ | 46 |
| tasks/ | 40 |

**Total files requiring review:** ~191

---

## Next Steps

Proceed to Phase 2: Manual File-by-File Audit
