# D:\...\Detection\code_test\test_model_regression.py
# (PHIÊN BẢN: SỬA LỖI NAMEERROR + XUẤT ẢNH VISUALIZATION)

import pytest
import sys
import pandas as pd
import cv2 
import numpy as np
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).parent.parent.parent
CODE_PATH = PROJECT_ROOT / "Detection" / "code"
sys.path.insert(0, str(CODE_PATH))

try:
    from data_loader import load_golden_dataset_per_image
except ImportError as e:
    print(f"Lỗi import: {e}")
    sys.exit(1)

# --- HẰNG SỐ VÀ ĐƯỜNG DẪN ---
MINIMUM_PERFECT_IMAGE_ACCURACY = 0.90 

PATH_TO_NEW_MODEL = PROJECT_ROOT / "Detection" / "weights" / "best.pt"
GOLDEN_DATA_PATH = PROJECT_ROOT / "Detection" / "test" 

# Đường dẫn cho báo cáo
REPORT_DIR = PROJECT_ROOT / "reports"
REPORT_DIR.mkdir(exist_ok=True) 

# Tạo timestamp dùng chung cho cả Excel và thư mục ảnh
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Tạo thư mục chứa ảnh đã vẽ box
VISUALIZATION_DIR = REPORT_DIR / f"visual_results_{TIMESTAMP}"
VISUALIZATION_DIR.mkdir(exist_ok=True)

# --- BẢNG MÀU CỐ ĐỊNH (BGR cho OpenCV) ---
# Danh sách màu sặc sỡ để phân biệt các hành vi khác nhau
CLASS_COLORS = [
    (0, 255, 0),    # Xanh lá (Thường dùng cho bình thường)
    (0, 0, 255),    # Đỏ (Cảnh báo nguy hiểm)
    (255, 0, 0),    # Xanh dương
    (0, 255, 255),  # Vàng
    (255, 0, 255),  # Tím
    (0, 165, 255),  # Cam
    (128, 0, 128),  # Tím đậm
    (255, 192, 203) # Hồng
]

# --- HÀM HỖ TRỢ ---

def auto_fit_excel_columns(worksheet):
    """Tự động điều chỉnh độ rộng cột của một worksheet openpyxl."""
    for col in worksheet.columns:
        max_length = 0
        column_letter = col[0].column_letter 
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        worksheet.column_dimensions[column_letter].width = adjusted_width

