#!/usr/bin/env bash
# THE MEMORY GATE (dynamics#20 rung 1, slice 3).
#
# WHY THIS EXISTS. A bifurcation sweep is the largest data structure this
# lab has ever put on screen, and the first attempt at this view grew
# 3.9 MB per frame — 859 MB by frame 300 — and froze a 4 GB box. A
# correctness suite cannot see that: every oracle was green while the
# machine was dying. So the shape of the memory curve is itself a gate.
#
# WHAT IT ASSERTS, at 30 / 100 / 300 frames, in two shapes:
#
#   1. CEILING — peak RSS stays under CEILING_KB.
#   2. FLATNESS — peak RSS at 300 frames is no more than GROWTH_KB above
#      peak RSS at 30 frames. This is the real gate: a ceiling alone
#      passes a leak that has not had time to bite yet.
#   3. STRUCTURE — the sweep, the chart series and the analytic markers
#      are built exactly once, however many times the views are toggled.
#      RSS is the symptom; "SERIES 1 after 150 view switches" is the
#      cause, asserted directly.
#
# THE NUMBERS, and why they are these numbers. Measured steady state on
# the reference box is 136.6–137.3 MB across all six legs, which is the
# same floor as the merged orbit view (137 MB) and as lib/ui's chart
# widget alone (135 MB) — i.e. essentially all of it is the runtime plus
# SDL, and the sweep itself is noise. CEILING_KB is 200 MB, ~1.45x that
# floor: loose enough to absorb a different SDL/driver/font cache on a CI
# runner, tight enough that the original leak — 258 MB at its FIRST rung,
# 30 frames — would have been caught before the second. GROWTH_KB is
# 25 MB against a measured 30->300 spread of under 1 MB, so ~25x headroom
# on the noise while the leak it is aimed at shows +600 MB.
#
# EVERY RUN IS CAPPED with `ulimit -v`. That is not belt-and-braces: it
# is what turns a runaway into a clean "out of memory" instead of a
# frozen workstation, and it is the reason this gate could be developed
# at all.
#
# The gate is validated with TWO planted faults: one that retains the
# frame's plotted points (per-frame retention, the class the original
# leak belonged to), one that removes the build-once guard. Each must be
# caught, and each is measured — a fault nobody has watched go red is a
# gate that has stopped discriminating.
#
# Exits 2 (= failure in CI, skip locally) when the runtime has no gfx
# builtins, so it can never be silently dropped.
set -euo pipefail

EIGS="${EIGENSCRIPT:-eigenscript}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TMP="$(mktemp -d)"
trap "rm -rf '$TMP'" EXIT

VCAP=1500000          # KB of address space per run — the runaway guard
CEILING_KB=204800     # 200 MB
GROWTH_KB=25600       # 25 MB, 30 frames -> 300 frames

XVFB=""
if [ -z "${DISPLAY:-}" ]; then
    XVFB="xvfb-run -a"
fi

# The measuring instrument itself is a precondition, and a LOUD one. GNU
# time is a separate package from the shell builtin; without it every run
# exits 127 and a naive gate reports "the process died under the cap" —
# i.e. it blames the thing it is measuring for the absence of the ruler.
# CI caught exactly that. This is a failure, never a skip: a memory gate
# that quietly does not measure is worse than no gate.
if ! command -v /usr/bin/time > /dev/null; then
    echo "FAIL: /usr/bin/time (GNU time, package 'time') is not installed — peak RSS cannot be measured, so this gate cannot run"
    exit 1
fi

echo "--- gfx capability probe ---"
cat > "$TMP/gfxprobe.eigs" <<'EOF'
w is gfx_open of [64, 48, "probe"]
gfx_close of null
print of "GFXOK"
EOF
PROBE_OUT=$( (ulimit -v $VCAP; $XVFB "$EIGS" "$TMP/gfxprobe.eigs" 2>&1) || true)
if ! echo "$PROBE_OUT" | grep -q "GFXOK"; then
    if echo "$PROBE_OUT" | grep -q "undefined variable 'gfx_open'"; then
        echo "SKIP: runtime is not gfx-capable (build with 'make gfx') — memory gate not run"
        exit 2
    fi
    echo "FAIL: gfx probe could not open a window — probe output:"
    echo "$PROBE_OUT"
    exit 1
