#!/usr/bin/env bash
# Planted faults for tests/check_physics_sweep.py (hq#58, DYN-LAB-1). Each
# plant mutates a copy of physics.eigs the way the zeta-sweep can go wrong,
# runs it, and requires the checker to reject the output. The unmodified
# program must pass first, and every plant must change exactly one line, so a
# plant that stops applying fails here instead of silently testing nothing.
set -euo pipefail

EIGS="${EIGENSCRIPT:-eigenscript}"
CHECK="$(pwd)/tests/check_physics_sweep.py"
TMP="$(mktemp -d)"
trap "rm -rf '$TMP'" EXIT

"$EIGS" physics.eigs 2>&1 | python3 "$CHECK" > "$TMP/base.log" \
    || { cat "$TMP/base.log"; echo "FAIL: unmodified physics.eigs rejected"; exit 1; }
echo "PASS: unmodified physics.eigs accepted"

plant() {
    local name="$1" from="$2" to="$3" want="$4"
    awk -v from="$from" -v to="$to" '$0 == from { $0 = to } { print }' \
        physics.eigs > "$TMP/physics.eigs"
    local changed
    changed=$(diff physics.eigs "$TMP/physics.eigs" | grep -c '^>' || true)
    [ "$changed" -eq 1 ] || { echo "FAIL: plant $name changed $changed lines, expected 1"; exit 1; }
    # The planted program must still run to completion: a crash is not the
    # checker rejecting the fault.
    "$EIGS" "$TMP/physics.eigs" > "$TMP/$name.out" 2>&1 \
        || { cat "$TMP/$name.out"; echo "FAIL: plant $name crashed the program"; exit 1; }
    grep -q '^DONE$' "$TMP/$name.out" || { echo "FAIL: plant $name did not finish"; exit 1; }
    if python3 "$CHECK" < "$TMP/$name.out" > "$TMP/$name.log" 2>&1; then
        cat "$TMP/$name.log"
        echo "FAIL: plant $name was accepted"
        exit 1
    fi
    grep -q '^FAIL: physics sweep: ' "$TMP/$name.log" \
        || { cat "$TMP/$name.log"; echo "FAIL: plant $name: checker errored instead of rejecting"; exit 1; }
    # Pin the check that fired: a plant rejected for an unrelated reason does
    # not prove the check it targets is alive.
    grep -qF "FAIL: physics sweep: $want" "$TMP/$name.log" \
        || { cat "$TMP/$name.log"; echo "FAIL: plant $name rejected for the wrong reason, expected: $want"; exit 1; }
    echo "PASS: plant $name rejected: $(grep '^FAIL' "$TMP/$name.log")"
}

# zeta>=1 rows read as oscillating (the DYN-LAB-1 reproduction).
plant overdamped-reads-oscillating \
    '    elif p[3] == 1:' \
    '    elif (p[3] == 1) or (z >= 1.0):' \
    "zeta=1 reads 'x OSCILLATES, energy settles', expected 'settles'"
# An observer `oscillating` false positive on the overdamped displacement.
plant x-osc-false-positive \
    '        if xr == "oscillating":' \
    '        if (xr == "oscillating") or (zeta >= 1.0):' \
    "zeta=1 reads 'x OSCILLATES, energy settles', expected 'settles'"
# The overdamped row is dropped from the sweep.
plant overdamped-row-dropped \
    'for z in [-0.05, 0.0, 0.1, 0.4, 1.0, 2.0]:' \
    'for z in [-0.05, 0.0, 0.1, 0.4, 1.0]:' \
    "expected zeta rows ['-0.05', '0', '0.1', '0.4', '1', '2'], got ['-0.05', '0', '0.1', '0.4', '1']"
# The printed x:osc flag is not the one the reading was derived from.
plant x-flag-column-desync \
    '    x_line is f"x:{yn of p[3]} {yn of p[4]} {yn of p[5]}"' \
    '    x_line is f"x:{yn of p[4]} {yn of p[4]} {yn of p[5]}"' \
    "zeta=0 x:osc flag '-' contradicts reading 'x OSCILLATES, energy settles'"
# The printed energy-grew flag is not the one the reading was derived from.
plant grew-column-desync \
    '    e_line is f"E:{yn of p[0]} {yn of p[1]} {yn of p[2]} {yn of p[6]}"' \
    '    e_line is f"E:{yn of p[0]} {yn of p[1]} {yn of p[2]} {yn of p[5]}"' \
    "zeta=-0.05 energy-grew flag '-' contradicts reading 'DIVERGES (energy grew)'"
# The undamped row reports energy converged (E:conv printed from E:osc).
plant zeta0-energy-converged \
    '    e_line is f"E:{yn of p[0]} {yn of p[1]} {yn of p[2]} {yn of p[6]}"' \
    '    e_line is f"E:{yn of p[0]} {yn of p[0]} {yn of p[2]} {yn of p[6]}"' \
    "zeta=0 energy reported converged"

echo "PASS: every physics-sweep plant is rejected"