def draw_visualizations(image_array, boxes, names, save_path):
    """
    Vẽ box và tên nhãn lên ảnh và lưu lại.
    """
    # Copy ảnh để không ảnh hưởng dữ liệu gốc
    img_vis = image_array.copy()
    
    for box in boxes:
        # Lấy tọa độ
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
        
        # Lấy class ID và tên
        cls_id = int(box.cls)
        label_name = names[cls_id]
        
        # Chọn màu dựa trên ID (chia lấy dư để vòng lại nếu hết màu)
        color = CLASS_COLORS[cls_id % len(CLASS_COLORS)]
        
        # 1. Vẽ hình chữ nhật (Bounding Box)
        cv2.rectangle(img_vis, (x1, y1), (x2, y2), color, 2)
        
        # 2. Vẽ nhãn (Label) ở phía trên box
        text_size, _ = cv2.getTextSize(label_name, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        text_w, text_h = text_size
        
        # Vẽ nền chữ nhật cho chữ dễ đọc hơn
        cv2.rectangle(img_vis, (x1, y1 - 20), (x1 + text_w, y1), color, -1)
        
        # Viết chữ màu trắng hoặc đen tùy độ sáng (ở đây chọn trắng cho nổi trên nền màu)
        cv2.putText(img_vis, label_name, (x1, y1 - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
    # Lưu ảnh
    cv2.imwrite(str(save_path), img_vis)

# --- Fixtures ---
@pytest.fixture(scope="module")
def new_model():
    """Tải mô hình YOLO."""
    assert PATH_TO_NEW_MODEL.exists(), f"Không tìm thấy model tại: {PATH_TO_NEW_MODEL}"
    model = YOLO(str(PATH_TO_NEW_MODEL)) 
    print(f"Đã tải model YOLO từ: {PATH_TO_NEW_MODEL}")
    print(f"Các nhãn model: {model.names}")
    return model

@pytest.fixture(scope="module")
def golden_data():
    """Tải bộ dữ liệu vàng."""
    assert GOLDEN_DATA_PATH.exists(), f"Không tìm thấy dữ liệu vàng tại: {GOLDEN_DATA_PATH}"
    dataset = load_golden_dataset_per_image(GOLDEN_DATA_PATH)
    if not dataset:
        pytest.fail("Bộ dữ liệu vàng không tải được hoặc bị rỗng.")
    return dataset

# --- HÀM TEST CHÍNH ---
@pytest.mark.slow
def test_model_multilabel_regression_report(new_model, golden_data):
    results_list = [] 
    total_images = len(golden_data)
    perfect_images_count = 0
    total_true_positives = 0 
    total_false_positives = 0 
    total_false_negatives = 0 

    class_names = new_model.names.values()
    per_class_tp = {name: 0 for name in class_names}
    per_class_fp = {name: 0 for name in class_names}
    per_class_fn = {name: 0 for name in class_names}

    print(f"\nBắt đầu chạy đánh giá trên {total_images} ảnh vàng...")
    print(f"Ảnh kết quả sẽ được lưu tại: {VISUALIZATION_DIR}")

    for filename, image_data, ground_truth_indices in golden_data:
        # --- 1. Xử lý Ground Truth ---
        try:
            gt_set = set([new_model.names[int(idx)] for idx in ground_truth_indices])
            gt_names_str = ", ".join(sorted(list(gt_set))) if gt_set else "None"
        except Exception as e:
            print(f"LỖI NGHIÊM TRỌNG: File {filename} có index nhãn không hợp lệ: {e}")
            gt_set = set()
            gt_names_str = "ERROR (Bad Index)"
        
        # --- 2. Dự đoán & Visualization ---
        try:
            # Chạy dự đoán
            yolo_results = new_model(image_data, verbose=False) 
            prediction_list = []
            
            if yolo_results and yolo_results[0]:
                r = yolo_results[0] # Result object
                boxes = r.boxes
                
                # --- VISUALIZATION (VẼ ẢNH) ---
                # Lấy tên file gốc để lưu
                save_img_path = VISUALIZATION_DIR / f"vis_{filename}"
                
                # Gọi hàm vẽ (truyền vào ảnh gốc dạng numpy array từ r.orig_img)
                draw_visualizations(r.orig_img, boxes, new_model.names, save_img_path)
                # ------------------------------

                for box in boxes:
                    label = new_model.names[int(box.cls)] 
                    prediction_list.append(label) 

            pred_set = set(prediction_list)

        except Exception as e:
            results_list.append({
                "Tên file": filename, "Trạng thái": "LỖI (Error)",
                "SL Nhãn Chuẩn (GT)": len(gt_set), "SL Nhãn Dự đoán": 0,
                "SL Nhãn Đúng (TP)": 0, "SL Nhãn Thiếu (FN)": len(gt_set), "SL Nhãn Thừa (FP)": 0,
                "Tỷ lệ Jaccard": 0.0,
                "Chi tiết Nhãn Thiếu": gt_names_str, "Chi tiết Nhãn Thừa": "ERROR",
                "Danh sách Nhãn Chuẩn": gt_names_str
            })
            for label_name in gt_set:
                per_class_fn[label_name] += 1
            total_false_negatives += len(gt_set)
            print(f"Lỗi xử lý ảnh {filename}: {e}")
            continue 

        # --- 3. Phép toán cốt lõi (So khớp) ---
        tp_set = gt_set.intersection(pred_set)
        fn_set = gt_set.difference(pred_set)
        fp_set = pred_set.difference(gt_set)
        
        for label_name in tp_set:
            per_class_tp[label_name] += 1
        for label_name in fn_set:
            per_class_fn[label_name] += 1
        for label_name in fp_set:
            per_class_fp[label_name] += 1
            
        total_true_positives += len(tp_set)
        total_false_positives += len(fp_set)
        total_false_negatives += len(fn_set)

        union_set_size = len(tp_set) + len(fn_set) + len(fp_set)
        jaccard_score = len(tp_set) / union_set_size if union_set_size > 0 else 0.0
        if len(gt_set) == 0 and len(pred_set) == 0:
            jaccard_score = 1.0
            
        is_perfect = (len(fn_set) == 0) and (len(fp_set) == 0)
        status = "PASS" if is_perfect else "FAIL"
        if is_perfect:
            perfect_images_count += 1
            
        results_list.append({
            "Tên file": filename,
            "Trạng thái": status,
            "Tỷ lệ Jaccard": f"{jaccard_score:.2%}",
            "SL Nhãn Chuẩn (GT)": len(gt_set),
            "SL Nhãn Dự đoán": len(pred_set),
            "SL Nhãn Đúng (TP)": len(tp_set),
            "SL Nhãn Thiếu (FN)": len(fn_set),
            "SL Nhãn Thừa (FP)": len(fp_set),
            "Chi tiết Nhãn Thiếu": ", ".join(sorted(list(fn_set))) if fn_set else "None",
            "Chi tiết Nhãn Thừa": ", ".join(sorted(list(fp_set))) if fp_set else "None",
            "Danh sách Nhãn Chuẩn": gt_names_str
        })

    print(f"Đánh giá hoàn tất. {perfect_images_count}/{total_images} ảnh nhận diện hoàn hảo.")

    # --- 4. TÍNH TOÁN TỔNG THỂ ---
    if total_images == 0:
        pytest.fail("Không có ảnh nào trong bộ dữ liệu vàng.")
        
    perfect_image_accuracy = perfect_images_count / total_images
    
    precision = total_true_positives / (total_true_positives + total_false_positives) \
                if (total_true_positives + total_false_positives) > 0 else 0
    recall = total_true_positives / (total_true_positives + total_false_negatives) \
             if (total_true_positives + total_false_negatives) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) \
               if (precision + recall) > 0 else 0

    # --- 5. TẠO BÁO CÁO EXCEL ---
    
    # Sheet 1: Chi tiết
    columns_order = [
        "Tên file", "Trạng thái", "Tỷ lệ Jaccard", "SL Nhãn Chuẩn (GT)", "SL Nhãn Dự đoán", 
        "SL Nhãn Đúng (TP)", "SL Nhãn Thiếu (FN)", "SL Nhãn Thừa (FP)", 
        "Chi tiết Nhãn Thiếu", "Chi tiết Nhãn Thừa", "Danh sách Nhãn Chuẩn"
    ]
    df = pd.DataFrame(results_list, columns=columns_order)
    
    # Sheet 2: Tổng thể
    summary_data = {
        "Chỉ số": [
            "--- ĐÁNH GIÁ TỔNG THỂ (THEO ẢNH) ---",
            "Tổng số ảnh", "Số ảnh Hoàn hảo (PASS)", "Số ảnh Lỗi (FAIL)",
            "Tỷ lệ ảnh Hoàn hảo (Accuracy)", "Ngưỡng yêu cầu (Accuracy)",
            "KẾT QUẢ TỔNG THỂ (HỒI QUY)",
            "",
            "--- ĐÁNH GIÁ TỔNG THỂ (THEO NHÃN) ---",
            "Tổng số nhãn thực tế (GT)", "Tổng số nhãn phát hiện đúng (TP)",
            "Tổng số nhãn phát hiện thừa (FP)", "Tổng số nhãn bỏ sót (FN)",
            "Độ chính xác (Precision) tổng thể", "Độ phủ (Recall) tổng thể",
            "Chỉ số F1-Score tổng thể",
            "",
            "--- ĐƯỜNG DẪN ẢNH TRỰC QUAN ---",
            "Thư mục ảnh kết quả"
        ],
        "Giá trị": [
            "", total_images, perfect_images_count, total_images - perfect_images_count,
            f"{perfect_image_accuracy:.2%}", f">= {MINIMUM_PERFECT_IMAGE_ACCURACY:.2%}",
            "PASS" if perfect_image_accuracy >= MINIMUM_PERFECT_IMAGE_ACCURACY else "FAIL - PHÁT HIỆN HỒI QUY",
            "", "",
            total_true_positives + total_false_negatives,
            total_true_positives, total_false_positives, total_false_negatives,
            f"{precision:.2%}", f"{recall:.2%}", f"{f1_score:.4f}",
            "", "",
            str(VISUALIZATION_DIR) # Ghi đường dẫn ảnh vào báo cáo
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    
    # Sheet 3: Theo Class
    per_class_results = []
    for name in class_names:
        tp = per_class_tp[name]
        fp = per_class_fp[name]
        fn = per_class_fn[name]
        
        class_precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        class_recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        class_f1 = 2 * (class_precision * class_recall) / (class_precision + class_recall) \
                   if (class_precision + class_recall) > 0 else 0
        
        per_class_results.append({
            "Tên Nhãn": name,
            "Tổng số nhãn đúng (TP)": tp,
            "Tổng số nhãn thừa (FP)": fp,
            "Tổng số nhãn thiếu (FN)": fn,
            "Precision": f"{class_precision:.2%}",
            "Recall": f"{class_recall:.2%}",
            "F1-Score": f"{class_f1:.4f}"
        })
    per_class_df = pd.DataFrame(per_class_results)

    # Ghi Excel
    report_filename = f"Bao_cao_Hoi_quy_Model_{TIMESTAMP}.xlsx"
    report_path = REPORT_DIR / report_filename

    try:
        with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Chi tiet tung anh', index=False)
            summary_df.to_excel(writer, sheet_name='Tom tat tong the', index=False)
            per_class_df.to_excel(writer, sheet_name='Phan tich tung loai nhan', index=False)
            
            auto_fit_excel_columns(writer.sheets['Chi tiet tung anh'])
            auto_fit_excel_columns(writer.sheets['Tom tat tong the'])
            auto_fit_excel_columns(writer.sheets['Phan tich tung loai nhan'])

        print(f"Đã xuất báo cáo chi tiết ra file: {report_path}")
        
    except Exception as e:
        print(f"LỖI: Không thể ghi file Excel: {e}")

    # 6. Assertion cuối cùng
    assert perfect_image_accuracy >= MINIMUM_PERFECT_IMAGE_ACCURACY, \
        f"Kiểm thử Hồi quy Thất bại! Accuracy: {perfect_image_accuracy:.2%} < {MINIMUM_PERFECT_IMAGE_ACCURACY:.2%}"