fi

# measure <tree> <mode> <frames> -> sets PEAK (KB) and STATS (file path).
# Runs the real window, the real chart render, under the address-space cap.
measure() {
    local tree="$1" mode="$2" frames="$3"
    STATS="$TMP/stats.$mode.$frames.txt"
    local tf="$TMP/time.$mode.$frames.txt"
    rm -f "$STATS" "$tf"
    set +e
    ( cd "$tree" && ulimit -v $VCAP && BIF_TICKS="$frames" BIF_MODE="$mode" BIF_OUT="$STATS" \
        /usr/bin/time -f "%M" -o "$tf" $XVFB "$EIGS" tests/bif_ui.eigs > /dev/null 2>&1 )
    RC=$?
    set -e
    PEAK=$(tail -1 "$tf" 2>/dev/null || echo 0)
    case "$PEAK" in ''|*[!0-9]*) PEAK=0 ;; esac
    # 0 KB is not a measurement. Separated from a real overrun so the
    # verdict never blames the program for a missing ruler.
    MEASURED=1
    if [ "$PEAK" -eq 0 ]; then MEASURED=0; fi
}

# stat_field <file> <name>
stat_field() { grep -E "^$2 " "$1" 2>/dev/null | awk '{print $2}'; }

# run_gate <tree> <quiet> <modes> <frames> — returns 0 when the tree
# satisfies ceiling + flatness + structure over the given legs. `quiet`
# suppresses per-check output AND stops at the first failure, which is
# what keeps a deliberately-broken tree from being measured for minutes.
run_gate() {
    local tree="$1" quiet="$2" modes="$3" frame_list="$4" bad=0
    local mode frames first last growth built series points markers
    say() { if [ -z "$quiet" ]; then echo "$1"; fi; }
    for mode in $modes; do
        first=0; last=0
        for frames in $frame_list; do
            measure "$tree" "$mode" "$frames"
            built=$(stat_field "$STATS" BUILT)
            series=$(stat_field "$STATS" SERIES)
            points=$(stat_field "$STATS" POINTS)
            markers=$(stat_field "$STATS" MARKERS)
            say "  $mode $frames frames: peak ${PEAK} KB  rc=$RC  built=${built:-?} series=${series:-?} points=${points:-?} markers=${markers:-?}"
            if [ "$MEASURED" -eq 0 ]; then
                say "FAIL: $mode/$frames produced no RSS measurement (exit $RC) — the instrument failed, not necessarily the program"
                bad=1
            elif [ "$RC" -ne 0 ]; then
                say "FAIL: $mode/$frames exited $RC — a run that dies under the ${VCAP} KB cap is the runaway this gate exists to catch"
                bad=1
            fi
            if [ "$PEAK" -gt "$CEILING_KB" ]; then
                say "FAIL: $mode/$frames peaked at ${PEAK} KB, ceiling ${CEILING_KB} KB"
                bad=1
            fi
            # Structure: one sweep, one series, one full point set, four
            # analytic markers — however many times the views switch.
            if [ "${built:-0}" != "1" ]; then
                say "FAIL: $mode/$frames reports built=${built:-none}"; bad=1
            fi
            if [ "${series:-0}" != "1" ]; then
                say "FAIL: $mode/$frames built ${series:-none} chart series — the build-once guard let go"; bad=1
            fi
            if [ "${points:-0}" != "4000" ]; then
                say "FAIL: $mode/$frames plotted ${points:-none} points, want 4000"; bad=1
            fi
            if [ "${markers:-0}" != "4" ]; then
                say "FAIL: $mode/$frames has ${markers:-none} markers, want 4"; bad=1
            fi
            if [ -n "$quiet" ] && [ "$bad" -ne 0 ]; then
                return 1
            fi
            if [ "$first" -eq 0 ]; then first=$PEAK; fi
            last=$PEAK
        done
        growth=$((last - first))
        say "  $mode growth over the frame sweep: ${growth} KB (limit ${GROWTH_KB} KB)"
        if [ "$growth" -gt "$GROWTH_KB" ]; then
            say "FAIL: $mode RSS grew ${growth} KB with frame count — that is a leak, not a working set"
            bad=1
            if [ -n "$quiet" ]; then return 1; fi
        fi
    done
    return $bad
}

