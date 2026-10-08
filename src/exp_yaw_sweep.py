"""Topic A: lệch yaw bao nhiêu độ thì điểm LiDAR rơi ra khỏi 2D box của vật thể.
Xuất phát từ script mẫu của codelab, mở rộng: tách hit_ratio theo class và theo khoảng cách (yaw_by_group.csv).

Chạy từ gốc repo:
    python -m src.exp_yaw_sweep
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd

from starter.datasets import load_frame
from starter.projection import perturb_extrinsic, project_velo_to_image, velo_to_cam

CLASSES = ("Car", "Van", "Pedestrian", "Cyclist")
DIST_BINS = [(0, 15), (15, 30), (30, 1e9)]


def points_in_box(points_cam: np.ndarray, obj) -> np.ndarray:
    """Mask (N,) các điểm (đã ở camera frame) nằm trong 3D box của label."""
    h, w, l = obj.dimensions
    c, s = np.cos(obj.rotation_y), np.sin(obj.rotation_y)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    local = (points_cam - obj.location) @ R        # toạ độ của điểm trong hệ trục gắn với box
    return ((np.abs(local[:, 0]) <= l / 2) & (local[:, 1] <= 0) & (local[:, 1] >= -h)
            & (np.abs(local[:, 2]) <= w / 2))


def run_one(fr: dict, yaw_deg: float) -> tuple[dict, list[dict]]:
    pts = fr["points"][np.isfinite(fr["points"]).all(axis=1)]
    cam_true = velo_to_cam(pts[:, :3], fr["calib"])           # vị trí thật, theo calib gốc
    calib = perturb_extrinsic(fr["calib"], yaw_deg=yaw_deg)   # calib đã bị lệch
    uv, _, mask = project_velo_to_image(pts, calib, fr["image"].shape)
    uv_all = np.full((len(pts), 2), np.nan)
    uv_all[mask] = uv

    objs = []
    for obj in fr["labels"]:
        if obj.type not in CLASSES:
            continue
        sel = points_in_box(cam_true, obj) & mask
        u, v = uv_all[sel, 0], uv_all[sel, 1]
        x1, y1, x2, y2 = obj.bbox
        objs.append({"type": obj.type, "dist_m": float(np.hypot(obj.location[0], obj.location[2])),
                     "n": int(sel.sum()), "hits": int(((u >= x1) & (u <= x2) & (v >= y1) & (v <= y2)).sum())})
    n, hits = sum(o["n"] for o in objs), sum(o["hits"] for o in objs)
    return ({"n_points": len(pts), "inside_image": int(mask.sum()), "object_points": n,
             "hit_ratio": round(hits / n, 4) if n else float("nan")}, objs)


def main() -> None:
    ap = argparse.ArgumentParser(description="Quét góc lệch yaw, đo % điểm của vật thể nằm trong 2D box")
    ap.add_argument("--data-root", default="data/kitti_mini")
    ap.add_argument("--frames", nargs="+", default=["000008", "000011", "000015", "000049"])
    ap.add_argument("--yaw-levels", nargs="+", type=float, default=[0, 0.5, 1, 2, 3])
    ap.add_argument("--out", default="results/yaw_perturb_sweep.csv")
    ap.add_argument("--out-group", default="results/yaw_by_group.csv")
    args = ap.parse_args()

    rows, recs = [], []
    for frame in args.frames:
        fr = load_frame(args.data_root, frame)
        for yaw in args.yaw_levels:
            summary, objs = run_one(fr, yaw)
            row = {"dataset": Path(args.data_root).name, "frame": frame, "yaw_deg": yaw, **summary}
            rows.append(row)
            print(row)
            recs += [{"frame": frame, "yaw_deg": yaw, **o} for o in objs]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"-> {out} ({len(rows)} dòng)")

    df = pd.DataFrame(recs)
    df["dist_bin"] = pd.cut(df["dist_m"], [b[0] for b in DIST_BINS] + [1e9], right=False,
                            labels=["0-15m", "15-30m", ">30m"])
    parts = []
    for by in ("type", "dist_bin"):
        g = df.groupby([by, "yaw_deg"], observed=True)[["n", "hits"]].sum().reset_index()
        g.insert(0, "group_by", by)
        g = g.rename(columns={by: "group"})
        g["hit_ratio"] = (g["hits"] / g["n"]).round(4)
        parts.append(g)
    pd.concat(parts).to_csv(args.out_group, index=False)
    print(f"-> {args.out_group}")


if __name__ == "__main__":
    main()
