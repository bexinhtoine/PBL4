import google.generativeai as genai
import pandas as pd
import os
import glob
from datetime import datetime

# ==========================================
# 1. CẤU HÌNH (USER SETUP)
# ==========================================
# LƯU Ý: Thay KEY thực của bạn vào đây
GEMINI_API_KEY = "AIzaSyBsllVSeAWDyPvMcBk16Oc-iSNYa0S2YFM"

# Đường dẫn phải khớp với nơi file test_model_regression.py xuất ra
REPORT_DIR = "reports" 

# Cấu hình API
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Lỗi cấu hình API Key: {e}")

generation_config = {
    'temperature': 0.2,
    'top_p': 0.8,
    'top_k': 40,
    'max_output_tokens': 8192,
}

MODEL_NAME = 'gemini-2.0-flash' 

try:
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config=generation_config
    )
    print(f"--> Đã khởi tạo model: {MODEL_NAME}\n")
except Exception as e:
    print(f"Lỗi khởi tạo model: {e}")

# ==========================================
# 2. HÀM ĐỌC DỮ LIỆU TỪ NHIỀU SHEET
# ==========================================

def find_latest_report(report_dir):
    """Tìm file Excel (.xlsx) mới nhất, bỏ qua file tạm."""
    if not os.path.exists(report_dir):
        print(f"Thư mục '{report_dir}' không tồn tại.")
        return None
        
    # Lấy tất cả file xlsx
    all_files = glob.glob(os.path.join(report_dir, "*.xlsx"))
    
    # Lọc bỏ các file tạm bắt đầu bằng "~$" (file do Excel tạo khi đang mở)
    files = [f for f in all_files if not os.path.basename(f).startswith("~$")]
    
    if not files:
        print(f"Không tìm thấy file báo cáo .xlsx hợp lệ nào (đã bỏ qua file tạm).")
        return None
        
    # Lấy file có thời gian sửa đổi mới nhất
    latest_file = max(files, key=os.path.getmtime)
    return latest_file

def read_regression_data(file_path):
    """
    Đọc dữ liệu an toàn hơn bằng cách kiểm tra sheet tồn tại trước.
    SỬA ĐỔI QUAN TRỌNG: Dùng .to_string() thay vì .to_markdown() để tránh lỗi thiếu thư viện 'tabulate'.
    """
    try:
        print(f"Đang đọc dữ liệu từ: {os.path.basename(file_path)}...")
        
        # Dùng ExcelFile để load metadata nhanh và check tên sheet
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names
        print(f"   -> Các sheet tìm thấy: {sheet_names}")
        
        # --- 1. Đọc Summary ---
        if 'Tom tat tong the' in sheet_names:
            df_summary = pd.read_excel(xls, 'Tom tat tong the')
            summary_str = df_summary.to_string(index=False)
        else:
            print("CẢNH BÁO: Không thấy sheet 'Tom tat tong the'")
            summary_str = "DỮ LIỆU BỊ THIẾU: Không tìm thấy sheet 'Tom tat tong the'"

        # --- 2. Đọc Per-Class ---
        if 'Phan tich tung loai nhan' in sheet_names:
            df_per_class = pd.read_excel(xls, 'Phan tich tung loai nhan')
            per_class_str = df_per_class.to_string(index=False)
        else:
            print("   ⚠️ CẢNH BÁO: Không thấy sheet 'Phan tich tung loai nhan'")
            per_class_str = "DỮ LIỆU BỊ THIẾU: Không tìm thấy sheet 'Phan tich tung loai nhan'"

        # --- 3. Đọc Detail ---
        detail_note = ""
        if 'Chi tiet tung anh' in sheet_names:
            df_detail = pd.read_excel(xls, 'Chi tiet tung anh')
            # Lọc lỗi
            if 'Trạng thái' in df_detail.columns:
                df_fails = df_detail[df_detail['Trạng thái'] != 'PASS']
                if not df_fails.empty:
                    detail_str = df_fails.head(20).to_string(index=False)
                    detail_note = f"(Dưới đây là 20/{len(df_fails)} trường hợp lỗi điển hình)"
                else:
                    detail_str = "Tuyệt vời! Không có ảnh nào bị lỗi (Perfect Run)."
            else:
                detail_str = "Lỗi định dạng: Không tìm thấy cột 'Trạng thái'"
        else:
            print("   ⚠️ CẢNH BÁO: Không thấy sheet 'Chi tiet tung anh'")
            detail_str = "DỮ LIỆU BỊ THIẾU: Không tìm thấy sheet 'Chi tiet tung anh'"

        return summary_str, per_class_str, detail_str, detail_note
        
    except PermissionError:
        print(f"❌ LỖI QUYỀN TRUY CẬP: Hãy đóng file Excel '{os.path.basename(file_path)}' lại trước khi chạy script này!")
        return None, None, None, None
    except Exception as e:
        print(f"❌ Lỗi không xác định khi đọc file Excel: {e}")
        return None, None, None, None

# ==========================================
# 3. PROMPT CHUYÊN SÂU CHO AI ENGINEER
# ==========================================

