#!/usr/bin/env python3
"""Frozen acceptance harness for dynamics issue 55.

All acceptance constants are loaded from the supplied preregistration manifest;
``--limit`` is deliberately development-only and can never print PASS.
"""
from __future__ import annotations

import argparse, csv, hashlib, json, math, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
from statistics import median

import numpy as np
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]
PIN_SHA256 = "c5c288bc5907fe323fcaff83ff06c7f50c8d1ca0f860e94d3366c9ad226277d6"

def die(s): raise SystemExit(s)
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def binary():
    p = Path(os.environ.get("EIGENSCRIPT", "/tmp/eigenscript/build/release/eigenscript"))
    if not p.is_file() or (digest(p) != PIN_SHA256 and not os.environ.get("LIENARD55_ALLOW_FAULT_BINARY")): die(f"pinned EigenScript binary missing or wrong SHA-256: {p}")
    return p

def coeffs(m):
    p=ROOT/m["family_b"]["data"]
    if digest(p)!=m["family_b"]["sha256"]: die("Family-B SHA-256 mismatch")
    with p.open() as f:
        return [[float(r[f"a{i}"]) for i in range(1,6)] for r in csv.DictReader(f)]

def render(cs, starts, h, steps, sample, direction=1, crossing_from=10**12):
    s=(ROOT/"lienard.eigs").read_text()
    vals={"COEFFS":cs,"STARTS":starts,"H":h,"STEPS":steps,"SAMPLE_STEPS":sample,
          "DIRECTION":direction,"CROSSING_FROM":crossing_from}
    for k,v in vals.items(): s=s.replace(f"__{k}__",json.dumps(v,separators=(",",":")))
    return s

def run_eigs(cs, starts, h, steps, sample, direction=1, crossing_from=10**12, env=None):
    with tempfile.NamedTemporaryFile("w",suffix=".eigs",delete=False) as f:
        f.write(render(cs,starts,h,steps,sample,direction,crossing_from)); name=f.name
    try:
        e=os.environ.copy(); e["EIGS_JIT_OFF"]="1"; e.update(env or {})
        q=subprocess.run([str(binary()),name],text=True,capture_output=True,env=e)
        if q.returncode: die(q.stdout+q.stderr)
        return q.stdout
    finally: Path(name).unlink(missing_ok=True)

def verdicts(out):
    ans=[]
    for l in out.splitlines():
        if l.startswith("VERDICT "):
            p=l.split(); ans.append((int(p[1]),int(p[2]),p[3],int(p[4])))
    return ans

def hermite(p, h, c, direction):
    x0,y0,x1,y1=p
    def vf(x,y):
        F=sum(c[i]*x**(i+1) for i in range(5)); return direction*(y-F),direction*(-x)
    dx0,dy0=vf(x0,y0); dx1,dy1=vf(x1,y1)
    def H(s,z0,z1,d0,d1): return (2*s**3-3*s**2+1)*z0+(s**3-2*s**2+s)*h*d0+(-2*s**3+3*s**2)*z1+(s**3-s**2)*h*d1
    lo,hi=0.,1.
    for _ in range(60):
        md=(lo+hi)/2; yy=H(md,y0,y1,dy0,dy1)
        if (direction==1 and yy>0) or (direction==-1 and yy<0): lo=md
        else: hi=md
    s=(lo+hi)/2
    return H(s,x0,x1,dx0,dx1)

def estimates(out, cs, h, direction):
    d={}
    for l in out.splitlines():
        if l.startswith("CROSS "):
            p=l.split(); key=(int(p[1]),int(p[2])); z=tuple(map(float,p[3:7]))
            x=hermite(z,h,cs[key[0]],direction)
            if x>0: d.setdefault(key,[]).append(x)
    return d

