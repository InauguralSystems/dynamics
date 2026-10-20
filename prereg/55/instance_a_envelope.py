#!/usr/bin/env python3
"""Integrate every Instance-A grid start and freeze its visited envelope."""
import numpy as np

H, STEPS = .01, 40_000

def field(x, y):
    return y-(x**5/50-x**3/3+x/2), -x

def advance(x, y, sign=1):
    k1x,k1y=field(x,y); k2x,k2y=field(x+sign*H*k1x/2,y+sign*H*k1y/2)
    k3x,k3y=field(x+sign*H*k2x/2,y+sign*H*k2y/2); k4x,k4y=field(x+sign*H*k3x,y+sign*H*k3y)
    return x+sign*H*(k1x+2*k2x+2*k3x+k4x)/6, y+sign*H*(k1y+2*k2y+2*k3y+k4y)/6

def main():
    starts=np.arange(.2,6.001,.05); x=starts.copy(); y=np.zeros_like(x); mx=np.abs(x); my=np.abs(y)
    for _ in range(STEPS):
        x,y=advance(x,y); mx=np.maximum(mx,abs(x)); my=np.maximum(my,abs(y))
    fx,fy=mx.max(),my.max(); bx=np.ceil(fx*1000)/1000; by=np.ceil(fy*1000)/1000
    x=starts.copy(); y=np.zeros_like(x); mx=np.abs(x); my=np.abs(y); active=np.ones(len(x),bool)
    for _ in range(STEPS):
        nx,ny=advance(x,y,-1); keep=active&(abs(nx)<=bx)&(abs(ny)<=by)&np.isfinite(nx)&np.isfinite(ny)
        x[keep]=nx[keep]; y[keep]=ny[keep]; mx[keep]=np.maximum(mx[keep],abs(x[keep])); my[keep]=np.maximum(my[keep],abs(y[keep])); active &= keep
        if not active.any(): break
    # F'=.1*x^4-x^2+.5.  On this symmetric interval its absolute maximum
    # occurs at an endpoint (the interior critical values are .5 and -2).
    derivative=max(abs(.1*bx**4-bx**2+.5),2.0)
    print(f"starts={len(starts)} steps={STEPS} directions=forward,reverse")
    print(f"forward_max_abs_x={fx:.12f} forward_max_abs_y={fy:.12f}")
    print(f"outward_rounding=0.001 box_x={bx:.3f} box_y={by:.3f}")
    print(f"reverse_completed={active.sum()} reverse_safety_stops={(~active).sum()} reverse_max_abs_x={mx.max():.12f} reverse_max_abs_y={my.max():.12f}")
    print(f"exact_max_abs_Fprime={derivative:.12f} h={H} stability_product={H*derivative:.12f}")
if __name__ == '__main__': main()
