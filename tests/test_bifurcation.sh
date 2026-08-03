#!/usr/bin/env bash
# THE BIFURCATION ORACLE (dynamics#20 rung 1, slice 3).
#
# The bifurcation view plots the logistic map's attractor, and the
# logistic map's cascade is analytically known — so this is a real
# external oracle, not a golden master. Nothing here compares against a
# number this repo chose; every threshold is checked against closed-form
# algebra (1 - 1/r, (r+1 ± sqrt((r-3)(r+1)))/(2r), r = 3, r = 1+sqrt(6),
# r = 1+sqrt(8)) or against a published constant (r3 = 3.5440903...,
# Feigenbaum's delta = 4.6692016...).
#
# Headless: no window, no gfx builtins, so it runs on every build.
#
# The checker is validated with TWO planted faults — one in the system
# under test (the map itself is perturbed) and one in the reference (an
# analytic constant is moved) — and each must be caught.
set -euo pipefail

EIGS="${EIGENSCRIPT:-eigenscript}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TMP="$(mktemp -d)"
trap "rm -rf '$TMP'" EXIT

field() { echo "$1" | grep -E "^$2 " | awk '{print $2}'; }
# floating-point comparison without leaving the shell
flt() { awk "BEGIN{exit !($1)}"; }

# ---- the sweep parameters must match the ones the window ships -------
# The oracle re-declares orbit.eigs's BIF_* values so it can stay free of
# lib/ui. That duplication is only safe if it cannot drift, so pin it.
echo "--- sweep parameters match the shipped window ---"
for pair in "BIF_R_LO R_LO" "BIF_R_HI R_HI" "BIF_COLS COLS" "BIF_SAMPLES SAMPLES" "BIF_TRANSIENT TRANSIENT"; do
    set -- $pair
    APP=$(grep -E "^$1 is " orbit.eigs | awk '{print $3}')
    ORC=$(grep -E "^$2 is " tests/bifurcation_oracle.eigs | awk '{print $3}')
    [ -n "$APP" ] || { echo "FAIL: orbit.eigs has no $1"; exit 1; }
    [ "$APP" = "$ORC" ] || {
        echo "FAIL: orbit.eigs $1=$APP but the oracle's $2=$ORC — the oracle is checking a sweep the window does not draw"
        exit 1
    }
    echo "  $1 = $APP"
done

# Returns 0 when every analytic check holds. `quiet` suppresses the
# per-check output (used by the planted faults).
check() {
    local out="$1" quiet="${2:-}" bad=0
    local n p1c p1e p2c p2e p2b tol r1e r2e r3e ratio pb pa c28 c32 c35 c355 c39
    n=$(field "$out" SWEEP_N)
    p1c=$(field "$out" P1_COLS);  p1e=$(field "$out" P1_MAXERR)
    p2c=$(field "$out" P2_COLS);  p2e=$(field "$out" P2_MAXERR)
    p2b=$(field "$out" P2_BOTH_BRANCHES)
    tol=$(field "$out" TOL)
    r1e=$(field "$out" R1_ERR); r2e=$(field "$out" R2_ERR); r3e=$(field "$out" R3_ERR)
    ratio=$(field "$out" RATIO)
    pb=$(field "$out" P3_BELOW); pa=$(field "$out" P3_ABOVE)
    c28=$(field "$out" CENSUS_2_8);  c32=$(field "$out" CENSUS_3_2)
    c35=$(field "$out" CENSUS_3_5);  c355=$(field "$out" CENSUS_3_55)
    c39=$(field "$out" CENSUS_3_9)
    say() { [ -n "$quiet" ] || echo "$1"; }

    # The sweep is the one the window plots, and it is non-trivial.
    [ "$n" -eq 4000 ] || { say "FAIL: sweep has $n points, want 4000"; bad=1; }
    [ "$p1c" -ge 20 ] || { say "FAIL: only $p1c period-1 columns checked"; bad=1; }
    [ "$p2c" -ge 40 ] || { say "FAIL: only $p2c period-2 columns checked"; bad=1; }

    # 1. plotted data vs closed form.
    flt "$p1e < $tol" || { say "FAIL: period-1 branch is off the analytic 1-1/r by $p1e (tol $tol)"; bad=1; }
    flt "$p2e < $tol" || { say "FAIL: period-2 branch is off the analytic 2-cycle by $p2e (tol $tol)"; bad=1; }
    [ "$p2b" = "1" ] || { say "FAIL: a period-2 column visited only one branch point — the plotted cycle collapsed"; bad=1; }

    # 2. cascade locations vs r=3, r=1+sqrt(6), r3=3.5440903...
    # 1e-3 is the detector's transient-limited floor, not slack: see
    # logistic.eigs's doubling_point header.
    flt "$r1e < 0.001" || { say "FAIL: measured first doubling is $r1e from r=3"; bad=1; }
    flt "$r2e < 0.001" || { say "FAIL: measured second doubling is $r2e from r=1+sqrt(6)"; bad=1; }
    flt "$r3e < 0.001" || { say "FAIL: measured third doubling is $r3e from r=3.5440903"; bad=1; }
    # First Feigenbaum ratio is 4.7514 (delta itself, 4.66920, is the
    # limit of the sequence, not this first term).
    flt "$ratio > 4.6 && $ratio < 4.9" || { say "FAIL: first Feigenbaum ratio $ratio outside [4.6, 4.9] (true 4.7514)"; bad=1; }

    # 3. the period-3 tangent bifurcation straddles 1+sqrt(8).
    [ "$pb" -gt 8 ] || { say "FAIL: attractor just BELOW 1+sqrt(8) has period $pb — expected chaos"; bad=1; }
    [ "$pa" -eq 3 ] || { say "FAIL: attractor just ABOVE 1+sqrt(8) has period $pa — expected exactly 3"; bad=1; }

    # 4. census, one per rung.
    [ "$c28" -eq 1 ] || { say "FAIL: period at r=2.8 is $c28, want 1"; bad=1; }
    [ "$c32" -eq 2 ] || { say "FAIL: period at r=3.2 is $c32, want 2"; bad=1; }
    [ "$c35" -eq 4 ] || { say "FAIL: period at r=3.5 is $c35, want 4"; bad=1; }
    [ "$c355" -eq 8 ] || { say "FAIL: period at r=3.55 is $c355, want 8"; bad=1; }
    [ "$c39" -gt 8 ] || { say "FAIL: attractor at r=3.9 has period $c39 — expected chaos"; bad=1; }
    return $bad
}

