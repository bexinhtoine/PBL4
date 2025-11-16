import google.generativeai as genai
import os
import traceback

# !!! QUAN TRỌNG: Dán API Key của bạn vào đây
# (Cách tốt hơn là dùng biến môi trường, nhưng để đơn giản, 
# bạn có thể dán trực tiếp vào đây)
try:
    # (Tùy chọn: Thử lấy từ biến môi trường trước)
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    if not GOOGLE_API_KEY:
        # Nếu không có, dùng key bạn dán vào
        GOOGLE_API_KEY = "DAN API VAO DAY" # <--- !!! THAY THẾ CHỖ NÀY
        
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"Lỗi cấu hình Google AI. Hãy chắc chắn bạn đã cài đặt thư viện và dán API Key. Lỗi: {e}")
    genai = None

# Cấu hình model (dùng Flash cho tốc độ)
try:
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

except Exception as e:
    print(f"Không thể khởi tạo model Gemini: {e}")
    model = None

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
                (ts, reason, change) = item[:3]
                op = "+" if change > 0 else ""
                log_strings.append(f"{reason} ({op}{change})")
            else:
                log_strings.append(str(item))
        log_input_text = ", ".join(log_strings)
    except Exception as e:
        print(f"Lỗi khi xử lý log_list: {e}")
        log_input_text = str(logs_list) # Gửi thô

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
        
        # In ra để debug (bạn có thể xóa sau)
        # print(f"-> Gemini Prompt: {prompt}")
        # print(f"-> Gemini Response: {response.text}")
        
        return response.text.strip()
        
    except Exception as e:
        print(f"Lỗi khi gọi Gemini API: {e}")
        traceback.print_exc()
        # Trả về log thô nếu API lỗi
        # [SỬA] Chuyển str(e) thành chuỗi để tránh lỗi [WinError 6]
        error_message = str(e)
        return f"Lỗi API: {error_message}. Logs: {log_input_text[:500]}..."

# --- Hàm test (chạy file này trực tiếp để kiểm tra) ---
if __name__ == "__main__":
    print("Đang kiểm tra AI Summarizer...")
    # Giả lập 2 trường hợp
    
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