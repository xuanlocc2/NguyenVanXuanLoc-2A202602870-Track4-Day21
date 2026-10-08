"""Kiểm tra 2 hàm TODO(CP2). Chạy từ gốc repo: python -m src.test_projection"""
import numpy as np

from starter.datasets import load_frame
from starter.projection import cam_to_image, velo_to_cam

fr = load_frame("data/synthetic", "000000")
calib, shape = fr["calib"], fr["image"].shape

# điểm 10 m phía trước xe: z_cam ~ 9.73, rơi gần giữa ảnh (614, 175)
cam = velo_to_cam(np.array([[10.0, 0, 0]]), calib)
assert abs(cam[0, 2] - 9.73) < 0.01, cam
uv, depth, mask = cam_to_image(cam, calib.P2, shape)
assert mask.tolist() == [True] and np.allclose(uv[0], [614, 175], atol=1), uv

# điểm 10 m phía sau xe (z_cam < 0) phải bị loại, không được chiếu lộn ngược
cam = velo_to_cam(np.array([[-10.0, 0, 0]]), calib)
assert cam[0, 2] < 0 and not cam_to_image(cam, calib.P2, shape)[2].any()

# NaN/Inf bị loại, điểm ngoài ảnh bị loại
bad = np.array([[np.nan, 0, 5], [np.inf, 0, 5], [100.0, 0, 5], [0, 0, 5]])
assert cam_to_image(bad, calib.P2, shape)[2].tolist() == [False, False, False, True]

# cả frame: số điểm vào ảnh khớp đề (3910)
_, _, mask = cam_to_image(velo_to_cam(fr["points"][:, :3], calib), calib.P2, shape)
assert mask.sum() == 3910, mask.sum()
print("OK: test_projection")
