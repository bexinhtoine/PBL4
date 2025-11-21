import google.generativeai as genai
import pandas as pd
import os
import glob
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

GEMINI_API_KEY = "AIzaSyBsllVSeAWDyPvMcBk16Oc-iSNYa0S2YFM"

# Đường dẫn phải khớp với nơi các file test xuất ra
REPORT_DIR = "reports" 

# Cấu hình API
try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    else:
        print("CẢNH BÁO: GEMINI_API_KEY đang trống.")
except Exception as e:
    print(f"Lỗi cấu hình API Key: {e}")

generation_config = {
    'temperature': 0.1,
    'top_p': 0.8,
    'top_k': 40,
    'max_output_tokens': 8192,
}

MODEL_NAME = 'gemini-2.5-flash' 
try:
    model = genai.GenerativeModel(model_name=MODEL_NAME, generation_config=generation_config)
    print(f"--> Đã khởi tạo model: {MODEL_NAME}\n")
except Exception as e:
    print(f"Lỗi khởi tạo model: {e}")
    model = None


# ==========================================
# 2. HÀM ĐỌC DỮ LIỆU TỪ HAI LOẠI FILE KHÁC NHAU
# ==========================================

def find_latest_reports_by_type(report_dir: str) -> Dict[str, Optional[str]]:
    """Tìm file báo cáo mới nhất cho từng loại (Performance và Stability)."""
    
    report_paths = {
        'performance': None,
        'stability': None
    }
    
    if not os.path.exists(report_dir):
        print(f"Thư mục '{report_dir}' không tồn tại.")
        return report_paths

    patterns = {
        'performance': 'Performance_Breakdown_Report_*.xlsx',
        'stability': 'Stability_Tracking_Report_*.xlsx'
    }

    for key, pattern in patterns.items():
        all_files = glob.glob(os.path.join(report_dir, pattern))
        
        # Lọc bỏ file tạm
        files = [f for f in all_files if not os.path.basename(f).startswith("~$")]
        
        if files:
            # Lấy file có thời gian sửa đổi mới nhất
            latest_file = max(files, key=os.path.getmtime)
            report_paths[key] = latest_file
            print(f"-> Đã tìm thấy báo cáo {key.upper()}: {os.path.basename(latest_file)}")
        else:
            print(f"⚠️ CẢNH BÁO: Không tìm thấy file báo cáo {key} nào.")

    return report_paths

def read_excel_sheet(file_path: str, sheet_name: str) -> str:
    """Đọc dữ liệu từ một sheet cụ thể và trả về dưới dạng chuỗi."""
    try:
        xls = pd.ExcelFile(file_path)
        if sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name)
            # Dùng .to_string() để đảm bảo format sạch
            return df.to_string(index=False)
        else:
            return f"DỮ LIỆU BỊ THIẾU: Không tìm thấy sheet '{sheet_name}' trong file."
    except PermissionError:
        return f"❌ LỖI QUYỀN TRUY CẬP: Hãy đóng file Excel '{os.path.basename(file_path)}' lại!"
    except Exception as e:
        return f"❌ LỖI ĐỌC EXCEL: Lỗi không xác định khi đọc file: {e}"

# ==========================================
# 3. PROMPT PHÂN TÍCH TỔNG HỢP (CHI TIẾT & CÓ MỤC MỚI)
# ==========================================

