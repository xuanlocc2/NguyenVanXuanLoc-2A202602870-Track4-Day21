"""Vẽ kết quả quét yaw. Chạy từ gốc repo: python -m src.plot_yaw_sweep"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv("results/yaw_perturb_sweep.csv", dtype={"frame": str})   # giữ "000011", không đổi thành 11
grp = pd.read_csv("results/yaw_by_group.csv")

fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
panels = [("Theo frame", [(f, g["yaw_deg"], g["hit_ratio"]) for f, g in df.groupby("frame")]),
          ("Theo class", [(k, g["yaw_deg"], g["hit_ratio"]) for k, g in grp[grp.group_by == "type"].groupby("group")]),
          ("Theo khoảng cách", [(k, g["yaw_deg"], g["hit_ratio"]) for k, g in grp[grp.group_by == "dist_bin"].groupby("group")])]
for ax, (title, lines) in zip(axes, panels):
    for name, x, y in lines:
        ax.plot(x, 100 * y, marker="o", label=name)
    ax.axhline(90, color="gray", ls="--", lw=1)
    ax.set_title(title)
    ax.set_xlabel("Lệch yaw (độ)")
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.3)
    ax.legend()
axes[0].set_ylabel("% điểm của vật thể nằm trong 2D box")
fig.tight_layout()

out = Path("results/figures/yaw_sweep.png")
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=150)
print(f"-> {out}")
