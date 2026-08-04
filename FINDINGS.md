# FINDINGS

`dynamics` is a forcing function: building observer-heavy code surfaces gaps in
the EigenScript runtime. Findings are logged here; confirmed runtime bugs graduate
to upstream EigenScript issues.

Each finding was reproduced minimally before being recorded (a divergence is a
neutral signal — verify before blaming the runtime).

---

## F-DYN-1 — `record_history` silently disables on a non-numeric flag → upstream EigenScript #255 (CLOSED upstream)

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
non-numeric→disable coercion (`builtin_record_history`, `src/builtins.c:3746`),
which masks a likely caller error; it should raise instead (cf. the strict-error
direction of #245/#246). Note `prev` does **not** need `record_history` at all in
normal programs — the C compiler auto-enables history when it compiles a temporal
query (`src/compiler.c:1486`/`2350`); calling `record_history of null` *overrides*
that auto-enable, which is what produced the surprising `null`. The physics module
uses `prev` directly and never calls `record_history`.

Filed upstream: **InauguralSystems/EigenScript#255**. (Lesson: verify the call
before blaming the runtime — a divergence is neutral.)

## F-DYN-2 — windowed predicates are sampling-rate sensitive (doc/semantics gap) → upstream EigenScript#256 (CLOSED upstream)

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

**Resolved upstream — EigenScript#259** (merged): documented in the new
`docs/PREDICATES.md` "Convergence loops in practice" section (the observation-cadence
note + the entropy-peak-at-`|x|=1`/`diverging` consequence). See F-DYN-6 below — both
findings landed in the same doc PR.

## F-DYN-3 — `f of <listvar>` does not spread; only a literal `[...]` does

`energy_of of state` (where `state` is a variable holding `[x, v]`) passes the
list as a **single** argument, so a one-param `energy_of(state)` receives the
list. But `step of [state, zeta]` (a literal list at the call site) **spreads**
into `step(state, zeta)`. Same `of`, different arity, depending on whether the
argument is a literal list or a variable. Cost a real bug here (a two-param
`energy_of(x, v)` silently got `v = null`). Known calling-convention behavior, but
a sharp edge worth a line in the docs.

## F-DYN-6 — predicate-driven convergence loops need "settled" + debounce, not bare `converged` → upstream EigenScript#256 (CLOSED upstream)

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

**Resolved upstream — EigenScript#259** (merged): `docs/PREDICATES.md`
gained a "Convergence loops in practice" section built from `solve.eigs`'s real
Gauss-Seidel and PageRank traces, the settled-plus-`HOLD` recipe, plus the
sampling-cadence (F-DYN-2) and entropy-peak-at-`|x|=1` notes. One correction came
out of writing it: the Gauss-Seidel residual was confirmed to read `equilibrium`
*permanently* and never `converged` — even held at `change == 0` to iter 25 — so
"never passes through `converged`" above is exactly right; a synthetic `r*0.1` toy
that *did* reach `converged` was the misleading case, and the real solver trace
(the oracle) settled it.

## F-DYN-5 — f-strings interpolate `name` / `name[i]` but not call expressions — FIXED upstream (verified 2026-07-03)

Re-verified against EigenScript main: `f"{(analyze of 5)[0]}"` and
`f"{len of [1,2,3]}"` both interpolate (the v0.23.0 f-string work).
Drop the bind-to-a-variable workaround on current pins. Original report:

`f"...{rr[0]}..."` works (variable, and variable-index), but
`f"...{(analyze of [...])[0]}..."` is emitted **literally** — an `f`-string
placeholder containing a function call (or parenthesized expression) is not
evaluated. Workaround: bind the expression to a variable first, then interpolate
`{var}`. Minor; a doc note or a parser extension would help.

## F-DYN-4 — `--lint` false-positive "unused parameter" (minor lint bug) — FIXED upstream (EigenScript PR #375, 2026-07-03)

