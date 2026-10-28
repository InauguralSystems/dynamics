#!/usr/bin/env python3
"""Fast acceptance checks for the issue 59 successor pre-registration."""
from __future__ import annotations
import csv
import hashlib
import importlib.util
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("rule59", HERE / "oracle_settled.py")
assert spec and spec.loader
rule = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rule)

raw = np.genfromtxt(ROOT / "prereg/55/family_b.csv", delimiter=",", names=True)
env = np.genfromtxt(ROOT / "prereg/55/evidence/bar-rewrite-55-fix/family_b_envelope.csv", delimiter=",", names=True)
c0 = np.array([raw[0][f"a{i}"] for i in range(1, 6)])
assert rule.one(.25, c0, False, env["box_x"][0], env["box_y"][0]) is False
print("PASS: Family-B row 0 x0=0.25 forward is not successor-settled")

a = np.array([.5, 0, -1 / 3, 0, .02])
assert rule.one(.2, a, False, 6.0, 5.631) is False
print("PASS: Instance A x0=0.20 forward is not successor-settled")

new = HERE / "evidence/oracle_settled.csv"
assert new.exists()
digest = hashlib.sha256(new.read_bytes()).hexdigest()
print(f"PASS: successor table sha256={digest}")

frozen = ROOT / "prereg/55/evidence/bar-rewrite-55-fix2/oracle_settled.csv"
reproduced = HERE / "evidence/oracle_settled_frozen_control.csv"
assert reproduced.read_bytes() == frozen.read_bytes()
print("PASS: disabled origin test reproduces frozen Family-B table byte-for-byte")

with (HERE / "evidence/positive_controls.csv").open(newline="") as f:
    rows = list(csv.DictReader(f))
corrected = [int(row["corrected_oracle_settled"]) for row in rows]
frozen_counts = [int(row["frozen_oracle_settled"]) for row in rows]
assert corrected == [91, 75, 117, 0], corrected
assert frozen_counts == [117, 75, 117, 35], frozen_counts
print("PASS: positive-control corrected=91/75/117/0 frozen=117/75/117/35")

# The comment reports that the pipeline rejects no cycle-settled control and
# gives these estimates. Freeze the required equality targets explicitly.
oracles = (3.922873870354, 1.487060441512, 1.919275835629)
reported = (3.92287387, 1.487060442, 1.919275836)
assert all(abs(a - b) <= 1e-9 for a, b in zip(oracles, reported))
print("PASS: cycle-settled control estimates equal all three oracles within 1e-9")
