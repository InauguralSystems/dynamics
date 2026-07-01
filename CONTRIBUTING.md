# Contributing to dynamics

Thanks for your interest. `dynamics` is an observer-rich dynamical-systems lab
written entirely in [EigenScript](https://github.com/InauguralSystems/EigenScript):
a forcing function for the observer/temporal semantics and a source of authentic
observer-dense training corpus. See the [README](README.md) for the intent.

## Setup

EigenScript is not vendored here. Either build it alongside this repo, or open
the repo in a devcontainer / [Codespace](https://codespaces.new/InauguralSystems/dynamics)
(which builds the pinned EigenScript for you).

```sh
# local: build EigenScript from source, then
eigenscript physics.eigs             # run a specimen
bash tests/test_smoke.sh             # stage + import as a consumer would
bash tests/test_lab.sh               # run the lab specimens
```

CI runs both test scripts in the pinned devcontainer on every push and PR.

## The discipline (what makes a good contribution here)

- **Runtime-verified, not hand-graded.** Every specimen must *parse and run* —
  the runtime certifies the code, not a human notion of "good" observer usage.
  This keeps the no-oracle property: `dynamics` is verified training data.
- **The observer must be load-bearing.** Add a specimen only if a
  convergence/stability/oscillation predicate or a temporal `prev` comparison is
  actually deciding something — not sprinkled on as decoration. If a plain scalar
  check would do, it doesn't belong here.
- **Surface gaps, don't work around them.** When the runtime does something wrong
  or surprising (a predicate misfires, `prev`/`record_history` interact oddly, a
  sampling-rate sensitivity), log it in [FINDINGS.md](FINDINGS.md) and file it
  upstream in [EigenScript](https://github.com/InauguralSystems/EigenScript) —
  that's half the point of this repo.

## Before you open a PR

- Every changed/added `.eigs` parses and runs; `tests/test_smoke.sh` and
  `tests/test_lab.sh` pass.
- Keep the prevailing style: `snake_case`, sectioned files with header comments,
  a short comment on each specimen saying which observer sub-surface it exercises.
- Bump `eigs.json`'s `version` if the importable facade (`dynamics.eigs`) changes.

## Reporting bugs

Open an issue with the specimen and how you ran it. For security concerns see
[SECURITY.md](SECURITY.md).
