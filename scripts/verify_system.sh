#!/bin/bash
# System health check - run after every wave of changes
# Usage: bash scripts/verify_system.sh

echo "=== IMPORT CHECK ==="
python3 -c "
import importlib, sys
sys.path.insert(0, '.')
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
python3 -m pytest tests/ -q --tb=no 2>&1 | tail -5

echo ""
echo "=== SYMBOL_MAP DUPLICATION CHECK ==="
echo -n "  SYMBOL_MAP definitions (should be 1 after fix): "
grep -rn "SYMBOL_MAP\s*=" src/ config/ 2>/dev/null | wc -l

echo ""
echo "=== DOC DRIFT CHECK ==="
echo -n "  'Binance' in docs (should be 0 after fix): "
grep -rl "Binance" docs/ 2>/dev/null | wc -l
echo -n "  '45 coins' in docs (should be 0 after fix): "
grep -rl "45 coins" docs/ 2>/dev/null | wc -l

echo ""
echo "=== VERIFICATION COMPLETE ==="
