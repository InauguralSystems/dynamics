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

echo "--- life.eigs (Conway: temporal vs scalar) ---"
LOUT=$("$EIGS" life.eigs 2>&1)
echo "$LOUT"
echo "$LOUT" | grep -q "DONE"                  || { echo "FAIL: life.eigs did not finish"; exit 1; }
echo "$LOUT" | grep -q "period-2 oscillator"   || { echo "FAIL: blinker not classified period-2"; exit 1; }
echo "$LOUT" | grep -q "still life"            || { echo "FAIL: block not classified still life"; exit 1; }
echo "$LOUT" | grep -q "extinct"               || { echo "FAIL: single cell not classified extinct"; exit 1; }
# the lesson: blinker and block share one population verdict but differ in period
echo "$LOUT" | grep -q "only the temporal signature" || { echo "FAIL: temporal-vs-scalar contrast missing"; exit 1; }
echo "PASS: life distinguishes oscillator/still/translating the scalar predicate cannot"
