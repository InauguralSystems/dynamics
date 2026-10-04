#!/usr/bin/env python3
"""Check the three numeric vectors printed by the standalone solver demo."""
import ast
import math
import re
import sys

output = sys.stdin.read()
# A @ [1, 1, 1] = b; G @ [0.4, 0.2, 0.4] = [0.4, 0.2, 0.4], sum = 1.
for label, expected in (
    ("Jacobi", (1.0, 1.0, 1.0)),
    ("Gauss-Seidel", (1.0, 1.0, 1.0)),
    ("PageRank", (0.4, 0.2, 0.4)),
):
    rows = re.findall(r"^" + re.escape(label) + r"\s+[^\n]*?-> (\[[^\n]*?\])(?:\s|$)", output, re.M)
    try:
        if len(rows) != 1:
            raise ValueError("expected one printed numeric vector")
        values = ast.literal_eval(rows[0])
        if len(values) != 3 or any(
            type(value) not in (int, float)
            or not math.isfinite(value)
            or not math.isclose(value, want, rel_tol=0.0, abs_tol=0.0001)
            for value, want in zip(values, expected)
        ):
            raise ValueError(f"incorrect components: {values!r}")
    except (ValueError, SyntaxError, TypeError) as error:
        sys.exit(f"FAIL: {label}: {error}")
    print(f"PASS: {label} prints all three converged components")
