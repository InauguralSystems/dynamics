#!/usr/bin/env python3
"""Reproduce the frozen Family-B forward oracle envelope and stability table."""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
H = 0.005
STEPS = 80_000


def field(x, y, c):
    a1, a2, a3, a4, a5 = c.T
    return y - (a1*x + a2*x**2 + a3*x**3 + a4*x**4 + a5*x**5), -x


def main() -> None:
    raw = np.genfromtxt(HERE / "family_b.csv", delimiter=",", names=True)
    coeff = np.column_stack([raw[f"a{i}"] for i in range(1, 6)])
    coeff = np.repeat(coeff, 20, axis=0)
    x = np.tile(np.arange(0.25, 5.01, 0.25), len(raw))
    y = np.zeros_like(x)
    rmx, rmy = np.abs(x), np.abs(y)
    mx, my = np.abs(x), np.abs(y)
    for _ in range(STEPS):
        k1x, k1y = field(x, y, coeff)
        k2x, k2y = field(x+H*k1x/2, y+H*k1y/2, coeff)
        k3x, k3y = field(x+H*k2x/2, y+H*k2y/2, coeff)
        k4x, k4y = field(x+H*k3x, y+H*k3y, coeff)
        x += H*(k1x+2*k2x+2*k3x+k4x)/6
        y += H*(k1y+2*k2y+2*k3y+k4y)/6
        mx = np.maximum(mx, np.abs(x)); my = np.maximum(my, np.abs(y))
    mx = mx.reshape(-1, 20).max(axis=1)
    my = my.reshape(-1, 20).max(axis=1)
    # Ten-percent outward margin, rounded upward to 0.001, is frozen per row.
    bx = np.ceil(mx * 1100) / 1000
    by = np.ceil(my * 1100) / 1000
    # Exercise every reverse start as well.  An anti-dissipative trajectory is
    # stopped immediately before it leaves the per-row box; that is a normal
    # rejected run, not part of the bounded-cycle envelope.
    x = np.tile(np.arange(0.25, 5.01, 0.25), len(raw))
    y = np.zeros_like(x)
    active = np.ones_like(x, dtype=bool)
    completed = np.zeros_like(x, dtype=bool)
    rbx = np.repeat(bx, 20); rby = np.repeat(by, 20)
    for _ in range(STEPS):
        if not active.any():
            break
        k1x, k1y = field(x, y, coeff)
        k2x, k2y = field(x-H*k1x/2, y-H*k1y/2, coeff)
        k3x, k3y = field(x-H*k2x/2, y-H*k2y/2, coeff)
        k4x, k4y = field(x-H*k3x, y-H*k3y, coeff)
        nx = x - H*(k1x+2*k2x+2*k3x+k4x)/6
        ny = y - H*(k1y+2*k2y+2*k3y+k4y)/6
        keep = active & (np.abs(nx) <= rbx) & (np.abs(ny) <= rby) & np.isfinite(nx) & np.isfinite(ny)
        x[keep], y[keep] = nx[keep], ny[keep]
        rmx[keep] = np.maximum(rmx[keep], np.abs(x[keep]))
        rmy[keep] = np.maximum(rmy[keep], np.abs(y[keep]))
        active &= keep
    completed[active] = True
    rmx = rmx.reshape(-1, 20).max(axis=1)
    rmy = rmy.reshape(-1, 20).max(axis=1)
    powers = np.column_stack([np.ones(len(bx)), 2*bx, 3*bx**2,
                              4*bx**3, 5*bx**4])
    derivative = (np.abs(np.column_stack([raw[f"a{i}"] for i in range(1, 6)])) * powers).sum(axis=1)
    out = HERE / "evidence/bar-rewrite-55-fix/family_b_envelope.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(("id", "forward_max_abs_x", "forward_max_abs_y",
                    "reverse_max_abs_x", "reverse_max_abs_y", "box_x",
                    "box_y", "max_abs_Fprime", "h_times_max_abs_Fprime"))
        for i in range(len(raw)):
            w.writerow((i, *(f"{v:.9f}" for v in (mx[i], my[i], rmx[i],
                                                   rmy[i], bx[i], by[i],
                                                   derivative[i], H*derivative[i]))))
    print(f"rows={len(raw)} starts_per_row=20 directions=forward,reverse reverse_completed={completed.sum()} reverse_safety_stops={(~completed).sum()}")
    print(f"max_abs_x={mx.max():.9f} row={mx.argmax()} max_abs_y={my.max():.9f} row={my.argmax()}")
    print(f"margin=10% max_box_x={bx.max():.3f} max_box_y={by.max():.3f}")
    print(f"max_stability_product={max(H*derivative):.9f} row={(H*derivative).argmax()} all_le_1={bool(np.all(H*derivative <= 1))}")


if __name__ == "__main__":
    main()
