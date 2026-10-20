#!/usr/bin/env python3
"""Freeze per-row SciPy-oracle settled counts used by item 3's coverage gate."""
from __future__ import annotations
import csv, hashlib
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from multiprocessing import Pool

HERE=Path(__file__).parent
RTOL, ATOL = 1e-10, 1e-12

def one(x0, c, reverse, bx, by):
    sign=-1 if reverse else 1
    def fun(t,z):
        x,y=z; f=sum(c[i]*x**(i+1) for i in range(5))
        return sign*np.array((y-f,-x))
    def section(t,z): return z[1]
    section.direction=1 if reverse else -1
    def escape(t,z): return min(bx-abs(z[0]),by-abs(z[1]))
    escape.direction=-1; escape.terminal=True
    sol=solve_ivp(fun,(0,300),(x0,0),method='DOP853',rtol=RTOL,atol=ATOL,
                  max_step=.5,events=(section,escape))
    if len(sol.t_events[1]): return False
    xs=sol.y_events[0][:,0]; ts=sol.t_events[0]
    xs=xs[(ts>=200)&(xs>0)]
    if len(xs)<4: return False
    cut=len(xs)//2
    return abs(float(np.median(xs[:cut]))-float(np.median(xs[cut:]))) <= 1e-7

def unpack(args): return one(*args)

def main():
    raw=np.genfromtxt(HERE/'family_b.csv',delimiter=',',names=True)
    env=np.genfromtxt(HERE/'evidence/bar-rewrite-55-fix/family_b_envelope.csv',delimiter=',',names=True)
    out=HERE/'evidence/bar-rewrite-55-fix2/oracle_settled.csv'; out.parent.mkdir(parents=True,exist_ok=True)
    jobs=[]
    for i,r in enumerate(raw):
        c=np.array([r[f'a{j}'] for j in range(1,6)])
        for reverse in (False,True):
            for x in np.arange(.25,5.01,.25): jobs.append((x,c,reverse,env['box_x'][i],env['box_y'][i]))
    with Pool() as pool: answers=pool.map(unpack,jobs)
    rows=[]
    for i in range(len(raw)):
        q=answers[i*40:(i+1)*40]; counts=(sum(q[:20]),sum(q[20:]))
        rows.append((i,*counts)); print(f"row={i} forward={counts[0]} reverse={counts[1]}")
    with out.open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n'); w.writerow(('id','forward_oracle_settled','reverse_oracle_settled')); w.writerows(rows)
    digest=hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"rows={len(rows)} forward_total={sum(r[1] for r in rows)} reverse_total={sum(r[2] for r in rows)}")
    print(f"sha256={digest} file={out.relative_to(HERE.parent.parent)}")
if __name__=='__main__': main()