def analyze_consolidated_results(perf_summary: str, stab_summary: str, perf_detail: str) -> str:
    """Gửi dữ liệu tổng hợp cho Gemini với vai trò Lead Performance Auditor."""
    
    prompt = f"""
    BỐI CẢNH:
    Bạn là một Lead Performance Auditor (Trưởng Kiểm toán Hiệu năng) chuyên về Computer Vision. Nhiệm vụ của bạn là phân tích và đưa ra kết luận kỹ thuật tổng hợp dựa trên hai bộ dữ liệu: Hiệu năng (tốc độ FPS, độ trễ) và Độ ổn định (chất lượng theo dõi khuôn mặt).

    DỮ LIỆU ĐẦU VÀO TỪ CÁC BÁO CÁO:
    
    ========================================
    [PHẦN 1: BÁO CÁO TÓM TẮT HIỆU NĂNG (PERFORMANCE BREAKDOWN - Sheet: Tong_Hop)]
    {perf_summary}

    ========================================
    [PHẦN 2: BÁO CÁO TÓM TẮT ĐỘ ỔN ĐỊNH (STABILITY TRACKING - Sheet: TongKet_OnDinh)]
    {stab_summary}
    
    ========================================
    [PHẦN 3: DỮ LIỆU CHI TIẾT THEO FRAME (PERFORMANCE DETAIL - Sheet: Chi_Tiet_Frame)]
    Đây là dữ liệu chi tiết theo từng khung hình. Hãy sử dụng nó để tìm ra các điểm bất thường/điểm lag (spikes):
    {perf_detail}

    ========================================
    YÊU CẦU ĐẦU RA (NGHIÊM NGẶT):
    1. Ngôn ngữ: Tiếng Việt chuyên ngành, văn phong báo cáo kỹ thuật.
    2. Định dạng: TUYỆT ĐỐI KHÔNG sử dụng in đậm (không dùng dấu **).
       - Chỉ sử dụng số thứ tự (1. 2. 3. 4. 5.) cho các mục lớn.
       - Sử dụng dấu gạch ngang (-) cho các ý nhỏ.
    3. Nội dung: Phải kết nối TỐC ĐỘ (FPS) và CHẤT LƯỢNG (Độ ổn định) để đưa ra kết luận.

    HÃY VIẾT BÁO CÁO KỸ THUẬT TỔNG HỢP THEO CẤU TRÚC SAU:

    1. Đánh giá Khả năng Ứng dụng Thời gian Thực (Real-Time Feasibility)
        - Phân tích chỉ số FPS Trung Bình và Độ Trễ Trung Bình (ms). Hệ thống có đáp ứng yêu cầu thời gian thực (ví dụ: > 15 FPS) hay không?
        - Đánh giá sự phân tách thời gian: Thành phần nào đang chiếm ưu thế (TG Dò Khuôn Mặt hay TG Phân Tích Logic)? Nêu ý nghĩa của sự phân tách này.
        - Phân tích chuyên sâu (Deep Dive): Nếu hệ thống không đạt FPS mục tiêu, tỉ lệ nào giữa TG Dò Khuôn Mặt và TG Phân Tích Logic cần được ưu tiên giảm thiểu nhất (ví dụ: nếu TG Phân Tích Logic chiếm 80% tổng độ trễ, đây là điểm cần tối ưu hóa)?

    2. Phân tích Chi phí Tài nguyên & Rủi ro Lỗi (Resource & Risk Analysis)
        - Nhận xét về chỉ số CPU và RAM (TB/Max). Hệ thống có hiệu quả về năng lượng/tài nguyên không?
        - Nhận xét về Độ Trễ Cao Nhất (Độ lag tồi tệ nhất) và tìm khung hình gây lag (sử dụng [PHẦN 3] Chi tiết Frame) và phỏng đoán nguyên nhân. Khả năng xảy ra lỗi trễ (spikes) là gì?
        - Phân tích rủi ro quá tải: Độ trễ Cao nhất có liên quan trực tiếp đến Số Khuôn Mặt tối đa được phát hiện trong khung hình đó không? Nếu có, hệ thống có ngưỡng quá tải (bottleneck threshold) là bao nhiêu khuôn mặt?

    3. Kết luận Tổng hợp về Chất lượng Theo dõi (Stability & Quality Conclusion)
        - Dựa trên báo cáo Độ ổn định, nhận xét về Tổng TG Phát Hiện Lũy Kế (s) của các khuôn mặt. Khuôn mặt nào (ID nào) được theo dõi ổn định nhất (TG Lũy Kế cao nhất)?
        - Nếu có khuôn mặt có TG Phát Hiện Lũy Kế thấp: Đề xuất lý do (ví dụ: góc khuất, di chuyển nhanh) và khuyến nghị cho đội Data/Model.
        - Phân tích chi tiết sự mất mát: Tỉ lệ trung bình của TG Bị Mất (s) so với Tổng TG Phát Hiện Lũy Kế (s) là bao nhiêu? Tỉ lệ này cho thấy mức độ gián đoạn theo dõi trung bình của hệ thống là cao hay thấp?

    4. Phân tích Nội dung & Ý nghĩa Dữ liệu (Data Interpretation)
        - Giải thích ý nghĩa của các chỉ số chính (ví dụ: FPS TB so với Độ Trễ Cao Nhất).
        - Phân tích mối liên hệ giữa dữ liệu Hiệu năng (Tốc độ) và Độ ổn định (Chất lượng theo dõi) để rút ra insight hành vi của hệ thống (ví dụ: Tốc độ cao nhưng độ ổn định thấp có thể do mô hình dò khuôn mặt quá nhạy/bị nhiễu).

    5. Khuyến nghị Kỹ thuật Toàn diện (Comprehensive Technical Recommendation)
        - Tóm tắt quyết định Go/No-Go dựa trên sự cân bằng giữa Tốc độ và Chất lượng.
        - Đề xuất 2 hành động cụ thể nhất cho đội ngũ Phát triển để cải thiện cả hiệu năng và độ ổn định.
    """
    
    if not model:
        return "❌ LỖI: Model Gemini chưa được khởi tạo thành công do lỗi cấu hình API trước đó."
        
    try:
        print("⏳ Gemini đang phân tích tổng hợp (vui lòng đợi)...")
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"❌ Lỗi khi gọi API Gemini: {e}"

