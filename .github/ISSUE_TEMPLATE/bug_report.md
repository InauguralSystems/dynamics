---
name: Bug Report
about: Report a bug in dynamics (a specimen, the package facade, or the tests)
title: ""
labels: bug
assignees: ""
---

**Describe the bug**
What went wrong — e.g. a specimen fails to parse/run, `import dynamics` breaks,
or an observer predicate reports the wrong verdict.

**To reproduce**
Which program and how you ran it:
```sh
eigenscript physics.eigs   # or life.eigs / solve.eigs / dynamics.eigs
```

**Expected vs actual**
What you expected (which predicate/verdict) vs what happened (include output).

**Environment**
- OS: [e.g., Ubuntu 24.04]
- EigenScript version: [output of `eigenscript --version`]
- dynamics version/tag: [e.g. v0.1.0]

> If the root cause is the EigenScript language, runtime, or an observer
> predicate itself, it belongs in the
> [EigenScript repo](https://github.com/InauguralSystems/EigenScript/issues) —
> and it's likely worth a note in [FINDINGS.md](../../FINDINGS.md).
