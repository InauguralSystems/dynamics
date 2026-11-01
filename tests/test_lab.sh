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
# Check each zeta row on its own: the critical/overdamped rows (zeta>=1) must
# read exactly "settles" with x:osc unset. Counting "settles" anywhere was
# satisfied by the underdamped rows' "x OSCILLATES, energy settles".
printf '%s\n' "$OUT" | python3 tests/check_physics_sweep.py

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

echo "--- solve.eigs (iterative solvers: predicate as loop condition) ---"
SOUT=$("$EIGS" solve.eigs 2>&1)
echo "$SOUT"
echo "$SOUT" | grep -q "DONE"                          || { echo "FAIL: solve.eigs did not finish"; exit 1; }
echo "$SOUT" | grep -q "dominant eigenvalue -> 2"      || { echo "FAIL: power iteration eigenvalue wrong"; exit 1; }
# Check every component on its own named row; a number printed by another
# solver must not mask a missing distribution or an incorrect component.
printf '%s\n' "$SOUT" | python3 tests/check_solver_output.py
echo "PASS: solvers converge via the predicate-driven loop (settled + hold)"
