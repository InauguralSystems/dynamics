# Fix-round evidence

All outputs in this directory were captured before implementation or observer
experiment runs; these are oracle integrations and arithmetic only.

* `hermite-output.txt`: `python3 prereg/55/hermite_check.py`
* `family_b_envelope.csv` and `envelope-output.txt`: `python3 prereg/55/envelope.py`
* `envelope-sha256.txt`: `sha256sum prereg/55/evidence/bar-rewrite-55-fix/family_b_envelope.csv`
* `orchestrator-original-envelope.txt`: the supplied 350-row defect-reproduction output.
* `theorem-fetch.txt` and `QuinticLienard.lean`: exact fetch command, identity, and statement.
* `compute-output.txt`: `python3 prereg/55/grid_and_budget.py`
* `item5-build.txt`: exact source patch and scratch build command.
* `removed-builtin-grep.txt`: absence check over the two normative contract files.
