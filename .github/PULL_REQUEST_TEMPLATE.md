## What does this PR do?

<!-- Brief description of the change -->

## Checklist

- [ ] Every changed/added specimen **parses and runs** (`eigenscript <file>.eigs`)
- [ ] `bash tests/test_smoke.sh` and `bash tests/test_lab.sh` pass locally
- [ ] Observer usage is **load-bearing** (a real convergence/stability/oscillation
      or temporal `prev` decision — not decoration)
- [ ] Any runtime gap or surprising predicate behavior is logged in
      [FINDINGS.md](../FINDINGS.md) (and, if it's an EigenScript bug, filed upstream)
- [ ] `eigs.json` version bumped if the importable surface changed
