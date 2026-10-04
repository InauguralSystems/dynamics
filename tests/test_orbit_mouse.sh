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
# The checker is validated by three planted faults (pan, pause, mode):
# each MUST fail its named assertion, or a green run means nothing.
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

RUN=()
if [ -z "${DISPLAY:-}" ]; then
    RUN=(xvfb-run -a)
fi

echo "--- gfx capability probe ---"
cat > "$TMP/gfxprobe.eigs" <<'EOF'
w is gfx_open of [64, 48, "probe"]
gfx_close of null
print of "GFXOK"
EOF
PROBE_RC=0
PROBE_OUT=$("${RUN[@]}" "$EIGS" "$TMP/gfxprobe.eigs" 2>&1) || PROBE_RC=$?
if [ "$PROBE_RC" -ne 0 ] || ! echo "$PROBE_OUT" | grep -qx "GFXOK"; then
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

# A wrapper/tool failure cannot stand in for the oracle's own verdict.
# Preserve both the exact exit and the named assertion population.
run_oracle() {
    local log="$1"; shift
    ORACLE_RC=0
    "${RUN[@]}" python3 tests/mouse_oracle.py "$@" > "$log" 2>&1 || ORACLE_RC=$?
    cat "$log"
}

echo "--- mouse + render-decode oracle (real window, real input) ---"
run_oracle "$TMP/clean.log"
UNIQUE_PASSES=$(grep '^PASS ' "$TMP/clean.log" | sort -u | wc -l) || {
    echo "FAIL: could not enumerate distinct mouse checks"
    exit 1
}
if [ "$ORACLE_RC" -ne 0 ] ||
   [ "$(grep -c '^PASS ' "$TMP/clean.log" || true)" -ne 16 ] ||
   grep -q '^FAIL \|^ERROR \|^DEADLINE ' "$TMP/clean.log" ||
   [ "$(grep -c '^all mouse + render-decode checks passed$' "$TMP/clean.log" || true)" -ne 1 ] ||
   [ "$UNIQUE_PASSES" -ne 16 ]; then
    echo "FAIL: the orbit-lab controls did not respond as specified"
    exit 1
fi

for fault in pause pan mode; do
    echo "--- planted fault: $fault ---"
    run_oracle "$TMP/fault_$fault.log" --fault "$fault" --stop-on-fail
    case "$fault" in
        pause) killed='pause: advancement freezes'; passes=3 ;;
        pan) killed='drag: panning redraws'; passes=5 ;;
        mode) killed='mode: the control column reads'; passes=11 ;;
    esac
    if [ "$ORACLE_RC" -ne 1 ] ||
       [ "$(grep -c '^PASS ' "$TMP/fault_$fault.log" || true)" -ne "$passes" ] ||
       [ "$(grep -c '^FAIL ' "$TMP/fault_$fault.log" || true)" -ne 1 ] ||
       grep -q '^ERROR ' "$TMP/fault_$fault.log" ||
       ! grep -q "^FAIL $killed" "$TMP/fault_$fault.log" ||
       [ "$(grep -c '^1 mouse-oracle failure(s)$' "$TMP/fault_$fault.log" || true)" -ne 1 ]; then
        echo "FAIL: planted fault '$fault' did not fail its named assertion with rc1"
        exit 1
    fi
    echo "PASS: planted fault '$fault' is caught by the oracle"
done

echo "PASS: mouse + render-decode oracle (16 checks), and all three planted faults caught"
