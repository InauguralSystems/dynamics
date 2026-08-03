#!/usr/bin/env bash
# Bounded-history gate (dynamics#20 rung 1, slice 2).
#
# The interactive orbit-lab path must not accumulate trajectory points
# forever, and the auto/dump path must keep every one of them (the
# byte-identical UI oracle is built on the full trajectory). Headless:
# no window, no gfx builtins, so this runs on every build.
#
# The checker is validated with a planted fault: the same program with
# the cap removed must be CAUGHT by the bound assertion.
set -euo pipefail

EIGS="${EIGENSCRIPT:-eigenscript}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TMP="$(mktemp -d)"
trap "rm -rf '$TMP'" EXIT

field() { echo "$1" | grep -E "^$2 " | awk '{print $2}'; }

# Returns 0 when the run satisfies every history invariant, 1 otherwise.
# `quiet` suppresses the per-check output (used by the planted fault).
check() {
    local out="$1" quiet="${2:-}" bad=0
    local full trimmed bound trail frames tailm frameq stateq
    full=$(field "$out" FULL_LEN)
    trimmed=$(field "$out" TRIMMED_LEN)
    bound=$(field "$out" BOUND)
    trail=$(field "$out" TRAIL)
    frames=$(field "$out" FRAMES)
    tailm=$(field "$out" TAIL_MATCH)
    frameq=$(field "$out" FRAME_EQ)
    stateq=$(field "$out" STATE_EQ)

    # dump path: complete — initial state plus one point per frame.
    if [ "$full" -ne $((frames + 1)) ]; then
        [ -n "$quiet" ] || echo "FAIL: dump path kept $full points, want $((frames + 1)) — the oracle's trajectory is incomplete"
        bad=1
    fi
    # interactive path: bounded, and still holding a full draw window.
    if [ "$trimmed" -gt "$bound" ]; then
        [ -n "$quiet" ] || echo "FAIL: interactive path kept $trimmed points over $frames frames (bound $bound) — history is unbounded"
        bad=1
    fi
    if [ "$trimmed" -le "$trail" ]; then
        [ -n "$quiet" ] || echo "FAIL: interactive path kept $trimmed points, fewer than the $trail-point draw window"
        bad=1
    fi
    # the trim is display-only.
    [ "$tailm" = "1" ]  || { [ -n "$quiet" ] || echo "FAIL: retained points are not the tail of the uncapped run"; bad=1; }
    [ "$frameq" = "1" ] || { [ -n "$quiet" ] || echo "FAIL: capped and uncapped runs disagree on frame count"; bad=1; }
    [ "$stateq" = "1" ] || { [ -n "$quiet" ] || echo "FAIL: capped and uncapped runs disagree on the current state"; bad=1; }
    return $bad
}

echo "--- interactive history is bounded, dump history is complete ---"
OUT=$("$EIGS" tests/orbit_hist_dump.eigs 2>&1)
echo "$OUT" | grep -q "HIST-CHECK-OK" || { echo "FAIL: history check did not finish"; echo "$OUT"; exit 1; }
echo "$OUT" | grep -E "^(FULL_LEN|TRIMMED_LEN|BOUND|TRAIL|FRAMES|TAIL_MATCH|FRAME_EQ|STATE_EQ) "
check "$OUT" || exit 1
echo "PASS: dump path keeps the whole trajectory; interactive path stays bounded and display-identical"

# Planted fault: drop the cap and the bound assertion must catch it.
sed 's/^trimmed.cap is orbit.HIST_CAP$/trimmed.cap is 0/' tests/orbit_hist_dump.eigs > "$TMP/nocap.eigs"
cmp -s tests/orbit_hist_dump.eigs "$TMP/nocap.eigs" && { echo "FAIL: planted-fault substitution did not apply"; exit 1; }
FOUT=$("$EIGS" "$TMP/nocap.eigs" 2>&1)
if check "$FOUT" quiet; then
    echo "FAIL: planted fault (cap removed) passed the bound check — the checker can't discriminate"
    exit 1
fi
echo "PASS: planted fault (cap removed, $(field "$FOUT" TRIMMED_LEN) points retained) is caught by the checker"
