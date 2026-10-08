# Báo cáo Day 6: Độ nhạy của projection với lệch yaw

> Thay **mọi** ô có chữ ĐIỀN nằm trong ngoặc vuông bằng nội dung của bạn, xoá luôn cả dấu ngoặc vuông. Lệnh `python tools/check_submission.py` sẽ báo FAIL nếu còn sót bất kỳ chỗ nào.

- **Họ tên:** Nguyễn Văn Xuân Lộc
- **MSSV:** 2A202602870 (phải trùng với MSSV trong tên repo `<HoVaTen>-<MSSV>-Track4-Day21`)
- **Lớp:** AI20K-T4
- **Link repo:** https://github.com/xuanlocc2/NguyenVanXuanLoc-2A202602870-Track4-Day21
- **Topic:** A — LiDAR-camera projection QA
- **Dataset:** data/kitti_mini
- **Các frame đã dùng:** 000008, 000011, 000015, 000049

> Hãy viết ngắn: mỗi mục từ 3 đến 8 dòng, ưu tiên số liệu và hình ảnh.

## 1. Claim

Một câu khẳng định kỹ thuật có thể kiểm chứng. Ví dụ: *"Lệch yaw 1° làm 12% điểm LiDAR rơi ra khỏi vật thể ở 30 m, phát hiện được bằng edge-alignment score với ngưỡng X."*

Lệch yaw 1° làm tỉ lệ điểm LiDAR của người đi bộ rơi đúng vào 2D box giảm hơn 20 điểm phần trăm, trong khi với xe con chỉ giảm dưới 5 điểm phần trăm.

## 2. Evidence

Bảng hoặc plot số liệu, kèm ảnh/video demo. Ghi rõ đường dẫn file trong `results/`.

Metric: % điểm LiDAR nằm trong 3D box của vật thể (theo calib gốc) mà sau khi chiếu bằng calib bị lệch yaw vẫn rơi vào 2D box của label. Dữ liệu: `results/yaw_perturb_sweep.csv` (theo frame), `results/yaw_by_group.csv` (theo class và khoảng cách). Mỗi lần chỉ đổi yaw, không có phép ngẫu nhiên, chạy lại hai lần ra file giống hệt nhau.

| Lệch yaw | 000008 (đông xe) | 000011 (nhiều người đi bộ) | 000015 (người đi bộ) | 000049 (nhiều vật bị che) | Pedestrian (gộp) | Car (gộp) |
|---|---|---|---|---|---|---|
| 0° | 99.6% | 99.5% | 98.0% | 99.3% | 95.9% | 99.7% |
| 0.5° | 99.6% | 91.9% | 92.6% | 97.5% | 84.2% | 99.2% |
| 1° | 98.6% | 77.4% | 86.2% | 93.5% | 68.7% | 97.4% |
| 2° | 94.8% | 45.4% | 78.4% | 84.7% | 45.6% | 92.6% |
| 3° | 91.0% | 21.2% | 73.3% | 74.3% | 29.0% | 87.2% |

![yaw sweep](../results/figures/yaw_sweep.png)

![demo](../results/figures/overlay_000011_r0.0_p0.0_y0.0_t0.0_0.0_0.0.png)

- Claim được xác nhận ở dạng gộp: ở 1°, người đi bộ giảm 27.2 điểm phần trăm (95.9% → 68.7%), xe con chỉ giảm 2.3 điểm (99.7% → 97.4%). Theo frame: 000011 giảm 22.0 điểm, 000008 giảm 1.0 điểm.
- Theo khoảng cách (gộp mọi class), ở 1°: vật 0–15 m còn 96.7%, vật 15–30 m còn 82.0%, vật trên 30 m còn 79.1%, vì lệch góc làm điểm trượt khoảng 12.6 px/độ bất kể khoảng cách trong khi vật xa nhỏ hơn trên ảnh.
- Mức sàn ở 0° là 98–99.6% theo frame (95.9% với người đi bộ) do label do người vẽ không khớp tuyệt đối, nên ngưỡng cảnh báo nên đặt khoảng 90%: người đi bộ (gộp) đã xuống dưới ngưỡng này ở 0.5° (84.2%), còn frame đông xe 000008 vẫn trên 90% đến tận 3° (91.0%).

## 3. Failure case

Nêu khi nào hệ thống hoặc phương pháp fail, vì sao fail, và liên hệ tới lớp nào trong 6 lớp debug: I/O, Geometry, Time, Preprocess, Model, Metric.

![failure](../results/figures/fail_01_yaw_pedestrian.png)

- **Trường hợp:** KITTI, frame 000011, người đi bộ thứ 6 (obj 5) ở 15.9 m, 2D box rộng 27.7 px, 81 điểm LiDAR. Chiếu bằng calib lệch yaw 0° / 0.5° / 1° / 2°.
- **Quan sát:** tỉ lệ điểm nằm trong 2D box giảm 100% → 81% → 35% → 0% (yaw 0 / 0.5 / 1 / 2°). Ở 2° cả cụm điểm trượt sang trái, nằm hoàn toàn ngoài box (ảnh bên phải). Người ở 34 m (box 15.3 px) mất 92 điểm phần trăm chỉ với 1°. Kết quả sơ bộ: mức giảm phụ thuộc bề rộng box trên ảnh chứ không phụ thuộc loại vật. Xe ở 33 m (box 51 px) cũng mất 24 điểm phần trăm ở 1°, còn xe gần (box ≥ 123 px) mất dưới 2 điểm phần trăm. Số liệu: `results/fail_yaw_objects.csv`.
- **Nguyên nhân:** xoay yaw θ làm điểm trượt khoảng f·tan(θ) pixel, gần như không đổi theo khoảng cách (f = 721.5 px: 1° ≈ 12.6 px, 2° ≈ 25.2 px), mà người đi bộ chỉ rộng 27.7 px nên 2° đủ đẩy cả cụm điểm ra ngoài box.
- **Lớp debug:** Geometry (extrinsic `Tr_velo_to_cam` sai). Kèm lớp Metric: "số điểm nằm trong ảnh" gần như không đổi khi lệch (data/synthetic, frame 000000: 3910 → 3956 ở yaw 2°), nên không phát hiện được lỗi này.
- **Cách phát hiện khi chạy thật:** theo dõi tỉ lệ điểm LiDAR nằm trong 2D box của vật mà detector ảnh phát hiện được (người đi bộ, cột), cảnh báo khi giảm dưới 90% so với lúc mới calibrate. Không dùng "% điểm nằm trong ảnh" làm chỉ số cảnh báo.

## 4. Khuyến nghị nếu triển khai thật

Use-case cụ thể (ADAS / robot / drone), trade-off và bước tiếp theo.

[ĐIỀN]

## 5. Cách chạy lại

Các lệnh tái tạo lại toàn bộ kết quả từ repo sạch.

```bash
[ĐIỀN]
```

## 6. Khai báo sử dụng AI

Ghi rõ đã dùng công cụ AI nào, dùng vào việc gì, và bạn đã tự kiểm chứng kết quả đó bằng cách nào. Nếu không dùng AI, ghi "Không sử dụng". Xem quy định ở `RULES.md` mục 2.

| Công cụ | Dùng cho việc gì | Bạn đã kiểm chứng thế nào |
|---|---|---|
| [ĐIỀN] | | |
