#!/usr/bin/env bash
# LINT GATE — every .eigs in the repo must pass `--lint` with no issues.
#
# The suite has always been able to run `--lint`; nothing made it. That let
# three warnings sit in the tree unseen (an unused package constant, a dead
# constant in predicate_fit.eigs, and `define dot` in solve.eigs shadowing
# the builtin of the same name). Upstream's lint-walker recursion train
# (EigenScript #781-#794, v0.35.0) also means new rules — and rules that
# now see inside `unobserved:` blocks and match arms — arrive with every
# runtime bump, so this needs to be mechanical rather than remembered.
#
# A deliberate suppression is a `# lint: allow WNNN -- reason` comment on
# the offending line, which is visible in review; silence is not.
#
# The gate is validated with a planted fault: a copy of the tree with an
# obvious unused variable must be REJECTED.
set -euo pipefail

EIGS="${EIGENSCRIPT:-eigenscript}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TMP="$(mktemp -d)"
trap "rm -rf '$TMP'" EXIT

# lint_tree <dir> -> 0 when every .eigs under it is clean; prints offenders.
lint_tree() {
    local dir="$1" quiet="${2:-}" bad=0 f out
    for f in "$dir"/*.eigs "$dir"/tests/*.eigs; do
        [ -e "$f" ] || continue
        out=$("$EIGS" --lint "$f" 2>&1) || true
        if ! echo "$out" | grep -q "no issues found"; then
            [ -n "$quiet" ] || { echo "FAIL: $f"; echo "$out" | sed 's/^/    /'; }
            bad=1
        fi
    done
    return $bad
}

N=$(ls -1 ./*.eigs tests/*.eigs 2>/dev/null | wc -l)
echo "--- --lint over $N .eigs files ---"
lint_tree "$ROOT" || exit 1
echo "PASS: all $N .eigs files lint clean"

# Planted fault: an unused variable must be caught.
echo "--- planted fault: an unused variable ---"
mkdir -p "$TMP/fault/tests"
cp ./*.eigs "$TMP/fault/"
printf 'DEAD_CONSTANT is 42\nprint of "hi"\n' > "$TMP/fault/planted.eigs"
if lint_tree "$TMP/fault" quiet; then
    echo "FAIL: an unused variable passed the lint gate — the gate isn't running"
    exit 1
fi
echo "PASS: planted fault (unused variable) is caught"
