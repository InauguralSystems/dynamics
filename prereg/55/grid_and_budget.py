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
print("family_b_stability source=evidence/bar-rewrite-55-fix/family_b_envelope.csv per_row_boxes=160 ceiling=1")
rate = Decimal("250000")
steps = 160 * 20 * 80000
# item2 (1), item3 forward+reverse (2), item5 forward+reverse (2), item6
# trace+replay (2): seven Family-B sweep-equivalents in total.
all_steps = 7 * steps + 117 * 40000 + 2 * 80000
print(f"budget population=160 amplitudes=20 steps_per_run=80000 steps_per_sweep={steps}")
print(f"budget sweeps=7 plus_instance_steps=4840000 total_steps={all_steps}")
print(f"budget conservative_rate={rate} step/s seconds={Decimal(all_steps)/rate} cpu_hours={Decimal(all_steps)/rate/3600:.3f}")
print("sizing_rule=largest_N_with_cpu_hours<=2 selected_N=160 next_N=161_exceeds=True")
