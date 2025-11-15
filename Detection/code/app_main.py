import tkinter as tk
from tkinter import ttk, messagebox
import os

# --- Import các file code của bạn ---
import database
import login # Import file login.py (chứa LoginFrame)
import camera

# --- IMPORT MỚI ---
# Import class App (giao diện camera) từ file camera.py
try:
    from camera import Camera
except ImportError as e:
    # Cần tạo root tạm thời để hiển thị lỗi
    root_err = tk.Tk()
    root_err.withdraw()
    messagebox.showerror("Lỗi Import", f"Không tìm thấy file camera.py: {e}\n\nHãy đảm bảo file camera.py ở cùng thư mục.")
    root_err.destroy()
    exit()
        
# ==========================================================
# LỚP ĐIỀU KHIỂN CHÍNH (Application Controller)
# ==========================================================
class MainApplication:
    """
    Lớp này điều khiển việc hiển thị các màn hình (Frame)
    bên trong cửa sổ 'root' chính.
    """
    def __init__(self, root):
        self.root = root
        self.current_frame = None
        self.user_info = None # Sẽ lưu thông tin user sau khi login
        
        # Bắt đầu bằng việc hiển thị màn hình đăng nhập
        self.show_login_screen()

    def show_login_screen(self):
        """Hiển thị màn hình đăng nhập."""
        
        print("Hiển thị màn hình đăng nhập...")
        self.user_info = None # Xóa user
        self.center_window(400, 450)
        self.root.title("Đăng nhập - Hệ thống Giám sát ATT")
        
        # Dọn dẹp frame cũ (nếu có)
        if self.current_frame:
            # Nếu frame cũ là camera, gọi hàm on_close(force=True)
            if hasattr(self.current_frame, 'on_close'):
                try:
                    # force=True để nó đóng ngay mà không hỏi
                    self.current_frame.on_close(force=True) 
                except Exception as e:
                    print(f"Lỗi khi đóng camera: {e}")
            self.current_frame.destroy()
            
        # Tạo và hiển thị LoginFrame (từ login.py)
        self.current_frame = login.LoginFrame(self.root, on_login_success=self.on_login_success)
        self.current_frame.pack(fill=tk.BOTH, expand=True)
        
        # Bind lại phím Enter cho đăng nhập
        self.root.bind("<Return>", lambda event: self.current_frame.attempt_login())

    def on_login_success(self, user_info):
        """
        Callback được gọi từ LoginFrame khi đăng nhập thành công.
        Đây là nơi chuyển hướng đến camera.py
        """
        
        print(f"Đăng nhập thành công với user: {user_info['username']}")
        self.user_info = user_info # Lưu thông tin user
        
        # Xóa frame đăng nhập
        if self.current_frame:
            self.current_frame.destroy()
            
        # 1. Xóa bind phím Enter cũ (rất quan trọng)
        self.root.unbind("<Return>")
            
        # 2. Phóng to cửa sổ cho ứng dụng chính
        # (Kích thước này là tổng kích thước của giao diện camera)
        main_app_width = 1400 
        main_app_height = 800
        self.root.geometry(f"{main_app_width}x{main_app_height}")
        self.center_window(main_app_width, main_app_height)
        
        # 3. Tạo và hiển thị Camera (màn hình chính, từ camera.py)
        self.current_frame = camera.Camera(self.root, user_info)
        self.current_frame.pack(fill=tk.BOTH, expand=True)
        self.root.title("Hệ thống Giám sát ATT")

    def center_window(self, width, height):
        """Hàm tiện ích để căn giữa cửa sổ root."""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

# ==========================================================
# KHỐI CHẠY CHÍNH (ĐIỂM BẮT ĐẦU CỦA ỨNG DỤNG)
# ==========================================================
if __name__ == "__main__":

    # 1. Khởi tạo CSDL
    try:
        database.init_db()
        try:
            # Thêm tài khoản 'admin'/'admin' nếu chưa có
            conn = database.get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT IGNORE INTO account (username, password) 
                    VALUES (%s, %s)
                """, ("admin", "admin"))
                conn.commit()
                cursor.close()
                conn.close()
                print("Đã kiểm tra/thêm tài khoản admin.")
        except Exception as e:
            print(f"Lỗi khi thêm admin (có thể bỏ qua): {e}")
            
    except Exception as e:
        # Lỗi nghiêm trọng: không kết nối được CSDL
        root_err = tk.Tk()
        root_err.withdraw()
        messagebox.showerror("Lỗi CSDL", f"Không thể kết nối hoặc khởi tạo CSDL.\n{e}\n\nVui lòng kiểm tra file 'database.py' và MySQL server.")
        root_err.destroy()
        exit()

    # 2. Tạo cửa sổ root (chỉ 1 lần)
    root = tk.Tk()
    
    # 3. Khởi tạo bộ điều khiển ứng dụng
    # Bộ điều khiển này sẽ tự lo việc hiển thị màn hình đăng nhập
    app_controller = MainApplication(root)
    
    # 4. Bắt đầu vòng lặp Tkinter
    print("Đang hiển thị cửa sổ đăng nhập...")
    root.mainloop()
    print("Ứng dụng đã đóng.")