Root cause confirmed and fixed at the root: the lint use-analysis never
descended into `unobserved:` blocks (`AST_UNOBSERVED` missing from the
walkers — slices and list-pattern assigns had the same blind spot), so a
parameter used only inside the recommended hot-loop idiom looked unused.
The zeta repro lints clean on EigenScript main. Original report:

`--lint` reports `unused parameter 'zeta'` for `profile`/`frame_velocity`, yet the
ζ-sweep demonstrably varies by `zeta` at runtime. The parameter is used inside an
`unobserved:` block (and as a literal-list call argument); the linter's
use-analysis appears not to descend into those, producing a false positive.

---

## F-DYN-7 — bare `converged` in `settle_steps` read the counter, not the value → fixed upstream EigenScript#280 (v0.20.0)

`settle_steps(rate)` ran `loop while not converged:` over a body that assigns the
decaying `x` **then** a counter `k is k + 1`. A bare predicate reads the
*last-observed* binding, and every assignment is observed, so the predicate read
`k` — whose entropy `H(1/(1+k))` flattens at a fixed step independent of `rate`.
The loop therefore halted on the counter: `settle_steps` returned the same count
(~88) for every rate, while `x` was nowhere near settled (at rate 0.99, x had
only decayed 100 → 41.3). `relax`/`last_delta` were unaffected — their loop
bodies assign only `x`, so the bare predicate unambiguously reads it (the comment
at `relax` states this invariant; `settle_steps` violated it).

