import google.generativeai as genai
import os
import traceback

# --- 1. CẤU HÌNH API & MODEL ---

# !!! LƯU Ý BẢO MẬT: API Key này hiện đang hiển thị trực tiếp trong code. 
# Nếu bạn chia sẻ code này (vd: lên GitHub), hãy xóa key hoặc dùng biến môi trường.
GEMINI_API_KEY = "DAN API KEY VAOÀO DĐAÂY"

try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    else:
        print("CẢNH BÁO: GEMINI_API_KEY đang trống.")
except Exception as e:
    print(f"Lỗi cấu hình API Key: {e}")

# Cấu hình tham số sinh văn bản (Temperature, Token limit, v.v.)
generation_config = {
    'temperature': 0.1,      # Độ sáng tạo thấp (0.1) giúp kết quả ổn định, ít bịa đặt
    'top_p': 0.8,
    'top_k': 40,
    'max_output_tokens': 8192,
}

# Khởi tạo model với cấu hình đã thiết lập
try:
    model = genai.GenerativeModel(
        model_name='gemini-2.0-flash', # Hoặc dùng 'gemini-1.5-flash'
        generation_config=generation_config   # <--- ĐÃ THÊM CẤU HÌNH VÀO ĐÂY
    )
except Exception as e:
    print(f"Không thể khởi tạo model Gemini: {e}")
    model = None

# --- 2. CÁC HÀM XỬ LÝ ---

def summarize_focus_logs(logs_list):
    """
    Sử dụng Gemini API để tóm tắt danh sách log.
    'logs_list' được kỳ vọng là danh sách các (timestamp, reason, point_change)
    hoặc một danh sách các chuỗi log thô.
    """
    if not model:
        print("Model AI chưa được khởi tạo. Trả về log thô.")
        return f"Lỗi AI: Model chưa khởi tạo. Logs: {str(logs_list)}"

    if not logs_list:
        return "Không có ghi nhận chi tiết."

    # 1. Chuyển đổi logs_list thành một chuỗi đơn giản
    log_strings = []
    try:
        for item in logs_list:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                # Giả sử format là (timestamp, lý do, điểm thay đổi)
                (ts, reason, change) = item[:3]
                op = "+" if change > 0 else ""
                log_strings.append(f"{reason} ({op}{change})")
            else:
                log_strings.append(str(item))
        
        log_input_text = ", ".join(log_strings)
    except Exception as e:
        print(f"Lỗi khi xử lý log_list: {e}")
        log_input_text = str(logs_list) # Gửi thô nếu lỗi format

    if not log_input_text:
        return "Không có ghi nhận chi tiết."

    # 2. Tạo Prompt (câu lệnh) cho AI
    prompt = f"""
    Bạn là một trợ lý giáo viên. Nhiệm vụ của bạn là xem danh sách các hành vi 
    cộng trừ điểm tập trung của một học sinh và viết một ghi chú nhận xét tóm tắt 
    (dưới 200 ký tự) bằng tiếng Việt.

    KHÔNG dùng markdown. CHỈ trả về một chuỗi văn bản thuần túy.

    Danh sách hành vi:
    "{log_input_text}"

    Ghi chú tóm tắt (ví dụ: "Tập trung tốt, thỉnh thoảng nhìn sang trái nhưng có giơ tay phát biểu."):
    """

    # 3. Gọi API
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        print(f"Lỗi khi gọi Gemini API: {e}")
        traceback.print_exc()
        error_message = str(e)
        return f"Lỗi API: {error_message}. Logs: {log_input_text[:500]}..."

# --- 3. HÀM TEST (Chạy trực tiếp) ---
if __name__ == "__main__":
    print("Đang kiểm tra AI Summarizer với Config mới...")
    
    # TH1: Có log
    test_logs = [
        (123, "nhìn sang trái", -1),
        (124, "nhìn sang trái", -1),
        (125, "giơ tay", 1),
        (126, "sử dụng điện thoại", -2),
        (127, "nhìn thẳng", 1),
        (128, "nhìn sang trái", -1)
    ]
    
    print(f"\nĐang test với {len(test_logs)} logs:")
    summary1 = summarize_focus_logs(test_logs)
    print(f"Kết quả tóm tắt:\n{summary1}")

    # TH2: Không có log
    print("\nĐang test với 0 logs:")
    summary2 = summarize_focus_logs([])
    print(f"Kết quả tóm tắt:\n{summary2}")