#!/usr/bin/env bash
# MOUSE + RENDER-DECODE ORACLE (dynamics#20 rung 1, slice 2).
#
# The trajectory oracle (tests/test_orbit_oracle.sh) proves the UI does
# not perturb the math — it never looks at what the user sees, and it
# never touches a control. This drives the REAL window with REAL pointer
# and key input and verifies by decoding pixels: the slider moves zeta,
# Pause freezes advancement, drag pans, the wheel zooms, and `r` restores
# the view exactly.
#
# The checker is validated by two planted faults (a drag that never
# claims the pointer, and a tick that advances while paused): each MUST
# be caught, or a green run means nothing.
#
# Exits 2 (= failure in CI, skip locally) when the runtime has no gfx
# builtins or the QA tooling is missing, so it can never be silently
# dropped from an environment that could have run it.
set -euo pipefail

EIGS="${EIGENSCRIPT:-eigenscript}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TMP="$(mktemp -d)"
trap "rm -rf '$TMP'" EXIT

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
        echo "SKIP: runtime is not gfx-capable (build with 'make gfx') — mouse oracle not run"
        exit 2
    fi
    echo "FAIL: gfx probe could not open a window — probe output:"
    echo "$PROBE_OUT"
    exit 1
fi

for tool in xdotool xwd; do
    command -v "$tool" > /dev/null || { echo "SKIP: $tool is not installed — mouse oracle not run"; exit 2; }
done
python3 -c "import PIL" 2>/dev/null || { echo "SKIP: python3 PIL is not installed — mouse oracle not run"; exit 2; }

# xvfb-run sometimes fails cleaning up its own tmpdir after the app is
# torn down, which would mask the oracle's verdict — so read the verdict
# from the oracle's own output, not from the wrapper's exit status.
run_oracle() {
    local log="$1"; shift
    set +e
    $XVFB python3 tests/mouse_oracle.py "$@" > "$log" 2>&1
    set -e
    cat "$log"
}

echo "--- mouse + render-decode oracle (real window, real input) ---"
run_oracle "$TMP/clean.log"
grep -q "^all mouse + render-decode checks passed$" "$TMP/clean.log" || {
    echo "FAIL: the orbit-lab controls did not respond as specified"
    exit 1
}

for fault in pause pan; do
    echo "--- planted fault: $fault ---"
    run_oracle "$TMP/fault_$fault.log" --fault "$fault" --stop-on-fail
    grep -q "mouse-oracle failure" "$TMP/fault_$fault.log" || {
        echo "FAIL: planted fault '$fault' was NOT caught — the mouse oracle can't discriminate"
        exit 1
    }
    echo "PASS: planted fault '$fault' is caught by the oracle"
done

echo "PASS: mouse + render-decode oracle, and both planted faults caught"
