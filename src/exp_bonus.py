"""Bonus topic A: B2 (stress test suy giảm), B3 (latency), B5 (nuScenes vs KITTI).
Dùng lại run_one của exp_yaw_sweep. Mỗi bonus ra một CSV trong results/.

    python -m src.exp_bonus --which b2 b3 b5
"""
from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd

from src.exp_yaw_sweep import run_one
from starter.datasets import load_frame
from starter.perturb import gaussian_noise, random_dropout

KITTI = "data/kitti_mini"
NUSC = "data/nuscenes_mini_subset"
YAWS = [0, 0.5, 1, 2, 3]


def hit(fr, yaw, points=None):
    if points is not None:
        fr = {**fr, "points": points}
    s, _ = run_one(fr, yaw)
    return s


def b2() -> pd.DataFrame:
    rows = []
    levels = [("random_dropout", "keep_ratio", k, lambda p, v: random_dropout(p, keep_ratio=v, seed=0)) for k in (1.0, 0.7, 0.5, 0.3)]
    levels = [(n, a, v, f) for n, a, v, f in levels]
    levels += [("gaussian_noise", "sigma_m", v, lambda p, v: gaussian_noise(p, sigma_xyz_m=v, seed=0)) for v in (0.0, 0.02, 0.05, 0.1)]
    for frame in ("000008", "000011"):
        fr = load_frame(KITTI, frame)
        for name, arg, v, fn in levels:
            pts = fn(fr["points"], v)
            for yaw in (0, 1, 2):
                s = hit(fr, yaw, pts)
                rows.append({"frame": frame, "degrade": name, arg: v, "yaw_deg": yaw,
                             "object_points": s["object_points"], "hit_ratio": s["hit_ratio"]})
    return pd.DataFrame(rows)


def b3() -> pd.DataFrame:
    fr = load_frame(KITTI, "000011")
    rows = []
    for i in range(21):
        t0 = time.perf_counter()
        hit(fr, 1.0)
        rows.append({"run": i, "ms": (time.perf_counter() - t0) * 1000, "dropped_warmup": i == 0})
    ms = np.array([r["ms"] for r in rows[1:]])
    print(f"p50 = {np.percentile(ms, 50):.1f} ms, p95 = {np.percentile(ms, 95):.1f} ms")
    return pd.DataFrame(rows)


def b5() -> pd.DataFrame:
    rows = []
    sets = [(KITTI, ["000008", "000011", "000015", "000049"]),
            (NUSC, ["scene-0103_010", "scene-0103_020", "scene-1094_010", "scene-1094_020"])]
    for root, frames in sets:
        for frame in frames:
            fr = load_frame(root, frame)
            for yaw in YAWS:
                s = hit(fr, yaw)
                rows.append({"dataset": root.split("/")[-1], "frame": frame, "yaw_deg": yaw, **s,
                             "focal_px": round(float(fr["calib"].P2[0, 0]), 1), "image_w": fr["image"].shape[1]})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Bonus B2/B3/B5 cho topic A")
    ap.add_argument("--which", nargs="+", default=["b2", "b3", "b5"], choices=["b2", "b3", "b5"])
    args = ap.parse_args()
    for w in args.which:
        df = {"b2": b2, "b3": b3, "b5": b5}[w]()
        out = {"b2": "results/b2_degradation.csv", "b3": "results/b3_latency.csv", "b5": "results/b5_kitti_vs_nuscenes.csv"}[w]
        df.to_csv(out, index=False, float_format="%.4f")
        print(f"-> {out}")


if __name__ == "__main__":
    main()
