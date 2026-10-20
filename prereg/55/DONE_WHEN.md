## Done when

This is a **pre-registration**, not an implementation.  The commands below are
the frozen CLI contract for the later builder; `tests/lienard_55.py` and
`lienard.eigs` deliberately do not exist in this change.  A command passes only
with exit status 0 and the exact terminal `PASS ...` record described for it.
Anything else (including an unlisted observer word, non-finite state, a missed
section, or an assertion that the visited `x` box was exceeded) is a miss and a
non-zero exit.

### Definitions and theorem oracle

The system is `x' = y - F(x), y' = -x`.  “Amplitude” means the coordinate
`x*` at the unique crossing of `Sigma = {y=0,x>0}` with `y'=-x<0`; equivalently
it is a fixed point of the first-return map.  It does **not** mean `max |x|` or
an averaging root.  All starts are `(x0,0)` on Sigma.  The independently
re-derived Instance-A references are

* inner `x*=1.487060441512`, and
* outer `x*=3.922873870354`,

with absolute reference allowance `1e-9`.  `python3 prereg/55/oracle.py
--rtol 1e-12` and the independent higher-effort `--rtol 1e-13` result agree in
all 12 printed decimals (the required minimum is 9).  Both use event location,
forward return-map iteration for the outer orbit, reverse-time iteration for
the inner orbit, and stop at successive section values differing by `<1e-12`.

The cycle-count oracle is the at-most-two theorem for polynomial Lienard
systems of degree five used by the Lean-checked `openai/math` family 143
`QuinticLienard.lean`, backed by G. S. Rychkov, *The maximum number of limit
cycles of polynomial Lienard systems of degree five is equal to two*,
Differential Equations 11 (1975), 301–302, and K. Odani, *Existence of exactly
N periodic solutions for Lienard systems*, Funkcialaj Ekvacioj 39 (1996),
217–234.  The later builder must vendor the checked theorem artifact; failure
to resolve it is an error, not permission to infer a third cycle.

For Family B, `a5>0` gives `F(+infinity)=+infinity` and
`F(-infinity)=-infinity`.  The precise dissipativity result relied on is the
classical Lienard boundedness statement: for continuous `F`, with `x g(x)>0`
off zero and `G(x)=integral_0^x g -> +infinity` at both ends, if `F` is bounded
below eventually on the positive half-line and bounded above eventually on the
negative half-line, every positive semitrajectory is ultimately bounded.  It
is the Levinson–Smith/Villari boundedness statement summarized in G. Villari,
“On the qualitative behaviour of solutions of Lienard equation,” *J. Differential
Equations* 67 (1987), section 4, pp. 269–297.  Here `g(x)=x` and a positive
quintic leading coefficient satisfies those hypotheses.  This is why negative
`a5` (anti-damping at infinity) is excluded rather than mislabeled
`diverging`.

### Frozen acceptance items

1. **Instance-A basin verdicts (116 graded, 1 gray).**  Run exactly
   `python3 tests/lienard_55.py item1 --manifest prereg/55/manifest.json`.
   On the 117 starts `0.20..6.00` by `0.05`, exclude only `x0=1.50`, the only
   member of the closed `+-2%` inner-amplitude band.  For each of the other
   116 starts, the observer verdict read after RK step 40,000 must equal
   `origin` when `x0<1.487060441512` and `outer` when it is greater.  Threshold:
   zero misses.  Success is exit 0 and
   `PASS item1 population=117 graded=116 gray=1 misses=0 gray_members=1.50`.

2. **No false forward divergence (7,117 runs).**  Run exactly
   `python3 tests/lienard_55.py item2 --manifest prereg/55/manifest.json`.
   Across the 117 Instance-A starts and all `350*20=7,000` Family-B
   coefficient/start pairs, the verdict read at the final forward step must
   never be `diverging`.  Threshold: 0.  Reverse-time oracle runs and the
   separately scoped reaction-network controls are excluded by name.  Success
   is exit 0 and `PASS item2 population=7117 diverging=0`.

3. **The theorem-backed cycle-count oracle (350 systems).**  Run exactly
   `python3 tests/lienard_55.py item3 --manifest prereg/55/manifest.json`.
   For every row of `family_b.csv`, start the 20-point grid, retain only runs
   whose observer gate says settled-cycle as defined below, estimate section
   fixed points from the final window, and apply the frozen complete-link
   clustering rule.  The distinct cluster count must be `<=2` for every
   system; threshold: zero systems reaching 3.  The oracle is Rychkov's bound,
   not another numerical integration.  Success is exit 0 and
   `PASS item3 population=350 starts=7000 max_clusters<=2 reaches_3=0`.

