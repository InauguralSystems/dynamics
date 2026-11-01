#!/usr/bin/env python3
"""Check physics.eigs' damped-oscillator zeta-sweep row by row.

The old shell check counted lines containing "settles" anywhere, and every
underdamped row reads "x OSCILLATES, energy settles", so it held even when the
critically damped and overdamped rows oscillated. This parses the table and
checks each zeta row's reading against both its flag columns and the regime
the physics requires (hq#58, finding DYN-LAB-1).
"""
import re
import sys

# zeta -> required reading. zeta < 0 pumps energy in; 0 <= zeta < 1 rings;
# zeta >= 1 (critical/overdamped) returns to rest without crossing zero.
EXPECTED = (
    ("-0.05", "DIVERGES (energy grew)"),
    ("0", "x OSCILLATES, energy settles"),
    ("0.1", "x OSCILLATES, energy settles"),
    ("0.4", "x OSCILLATES, energy settles"),
    ("1", "settles"),
    ("2", "settles"),
)
FLAG = r"([Y-])"
ROW = re.compile(
    r"^  (\S+)\t\| E:" + r" ".join([FLAG] * 4)
    + r"\s+\| x:" + r" ".join([FLAG] * 3)
    + r"\s+\| (.+?)\s*$"
)


def fail(message):
    sys.exit(f"FAIL: physics sweep: {message}")


lines = sys.stdin.read().splitlines()
try:
    header = lines.index("  zeta     | E:osc conv div grew | x:osc conv div | reading")
except ValueError:
    fail("sweep table header not found")

rows = []
for line in lines[header + 1:]:
    match = ROW.match(line)
    if not match:
        break
    rows.append(match.groups())

if [row[0] for row in rows] != [zeta for zeta, _ in EXPECTED]:
    fail(f"expected zeta rows {[z for z, _ in EXPECTED]}, got {[r[0] for r in rows]}")

for (zeta, want), row in zip(EXPECTED, rows):
    e_osc, e_conv, e_div, grew, x_osc, x_conv, x_div, reading = row[1:]
    if reading != want:
        fail(f"zeta={zeta} reads {reading!r}, expected {want!r}")
    # The reading is derived from the flags (energy grew wins, then x:osc); a
    # row whose flags contradict its reading prints a verdict nobody observed.
    if (grew == "Y") != reading.startswith("DIVERGES"):
        fail(f"zeta={zeta} energy-grew flag {grew!r} contradicts reading {reading!r}")
    if grew == "-" and (x_osc == "Y") != reading.startswith("x OSCILLATES"):
        fail(f"zeta={zeta} x:osc flag {x_osc!r} contradicts reading {reading!r}")
    print(f"PASS: zeta={zeta} reads {reading!r} (grew={grew}, x:osc={x_osc})")

# The lab's headline claim: at zeta=0 energy is conserved, so the energy
# observer never reports convergence while x oscillates.
if rows[1][2] != "-":
    fail("zeta=0 energy reported converged; the undamped row must conserve energy")
print("PASS: zeta=0 energy never converges while x oscillates")
