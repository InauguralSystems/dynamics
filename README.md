# dynamics

[![CI](https://github.com/InauguralSystems/dynamics/actions/workflows/test.yml/badge.svg)](https://github.com/InauguralSystems/dynamics/actions/workflows/test.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/InauguralSystems/dynamics/badge)](https://securityscorecards.dev/viewer/?uri=github.com/InauguralSystems/dynamics)
[![tag](https://img.shields.io/github/v/tag/InauguralSystems/dynamics?label=version)](https://github.com/InauguralSystems/dynamics/tags)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

An **observer-rich dynamical-systems lab** in [EigenScript](https://github.com/InauguralSystems/EigenScript).

Most EigenScript code is observer-*sparse*: the convergence/stability/oscillation
predicates and temporal `prev` show up rarely, because the usual domains (parsers,
stores, games, emulators) don't need them. `dynamics` deliberately lives where the
observer is **load-bearing** — systems that *seek an equilibrium* — so its code
exercises `loop while not converged`, the six windowed predicates
(`converged` / `stable` / `improving` / `oscillating` / `diverging` /
`equilibrium`), and temporal history *authentically*, not as decoration.

## Why it exists

Two jobs:

1. **Forcing function.** The windowed-predicate semantics were rebuilt in the
   EigenScript runtime but have no heavy real consumer to battle-test them across
   their full range — the settling `improving∧stable` gray band, the limit cycle
   (`stable` amplitude ∧ `oscillating` phase), spurious `converged` on numerical
   jitter. A damped oscillator sweeps that whole space; this package is the
   consumer that stresses it and surfaces gaps upstream.

2. **Corpus source.** A measurement of the
   [iLambdaAi](https://github.com/InauguralSystems/iLambdaAi) training corpus found
   the observer idioms at noise level (~0.08%) — the model was learning a
   conventional language, not the observer-centric one that *is* EigenScript. The
   other ecosystem repos are observer-deserts. This package is dense, authentic
   observer usage to fill that gap.

Every member is **runtime-verified** (it parses and runs; CI imports it the way a
consumer would). The runtime — not a human — certifies the code, which keeps the
no-oracle discipline: this is verified training data, not a hand-authored notion of
"good" observer code.

## Surface (0.1.0 seed)

```eigenscript
import dynamics

dynamics.relax of [0.0, 0.5, 100.0]   # geometric relaxation to a target; observer decides convergence
dynamics.settle_steps of 0.8          # iterations to converge (no fixed tolerance constant)
dynamics.last_delta of 0.5            # final pre-convergence step, read via temporal `prev`
dynamics.VERSION
```

`dynamics.eigs` is the importable package facade (the 0.1.0 relaxation primitive).
The lab itself is a set of standalone runnable programs (corpus specimens +
forcing functions), each exercising a different observer sub-surface:

- **physics** (`physics.eigs`) — **built.** The damped-oscillator ζ-sweep: the
  predicate showcase. Observes energy (Lyapunov → `improving`/`converged`) and
  displacement (`oscillating`) of the *same* system; the damping ratio sweeps the
  full predicate space, and the ζ=0 row shows the founding-question lesson —
  energy conserved (never converges) while x oscillates, opposite verdicts set by
  what the observer watches. Run: `eigenscript physics.eigs`.
- **life** (`life.eigs`) — **built.** Conway's Game of Life: the temporal
  showcase. A blinker, a block, and a glider all have constant population, so
  `report of population` calls all three the same — only comparing the board to its
  own past (a position-sensitive signature + `prev`) reveals period-2 oscillator
  vs. still life vs. translating. The temporal observer doing what the scalar
  predicate cannot. Run: `eigenscript life.eigs`.
- **solve** (`solve.eigs`) — **built.** Jacobi / Gauss-Seidel / power iteration /
  PageRank: the loop-idiom showcase. Every loop runs until `report of change` is
  settled (and holds) — the observer, not a magnitude tolerance, decides "done".
  Gauss-Seidel converges in fewer iterations than Jacobi under the *same* idiom;
  PageRank's oscillatory residual needs the debounce. Run: `eigenscript solve.eigs`.

Forcing-function findings (runtime gaps surfaced while building) are logged in
[FINDINGS.md](FINDINGS.md) — most have graduated to upstream fixes
(#255/#256/#280/#375); a calling-convention edge remains open.

## Develop locally

```sh
eigenscript dynamics.eigs            # parse + run the entry point
bash tests/test_smoke.sh             # stage as a consumer would and import
```

CI builds EigenScript from source on Linux and runs the smoke and lab test scripts
on every push and PR (see `.github/workflows/test.yml`).

## Publish

A "publish" is a git tag; consumers pin against tags ([semver](https://semver.org/)).

```sh
git tag v0.1.0 && git push --tags
```

## Consume

```sh
eigenscript --pkg add InauguralSystems/dynamics https://github.com/InauguralSystems/dynamics v0.1.0
```
