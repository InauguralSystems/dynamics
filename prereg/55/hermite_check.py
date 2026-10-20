#!/usr/bin/env python3
"""Reproduce the pre-registered linear/Hermite section convergence check."""
import numpy as np


def rhs(z):
    x, y = z
    return np.array((y - (x**5/50 - x**3/3 + x/2), -x))


def crossing(z0, z1, f0, f1, h, hermite):
    if not hermite:
        s = -z0[1] / (z1[1] - z0[1])
        return z0[0] + s * (z1[0] - z0[0])
    def H(s):
        return ((2*s**3-3*s**2+1)*z0 + (s**3-2*s**2+s)*h*f0
                + (-2*s**3+3*s**2)*z1 + (s**3-s**2)*h*f1)
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if H(mid)[1] > 0: lo = mid
        else: hi = mid
    return H((lo + hi) / 2)[0]


def run(h, hermite):
    z = np.array((4.0, 0.0)); xs = []
    for i in range(round(400/h)):
        f0 = rhs(z); k2 = rhs(z+h*f0/2); k3 = rhs(z+h*k2/2); k4 = rhs(z+h*k3)
        zn = z + h*(f0+2*k2+2*k3+k4)/6
        if (i+1)*h >= 300 and z[1] > 0 >= zn[1]:
            q = crossing(z, zn, f0, rhs(zn), h, hermite)
            if q > 0: xs.append(q)
        z = zn
    return float(np.median(xs))


for kind in (False, True):
    a, b = run(.01, kind), run(.005, kind)
    print(f"method={'hermite' if kind else 'linear'} h=.01 {a:.12f} h=.005 {b:.12f} delta={abs(a-b):.12g}")
