# Issue 59 successor pre-registration

This successor is frozen **before** any successor item 3 run. It changes only
item 3's oracle-settled population; all other definitions, numerical settings,
controls, retention floors, clustering, oracles, and acceptance rules remain
those in `prereg/55/`. The banked issue 55 outcome and every file under
`prereg/55/` remain untouched.

## Corrected settledness rule

`oracle_settled.py::one` imports and calls the unchanged
`prereg/55/oracle_settled.py::one`. A start is successor-oracle-settled exactly
when the frozen function returns true **and** every positive-x Sigma crossing
in the frozen `[200,300]` window has `x* >= 1e-6`. Box escape continues to
return false. The added measurable condition excludes decay to the stable
origin rather than mistaking repeated numerical-noise crossings near zero for
a settled limit cycle.

The threshold is deliberately inside an empty empirical gap. For the reported Family-B origin-decay diagnostic and the smallest registered
positive-control cycle, the two bounding crossing amplitudes are recorded in
the evidence. Their ratio and
base-10 order gap are recorded; `1e-6` lies between them by a wide margin.
The rule is not to be retuned after successor item 3 data exist.

## Frozen populations

The Family-B starts, coefficients, directions, envelopes, SciPy method and
accuracy are inherited unchanged from issue 55. Run:

```sh
python3 prereg/59/oracle_settled.py
```

The generated `evidence/oracle_settled.csv` and its SHA-256 below are the
successor coverage denominators. The per-row/direction retention requirement
remains `ceil(0.90 * corrected_oracle_settled)` when the denominator is nonzero.

The same rule was applied to every positive-control start `0.20..6.00` by
`0.05`, in both directions, using Instance A's registered `(6.000,5.631)` box
and van der Pol's `1e6` box. `evidence/positive_controls.csv` freezes those
retention denominators. The required retention remains 100%. Retained cycle
estimates must still equal the registered oracles within `1e-9`:

* Instance A forward outer: `3.922873870354`;
* Instance A reverse inner: `1.487060441512`;
* van der Pol forward: `1.919275835629`.

The control starts that decay to the origin are not denominator members.
So van der Pol REVERSE has an empty denominator: all 35 of its frozen-rule
oracle-settled runs decay to the origin, and 0 remain. That direction is an
empty control and gives no positive evidence; the positive controls cover
three of the four control directions (Instance A forward and reverse, van der
Pol forward). The counts are in `evidence/positive_controls.csv`.
Specifically, Instance A `x0=0.20` forward and Family-B row 0 `x0=0.25`
forward must both return false.

## Attribution and sequencing

Passing `origin_test=False` to the wrapper returns the frozen function's result
verbatim without evaluating the new amplitude floor. Its regenerated Family-B
CSV must be byte-identical to issue 55's frozen CSV, and its positive-control
counts must be exactly the comment's frozen `117/75/117/35`. Thus every
successor denominator change is attributable to the single origin criterion.

No successor item 3 may run until this document, scripts, tables, hashes and
checks are committed. This pre-registration does **not** run item 3.