# ==========================================
# 4. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("--- BẮT ĐẦU QUÁ TRÌNH AI AUDIT TỔNG HỢP HIỆU NĂNG & ĐỘ ỔN ĐỊNH ---\n")
    
    # 1. Tìm file báo cáo mới nhất cho từng loại
    report_paths = find_latest_reports_by_type(REPORT_DIR)
    
    perf_path = report_paths['performance']
    stab_path = report_paths['stability']

    if perf_path and stab_path:
        
        # 2. Đọc dữ liệu Tóm tắt và Chi tiết từ hai file
        perf_summary_str = read_excel_sheet(perf_path, 'Tong_Hop')
        stab_summary_str = read_excel_sheet(stab_path, 'TongKet_OnDinh')
        perf_detail_str = read_excel_sheet(perf_path, 'Chi_Tiet_Frame') 
        
        # 3. Kiểm tra lỗi đọc file trước khi phân tích
        if "LỖI" in perf_summary_str or "LỖI" in stab_summary_str or "LỖI" in perf_detail_str:
            print(f"\n❌ KHÔNG THỂ PHÂN TÍCH do lỗi đọc file:")
            if "LỖI" in perf_summary_str: print(f"- Lỗi Performance Summary: {perf_summary_str}")
            if "LỖI" in stab_summary_str: print(f"- Lỗi Stability Summary: {stab_summary_str}")
            if "LỖI" in perf_detail_str: print(f"- Lỗi Performance Detail: {perf_detail_str}")
        else:
            # 4. Gửi cho Gemini để phân tích tổng hợp
            result = analyze_consolidated_results(perf_summary_str, stab_summary_str, perf_detail_str)
            
            # 5. Lưu kết quả
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"AI_Audit_CONSOLIDATED_{timestamp}.txt"
            output_path = os.path.join(REPORT_DIR, output_filename)
            
            print("\n" + "="*30 + " BÁO CÁO TỔNG HỢP HIỆU NĂNG & ĐỘ ỔN ĐỊNH " + "="*30)
            print(result)
            print("="*80)
            
            try:
                os.makedirs(REPORT_DIR, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result)
                print(f"\n✅ Đã lưu báo cáo tổng hợp vào: {output_path}")
            except Exception as e:
                print(f"❌ Lỗi khi lưu file: {e}")
            
    else:
        print("\n❌ KHÔNG THỂ THỰC HIỆN PHÂN TÍCH: Cần cả hai file báo cáo (Performance và Stability) trong thư mục 'reports'.")
