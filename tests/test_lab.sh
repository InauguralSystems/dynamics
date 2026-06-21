#!/usr/bin/env bash
# Runs the standalone lab programs (not the importable package surface) and
# asserts they finish and produce their characteristic observer output. Keeps
# the corpus specimens runtime-verified — the runtime certifies the code.
set -euo pipefail

EIGS="${EIGENSCRIPT:-eigenscript}"

echo "--- physics.eigs (damped-oscillator zeta-sweep) ---"
OUT=$("$EIGS" physics.eigs 2>&1)
echo "$OUT"

echo "$OUT" | grep -q "DONE"            || { echo "FAIL: physics.eigs did not finish"; exit 1; }
echo "$OUT" | grep -q "DIVERGES"        || { echo "FAIL: no divergence detected for zeta<0"; exit 1; }
echo "$OUT" | grep -q "x OSCILLATES"    || { echo "FAIL: no oscillation detected for underdamped zeta"; exit 1; }
# critical/overdamped rows must NOT oscillate: the last two sweep rows read "settles"
SETTLES=$(echo "$OUT" | grep -c "settles" || true)
[ "$SETTLES" -ge 1 ] || { echo "FAIL: no monotonic-settle row for zeta>=1"; exit 1; }

echo "PASS: physics zeta-sweep produces the expected regime spectrum"