Upstream fix (EigenScript#280, v0.20.0): a **named** predicate form
`<predicate> of <var>` that binds to a specific binding's slot trajectory, plus
lint `W014` for a bare predicate in a multi-observe loop condition. `settle_steps`
now uses `loop while not (converged of x)` — it reads x's slot each iteration and
is rate-dependent (e.g. 30 / 120 / 10 steps at 0.5 / 0.9 / 0.99). `EIGS_REF`
bumped to v0.20.0. Prefer the named form whenever a convergence loop assigns more
than one binding.

---

## F-DYN-8 — `import` silently prefers the stdlib over a same-named module in the working directory

`import physics` from the orbit-lab front-end resolved to the **stdlib's**
`lib/physics.eigs` (the physics *formula* library), not this repo's
`physics.eigs` sitting in the working directory. No error, no warning — the
module simply has none of the expected members, so `physics.SUB` reads `null`
and the first symptom is a downstream type error ("cannot compare num and none").
Search order is stdlib-first, and the stdlib is large enough (~75 modules) that
name collisions with consumer files are easy to hit. Cost a real bug here.
Workaround used: `load_file of "physics.eigs"` (path-explicit, DeslanStudio's
shared-scope pattern). Candidate upstream: a shadowing warning when a
cwd module is eclipsed by a stdlib module of the same name, or cwd-first
resolution for explicit relative candidates. Upstream-fileable (EigenScript).

## F-DYN-9 — lib/ui gap: no x-y (parametric) plot widget — phase portraits need raw canvas

Fleet UI ladder rung 1 (dynamics#20) needed a live **phase portrait**: a
polyline in *world coordinates* (x, v), fixed world window, axes through the
world origin, an equilibrium marker. `lib/ui_w_viz.eigs`'s `chart` widget is
strictly a y-vs-index series plot (each series is a list of y values; x is
`i/(n-1)` across the plot width, y autoscaled) — there is no way to express an
x-y parametric/scatter series, a fixed aspect world window, or pan/zoom.
This slice canvas-draws the portrait (`orbit.eigs` `_paint_phase` on a
`ui.canvas`), which the fleet standard permits, but this is the third consumer
now forcing the chart/plot widget (with eigen-sheet#26 and EigenMiniSat#76):
needed are xy series in data coordinates, axis placement at data zero,
markers, and pan/zoom interaction. For `eigenscript-ui-toolkit-engineer`.

**RESOLVED upstream — EigenScript#819 (PR #824), shipped in v0.35.0.** `chart`
was generalised in place into a data-coordinate x-y plot: per-series `x` lists,
`fixed_aspect`, labelled `vline`/`hline`/`point` markers, widget-owned
drag-pan/wheel-zoom, incremental `add_xy`/`chart_trim`, and clipping by
construction. dynamics is its first production consumer — the bifurcation view
(slice 3) is built on it with no consumer-side workarounds. The phase portrait
keeps its `canvas` on purpose: it needs a custom trail renderer, which is what
the canvas escape hatch is for. Residual friction is F-DYN-14.

## F-DYN-10 — lib/ui gap: viz widget surfaces hardcode their colours instead of reading theme keys

`_render_chart` / `_render_bar_chart` / `_render_waveform_view` in
`lib/ui_w_viz.eigs` paint their backgrounds, borders and grids with literal
RGB values (`25, 25, 35`, `40, 40, 55`, `18, 18, 26`, …) rather than theme
keys. A themed app (the DeslanStudio in-place theme-apply pattern, used here
by `orbit_theme.eigs`) can restyle every button and slider but NOT a chart's
plot surface — the one surface a data app is mostly made of. Even if F-DYN-9's
xy chart existed today, it could not have taken the orbit-lab palette. Wants
theme keys (e.g. `plot_bg`, `plot_grid`, `plot_border`) read at render time.
For `eigenscript-ui-toolkit-engineer`.

**RESOLVED upstream — EigenScript#820 (PR #824), shipped in v0.35.0.** The viz
surfaces now read `plot_bg` / `plot_grid` / `plot_axis` / `plot_border` /
`plot_series` (and `wave_*`) off the active theme, falling back to the built-in
defaults for a theme dict that predates them. `orbit_theme.eigs` maps all five
onto the same palette entries the phase-portrait canvas reads, so chrome and
data surface are themed from the one module — verified in real pixels by the
committed screenshot.

## F-DYN-11 — lib/ui gap: the wheel event carries no cursor position

`ev.x` / `ev.y` on a `wheel` event are the scroll **deltas** (#569), and the
event dict carries nothing else positional — `src/ext_gfx.c` never puts the
pointer location on it. `dispatch` knows where the pointer is (it hit-tests
with `_ui.last_mouse_x` / `_ui.last_mouse_y`), but `_ui` is private, so a
consumer cannot read it. Any widget wanting **cursor-anchored zoom** — the
universal convention for a map, a plot or a canvas — therefore has to shadow
the pointer itself by recording every hover `mousemove` through `on_mouse`,
and is wrong for any wheel that arrives before the first motion event
(orbit.eigs defaults `_ptr` to the canvas centre for exactly that window).
Wants either the pointer position on the wheel event dict (SDL has it at
event time) or a public `ui.pointer of null`. For
`eigenscript-ui-toolkit-engineer`.

## F-DYN-12 — lib/ui ergonomics: `canvas` does not clip its own `on_paint`

`_render_canvas` calls `widget.on_paint` with the widget's absolute origin and
nothing else — no clip rectangle. Several other widgets set one around their
body (`ui_w_data`'s table/code_view, `ui_w_container`'s scroll panel,
`ui_w_viz`'s waveform view all `gfx_clip` then `gfx_clip of null`), so the
absence here is easy to read as "the canvas is clipped like everything else".
It is not, and the canvas is precisely the widget whose geometry is
data-dependent: the moment the orbit lab gained pan/zoom, trail segments
mapped outside the plot rect and painted straight over the control column.
The fix inside `_paint_phase` is two lines, but it has to be *known about* —
nothing fails loudly, the drawing just lands on a neighbour. The same class
bit the chrome in the other direction and was only caught by driving the real
window: a plain `panel` does not clip its children either, so every side-panel
`label` whose text exceeded the panel width ran off the edge of the *window*
and was silently truncated mid-word ("energy : converge", "drag pan - wheel
z"). No API reports the overflow and no test could see it — a screenshot did.
The labels are now sized to the column by hand. Proposal: have
`_render_canvas` wrap `on_paint` in the widget's clip (an escape hatch that
still cannot corrupt the rest of the tree), or say so in the `canvas` doc
comment next to the `on_mouse` / `on_wheel` notes. For
`eigenscript-ui-toolkit-engineer`.

## F-DYN-13 — the temporal assignment history is unbounded and arms on dead code → upstream EigenScript#827

**This one froze the box.** Building the bifurcation view (dynamics#20 rung 1,
slice 3), the new window grew **3.9 MB per rendered frame** — 258 MB at frame
30, 529 MB at frame 100, 859 MB at frame 300, then SIGSEGV against a
`ulimit -v` cap. Every correctness oracle was green throughout.

Bisected to `load_file of "physics.eigs"`, and inside it to a single token:
`frame_velocity`'s `prev of x`, in a demo helper the window **never calls**.
The compiler arms `g_trace_hist` from a whole-program scan, and the history
table it turns on (`src/trace.c`, `HistoryEntry`) is append-only with **no cap**
and holds a **reference to every assigned value**. `lib/ui`'s chart allocates a
coordinate pair per plotted point per frame (4,000 of them here), so every one
of those was pinned forever.

Minimal repro, no gfx and no lib/ui — a `prev of` inside a function that is
never called, versus the same program without it:

```
prev_off N=100000  PEAK_KB 3456      prev_on N=100000  PEAK_KB 37248
prev_off N=400000  PEAK_KB 3328      prev_on N=400000  PEAK_KB 140416
```

Flat versus linear in the iteration count. `record_history of 0` restores flat.

Note this is the *other half* of F-DYN-1: that finding recorded the silent
non-numeric coercion of the same builtin, and its "non-findings" note that
`prev` works "provided `record_history` is never called" is now qualified —
`prev` works, and arms an unbounded table for the whole program while doing it.

**FIXED upstream** by EigenScript#829, shipped in **v0.35.1** (carried by this
repo's pin): the history table is bounded by program TEXT — entries no backward
query can reach are pruned at append time — and arming is per NAME instead of
whole-program, so `physics.eigs`'s dead-code `prev of` arms nothing here.

**In this repo:** `orbit.eigs`'s `_run` used to call `record_history of 0` for
the lifetime of a window session and restore it on exit; that opt-out is gone
(dynamics#24). Removing it changed peak RSS by nothing measurable — 134.3 /
134.5 / 134.4 MB with it, 134.7 / 134.3 / 134.4 MB without, at 30 / 100 / 300
frames. The same tree with history explicitly ON measures 304 MB at 30 frames
and 674 MB at 100 on v0.35.0, and 134.5 / 134.9 / 134.8 MB flat on v0.35.1 —
which is why `tests/test_bif_mem.sh`'s planted fault 1 could no longer be
planted and was re-pointed at a per-frame retention fault instead of deleted.
For `eigenscript-runtime-engineer` / `eigenscript-trace-tape-engineer`.

## F-DYN-14 — lib/ui: `chart` allocates a list per plotted point per frame → upstream EigenScript#828

Surfaced as `chart`'s first production consumer. `_render_chart`'s per-sample
loop calls `_chart_map`, which returns a fresh 2-element list, for every sample
of every series on every frame — even when the data has not changed. Measured
~24.5 µs/point/frame (4,000 points ≈ 98 ms/frame, 8,800 ≈ 190 ms), so a static
diagram renders at ~10 fps and essentially all of it is allocation, not drawing.

RSS is flat, so this is not a leak in the widget (verified separately at 4,000
points over 30/100/300 frames: 130.9 / 131.1 / 131.2 MB, both styles, with and
without markers and fixed bounds) — it is throughput and allocation pressure,
and it is what turned F-DYN-13 from a slow drip into an OOM.

Also filed there: `chart_marker of ["vline", x, y, label, color]` makes the
caller invent a `y` that a vertical line ignores (and vice versa for `hline`),
which is silently accepted if wrong.

**Not** a blocker: F-DYN-9's ask (an x-y plot widget) is fully answered — the
API needed no changes to carry this view. For `eigenscript-ui-toolkit-engineer`.

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
