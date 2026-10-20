#!/usr/bin/env python3
"""Generate the immutable Family-B coefficient population."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
from pathlib import Path
import numpy as np


def payload(n: int) -> bytes:
    rng = np.random.default_rng(55)
    columns = [rng.uniform(-0.5, 0.5, n), rng.uniform(-0.1, 0.1, n),
               rng.uniform(-0.05, 0.05, n), rng.uniform(-0.005, 0.005, n),
               rng.uniform(0.001, 0.005, n)]
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(("id", "a1", "a2", "a3", "a4", "a5"))
    for i, row in enumerate(zip(*columns)):
        writer.writerow((i, *(format(float(x), ".17g") for x in row)))
    return out.getvalue().encode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=350)
    ap.add_argument("--output", type=Path, default=Path(__file__).with_name("family_b.csv"))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    data = payload(args.count)
    digest = hashlib.sha256(data).hexdigest()
    if args.check:
        if args.output.read_bytes() != data:
            raise SystemExit(f"MISMATCH {args.output}")
        print(f"OK count={args.count} sha256={digest} file={args.output}")
    else:
        args.output.write_bytes(data)
        print(f"WROTE count={args.count} sha256={digest} file={args.output}")


if __name__ == "__main__":
    main()
