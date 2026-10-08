"""CP4: tìm failure case của projection khi calibration lệch yaw.

Metric: với mỗi vật thể, lấy các điểm LiDAR nằm trong 3D box (calib gốc), chiếu lại bằng calib bị lệch yaw,
đếm tỉ lệ điểm rơi trong 2D box của label.

    python -m src.yaw_failure
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from starter.datasets import load_frame
from starter.projection import cam_to_image, draw_box2d, perturb_extrinsic, velo_to_cam

ROOT = "data/kitti_mini"
FRAMES = ["000008", "000011", "000015"]
YAWS = [0, 0.5, 1, 2, 3]
TYPES = {"Car", "Pedestrian", "Cyclist"}
MIN_PTS = 10
OUT = Path("results")


def points_in_box3d(pts_cam: np.ndarray, obj) -> np.ndarray:
    h, w, l = obj.dimensions
    c, s = np.cos(obj.rotation_y), np.sin(obj.rotation_y)
    d = pts_cam - obj.location
    x, z = c * d[:, 0] - s * d[:, 2], s * d[:, 0] + c * d[:, 2]  # xoay ngược rotation_y
    return (np.abs(x) <= l / 2) & (np.abs(z) <= w / 2) & (d[:, 1] <= 0) & (d[:, 1] >= -h)


def hit_rate(pts_velo: np.ndarray, calib, shape, bbox) -> float:
    uv, _, _ = cam_to_image(velo_to_cam(pts_velo, calib), calib.P2, shape)
    if len(uv) == 0:
        return 0.0
    x1, y1, x2, y2 = bbox
    return float(((uv[:, 0] >= x1) & (uv[:, 0] <= x2) & (uv[:, 1] >= y1) & (uv[:, 1] <= y2)).sum() / len(pts_velo))


def main() -> None:
    rows = []
    for fid in FRAMES:
        fr = load_frame(ROOT, fid)
        xyz = fr["points"][:, :3]
        cam = velo_to_cam(xyz, fr["calib"])
        for i, obj in enumerate(fr["labels"]):
            if obj.type not in TYPES:
                continue
            sel = xyz[points_in_box3d(cam, obj)]
            if len(sel) < MIN_PTS:
                continue
            row = dict(frame=fid, obj=i, type=obj.type, dist_m=round(float(obj.location[2]), 1),
                       box_w_px=round(float(obj.bbox[2] - obj.bbox[0]), 1), n_pts=len(sel),
                       occluded=obj.occluded, truncated=obj.truncated)
            for y in YAWS:
                row[f"yaw{y}"] = hit_rate(sel, perturb_extrinsic(fr["calib"], yaw_deg=y), fr["image"].shape, obj.bbox)
            rows.append(row)
    df = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    df.to_csv(OUT / "fail_yaw_objects.csv", index=False, float_format="%.3f")
    print(df.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    print(df.groupby("type")[[f"yaw{y}" for y in YAWS]].mean().round(3))

    # failure: người đi bộ tệ nhất ở yaw 2 độ trong số vật đang còn trúng ở 0 độ
    ped = df[(df.type == "Pedestrian") & (df.yaw0 >= 0.9)].sort_values("yaw2")
    w = ped.iloc[0]
    print("worst:", dict(w))
    fr = load_frame(ROOT, w.frame)
    obj = fr["labels"][int(w.obj)]
    x1, y1, x2, y2 = obj.bbox
    xyz = fr["points"][:, :3]
    sel = xyz[points_in_box3d(velo_to_cam(xyz, fr["calib"]), obj)]  # chỉ vẽ điểm của vật này
    pad = 60
    panels = []
    for y in (0, 2):
        c = perturb_extrinsic(fr["calib"], yaw_deg=y)
        uv, _, _ = cam_to_image(velo_to_cam(sel, c), c.P2, fr["image"].shape)
        img = fr["image"].copy()
        img = draw_box2d(img, obj.bbox)
        crop = img[max(0, int(y1) - pad):int(y2) + pad, max(0, int(x1) - pad):int(x2) + pad]
        crop = cv2.resize(crop, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
        ox, oy = max(0, int(x1) - pad), max(0, int(y1) - pad)
        for u, v in uv:
            cv2.circle(crop, (int((u - ox) * 4), int((v - oy) * 4)), 5, (0, 0, 255), -1)
        rate = w[f"yaw{y}"]
        cv2.putText(crop, f"yaw {y} deg: {rate:.0%} pts in box", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        panels.append(crop)
    hh = min(p.shape[0] for p in panels)
    out = OUT / "figures" / "fail_01_yaw_pedestrian.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), np.hstack([p[:hh] for p in panels]))
    print("->", out)


if __name__ == "__main__":
    main()