echo "--- bifurcation view under a ${VCAP} KB address-space cap ---"
if ! run_gate "$ROOT" "" "static toggle" "30 100 300"; then
    exit 1
fi
echo "PASS: peak RSS under ${CEILING_KB} KB and flat in frame count, in both the steady-state and the toggle-every-frame shape"

# ---- planted faults ---------------------------------------------------
# A memory gate nobody has seen go red is decoration. Each fault below
# recreates a real unbounded shape and is measured by the SAME run_gate
# with the SAME thresholds — on the shorter leg the fault targets, since
# a broken tree is expensive to measure.

plant() {
    local name="$1" needle="$2" repl="$3"
    local tree="$TMP/$name"
    rm -rf "$tree"; mkdir -p "$tree/tests"
    cp "$ROOT"/*.eigs "$tree/"
    cp "$ROOT"/tests/*.eigs "$tree/tests/"
    python3 - "$tree/orbit.eigs" "$needle" "$repl" <<'PY_END'
import sys
path, needle, repl = sys.argv[1], sys.argv[2], sys.argv[3]
src = open(path).read()
if needle not in src:
    raise SystemExit("planted fault no longer matches orbit.eigs: %r" % needle)
open(path, "w").write(src.replace(needle, repl, 1))
PY_END
    echo "$tree"
}

echo "--- planted fault 1: the bifurcation tick keeps its frame's points ---"
# The headline invariant of this view is that bifurcation mode does NO
# per-frame work (orbit.eigs `_tick`). This fault breaks exactly that:
# every frame rebuilds the plotted point set and KEEPS it — the shape any
# naive per-frame cache (a pick index, a frame history, an undo trail)
# would have, and the same class as the two retention bugs this repo has
# already had: the unbounded `sim.pts` trail and the pinned per-point
# allocations of F-DYN-13. Every structural counter stays CORRECT under
# it — built=1, series=1, points=4000, markers=4 — so only the shape of
# the memory curve can see it, which is the thing this fault has to
# prove. Measured on v0.35.1: 176,384 KB at 30 frames, 279,104 KB at 100
# (~1.46 MB/frame) — it fails BOTH RSS checks, the 200 MB ceiling on the
# second rung and the flatness limit by 102,720 KB against 25,600.
#
# WHAT USED TO BE HERE, and why it went. This leg used to flip
# `record_history of 0` — the opt-out `_run` carried against the
# runtime's unbounded temporal history (EigenScript#827) — back on, and
# require the resulting 3.9 MB/frame build to be rejected. EigenScript#829
# (v0.35.1) bounds that table by program TEXT and arms it per NAME, so
# turning history on grows nothing any more: measured, not assumed, the
# flipped build ran flat at ~134 MB and SAILED THROUGH this gate. The
# opt-out is gone from `_run` and a fault that can no longer be planted
# validates nothing — so it is re-pointed, not deleted (dynamics#24).
T1=$(plant framepts "    if _app.mode == \"bif\":
        if _app.hook != null:
            _app.hook of _app.sim
        return null" "    if _app.mode == \"bif\":
        if _app.frame_pts == null:
            _app.frame_pts is []
        local fs is _app.chart.series[0]
        local pts is []
        local i is 0
        loop while i < (len of fs.data):
            append of [pts, [fs.x[i], fs.data[i]]]
            i is i + 1
        append of [_app.frame_pts, pts]
        if _app.hook != null:
            _app.hook of _app.sim
        return null")
if run_gate "$T1" quiet "static" "30 100"; then
    echo "FAIL: the leaking build passed the memory gate — the gate can't discriminate"
    exit 1
fi
echo "PASS: planted fault 'framepts' is caught (per-frame retention, every structural counter still correct)"

echo "--- planted fault 2: the build-once sweep guard removed ---"
T2=$(plant guard "    if _app.sweep_done == 1:
        return null" "    if _app.sweep_done == 2:
        return null")
if run_gate "$T2" quiet "toggle" "30"; then
    echo "FAIL: an unguarded sweep passed the memory gate — the structural checks can't discriminate"
    exit 1
fi
echo "PASS: planted fault 'guard' is caught (every view switch rebuilds the sweep)"

echo "PASS: memory gate green, both planted faults caught"
