# dynamics

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

This 0.1.0 is the equilibrium-relaxation primitive. Planned modules, each chosen
to exercise a different observer sub-surface:

- **physics** (ζ-sweep damped oscillator, n-body settling, diffusion relaxation) —
  the predicate showcase; all six predicates on continuous trajectories. The
  damping ratio sweeps the full predicate space, and observing energy vs.
  displacement gives opposite verdicts on the same system — the founding-question
  lesson that the observer constitutes the measurement.
- **life** (Conway) — the temporal showcase; `prev`/`at` for period/oscillator
  detection where scalar predicates alone are fooled.
- **solve** (Jacobi / Gauss-Seidel / SOR / power iteration / PageRank) — the
  canonical `loop while not converged` control-flow idiom.

## Develop locally

```sh
eigenscript dynamics.eigs            # parse + run the entry point
bash tests/test_smoke.sh             # stage as a consumer would and import
```

CI builds EigenScript from source on Linux and runs the smoke test on every push
and PR (see `.github/workflows/test.yml`).

## Publish

A "publish" is a git tag; consumers pin against tags ([semver](https://semver.org/)).

```sh
git tag v0.1.0 && git push --tags
```

## Consume

```sh
eigenscript --pkg add InauguralSystems/dynamics https://github.com/InauguralSystems/dynamics v0.1.0
```
