#!/usr/bin/env python3
"""Independently re-derive the section-fixed-point controls for issue 55."""
from __future__ import annotations

import argparse
from scipy.integrate import solve_ivp


def rhs(_t, z, reverse=False, system="instance-a"):
    x, y = z
    f = (x**5 / 50.0 - x**3 / 3.0 + x / 2.0
         if system == "instance-a" else x**3 / 3.0 - x)
    q = (y - f, -x)
    return (-q[0], -q[1]) if reverse else q


def return_map(x0: float, reverse: bool, rtol: float, system: str) -> float:
    # Move off Sigma before arming the terminal event, so t=0 is not returned.
    kick = solve_ivp(lambda t, z: rhs(t, z, reverse, system), (0.0, 1e-6), (x0, 0.0),
                     method="DOP853", rtol=rtol, atol=rtol * 1e-2)

    def section(_t, z):
        return z[1]
    section.direction = 1 if reverse else -1
    section.terminal = True
    sol = solve_ivp(lambda t, z: rhs(t, z, reverse, system), (1e-6, 30.0), kick.y[:, -1],
                    method="DOP853", rtol=rtol, atol=rtol * 1e-2,
                    events=section, max_step=0.05)
    if len(sol.t_events[0]) != 1 or sol.y_events[0][0, 0] <= 0:
        raise RuntimeError("positive-x decreasing-y section was not reached")
    return float(sol.y_events[0][0, 0])


def fixed_point(seed: float, reverse: bool, rtol: float, system="instance-a"):
    old = seed
    for iterations in range(1, 10000):
        new = return_map(old, reverse, rtol, system)
        delta = abs(new - old)
        if delta < 1e-12:
            return new, iterations, delta
        old = new
    raise RuntimeError("return-map iteration did not converge")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtol", type=float, choices=(1e-12, 1e-13), required=True)
    args = ap.parse_args()
    inner = fixed_point(1.5, True, args.rtol)
    outer = fixed_point(4.0, False, args.rtol)
    vdp = fixed_point(2.0, False, args.rtol, "van-der-pol")
    print(f"method=DOP853 rtol={args.rtol:.0e} atol={args.rtol*1e-2:.0e} event=y direction=physical--1")
    print(f"inner={inner[0]:.12f} iterations={inner[1]} final_delta={inner[2]:.3e} mode=reverse")
    print(f"outer={outer[0]:.12f} iterations={outer[1]} final_delta={outer[2]:.3e} mode=forward")
    print(f"vanderpol={vdp[0]:.12f} iterations={vdp[1]} final_delta={vdp[2]:.3e} mode=forward F=x^3/3-x")


if __name__ == "__main__":
    main()
