# view_faces_db.py
import argparse
import numpy as np
from collections import Counter
from textwrap import indent

def main():
    parser = argparse.ArgumentParser(description="Xem nội dung faces_db.npz")
    parser.add_argument("path", help="Đường dẫn tới file .npz (ví dụ: faces_db.npz)")
    parser.add_argument("--show", type=int, default=10,
                        help="Số tên/embedding mẫu muốn in ra (mặc định 10)")
    args = parser.parse_args()

    data = np.load(args.path, allow_pickle=True)

    # Lấy dữ liệu
    embs  = data["embs"].astype("float32")      # (N, 512)
    names = data["names"]                       # (N,)

    # Thông tin tổng quan
    print("=== THÔNG TIN DATABASE ===")
    print(f"File: {args.path}")
    print(f"Số mẫu (N): {embs.shape[0]}")
    print(f"Kích thước embedding: {embs.shape[1]} (mặc định FaceNet = 512)")
    print(f"Kiểu dữ liệu embedding: {embs.dtype}")
    print()

    # Thống kê tên
    names_list = names.tolist()
    counter = Counter(names_list)
    print("=== THỐNG KÊ TÊN (top) ===")
    for name, cnt in counter.most_common(20):
        print(f"- {name}: {cnt}")
    print()

    # In một số dòng mẫu
    k = min(args.show, embs.shape[0])
    print(f"=== {k} MẪU ĐẦU TIÊN ===")
    for i in range(k):
        n = names_list[i]
        v = embs[i]
        # In 8 phần tử đầu của vector cho gọn
        preview = ", ".join(f"{x:.4f}" for x in v[:8])
        print(f"[{i:>4}] name = {n}")
        print(indent(f"emb[0:8] = [{preview}] ... (len={len(v)})", "    "))
    print()

    # Kiểm tra tính hợp lệ cơ bản
    print("=== KIỂM TRA CƠ BẢN ===")
    ok_len = (embs.shape[0] == len(names_list))
    norms  = np.linalg.norm(embs, axis=1)
    norm_min, norm_max, norm_mean = float(norms.min()), float(norms.max()), float(norms.mean())
    print(f"Số mẫu khớp giữa embs và names: {ok_len} (embs={embs.shape[0]} vs names={len(names_list)})")
    print(f"Chuẩn L2 trung bình của embedding: min={norm_min:.4f}, max={norm_max:.4f}, mean={norm_mean:.4f}")
    print("(Embedding thường đã L2-normalized xấp xỉ 1.0)")

if __name__ == "__main__":
    main()
