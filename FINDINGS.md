# FINDINGS

`dynamics` is a forcing function: building observer-heavy code surfaces gaps in
the EigenScript runtime. Findings are logged here; confirmed runtime bugs graduate
to upstream EigenScript issues.

Each finding was reproduced minimally before being recorded (a divergence is a
neutral signal — verify before blaming the runtime).

---

## F-DYN-1 — `record_history` silently disables on a non-numeric flag → upstream EigenScript #255

`record_history of <flag>` is a flag setter: nonzero enables per-assignment
history, `0` disables it. It treats **any non-numeric arg as `0` (disable)** — so
`record_history of null` (or a string) silently turns history *off*, and a later
`prev of x` returns `null` with no error.

```eigenscript
record_history of 1     ; a is 10.0 ; a is 7.0 ; print of (prev of a)   # 10   (works)
record_history of 0     ; b is 10.0 ; b is 7.0 ; print of (prev of b)   # null (disabled)
record_history of null  ; c is 10.0 ; c is 7.0 ; print of (prev of c)   # null (SILENT disable)
```

Originally mis-recorded here as "record_history breaks prev" — it was a wrong
*call* (`null` instead of `1`). The real, fileable bug is the silent
non-numeric→disable coercion (`builtin_record_history`, `src/builtins.c:3451`),
which masks a likely caller error; it should raise instead (cf. the strict-error
direction of #245/#246). Note `prev` does **not** need `record_history` at all in
normal programs — the C compiler auto-enables history when it compiles a temporal
query (`src/compiler.c:1077`/`1818`); calling `record_history of null` *overrides*
that auto-enable, which is what produced the surprising `null`. The physics module
uses `prev` directly and never calls `record_history`.

Filed upstream: **InauguralSystems/EigenScript#255**. (Lesson: verify the call
before blaming the runtime — a divergence is neutral.)

## F-DYN-2 — windowed predicates are sampling-rate sensitive (doc/semantics gap) → upstream EigenScript#256

Entropy of a number is `H(1/(1+|x|))` and the predicates fire on dH against
`dh_small=0.01` / `dh_zero=0.001`. If you observe a smoothly-evolving quantity
*every integration step* (small per-step change), dH falls below `dh_zero` and the
observer reports `equilibrium` for **everything** — a damped oscillator, a
diverging one, and a steady oscillation all look identical.

The fix is to observe at a cadence matched to the dynamics: the physics module
runs `SUB` integration substeps `unobserved`, then observes once per *frame*, so
per-observation dH is large enough to be legible. This sampling/threshold coupling
is not documented in `docs/PREDICATES.md` and is easy to trip over — a real
consumer of the predicates needs to know it. Candidate doc finding upstream.

## F-DYN-3 — `f of <listvar>` does not spread; only a literal `[...]` does

`energy_of of state` (where `state` is a variable holding `[x, v]`) passes the
list as a **single** argument, so a one-param `energy_of(state)` receives the
list. But `step of [state, zeta]` (a literal list at the call site) **spreads**
into `step(state, zeta)`. Same `of`, different arity, depending on whether the
argument is a literal list or a variable. Cost a real bug here (a two-param
`energy_of(x, v)` silently got `v = null`). Known calling-convention behavior, but
a sharp edge worth a line in the docs.

## F-DYN-6 — predicate-driven convergence loops need "settled" + debounce, not bare `converged` → upstream EigenScript#256

The idiomatic `loop while not converged` (stop the instant `report` says
`converged`) is insufficient for two common, legitimate convergence shapes:

- **Fast monotone** (Gauss-Seidel): the residual falls so steeply it lands in
  `equilibrium` (dH stopped) without the observer ever passing through
  `converged`. A `converged`-only loop runs to the iteration cap despite being
  solved by iter ~8.
- **Oscillatory** (PageRank power iteration toward a stationary point): the
  residual swings, so a *single* `equilibrium`/`converged` reading appears
  mid-swing and a naive "stop when settled" quits early with the wrong answer.

A robust predicate-driven solver loop therefore needs **(a)** treat
`converged` OR `equilibrium` as "settled", and **(b)** debounce — require the
settled reading to HOLD for several consecutive iterations (`solve.eigs` uses
`HOLD = 3`). Transient blips reset the count; real convergence holds. This is a
useful pattern but it isn't obvious from `docs/PREDICATES.md`, which presents
`loop while not converged` as the canonical form — worth a doc note that fast and
oscillatory residuals need the settled+hold variant.

## F-DYN-5 — f-strings interpolate `name` / `name[i]` but not call expressions

`f"...{rr[0]}..."` works (variable, and variable-index), but
`f"...{(analyze of [...])[0]}..."` is emitted **literally** — an `f`-string
placeholder containing a function call (or parenthesized expression) is not
evaluated. Workaround: bind the expression to a variable first, then interpolate
`{var}`. Minor; a doc note or a parser extension would help.

## F-DYN-4 — `--lint` false-positive "unused parameter" (minor lint bug)

`--lint` reports `unused parameter 'zeta'` for `profile`/`frame_velocity`, yet the
ζ-sweep demonstrably varies by `zeta` at runtime. The parameter is used inside an
`unobserved:` block (and as a literal-list call argument); the linter's
use-analysis appears not to descend into those, producing a false positive.

---

## Non-findings (verified working — recorded to avoid re-investigating)

- **Interrogatives work** as expressions: `print of (what is energy)`,
  `(when is converged)`, `(where is e)`, `(how is e)` all return values. They
  produce nothing as bare statements (the value is discarded) — that is expected,
  not a bug.
- **`prev` works** across `unobserved` blocks and on list-index-derived values,
  *provided* `record_history` is never called (see F-DYN-1). Parenthesize it:
  `x - (prev of x)`, not `x - prev of x`.
- **`report of <var>`** classifies a *specific* named variable independent of
  last-observed, which is what lets the physics module classify energy and
  displacement separately in the same loop.