4. **Outer section amplitude (one orbit, observer only gates).**  Run exactly
   `python3 tests/lienard_55.py item4 --manifest prereg/55/manifest.json`.
   Start Instance A at `(4,0)`.  The observer does **not** derive amplitude:
   it only supplies the `oscillating of E` settled-cycle gate.  The harness's
   linearly event-located Sigma crossings supply `x*`.  Their final-window
   median must be within `0.5%` (`0.019614369352` absolute) of
   `3.922873870354`; additionally the estimates at `h=0.01` and `h=0.005`
   must differ by `<=1e-7`.  Success is exit 0 and
   `PASS item4 oracle=3.922873870354 rel_error<=0.005 h_delta<=1e-7`.

5. **One planted-window control.**  Run exactly
   `python3 tests/lienard_55.py item5 --manifest prereg/55/manifest.json`.
   Run item 3 once in a scratch-generated copy of the future EigenScript
   specimen, changing only `set_observer_window of 10` to
   `set_observer_window of 4`; never edit the pinned runtime or committed
   source.  Normal depth is 10, fault depth is 4.  The control passes only if
   the item-3 gate itself fails (at least one system has at least 3 accepted
   clusters), while the command converts that expected failure into exit 0.
   Output contract:
   `PASS item5 normal_window=10 fault_window=4 item3_exit=1 reaches_3>=1`.

6. **Trace/replay identity (7,000 verdict records).**  Run exactly
   `python3 tests/lienard_55.py item6 --manifest prereg/55/manifest.json`.
   Execute the same Family-B sweep once with `EIGS_TRACE=<temporary tape>`,
   then once with `EIGS_REPLAY=<that tape>` and
   `EIGS_REPLAY_STRICT=1`; trace occurrence window is the pinned default 256.
   Compare the 7,000 canonical verdict JSON lines as bytes (not the tape or
   timing text).  Threshold: zero differing bytes.  Success is exit 0 and
   `PASS item6 population=7000 differing_bytes=0`.

7. **Frozen SciPy baseline and “beats.”**  Run exactly
   `python3 tests/lienard_55.py item7 --manifest prereg/55/manifest.json`.
   On the same 117 Instance-A starts, integrate with `solve_ivp(method="DOP853",
   rtol=1e-10, atol=1e-12)`, locate Sigma with a terminal-free event
   `y=0, direction=-1`, and classify after the same 300-time-unit transient:
   `origin` if final Euclidean norm `<1e-6`, `outer` if the median of the final
   100-time-unit crossings is within `1e-6` of the baseline's converged outer
   fixed point, otherwise `miss`.  Exclude `1.50`.  “Beats” means the observer
   has equal or fewer misses than this baseline among the same 116 graded
   starts, while items 1–4 also pass.  The two `1e-6` values belong only to the
   baseline label, never the observer verdict path.  Success is exit 0 and
   `PASS item7 population=117 graded=116 observer_misses<=baseline_misses items1_4=PASS`.

### Observer verdict contract

The observed scalar is assigned as `E=(x*x+y*y)/2` at a fixed **one-time-unit
cadence** (every 100 completed A steps and every 200 completed B steps), not at
every RK micro-step; this makes the 10-sample release window cover 10 time
units rather than an arbitrary integrator-dependent sliver.  At exactly the
final forward step (which is also an observation step), `converged of E` maps to
`origin`, and `oscillating of E` maps to `outer`/settled-cycle.  Every other
predicate outcome—including `stable`, `equilibrium`, `improving`, `moving`,
`diverging`, or no trajectory—is a miss (and `diverging` also increments item
2).  Item 4 is explicit that the observer gates the estimator rather than
manufacturing an amplitude.

This follows the pinned value-channel API: numeric `report` and named
predicates route to the value trajectory, and `report_value` exposes it
directly.  The repo demonstrations assign a binding during warm-up and read
`report_value of x` afterward (`predicate_calibration.eigs:51-72`) and snapshot
the same trajectory in `predicate_fit.eigs:35-58`.  At EigenScript
`4a3a5c1941568e9bc562c7c8221cff22dc8ba697`, the constants are window 10,
minimum 4, maximum 64, `dh_zero=0.001`, `dh_small=0.01`, `h_low=0.1`, and
scale `0.001` (`src/eigenscript.h:609-626`); the value step is
`Delta v/max(|v|,|v_prev|,scale)` (`src/eigenscript.c:671-706`), `converged`
requires a full window (`src/eigenscript.c:1114-1125`), and report priority is
oscillating, diverging, improving, then the rest bands
(`src/eigenscript.c:1168-1189`).  “No hand-set tolerance” means the future
harness adds no constant to that path and does not call any threshold setter;
these release constants are recorded, not tuned.  `set_observer_window` is
used only to state the normal value and inject item 5's named fault.

