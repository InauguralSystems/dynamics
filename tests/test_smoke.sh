#!/usr/bin/env bash
# Smoke tests for the dynamics package, run from CI and from a clean clone.
# Pattern: build a tiny consumer in a tmpdir whose eigs_modules/<name>/
# points at this repo, then `import <name>` and exercise the real surface
# (the observer-driven convergence helpers).
set -euo pipefail

EIGS="${EIGENSCRIPT:-eigenscript}"
PKG_NAME="$(python3 -c 'import json,sys;print(json.load(open("eigs.json"))["name"])')"
PKG_ROOT="$(pwd)"

TMP="$(mktemp -d)"
trap "rm -rf '$TMP'" EXIT

# Pretend a consumer has cloned this package into eigs_modules/<name>/.
mkdir -p "$TMP/eigs_modules/$PKG_NAME"
cp -a "$PKG_ROOT/$PKG_NAME.eigs" "$TMP/eigs_modules/$PKG_NAME/"
[ -f "$PKG_ROOT/eigs.json" ] && cp -a "$PKG_ROOT/eigs.json" "$TMP/eigs_modules/$PKG_NAME/"

# 1. Public surface imports and the observer-driven helpers run.
cat > "$TMP/app.eigs" <<EOF
import $PKG_NAME
print of $PKG_NAME.VERSION
# relax 100 -> 0 at rate 0.5; observer decides convergence
print of $PKG_NAME.relax of [0.0, 0.5, 100.0]
# step count is positive and finite
print of $PKG_NAME.settle_steps of 0.8
# temporal: final pre-convergence delta is non-negative
print of $PKG_NAME.last_delta of 0.5
EOF

cd "$TMP"
OUT=$("$EIGS" app.eigs 2>&1)
echo "$OUT"
if ! echo "$OUT" | head -1 | grep -q "0.1.0"; then
    echo "FAIL: VERSION did not render"
    exit 1
fi
# relax should converge near the target (0): tiny magnitude on line 2
RELAXED=$(echo "$OUT" | sed -n '2p')
if ! echo "$RELAXED" | grep -qE "e-0|^0(\.0+)?$"; then
    echo "FAIL: relax did not converge near target — got: $RELAXED"
    exit 1
fi
# settle_steps positive
STEPS=$(echo "$OUT" | sed -n '3p')
if [ "$STEPS" -le 0 ] 2>/dev/null; then
    echo "FAIL: settle_steps not positive — got: $STEPS"
    exit 1
fi
echo "PASS: import $PKG_NAME → observer convergence helpers run"

# 2. Private (leading-underscore) names stay off the public surface.
cat > "$TMP/app2.eigs" <<EOF
import $PKG_NAME
ks is keys of $PKG_NAME
if (contains of [ks, "_seed_marker"]) == 1:
    print of "LEAKED"
else:
    print of "private"
EOF
OUT2=$("$EIGS" "$TMP/app2.eigs" 2>&1)
if [ "$OUT2" != "private" ]; then
    echo "FAIL: _seed_marker should be private but appears in module keys"
    echo "$OUT2"
    exit 1
fi
echo "PASS: leading-underscore names stay private"
