import pytest
import sys
import os
import tkinter as tk
import threading

# --- 1. CẤU HÌNH ĐƯỜNG DẪN IMPORT ---
current_dir = os.path.dirname(os.path.abspath(__file__))
# Lùi ra thư mục Detection
detection_dir = os.path.abspath(os.path.join(current_dir, '..'))
# Vào thư mục code
code_dir = os.path.join(detection_dir, 'code')

if code_dir not in sys.path:
    sys.path.insert(0, code_dir)
    print(f"[Path] Đã thêm đường dẫn code: {code_dir}")

import app_main
import database

# --- 2. CẤU HÌNH ĐƯỜNG DẪN VIDEO ---
# Lùi ra khỏi Detection để về thư mục gốc chứa Input_video
project_root = os.path.abspath(os.path.join(detection_dir, '..'))
DEFAULT_VIDEO_PATH = os.path.join(project_root, "Input_video", "Untitled video.mp4")

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    print("\n[Setup] Khởi tạo DB...")
    try:
        database.init_db()
    except Exception as e:
        print(f"Cảnh báo DB: {e}")
    yield

@pytest.fixture(scope="function")
def app_context():
    """Tạo cửa sổ App cho mỗi bài test và HIỂN THỊ LÊN."""
    root = tk.Tk()
    
    # --- QUAN TRỌNG: CẤU HÌNH HIỂN THỊ CỬA SỔ ---
    root.deiconify()       # Bỏ chế độ ẩn (nếu có)
    root.state('normal')   # Đặt trạng thái bình thường
    root.lift()            # Đưa cửa sổ lên trên cùng các cửa sổ khác
    root.attributes('-topmost', True)  # Ghim lên trên cùng
    root.after(1000, lambda: root.attributes('-topmost', False)) # Sau 1 giây thì bỏ ghim để dùng chuột được
    
    app = app_main.MainApplication(root)
    
    # Cập nhật GUI ngay lập tức
    root.update_idletasks()
    root.update()
    
    print(" [App] Cửa sổ ứng dụng đã được hiển thị.")
    
    yield root, app
    
    try:
        if app.current_frame and hasattr(app.current_frame, 'stop'):
            app.current_frame.stop()
        root.destroy()
    except:
        pass

@pytest.fixture(scope="session")
def real_video_path():
    """Trả về đường dẫn video test"""
    if os.path.exists(DEFAULT_VIDEO_PATH):
        print(f"[Video] Tìm thấy tại: {DEFAULT_VIDEO_PATH}")
        return DEFAULT_VIDEO_PATH
    
    # Fallback cứng (đường dẫn tuyệt đối của bạn)
    hardcoded_path = r"D:\STUDY_YOLOV8 - Copy\STUDY_YOLOV8 - Copy - Copy\Input_video\Untitled video.mp4"
    if os.path.exists(hardcoded_path):
        print(f"[Video] Tìm thấy tại (hardcoded): {hardcoded_path}")
        return hardcoded_path
        
    pytest.skip(f"KHÔNG TÌM THẤY VIDEO TẠI: {DEFAULT_VIDEO_PATH}")