#!/usr/bin/env python3
"""Generate issue 59 corrected and attribution-control denominators."""
from __future__ import annotations
import csv
import importlib.util
from multiprocessing import Pool
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("successor_rule", HERE / "oracle_settled.py")
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load successor rule")
rule = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rule)

CONTROLS = (
    ("instance_a", np.array([.5, 0, -1 / 3, 0, .02]), 6.0, 5.631),
    ("van_der_pol", np.array([-1, 0, 1 / 3, 0, 0]), 1e6, 1e6),
)


def decisions(args):
    x, coefficients, reverse, bx, by = args
    return (
        rule.one(x, coefficients, reverse, bx, by),
        rule.one(x, coefficients, reverse, bx, by, False),
    )


def main():
    rows = []
    starts = np.arange(.2, 6.001, .05)
    for name, coefficients, bx, by in CONTROLS:
        for reverse in (False, True):
            jobs = [(x, coefficients, reverse, bx, by) for x in starts]
            with Pool() as pool:
                values = pool.map(decisions, jobs)
            corrected = sum(value[0] for value in values)
            frozen = sum(value[1] for value in values)
            direction = "reverse" if reverse else "forward"
            rows.append((name, direction, corrected, frozen))
            print(f"control={name} direction={direction} corrected={corrected} frozen={frozen}")
    output = HERE / "evidence/positive_controls.csv"
    with output.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(("control", "direction", "corrected_oracle_settled", "frozen_oracle_settled"))
        writer.writerows(rows)


if __name__ == "__main__":
    main()
