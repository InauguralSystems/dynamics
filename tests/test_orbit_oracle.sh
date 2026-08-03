#!/usr/bin/env bash
# THE UI ORACLE (dynamics#20, fleet UI ladder rung 1): a headless run and
# a UI-stepped run of the same system/params/frames must produce
# byte-identical trajectory dumps. The window is a pure reader of the
# simulation — if the dumps ever differ, the UI has perturbed the math.
#
# Also validates the checker itself with a planted fault (a headless run
# at a different zeta MUST differ), so a broken diff can't go green.
#
# Needs a gfx-capable EigenScript (make gfx) and a display; without a
# DISPLAY it self-wraps the gfx runs in xvfb-run. Exits 2 (= failure in
# CI, skip locally) when the runtime has no gfx builtins, so the UI
# oracle can never be silently dropped from a gfx-capable environment.
set -euo pipefail

EIGS="${EIGENSCRIPT:-eigenscript}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TMP="$(mktemp -d)"
trap "rm -rf '$TMP'" EXIT

ZETA=0.15
FRAMES=200

XVFB=""
if [ -z "${DISPLAY:-}" ]; then
    XVFB="xvfb-run -a"
fi

echo "--- gfx capability probe ---"
cat > "$TMP/gfxprobe.eigs" <<'EOF'
w is gfx_open of [64, 48, "probe"]
gfx_close of null
print of "GFXOK"
EOF
PROBE_OUT=$($XVFB "$EIGS" "$TMP/gfxprobe.eigs" 2>&1 || true)
if ! echo "$PROBE_OUT" | grep -q "GFXOK"; then
    if echo "$PROBE_OUT" | grep -q "undefined variable 'gfx_open'"; then
        echo "SKIP: runtime is not gfx-capable (build with 'make gfx') — UI oracle not run"
        exit 2
    fi
    # gfx builtins exist (or the probe died before the interpreter ran):
    # the display/SDL environment is broken, which is a FAILURE, not a skip.
    echo "FAIL: gfx probe could not open a window — probe output:"
    echo "$PROBE_OUT"
    exit 1
fi

echo "--- headless reference trajectory (zeta=$ZETA, frames=$FRAMES) ---"
ORBIT_ZETA=$ZETA ORBIT_FRAMES=$FRAMES ORBIT_OUT="$TMP/headless.txt" \
    "$EIGS" tests/orbit_headless_dump.eigs > /dev/null
[ -s "$TMP/headless.txt" ] || { echo "FAIL: headless dump is empty"; exit 1; }

echo "--- UI-stepped trajectory (real window, real per-frame draw) ---"
ORBIT_ZETA=$ZETA ORBIT_FRAMES=$FRAMES ORBIT_OUT="$TMP/ui.txt" \
    $XVFB "$EIGS" tests/orbit_ui_dump.eigs > /dev/null
[ -s "$TMP/ui.txt" ] || { echo "FAIL: UI dump is empty"; exit 1; }

# Structural check: initial state + one line per frame, both dumps.
WANT=$((FRAMES + 1))
HL=$(wc -l < "$TMP/headless.txt")
UL=$(wc -l < "$TMP/ui.txt")
[ "$HL" -eq "$WANT" ] || { echo "FAIL: headless dump has $HL lines, want $WANT"; exit 1; }
[ "$UL" -eq "$WANT" ] || { echo "FAIL: UI dump has $UL lines, want $WANT"; exit 1; }

# THE oracle: byte-identical.
if ! cmp "$TMP/headless.txt" "$TMP/ui.txt"; then
    echo "FAIL: UI-stepped trajectory diverged from the headless reference —"
    echo "      the UI perturbed the math. First differing lines:"
    diff "$TMP/headless.txt" "$TMP/ui.txt" | head -10
    exit 1
fi
echo "PASS: headless and UI-stepped trajectories are byte-identical ($WANT lines)"

# Planted fault: a trajectory at a different zeta must NOT compare equal,
# or the checker itself is broken.
ORBIT_ZETA=0.16 ORBIT_FRAMES=$FRAMES ORBIT_OUT="$TMP/fault.txt" \
    "$EIGS" tests/orbit_headless_dump.eigs > /dev/null
if cmp -s "$TMP/fault.txt" "$TMP/ui.txt"; then
    echo "FAIL: planted fault (zeta=0.16) compared equal — the checker can't discriminate"
    exit 1
fi
echo "PASS: planted fault (zeta=0.16) is caught by the checker"

# Slice 2 — pan/zoom is VIEW STATE ONLY. Same run again with the view
# panned, zoomed (both clamps) and reset on every frame: the trajectory
# must be byte-identical still. This is what stops an interaction from
# leaking into the math.
echo "--- UI-stepped trajectory with the view panned/zoomed every frame ---"
ORBIT_ZETA=$ZETA ORBIT_FRAMES=$FRAMES ORBIT_OUT="$TMP/ui_pan.txt" \
    $XVFB "$EIGS" tests/orbit_ui_pan_dump.eigs > /dev/null
[ -s "$TMP/ui_pan.txt" ] || { echo "FAIL: pan/zoom UI dump is empty"; exit 1; }
PL=$(wc -l < "$TMP/ui_pan.txt")
[ "$PL" -eq "$WANT" ] || { echo "FAIL: pan/zoom UI dump has $PL lines, want $WANT"; exit 1; }
if ! cmp "$TMP/headless.txt" "$TMP/ui_pan.txt"; then
    echo "FAIL: panning/zooming perturbed the trajectory — the view is not display-only."
    echo "      First differing lines:"
    diff "$TMP/headless.txt" "$TMP/ui_pan.txt" | head -10
    exit 1
fi
echo "PASS: pan/zoom on every frame leaves the trajectory byte-identical ($WANT lines)"

# Slice 2 — the INTERACTIVE path bounds its trajectory history. The
# headless half of this invariant (and its planted fault) is
# tests/test_orbit_hist.sh; this leg pins the wiring through the real
# window: run_session's interactive branch must set the cap, and the
# trim must actually fire on the live per-frame path.
echo "--- interactive-session history bound (real window) ---"
$XVFB env ORBIT_OUT="$TMP/hist.txt" "$EIGS" tests/orbit_hist_ui.eigs > /dev/null
[ -s "$TMP/hist.txt" ] || { echo "FAIL: interactive history probe wrote nothing"; exit 1; }
cat "$TMP/hist.txt"
hfield() { grep -E "^$1 " "$TMP/hist.txt" | awk '{print $2}'; }
WIRED=$(hfield WIRED_CAP); HCAP=$(hfield HIST_CAP)
PLEN=$(hfield LEN); PCAP=$(hfield CAP); PFRAME=$(hfield FRAME)
if [ "$WIRED" != "$HCAP" ] || [ "$HCAP" -le 0 ]; then
    echo "FAIL: interactive run_session wired cap=$WIRED, want HIST_CAP=$HCAP — history is unbounded in a real session"
    exit 1
fi
if [ "$PLEN" -gt $((PCAP * 2)) ]; then
    echo "FAIL: live history reached $PLEN points at frame $PFRAME (bound $((PCAP * 2))) — the trim never fired"
    exit 1
fi
if [ "$PLEN" -ge "$PFRAME" ]; then
    echo "FAIL: live history ($PLEN points) grew with the frame count ($PFRAME) — the trim never fired"
    exit 1
fi
echo "PASS: interactive session caps history at HIST_CAP=$HCAP; live size $PLEN points after $PFRAME frames"
