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

The cycle-count oracle is **only** the Lean-checked general comparator from
`openai/math` family 143, not Rychkov 1975 (which assumes odd `F` and therefore
does not cover Family B's nonzero even coefficients).  The fetched artifact is
`lean/ComparatorChallenges/QuinticLienard.lean` at commit
`1581d4cbdd69a0faf34b2089614fe2a814316a6a`, URL
`https://raw.githubusercontent.com/openai/math/1581d4cbdd69a0faf34b2089614fe2a814316a6a/lean/ComparatorChallenges/QuinticLienard.lean`, SHA-256
`cb34f454db432f46902a17036812adde4c73fe276d6d7a8a8b21797ace40d000`.
Its exact theorem (and its only hypothesis, `F.degree ≤ 5`) is:

```lean
theorem main :
    (∀ F : Polynomial ℝ, F.degree ≤ 5 → {C : Set Plane | IsLimitCycle F C}.encard ≤ 2) ∧
    (∃ F : Polynomial ℝ, F.degree ≤ 5 ∧ {C : Set Plane | IsLimitCycle F C}.encard = 2) := by
```

Here `vectorField F z := (z.2 - F.eval z.1, -z.1)` and `IsLimitCycle` means an
isolated set-range of a nonconstant periodic global solution, exactly as quoted
in the vendored evidence.  Thus every frozen Family-B quintic is covered; there
are no sign, parity, hyperbolicity, or amplitude hypotheses.

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

2. **No false forward divergence (3,317 runs).**  Run exactly
   `python3 tests/lienard_55.py item2 --manifest prereg/55/manifest.json`.
   Across the 117 Instance-A starts and all `160*20=3,200` Family-B
   coefficient/start pairs, the verdict read at the final forward step must
   never be `diverging`.  Threshold: 0.  Reverse-time oracle runs and the
   separately scoped reaction-network controls are excluded by name.  Success
   is exit 0 and `PASS item2 population=3317 diverging=0`.

3. **The theorem-backed cycle-count oracle (160 systems).**  Run exactly
   `python3 tests/lienard_55.py item3 --manifest prereg/55/manifest.json`.
   For every row of `family_b.csv`, run the 20-point grid both forward and under the reversed vector field, retain only runs
   whose observer gate says settled-cycle as defined below, estimate section
   fixed points from the final window, and apply the frozen complete-link
   clustering rule.  The distinct cluster count must be `<=2` for every
   system; threshold: zero systems reaching 3.  Merge the forward and reverse
   estimates before clustering: a forward cluster and reverse cluster whose
   union has complete-link span `<=0.01` is one semi-stable-cycle candidate,
   never two cycles.  Success is exit 0 and
   `PASS item3 population=160 starts=3200 directions=2 runs=6400 max_clusters<=2 reaches_3=0`.

4. **Outer section amplitude (one orbit, observer only gates).**  Run exactly
   `python3 tests/lienard_55.py item4 --manifest prereg/55/manifest.json`.
   Start Instance A at `(4,0)`.  The observer does **not** derive amplitude:
   it only supplies the `oscillating of E` settled-cycle gate.  The harness's
   cubic-Hermite event-located Sigma crossings supply `x*`.  Their final-window
   median must be within `0.5%` (`0.019614369352` absolute) of
   `3.922873870354`; additionally the estimates at `h=0.01` and `h=0.005`
   must differ by `<=1e-7`.  Success is exit 0 and
   `PASS item4 oracle=3.922873870354 rel_error<=0.005 h_delta<=1e-7`.

5. **One planted-window control.**  Run exactly
   `python3 tests/lienard_55.py item5 --manifest prereg/55/manifest.json`.
   Clone the pinned runtime to a disposable directory, apply exactly
   `sed -i 's/^#define OBSERVER_WINDOW_N 10$/#define OBSERVER_WINDOW_N 4/' src/eigenscript.h`,
   and build exactly `make -C "$scratch" gfx CC=gcc`.  Run item 3 once using
   that rebuilt binary; never edit the committed source or the normal pinned
   installation.  Normal depth is 10 and fault depth is 4.  The control passes
   only after a **completed** item-3 run prints `reaches_3>=1`.  A crash,
   refusal, undefined-name error, nonzero run without that record, or any
   incomplete run fails item 5; no expected failure is converted to success.
   Output contract:
   `PASS item5 normal_window=10 fault_window=4 item3_exit=1 reaches_3>=1`.

6. **Trace/replay identity (3,200 verdict records).**  Run exactly
   `python3 tests/lienard_55.py item6 --manifest prereg/55/manifest.json`.
   Execute the same Family-B sweep once with `EIGS_TRACE=<temporary tape>`,
   then once with `EIGS_REPLAY=<that tape>` and
   `EIGS_REPLAY_STRICT=1`; trace occurrence window is the pinned default 256.
   Compare the 3,200 canonical verdict JSON lines as bytes (not the tape or
   timing text).  Threshold: zero differing bytes.  Success is exit 0 and
   `PASS item6 population=3200 differing_bytes=0`.

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
final step (which is also an observation step), `converged of E` maps to
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
these release constants are recorded, not tuned.  Item 5 changes the compile-
time constant in a disposable rebuild because no runtime builtin exists at
the pin.

### Closest calls

* The only gray-grid start is `x0=1.50`; it is `0.870%` above the inner
  section crossing, leaving `1.130` percentage points to the `2%` edge.
* The nearest graded starts are `1.45` (`2.492%` below; `0.492` percentage
  points outside the band) and `1.55` (`4.232%` above; `2.232` points outside).
* The oracle effort levels print the same 12 decimals; the acceptance allowance
  is absolute `1e-9` (three decimal orders looser than the printed agreement).
* The RK4 stability products are `0.1620` for Instance A and at most
  `0.252789708` across the resized Family B per-row boxes, against the
  pre-registered heuristic ceiling 1.
* Item 4's widest allowed outer-amplitude error is `0.019614369352`; its
  separate discretization call is the tighter `1e-7` comparison.

### Settings

| Setting | Frozen value |
|---|---|
| EigenScript before version | repo pin `v0.46.0`, commit `4a3a5c1941568e9bc562c7c8221cff22dc8ba697`; interpreter forced with `EIGS_JIT_OFF=1` |
| after sequence | EigenScript #1758 round 3 is a follow-up row and is not part of this bar |
| Instance A | `F=x^5/50-x^3/3+x/2`; grid 117, `0.20..6.00` step `0.05`; `(x0,0)` |
| Family B law | `a1~U[-0.5,0.5]`, `a2~U[-0.1,0.1]`, `a3~U[-0.05,0.05]`, `a4~U[-0.005,0.005]`, `a5~U[0.001,0.005]`, independently via `numpy.default_rng(55)`; 160 frozen rows |
| Family B starts | 20, `0.25..5.00` step `0.25`; `(x0,0)` |
| coefficient data | `prereg/55/family_b.csv`; SHA-256 `aeda5368669b07a926535bfece612d9543b7d6c9b2cd19d647d69fd59e729eff` |
| RK4, A | fixed `h=0.01`; `T=400` = 40,000 steps; transient `T=300` = 30,000; measurement window `T=100` = 10,000 |
| RK4, B | fixed `h=0.005`; `T=400` = 80,000 steps; transient `T=300` = 60,000; measurement window `T=100` = 20,000 |
| stability derivation, A | asserted visited `|x|<=4.3`; `max|F'|<=16.20`, hence `h max|F'|<=0.1620` |
| stability derivation, B | per-row 10%-margin boxes frozen in `evidence/bar-rewrite-55-fix/family_b_envelope.csv` (SHA-256 `735a329e1019786e2851c96b429e3f6e128622353c86efe0e4eba6bdc1652e6d`); per-row triangle maxima of `|F'|` give a worst product below 1; exceeding the applicable box fails loudly |
| RK4 convergence | Instance-A outer section `x*` at `h` and `h/2` differs by `<=1e-7` |
| section estimator | cubic Hermite interpolation for every Sigma estimate in items 3, 4, and item 7's observer side: `H(s)=(2s^3-3s^2+1)z0+(s^3-2s^2+s)h f(z0)+(-2s^3+3s^2)z1+(s^3-s^2)h f(z1)`; bisect `H_y(s)=0` on `s in [0,1]` for the direction-appropriate sign change, then require `H_x(s)>0`; final-window median; successive median halves within `1e-7` |
| reverse oracle | reversed vector field (so its event direction is `+1`, representing physical Sigma direction `-1`); observer-gated exactly as forward; reject an escaping run at its per-row 10%-margin `(abs(x),abs(y))` safety box |
| forward safety | non-finite state or `max(|x|,|y|)>1e6` is a loud numerical failure, never a `diverging` success |
| clustering | sort estimates; greedily extend a cluster iff resulting complete-link span is `<=0.01`; cluster representative is median; singleton allowed |
| observer | binding `E`; assign every `1.0` time unit (100 A steps, 200 B steps); read final step; origin=`converged`; outer/settled-cycle=`oscillating`; built-ins window 10, thresholds `0.001,0.01,0.1`, scale `0.001` |
| planted fault | scratch rebuild changes only `#define OBSERVER_WINDOW_N 10` to `4`, once; completed item 3 must report `reaches_3>=1` |
| trace | `EIGS_TRACE`, then `EIGS_REPLAY` plus `EIGS_REPLAY_STRICT=1`; occurrence window 256; compare canonical verdict lines |
| baseline | SciPy DOP853, `rtol=1e-10`, `atol=1e-12`, event `y=0,x>0,direction=-1`, same grid/time split; classifier tolerance `1e-6` |
| compute budget | conservative 250,000 RK4 steps/s; 7 B sweep-equivalents plus A and `h/2` = 1,796,840,000 steps = 7,187.36 s = 1.996 CPU-h; `N=160` is the largest integer fitting 2 h |
| companion networks | moved to its own future issue/pre-registration; no network population or planted reaction is in items 1–7 |