echo "--- the plotted sweep against closed-form algebra ---"
OUT=$("$EIGS" tests/bifurcation_oracle.eigs 2>&1)
echo "$OUT" | grep -q "BIF-ORACLE-OK" || { echo "FAIL: the oracle did not finish"; echo "$OUT"; exit 1; }
echo "$OUT" | grep -vE "^(TOL|DELTA|BIF-ORACLE-OK)"
check "$OUT" || exit 1
echo "PASS: plotted branches match 1-1/r and the analytic 2-cycle to $(field "$OUT" P1_MAXERR) / $(field "$OUT" P2_MAXERR)"
echo "PASS: doublings land on r=3, r=1+sqrt(6), r=3.5440903; first Feigenbaum ratio $(field "$OUT" RATIO) (true 4.7514)"
echo "PASS: period-3 window opens exactly at r=1+sqrt(8)"

# ---- planted faults ---------------------------------------------------
# Each runs the SAME checker over a deliberately broken tree, and must
# come back red. Fault 1 breaks the system under test, fault 2 breaks the
# reference it is measured against — a checker that only catches one of
# those is only half a checker.

plant() {
    local name="$1" needle="$2" repl="$3"
    local tree="$TMP/$name"
    rm -rf "$tree"; mkdir -p "$tree/tests"
    cp logistic.eigs "$tree/"
    cp tests/bifurcation_oracle.eigs "$tree/tests/"
    python3 - "$tree/logistic.eigs" "$needle" "$repl" <<'PY'
import sys
path, needle, repl = sys.argv[1], sys.argv[2], sys.argv[3]
src = open(path).read()
if needle not in src:
    raise SystemExit("planted fault no longer matches logistic.eigs: %r" % needle)
open(path, "w").write(src.replace(needle, repl))
PY
    ( cd "$tree" && "$EIGS" tests/bifurcation_oracle.eigs 2>&1 ) || true
}

# A fault must be caught by an ASSERTION, not by the program dying —
# otherwise "the fault run failed" would also be satisfied by a syntax
# error, and the fault would validate nothing.
faulted() {
    local name="$1" out="$2"
    echo "$out" | grep -q "BIF-ORACLE-OK" || {
        echo "FAIL: planted fault '$name' stopped the oracle instead of failing its checks:"
        echo "$out" | tail -5
        exit 1
    }
    if check "$out" quiet; then
        echo "FAIL: planted fault '$name' passed every analytic check — the oracle can't discriminate"
        exit 1
    fi
}

echo "--- planted fault 1: the map itself is perturbed (r off by 0.1%) ---"
F1=$(plant map "x is r * x * (1.0 - x)" "x is 1.001 * r * x * (1.0 - x)")
faulted map "$F1"
echo "PASS: perturbed map is caught — branches off by $(field "$F1" P2_MAXERR), doublings off by $(field "$F1" R1_ERR) / $(field "$F1" R2_ERR) / $(field "$F1" R3_ERR), and the period-3 straddle collapses (below=$(field "$F1" P3_BELOW))"

echo "--- planted fault 2: an analytic reference constant is moved ---"
F2=$(plant const "R2 is 1.0 + (sqrt of 6.0)" "R2 is 3.5")
faulted const "$F2"
echo "PASS: moved reference constant (R2 := 3.5) is caught — R2_ERR $(field "$F2" R2_ERR)"

echo "PASS: bifurcation oracle green, both planted faults caught"
