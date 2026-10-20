# Fix-round-2 evidence

Verbatim outputs were captured with:

```sh
python3 prereg/55/oracle.py --rtol 1e-12
python3 prereg/55/oracle.py --rtol 1e-13
python3 prereg/55/oracle_settled.py
python3 prereg/55/instance_a_envelope.py
```

`step-rate.txt` records the exact binary/workload hashes, invocation, clock,
repetitions, selected statistic, CPU, and all five results. `coverage-floor.txt`
records the pre-registered derivation. `oracle-settled-output.txt` is the
verbatim progress/summary output; `oracle_settled.csv` is the committed table.
