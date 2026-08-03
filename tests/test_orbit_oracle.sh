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
if ! $XVFB "$EIGS" "$TMP/gfxprobe.eigs" 2>/dev/null | grep -q "GFXOK"; then
    echo "SKIP: runtime is not gfx-capable (build with 'make gfx') — UI oracle not run"
    exit 2
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
