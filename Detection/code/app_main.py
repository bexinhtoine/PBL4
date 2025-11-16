import tkinter as tk
from tkinter import ttk, messagebox
import os
import traceback # <<< (1) THÊM IMPORT NÀY ĐỂ IN LỖI CHI TIẾT >>>

# --- Import các file code của bạn ---
import database
import login # Import file login.py (chứa LoginFrame)

# --- IMPORT CÁC GIAO DIỆN MỚI ---
try:
    from home import HomeFrame
    from lichsu import LichSuFrame
    from hocsinh import HocSinhFrame
    from chitiet import ChiTietFrame
    from camera import Camera
except ImportError as e:
    # Cần tạo root tạm thời để hiển thị lỗi
    root_err = tk.Tk()
    root_err.withdraw()
    messagebox.showerror("Lỗi Import", f"Không tìm thấy file: {e}\n\nHãy đảm bảo tất cả file ở cùng thư mục.")
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

    def _safe_cleanup_current_frame(self, target_page="unknown"):
        # <<< (2) TÔI ĐÃ TẠO MỘT HÀM DỌN DẸP AN TOÀN MỚI >>>
        """
        Hàm nội bộ để dọn dẹp frame hiện tại một cách an toàn
        trước khi chuyển trang.
        """
        if self.current_frame:
            try:
                # 1. Gọi on_close nếu có (để giải phóng camera, v.v.)
                if hasattr(self.current_frame, 'on_close'):
                    print(f"AppMain: Đang gọi on_close() (khi chuyển đến '{target_page}')...")
                    self.current_frame.on_close(force=True)
                    print("AppMain: on_close() hoàn tất.")
                
                # 2. Hủy widget frame
                print(f"AppMain: Đang destroy() frame cũ (khi chuyển đến '{target_page}')...")
                self.current_frame.destroy()
                print("AppMain: destroy() hoàn tất.")

            except Exception as e:
                # Bắt BẤT KỲ lỗi nào xảy ra khi dọn dẹp
                print(f"!!! LỖI NGHIÊM TRỌNG KHI DỌN DẸP FRAME (-> {target_page}): {e}")
                traceback.print_exc()
            
            # Dù sao cũng phải dọn dẹp biến này
            self.current_frame = None
            
            
    def show_login_screen(self):
        """Hiển thị màn hình đăng nhập."""
        
        print("Hiển thị màn hình đăng nhập...")
        self.user_info = None # Xóa user
        
        # <<< (3) SỬ DỤNG HÀM DỌN DẸP MỚI >>>
        self._safe_cleanup_current_frame(target_page="login")
        
        self.center_window(400, 450)
        self.root.title("Đăng nhập - Hệ thống Giám sát ATT")
            
        # Tạo và hiển thị LoginFrame (từ login.py)
        self.current_frame = login.LoginFrame(self.root, on_login_success=self.on_login_success)
        self.current_frame.pack(fill=tk.BOTH, expand=True)
        
        # Bind lại phím Enter cho đăng nhập
        self.root.bind("<Return>", lambda event: self.current_frame.attempt_login())

    def on_login_success(self, user_info):
        """
        Callback được gọi từ LoginFrame khi đăng nhập thành công.
        """
        
        print(f"Đăng nhập thành công với user: {user_info['username']}")
        self.user_info = user_info # Lưu thông tin user
        
        # <<< (4) SỬ DỤNG HÀM DỌN DẸP MỚI (chỉ destroy, không cần on_close) >>>
        if self.current_frame:
            try:
                self.current_frame.destroy()
            except Exception as e:
                print(f"Lỗi khi đóng frame login: {e}")
            
        # 1. Xóa bind phím Enter cũ (rất quan trọng)
        self.root.unbind("<Return>")
            
        # 2. Phóng to cửa sổ cho ứng dụng chính
        main_app_width = 1000 
        main_app_height = 700
        self.root.geometry(f"{main_app_width}x{main_app_height}")
        self.center_window(main_app_width, main_app_height)
        
        # 3. Hiển thị trang chủ (Home)
        self.show_home()
    
    def show_home(self):
        """Hiển thị trang chủ"""
        print("Hiển thị trang chủ...")
        
        # <<< (5) SỬ DỤNG HÀM DỌN DẸP MỚI >>>
        self._safe_cleanup_current_frame(target_page="home")
        
        # Tạo và hiển thị HomeFrame
        self.current_frame = HomeFrame(self.root, self.user_info, self.navigate, self.logout)
        self.current_frame.pack(fill=tk.BOTH, expand=True)
        self.root.title("Hệ thống Giám sát ATT - Trang chủ")
    
    def show_lichsu(self):
        """Hiển thị lịch sử buổi học"""
        print("Hiển thị lịch sử...")
        
        # <<< (6) SỬ DỤNG HÀM DỌN DẸP MỚI >>>
        self._safe_cleanup_current_frame(target_page="lichsu")
        
        # Tạo và hiển thị LichSuFrame
        self.current_frame = LichSuFrame(self.root, self.user_info, self.navigate, self.view_detail)
        self.current_frame.pack(fill=tk.BOTH, expand=True)
        self.root.title("Hệ thống Giám sát ATT - Lịch sử")
    
    def show_hocsinh(self):
        """Hiển thị quản lý học sinh"""
        print("Hiển thị quản lý học sinh...")
        
        # <<< (7) SỬ DỤNG HÀM DỌN DẸP MỚI >>>
        self._safe_cleanup_current_frame(target_page="hocsinh")
        
        # Tạo và hiển thị HocSinhFrame
        self.current_frame = HocSinhFrame(self.root, self.user_info, self.navigate)
        self.current_frame.pack(fill=tk.BOTH, expand=True)
        self.root.title("Hệ thống Giám sát ATT - Quản lý học sinh")
    
    def show_chitiet(self, seasion_id):
        """Hiển thị chi tiết buổi học"""
        print(f"Hiển thị chi tiết buổi học ID: {seasion_id}...")
        
        # <<< (8) SỬ DỤNG HÀM DỌN DẸP MỚI >>>
        self._safe_cleanup_current_frame(target_page="chitiet")
        
        # Tạo và hiển thị ChiTietFrame
        self.current_frame = ChiTietFrame(self.root, self.user_info, seasion_id, self.navigate)
        self.current_frame.pack(fill=tk.BOTH, expand=True)
        self.root.title("Hệ thống Giám sát ATT - Chi tiết buổi học")
    
    def show_camera(self):
        """Hiển thị màn hình camera"""
        print("Hiển thị màn hình camera...")
        
        # <<< (9) SỬ DỤNG HÀM DỌN DẸP MỚI >>>
        self._safe_cleanup_current_frame(target_page="camera")
        
        try:
            # Tạo và hiển thị CameraFrame
            self.current_frame = Camera(self.root, self.user_info, self.navigate)
            self.current_frame.pack(fill=tk.BOTH, expand=True)
            self.root.title("Hệ thống Giám sát ATT - Tạo buổi học")
        
        except Exception as e:
            # Khối này bắt lỗi KHI KHỞI TẠO camera
            print(f"!!! LỖI NGHIÊM TRỌNG KHI KHỞI TẠO CAMERA: {e}")
            traceback.print_exc()
            
            messagebox.showerror(
                "Lỗi Camera",
                f"Không thể khởi động chức năng camera.\n\nLỗi: {e}\n\n"
                "Vui lòng kiểm tra camera hoặc file cấu hình model."
            )
            
            # Tự động quay về trang chủ một cách an toàn
            self.show_home()
    
    def navigate(self, page_name):
        """
        Hàm điều hướng chung cho tất cả các frame
        """
        if page_name == 'home':
            self.show_home()
        elif page_name == 'lichsu':
            self.show_lichsu()
        elif page_name == 'hocsinh':
            self.show_hocsinh()
        elif page_name == 'camera':
            self.show_camera()
        else:
            print(f"Trang không xác định: {page_name}")
    
    def view_detail(self, seasion_id):
        """Callback để xem chi tiết buổi học từ LichSuFrame"""
        self.show_chitiet(seasion_id)
    
    def logout(self):
        """Đăng xuất và quay về màn hình đăng nhập"""
        print("Đăng xuất...")
        # show_login_screen đã có hàm dọn dẹp an toàn
        self.show_login_screen()

    def center_window(self, width, height):
        """Hàm tiện ích để căn giữa cửa sổ root."""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

# ==========================================================
# KHỐI CHẠY CHÍNH
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
    app_controller = MainApplication(root)
    
    # 4. Bắt đầu vòng lặp Tkinter
    print("Đang hiển thị cửa sổ đăng nhập...")
    root.mainloop()
    print("Ứng dụng đã đóng.")