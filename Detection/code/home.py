import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import os

class HomeFrame(tk.Frame):
    """
    Màn hình trang chủ với các nút điều hướng chính
    """
    def __init__(self, parent, user_info, on_navigate, on_logout=None):
        """
        parent: Widget cha
        user_info: Thông tin người dùng đã đăng nhập
        on_navigate: Callback để chuyển trang (nhận tham số: tên_trang)
        on_logout: Callback để đăng xuất
        """
        super().__init__(parent, bg='#f0f0f0')
        self.parent = parent
        self.user_info = user_info
        self.on_navigate = on_navigate
        self.on_logout = on_logout
        
        self.create_widgets()
    
    def create_widgets(self):
        """Tạo giao diện trang chủ"""
        
        # === HEADER ===
        header_frame = tk.Frame(self, bg='#2c3e50', height=80)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)
        
        # Tiêu đề (căn trái, font nhỏ hơn)
        title_label = tk.Label(
            header_frame,
            text="HỆ THỐNG GIÁM SÁT ĐIỂM DANH & TẬP TRUNG",
            font=('Arial', 18, 'bold'),
            bg='#2c3e50',
            fg='white'
        )
        title_label.place(x=20, rely=0.5, anchor='w')
        
        # Nút đăng xuất
        btn_logout = tk.Button(
            header_frame,
            text="🚪 Đăng xuất",
            font=('Arial', 10),
            bg='#e74c3c',
            fg='black',
            cursor='hand2',
            command=self.logout,
            relief=tk.RAISED,
            padx=15,
            pady=5
        )
        btn_logout.place(relx=0.95, rely=0.5, anchor='e')
        
        # === MAIN CONTENT ===
        main_frame = tk.Frame(self, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=50)
        
        # Container cho các nút
        buttons_frame = tk.Frame(main_frame, bg='#f0f0f0')
        buttons_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        # Cấu hình style cho các nút
        button_style = {
            'font': ('Arial', 14, 'bold'),
            'width': 25,
            'height': 3,
            'relief': tk.RAISED,
            'bd': 3,
            'cursor': 'hand2'
        }
        
        # === CÁC NÚT CHỨC NĂNG ===
        
        # Nút Trang chủ (hiện tại)
        btn_home = tk.Button(
            buttons_frame,
            text="🏠 TRANG CHỦ",
            bg='#3498db',
            fg='black',
            activebackground='#2980b9',
            activeforeground='black',
            **button_style
        )
        btn_home.grid(row=0, column=0, padx=20, pady=15)
        # Vô hiệu hóa vì đang ở trang chủ
        btn_home.config(state='disabled')
        
        # Nút Tạo buổi học (chưa implement)
        btn_create_session = tk.Button(
            buttons_frame,
            text="📝 TẠO BUỔI HỌC",
            bg='#27ae60',
            fg='black',
            activebackground='#229954',
            activeforeground='black',
            command=lambda: self.on_navigate('camera'),
            **button_style
        )
        btn_create_session.grid(row=1, column=0, padx=20, pady=15)
        
        # Nút Lịch sử
        btn_history = tk.Button(
            buttons_frame,
            text="📚 LỊCH SỬ BUỔI HỌC",
            bg='#e74c3c',
            fg='black',
            activebackground='#c0392b',
            activeforeground='black',
            command=lambda: self.on_navigate('lichsu'),
            **button_style
        )
        btn_history.grid(row=2, column=0, padx=20, pady=15)
        
        # Nút Quản lý học sinh
        btn_students = tk.Button(
            buttons_frame,
            text="👥 QUẢN LÝ HỌC SINH",
            bg='#f39c12',
            fg='black',
            activebackground='#d68910',
            activeforeground='black',
            command=lambda: self.on_navigate('hocsinh'),
            **button_style
        )
        btn_students.grid(row=3, column=0, padx=20, pady=15)
        
        # === FOOTER ===
        footer_frame = tk.Frame(self, bg='#34495e', height=40)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        footer_frame.pack_propagate(False)
        
        footer_label = tk.Label(
            footer_frame,
            text="© 2024 Hệ thống Giám sát ATT - Phiên bản 1.0",
            font=('Arial', 9),
            bg='#34495e',
            fg='#bdc3c7'
        )
        footer_label.pack(pady=10)
        
        # Thêm hiệu ứng hover cho các nút
        self.add_hover_effects(btn_home, '#3498db', '#2980b9')
        self.add_hover_effects(btn_create_session, '#27ae60', '#229954')
        self.add_hover_effects(btn_history, '#e74c3c', '#c0392b')
        self.add_hover_effects(btn_students, '#f39c12', '#d68910')
    
    def add_hover_effects(self, button, normal_color, hover_color):
        """Thêm hiệu ứng hover cho nút"""
        if button['state'] == 'disabled':
            return
            
        def on_enter(e):
            button['background'] = hover_color
        
        def on_leave(e):
            button['background'] = normal_color
        
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
    
    def logout(self):
        """Đăng xuất và quay về màn hình đăng nhập"""
        confirm = messagebox.askyesno(
            "Xác nhận đăng xuất",
            "Bạn có chắc chắn muốn đăng xuất?"
        )
        if confirm:
            # Gọi callback để quay về login (cần truyền từ app_main)
            if hasattr(self, 'on_logout') and self.on_logout:
                self.on_logout()
            else:
                # Fallback: đóng cửa sổ
                self.master.quit()


# Test frame nếu chạy riêng file này
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test Home Frame")
    root.geometry("1000x700")
    
    # Mock user info và callback
    test_user = {"username": "admin"}
    
    def test_navigate(page):
        print(f"Điều hướng đến: {page}")
    
    frame = HomeFrame(root, test_user, test_navigate)
    frame.pack(fill=tk.BOTH, expand=True)
    
    root.mainloop()
