#!/usr/bin/env python3
"""Issue 59 successor oracle-settled rule and frozen denominator generator."""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN_PATH = ROOT / "prereg/55/oracle_settled.py"
_spec = importlib.util.spec_from_file_location("issue55_frozen_oracle_settled", FROZEN_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"cannot load frozen rule: {FROZEN_PATH}")
_frozen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_frozen)

ORIGIN_CROSSING_FLOOR = 1e-6
RTOL, ATOL = _frozen.RTOL, _frozen.ATOL


def window_crossings(x0, c, reverse, bx, by):
    """Return positive-x Sigma crossings in the frozen [200, 300] window."""
    sign = -1 if reverse else 1

    def fun(t, z):
        x, y = z
        f = sum(c[i] * x ** (i + 1) for i in range(5))
        return sign * np.array((y - f, -x))

    def section(t, z):
        return z[1]

    section.direction = 1 if reverse else -1

    def escape(t, z):
        return min(bx - abs(z[0]), by - abs(z[1]))

    escape.direction = -1
    escape.terminal = True
    sol = solve_ivp(
        fun, (0, 300), (x0, 0), method="DOP853", rtol=RTOL, atol=ATOL,
        max_step=.5, events=(section, escape)
    )
    if len(sol.t_events[1]):
        return np.array([], dtype=float)
    xs = sol.y_events[0][:, 0]
    ts = sol.t_events[0]
    return xs[(ts >= 200) & (xs > 0)]


def one(x0, c, reverse, bx, by, origin_test=True):
    """Wrap issue 55's frozen rule, optionally excluding origin decay.

    The frozen decision is always evaluated first and is returned verbatim when
    ``origin_test`` is false.  With the correction enabled, every positive-x
    crossing in the settledness window must be at least 1e-6.
    """
    captured = []
    original_solve_ivp = _frozen.solve_ivp

    def capture_solve_ivp(*args, **kwargs):
        solution = original_solve_ivp(*args, **kwargs)
        captured.append(solution)
        return solution

    # The imported function remains byte-for-byte unchanged.  Intercepting its
    # solver call lets the wrapper inspect that same trajectory, avoiding a
    # second integration and any possibility of numerical disagreement.
    _frozen.solve_ivp = capture_solve_ivp
    try:
        settled = _frozen.one(x0, c, reverse, bx, by)
    finally:
        _frozen.solve_ivp = original_solve_ivp
    if not settled or not origin_test:
        return settled
    solution = captured[0]
    xs = solution.y_events[0][:, 0]
    ts = solution.t_events[0]
    xs = xs[(ts >= 200) & (xs > 0)]
    return bool(len(xs) and float(np.min(xs)) >= ORIGIN_CROSSING_FLOOR)


def unpack(args):
    return one(*args)


def jobs_and_rows():
    raw = np.genfromtxt(ROOT / "prereg/55/family_b.csv", delimiter=",", names=True)
    env = np.genfromtxt(
        ROOT / "prereg/55/evidence/bar-rewrite-55-fix/family_b_envelope.csv",
        delimiter=",", names=True
    )
    jobs = []
    for i, row in enumerate(raw):
        c = np.array([row[f"a{j}"] for j in range(1, 6)])
        for reverse in (False, True):
            for x0 in np.arange(.25, 5.01, .25):
                jobs.append((x0, c, reverse, env["box_x"][i], env["box_y"][i]))
    return raw, jobs


def generate(origin_test=True):
    raw, jobs = jobs_and_rows()
    with Pool() as pool:
        answers = pool.starmap(one, (job + (origin_test,) for job in jobs))
    rows = []
    for i in range(len(raw)):
        q = answers[i * 40:(i + 1) * 40]
        counts = (sum(q[:20]), sum(q[20:]))
        rows.append((i, *counts))
        print(f"row={i} forward={counts[0]} reverse={counts[1]}")
    return rows


def write_rows(rows, output):
    with output.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(("id", "forward_oracle_settled", "reverse_oracle_settled"))
        writer.writerows(rows)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print(f"rows={len(rows)} forward_total={sum(r[1] for r in rows)} reverse_total={sum(r[2] for r in rows)}")
    print(f"sha256={digest} file={output.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--disable-origin-test", action="store_true")
    parser.add_argument("--output", type=Path, default=HERE / "evidence/oracle_settled.csv")
    args = parser.parse_args()
    rows = generate(not args.disable_origin_test)
    write_rows(rows, args.output)


if __name__ == "__main__":
    main()
