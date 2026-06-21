# FINDINGS

`dynamics` is a forcing function: building observer-heavy code surfaces gaps in
the EigenScript runtime. Findings are logged here; confirmed runtime bugs graduate
to upstream EigenScript issues.

Each finding was reproduced minimally before being recorded (a divergence is a
neutral signal — verify before blaming the runtime).

---

## F-DYN-1 — `record_history` breaks temporal `prev` (runtime bug)

Calling `record_history of null` causes a subsequently-observed variable's
`prev of x` to return `null` instead of its previous value. `prev` works
correctly when `record_history` is never called.

```eigenscript
a is 10.0
a is 7.0
print of (prev of a)        # 10  (correct)

record_history of null
b is 10.0
b is 7.0
print of (prev of b)        # null  (BROKEN)
```

Impact: the temporal-history surface (`prev`, and the interrogatives' deeper
"when/where" forms that rely on recorded history) can't be combined with
`record_history` in one program. The physics module therefore uses `prev`
directly and does **not** call `record_history`. Candidate for an upstream issue;
relates to the history flags `record_history` was added to set (EigenScript #253).

## F-DYN-2 — windowed predicates are sampling-rate sensitive (doc/semantics gap)

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