def analyze_regression_test(summary_str, per_class_str, detail_str, detail_note):
    """Gửi dữ liệu cho Gemini với vai trò Senior AI Engineer."""
    try:
        prompt = f"""
        BỐI CẢNH:
        Bạn là một Chuyên gia Kiểm định chất lượng AI (Lead AI QA & Research Engineer). Bạn đang thực hiện audit kỹ thuật cho kết quả test hồi quy (Regression Test) của model YOLOv8.

        DỮ LIỆU ĐẦU VÀO TỪ BÁO CÁO:
        
        [PHẦN 1: TÓM TẮT CHỈ SỐ]
        {summary_str}

        [PHẦN 2: HIỆU SUẤT TỪNG LỚP (PER-CLASS)]
        {per_class_str}

        [PHẦN 3: CÁC TRƯỜNG HỢP LỖI ĐIỂN HÌNH ({detail_note})]
        {detail_str}

        ========================================
        YÊU CẦU ĐẦU RA (NGHIÊM NGẶT):
        1. Ngôn ngữ: Tiếng Việt chuyên ngành.
        2. Định dạng: TUYỆT ĐỐI KHÔNG sử dụng in đậm (không dùng dấu **).
           - Chỉ sử dụng số thứ tự (1. 2. 3.) cho các mục lớn.
           - Sử dụng dấu gạch ngang (-) hoặc dấu cộng (+) cho các ý nhỏ.
        3. Nội dung: Phải sâu sắc, suy luận logic từ số liệu, không chỉ mô tả lại con số.

        HÃY VIẾT BÁO CÁO KỸ THUẬT THEO CẤU TRÚC SAU:

        1. Đánh giá Hiệu suất & Quyết định Phát hành (Go/No-Go)
           - Dựa trên tỷ lệ ảnh hoàn hảo (Perfect Image Accuracy) và F1-Score tổng thể, model này có đủ điều kiện để deploy không?
           - So sánh mức độ nghiêm trọng: Nếu trạng thái là FAIL, mức độ hồi quy là nhẹ hay nghiêm trọng?

        2. Phân tích Nguyên nhân Gốc rễ (Root Cause Analysis - Deep Dive)
           - Hãy nhìn vào bảng Per-Class Metrics: Class nào đang là "tội đồ" kéo tụt hiệu suất?
           - Phân tích tính chất lỗi của Class đó dựa trên Precision và Recall:
             + Nếu Precision thấp: Model đang bị "ảo giác" (nhận diện nhầm background hoặc vật thể khác thành class này).
             + Nếu Recall thấp: Model đang bị "mù" (bỏ sót đối tượng, có thể do vật thể nhỏ, bị che khuất hoặc thiếu sáng).
           - Phân tích các ca lỗi (Failed Cases): Dựa trên tên file (nếu có manh mối) hoặc logic nhãn (thừa/thiếu), hãy phỏng đoán nguyên nhân vật lý (ví dụ: do góc chụp, do môi trường nhiễu, hay do nhãn không rõ ràng?).

        3. Chiến lược Khắc phục & Khuyến nghị (Action Items)
           - Đề xuất cho đội Data: Cần thu thập thêm loại dữ liệu nào? Cần gán nhãn lại (re-label) class nào? Có cần thêm ảnh negative (ảnh nền không có vật thể) để giảm False Positive không?
           - Đề xuất cho đội Model: Cần điều chỉnh siêu tham số (Hyperparameters) nào? (Ví dụ: Tăng/giảm Confidence Threshold, điều chỉnh IOU Threshold, hay thay đổi Augmentation).
        """
        
        print("⏳ Gemini đang phân tích chuyên sâu (vui lòng đợi)...")
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"❌ Lỗi khi gọi API Gemini: {e}"

# ==========================================
# 4. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("--- BẮT ĐẦU QUÁ TRÌNH AI AUDIT ---\n")
    
    # 1. Tìm file báo cáo mới nhất
    latest_file = find_latest_report(REPORT_DIR)
    
    if latest_file:
        print(f"-> Đã chọn file: {latest_file}")
        
        # 2. Đọc dữ liệu
        summary_data, class_data, detail_data, note = read_regression_data(latest_file)
        
        # Chỉ phân tích nếu đọc được ít nhất phần Summary
        if summary_data and "DỮ LIỆU BỊ THIẾU" not in summary_data:
            # 3. Gửi cho Gemini
            result = analyze_regression_test(summary_data, class_data, detail_data, note)
            
            # 4. Lưu kết quả
            base_name = os.path.basename(latest_file).replace('.xlsx', '')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            output_filename = f"AI_Audit_{base_name}_{timestamp}.txt"
            output_path = os.path.join(REPORT_DIR, output_filename)
            
            print("\n" + "="*30 + " AI ENGINEER ASSESSMENT " + "="*30)
            print(result)
            print("="*80)
            
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result)
                print(f"\n✅ Đã lưu báo cáo vào: {output_path}")
            except Exception as e:
                print(f"❌ Lỗi khi lưu file: {e}")
        else:
            print("\n⚠️ KHÔNG THỂ PHÂN TÍCH: Dữ liệu đọc từ Excel bị lỗi hoặc trống.")
            if summary_data:
                print(f"Nội dung đọc được: {summary_data[:100]}...")
            
    else:
        print("\n❌ Không tìm thấy file báo cáo đầu vào.")
        print("Gợi ý: Hãy chạy 'test_model_regression.py' trước để tạo file Excel.")