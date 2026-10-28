# Generated successor evidence

`oracle_settled.csv` and `oracle-settled-output.txt` were generated with
`python3 prereg/59/oracle_settled.py`. `positive_controls.csv` and its output
were generated with `python3 prereg/59/positive_controls.py`.

`oracle_settled_frozen_control.csv` is the byte-identical frozen issue 55 table.
The wrapper's `origin_test=False` path returns the imported frozen decision
verbatim; the positive-control generator evaluates that path over all controls,
and `check.py` compares the Family-B control table byte-for-byte. The frozen
SHA-256 is `4f0ecb1b4b0a0c9f25a9226e5e313006fbfdb7ed27b99e8b4095ecf0522e7bc7`.

The measured 15.486-order empty gap in `threshold-gap.txt` separates the known
origin-decayed diagnostic (maximum crossing below `4.86e-16`) from the smallest
registered control cycle (`1.487...`). The pre-registered `1e-6` floor is more
than nine orders above the former and more than six below the latter.
