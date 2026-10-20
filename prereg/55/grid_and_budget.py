#!/usr/bin/env python3
"""Print frozen grids, stability arithmetic, and compute-budget arithmetic."""
from decimal import Decimal

inner = Decimal("1.487060441512")
grid_a = [Decimal("0.20") + Decimal("0.05") * i for i in range(117)]
gray = [x for x in grid_a if abs(x / inner - 1) <= Decimal("0.02")]
print("instance_a_grid count=117 start=0.20 stop=6.00 step=0.05")
print("gray_band=[%s]" % ",".join(format(x, ".2f") for x in gray))
for x in gray:
    print(f"gray_member={x:.2f} relative_margin={abs(x/inner-1)*100:.3f}%")
for x in (Decimal("1.45"), Decimal("1.55")):
    margin = abs(x / inner - 1) * 100
    print(f"nearest_graded={x:.2f} relative_margin={margin:.3f}% outside_band={margin-2:.3f}_percentage_points")
print("family_b_grid count=20 start=0.25 stop=5.00 step=0.25")
print("instance_a_derivative_bound_box4.3=16.20 h=0.01 product=0.1620")
print("family_b_derivative_bound_box8=124.34 h=0.005 product=0.62170")
rate = Decimal("250000")
steps = 350 * 20 * 80000
all_steps = 3 * steps + 117 * 40000 + 2 * 80000
print(f"budget population=350 amplitudes=20 steps_per_run=80000 steps_per_sweep={steps}")
print(f"budget sweeps=3 plus_instance_steps=4840000 total_steps={all_steps}")
print(f"budget conservative_rate={rate} step/s seconds={Decimal(all_steps)/rate} cpu_hours={Decimal(all_steps)/rate/3600:.3f}")
