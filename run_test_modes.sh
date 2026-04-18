#!/bin/bash
cd /home/ck_kun/TianDao-Info

# Test 1: --dry-run should NOT write selected_quote.json
rm -f data/quotes/selected_quote.json
echo "=== TEST 1: --dry-run ==="
python3 daily_select.py --dry-run
echo "selected_quote.json exists after dry-run: $(ls data/quotes/selected_quote.json 2>/dev/null && echo YES || echo NO)"

# Test 2: normal mode should write selected_quote.json only
echo ""
echo "=== TEST 2: normal mode (no flags) ==="
python3 daily_select.py
echo "selected_quote.json exists after normal: $(ls data/quotes/selected_quote.json 2>/dev/null && echo YES || echo NO)"
echo "rotation_state.json rotation_index before --commit-state:"
cat data/state/rotation_state.json

# Test 3: --commit-state should update state.json
echo ""
echo "=== TEST 3: --commit-state ==="
python3 daily_select.py --commit-state
echo "rotation_state.json rotation_index after --commit-state:"
cat data/state/rotation_state.json
echo "selected_quote.json exists after commit: $(ls data/quotes/selected_quote.json 2>/dev/null && echo YES || echo NO)"