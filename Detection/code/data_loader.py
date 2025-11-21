# D:\STUDY_YOLOV8...\Detection\code\data_loader.py
# (PHIÊN BẢN SỬA LỖI ĐỌC INDEX)

import cv2
from pathlib import Path

def load_golden_dataset_per_image(dataset_path: Path):
    """
    Tải Bộ Dữ liệu Vàng từ một đường dẫn.

    GIẢ ĐỊNH:
    - Thư mục 'dataset_path' chứa 2 thư mục con: 'images' và 'labels'.
    - File nhãn .txt (ví dụ: 'img1.txt') trong 'labels'
    - File .txt chứa định dạng YOLO: [class_id] [x] [y] [w] [h]
      Ví dụ:
      0 0.5 0.5 0.1 0.1
      11 0.6 0.6 0.2 0.2
    """
    print(f"Đang tải dữ liệu vàng từ: {dataset_path}")
    
    image_dir = dataset_path / "images"
    label_dir = dataset_path / "labels"
    
    dataset = [] # List để chứa kết quả
    
    if not image_dir.exists() or not label_dir.exists():
        print(f"LỖI: Không tìm thấy thư mục 'images' hoặc 'labels' trong {dataset_path}")
        return []

    # Lặp qua tất cả các file ảnh
    image_extensions = [".jpg", ".jpeg", ".png"]
    for img_path in image_dir.iterdir():
        if img_path.suffix.lower() not in image_extensions:
            continue
            
        filename = img_path.name
        image_data = cv2.imread(str(img_path))
        
        if image_data is None:
            print(f"Cảnh báo: Không thể đọc file ảnh {filename}")
            continue
            
        # Tìm file nhãn .txt tương ứng
        label_path = label_dir / img_path.with_suffix(".txt").name
        
        # SỬA Ở ĐÂY: ground_truth_indices là một list các SỐ NGUYÊN (index)
        ground_truth_indices = [] 
        
        if label_path.exists():
            try:
                with open(label_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts: # Đảm bảo dòng không trống
                            # Lấy phần tử đầu tiên (class_id) và chuyển sang int
                            class_index = int(parts[0])
                            ground_truth_indices.append(class_index)
            except Exception as e:
                print(f"LỖI khi đọc file nhãn {label_path}: {e}")
        else:
            pass 
            
        # Thêm vào bộ dữ liệu (ảnh, và list các SỐ index)
        dataset.append( (filename, image_data, ground_truth_indices) )

    print(f"Đã tải {len(dataset)} ảnh từ bộ dữ liệu vàng.")
    return dataset