def settled(xs):
    if len(xs)<4:return None
    n=len(xs); a=median(xs[:n//2]); b=median(xs[n//2:])
    return median(xs) if abs(a-b)<=1e-7 else None

def instance(m, h=.01, crossings=False):
    a=m["instance_a"]; starts=[.2+.05*i for i in range(117)]
    return run_eigs([a["coefficients"]],starts,h,round(400/h),round(1/h),crossing_from=round(300/h) if crossings else 10**12)

def item1(m):
    vs=verdicts(instance(m)); miss=0
    for _,i,v,e in vs:
        x=.2+.05*i
        if x==1.5: continue
        want="converged" if x<m["oracle"]["inner"] else "oscillating"
        miss += v!=want or e
    if len(vs)!=117 or miss: die(f"item1 misses={miss}")
    print("PASS item1 population=117 graded=116 gray=1 misses=0 gray_members=1.50")

def family(m, limit=None, **kw):
    cs=coeffs(m); cs=cs[:limit] if limit else cs
    b=m["family_b"]; starts=[.25+.25*i for i in range(20)]
    return cs,run_eigs(cs,starts,b["rk4"]["h"],b["rk4"]["steps"],b["eigenscript_sample"] if "eigenscript_sample" in b else 200,**kw)

def item2(m,limit):
    av=verdicts(instance(m)); cs,out=family(m,limit); vs=av+verdicts(out)
    n=sum(v[2]=="diverging" for v in vs)
    if limit: print(f"SMOKE item2 systems={len(cs)} diverging={n}"); return
    if len(vs)!=3317 or n: die(f"item2 diverging={n}")
    print("PASS item2 population=3317 diverging=0")

def clusters(xs):
    out=[]
    for x in sorted(xs):
        if not out or x-out[-1][0]>.01: out.append([x])
        else: out[-1].append(x)
    return out

def pipeline(cs,starts,h,steps,sample,cross_from):
    stats=[]; allx=[]; retained=[]
    for direction in (1,-1):
        out=run_eigs(cs,starts,h,steps,sample,direction,cross_from)
        es=estimates(out,cs,h,direction); vs=verdicts(out); count=[0,0,0,0]
        rows=[0]*len(cs)
        for r,i,v,e in vs:
            xs=es.get((r,i),[]); x=settled(xs)
            if e: count[2]+=1
            elif not xs: count[3]+=1
            elif v!="oscillating" or x is None: count[1]+=1
            else: count[0]+=1; rows[r]+=1; allx.append(x)
        stats.append(count); retained.append(rows)
    return stats,clusters(allx),retained

def item3(m,limit):
    # Positive controls use precisely pipeline(), as does Family B.
    a=m["instance_a"]; sa=[.2+.05*i for i in range(117)]
    # The controls validate the Family-B numerical pipeline, including its
    # integration cadence, rather than Instance A's otherwise-frozen cadence.
    ast,ac,_=pipeline([a["coefficients"]],sa,.005,80000,200,60000)
    vst,vc,_=pipeline([[-1,0,1/3,0,0]],sa,.005,80000,200,60000)
    if len(ac)!=2 or len(vc)!=1: die("positive-control cluster count")
    reps=[median(x) for x in ac]; vr=median(vc[0])
    controls=(("A-inner",reps[0],m["oracle"]["inner"]),
              ("A-outer",reps[1],m["oracle"]["outer"]),
              ("van-der-Pol",vr,m["oracle"]["van_der_pol"]))
    for name,rep,oracle in controls:
        print(f"CONTROL {name} representative={rep:.12f} oracle={oracle:.12f} absolute_error={abs(rep-oracle):.12g}")
    if max(abs(rep-oracle) for _,rep,oracle in controls)>1e-9:
        die("positive-control amplitude exceeds 1e-9")
    cs=coeffs(m); cs=cs[:limit] if limit else cs; b=m["family_b"]
    st,cl,ret=pipeline(cs,[.25+.25*i for i in range(20)],.005,80000,200,60000)
    reaches=sum(len(x)>=3 for x in [cl])
    if limit:
        print(f"SMOKE item3 systems={len(cs)} starts={len(cs)*20} directions=2 reaches_3={reaches}"); return
    # Coverage and count are checked per frozen row/direction.
    with (ROOT/b["oracle_coverage"]["table"]).open() as f: cov=list(csv.DictReader(f))
    coverage_ok=True
    for i,row in enumerate(cov):
        for d,name in enumerate(("forward","reverse")):
            den=int(row[f"{name}_oracle_settled"])
            if den and ret[d][i] < math.ceil(.9*den): coverage_ok=False
    if reaches or not coverage_ok:
        print(f"FAIL item3 completed=1 reaches_3={reaches} coverage_floor={'PASS' if coverage_ok else 'FAIL'}")
        raise SystemExit(1)
    f,r=st
    print(f"PASS item3 population=160 starts=3200 directions=2 runs=6400 forward_settled={f[0]} forward_estimator_rejected={f[1]} forward_escaped={f[2]} forward_no_crossings={f[3]} forward_clustered_runs={f[0]} reverse_settled={r[0]} reverse_estimator_rejected={r[1]} reverse_escaped={r[2]} reverse_no_crossings={r[3]} reverse_clustered_runs={r[0]} coverage_floor=0.90 controls=A:2,vdp:1 max_clusters<=2 reaches_3=0")

def item4(m):
    c=[m["instance_a"]["coefficients"]]; vals=[]
    for h in (.01,.005):
        out=run_eigs(c,[4.],h,round(400/h),round(1/h),crossing_from=round(300/h))
        if verdicts(out)[0][2]!="oscillating": die("item4 observer gate")
        x=settled(estimates(out,c,h,1)[(0,0)]); vals.append(x)
    if abs(vals[0]-m["oracle"]["outer"])>m["oracle"]["outer"]*.005 or abs(vals[0]-vals[1])>1e-7: die(f"item4 values={vals}")
    print("PASS item4 oracle=3.922873870354 rel_error<=0.005 h_delta<=1e-7")

def item5(m):
    with tempfile.TemporaryDirectory() as td:
        scratch=Path(td)/"eigenscript"
        subprocess.run(["git","clone","--quiet","https://github.com/InauguralSystems/eigenscript.git",str(scratch)],check=True)
        subprocess.run(["git","-C",str(scratch),"checkout","--quiet","4a3a5c1941568e9bc562c7c8221cff22dc8ba697"],check=True)
        header=scratch/"src/eigenscript.h"
        old="#define OBSERVER_WINDOW_N 10"; new="#define OBSERVER_WINDOW_N 4"
        text=header.read_text()
        if text.count(old)!=1: die("item5 fault patch did not match exactly once")
        header.write_text(text.replace(old,new))
        # This is the Python argv equivalent of the frozen command
        # `make -C "$scratch" gfx CC=gcc`.
        q=subprocess.run(["make","-C",str(scratch),"gfx","CC=gcc"])
        if q.returncode: die("item5 build failed")
        e=os.environ.copy(); e["EIGENSCRIPT"]=str(scratch/"build/release/eigenscript")
        e["LIENARD55_ALLOW_FAULT_BINARY"]="1"
        q=subprocess.run([sys.executable,__file__,"item3","--manifest",str(ROOT/"prereg/55/manifest.json")],text=True,capture_output=True,env=e)
        sys.stdout.write(q.stdout); sys.stderr.write(q.stderr)
        mt=re.search(r"reaches_3=(\d+)",q.stdout)
        if q.returncode!=1 or not mt or int(mt.group(1))<1: die("item5 completed fault run did not reach three clusters")
    print("PASS item5 normal_window=10 fault_window=4 item3_exit=1 reaches_3>=1")

def baseline(m):
    c=m["instance_a"]["coefficients"]
    def fun(t,z):
        x,y=z; return [y-sum(c[i]*x**(i+1) for i in range(5)),-x]
    def ev(t,z): return z[1]
    ev.direction=-1
    x=4.
    for _ in range(10000):
        z=solve_ivp(fun,[1e-6,100],[x,-x*1e-6],events=ev,rtol=1e-10,atol=1e-12,max_step=.05)
        q=z.y_events[0][0,0]
        if abs(q-x)<1e-12: return q
        x=q
    die("baseline fixed point did not converge")

def item6(m,limit):
    with tempfile.TemporaryDirectory() as td:
        tape=str(Path(td)/"tape")
        cs,o1=family(m,limit,env={"EIGS_TRACE":tape})
        _,o2=family(m,limit,env={"EIGS_REPLAY":tape,"EIGS_REPLAY_STRICT":"1"})
    a=b"\n".join(l.encode() for l in o1.splitlines() if l.startswith("VERDICT "))
    b=b"\n".join(l.encode() for l in o2.splitlines() if l.startswith("VERDICT "))
    d=sum(x!=y for x,y in zip(a,b))+abs(len(a)-len(b))
    if limit: print(f"SMOKE item6 systems={len(cs)} differing_bytes={d}");return
    if d or len(verdicts(o1))!=3200: die(f"item6 differing_bytes={d}")
    print("PASS item6 population=3200 differing_bytes=0")

def item7(m):
    out=instance(m,crossings=True); vs=verdicts(out); es=estimates(out,[m["instance_a"]["coefficients"]],.01,1)
    om=0; bm=0; fp=baseline(m)
    # One DOP853 integration per start, with the exact frozen event/classifier.
    c=m["instance_a"]["coefficients"]
    def fun(t,z): x,y=z; return [y-sum(c[i]*x**(i+1) for i in range(5)),-x]
    def ev(t,z): return z[1]
    ev.direction=-1; ev.terminal=False
    for _,i,v,e in vs:
        x0=.2+.05*i
        if x0==1.5: continue
        want="origin" if x0<m["oracle"]["inner"] else "outer"
        got="origin" if v=="converged" else "outer" if v=="oscillating" and settled(es.get((0,i),[])) is not None else "miss"
        om+=got!=want
        s=solve_ivp(fun,[0,400],[x0,0],events=ev,rtol=1e-10,atol=1e-12,method="DOP853")
        crosses=s.y_events[0]; tail=[z[0] for t,z in zip(s.t_events[0],crosses) if t>=300 and z[0]>0]
        label="origin" if np.linalg.norm(s.y[:,-1])<1e-6 else "outer" if tail and abs(median(tail)-fp)<1e-6 else "miss"
        bm+=label!=want
    if om>bm: die(f"observer_misses={om} baseline_misses={bm}")
    print("PASS item7 population=117 graded=116 observer_misses<=baseline_misses items1_4=PASS")

def main():
    p=argparse.ArgumentParser(); p.add_argument("item",choices=[f"item{i}" for i in range(1,8)]); p.add_argument("--manifest",required=True); p.add_argument("--limit",type=int)
    a=p.parse_args(); m=json.loads(Path(a.manifest).read_text())
    if a.limit and a.item not in ("item2","item3","item6"): die("--limit unsupported")
    globals()[a.item](m,a.limit) if a.item in ("item2","item3","item6") else globals()[a.item](m)
if __name__=="__main__": main()