### Closest calls

* The only gray-grid start is `x0=1.50`; it is `0.870%` above the inner
  section crossing, leaving `1.130` percentage points to the `2%` edge.
* The nearest graded starts are `1.45` (`2.492%` below; `0.492` percentage
  points outside the band) and `1.55` (`4.232%` above; `2.232` points outside).
* The oracle effort levels print the same 12 decimals; the acceptance allowance
  is absolute `1e-9` (three decimal orders looser than the printed agreement).
* The RK4 stability products are `0.1620` for Instance A and `0.62170` for
  Family B, against the pre-registered heuristic ceiling 1.
* Item 4's widest allowed outer-amplitude error is `0.019614369352`; its
  separate discretization call is the tighter `1e-7` comparison.

### Settings

| Setting | Frozen value |
|---|---|
| EigenScript before version | repo pin `v0.46.0`, commit `4a3a5c1941568e9bc562c7c8221cff22dc8ba697`; interpreter forced with `EIGS_JIT_OFF=1` |
| after sequence | EigenScript #1758 round 3 is a follow-up row and is not part of this bar |
| Instance A | `F=x^5/50-x^3/3+x/2`; grid 117, `0.20..6.00` step `0.05`; `(x0,0)` |
| Family B law | `a1~U[-0.5,0.5]`, `a2~U[-0.1,0.1]`, `a3~U[-0.05,0.05]`, `a4~U[-0.005,0.005]`, `a5~U[0.001,0.005]`, independently via `numpy.default_rng(55)`; 350 frozen rows |
| Family B starts | 20, `0.25..5.00` step `0.25`; `(x0,0)` |
| coefficient data | `prereg/55/family_b.csv`; SHA-256 `ada17452ff5fc1b4cba290ee65a62105d09c5c4bee54073d8cfed88ef8017211` |
| RK4, A | fixed `h=0.01`; `T=400` = 40,000 steps; transient `T=300` = 30,000; measurement window `T=100` = 10,000 |
| RK4, B | fixed `h=0.005`; `T=400` = 80,000 steps; transient `T=300` = 60,000; measurement window `T=100` = 20,000 |
| stability derivation, A | asserted visited `|x|<=4.3`; `max|F'|<=16.20`, hence `h max|F'|<=0.1620` |
| stability derivation, B | asserted visited `|x|<=8`; coefficient-range triangle bound `max|F'|<=0.5+1.6+9.6+10.24+102.4=124.34`, hence product `0.62170`; exceeding box fails loudly |
| RK4 convergence | Instance-A outer section `x*` at `h` and `h/2` differs by `<=1e-7` |
| section estimator | linear interpolation of every direction `-1` `y=0,x>0` crossing; final-window median; settled crossings require successive median-half estimates within `1e-7` |
| reverse oracle | reversed vector field, physical Sigma direction `-1`; stop on successive crossings `<1e-12` or ungraded safety box `max(|x|,|y|)>8` |
| forward safety | non-finite state or `max(|x|,|y|)>1e6` is a loud numerical failure, never a `diverging` success |
| clustering | sort estimates; greedily extend a cluster iff resulting complete-link span is `<=0.01`; cluster representative is median; singleton allowed |
| observer | binding `E`; assign every `1.0` time unit (100 A steps, 200 B steps); read final step; origin=`converged`; outer/settled-cycle=`oscillating`; built-ins window 10, thresholds `0.001,0.01,0.1`, scale `0.001` |
| planted fault | scratch specimen changes only window 10 to 4, once |
| trace | `EIGS_TRACE`, then `EIGS_REPLAY` plus `EIGS_REPLAY_STRICT=1`; occurrence window 256; compare canonical verdict lines |
| baseline | SciPy DOP853, `rtol=1e-10`, `atol=1e-12`, event `y=0,x>0,direction=-1`, same grid/time split; classifier tolerance `1e-6` |
| compute budget | measured 257,533 RK4 steps/s; conservative 250,000; 3 B sweeps plus A and `h/2` = 1,684,840,000 steps = 6,739.36 s = 1.872 CPU-h |
| companion networks | moved to its own future issue/pre-registration; no network population or planted reaction is in items 1–7 |
