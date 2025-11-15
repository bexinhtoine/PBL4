import tkinter as tk
from tkinter import ttk, messagebox
import database # Import file CSDL của bạn

# ===================================================================
# LỚP NÀY THAY THẾ CHO `login.html` VÀ `login_view`
# (Phiên bản ttk.Frame - Khung giao diện)
# ===================================================================
class LoginFrame(ttk.Frame):
    """
    Đây KHÔNG còn là cửa sổ Toplevel, mà là một Frame
    để đặt vào cửa sổ 'root' chính.
    """
    def __init__(self, master, on_login_success):
        super().__init__(master, padding=30)
        
        # Lưu lại hàm callback để gọi khi đăng nhập thành công
        self.on_login_success = on_login_success 
        
        self.logged_in_user = None
        
        # --- Cấu hình style (giống hệt code cũ) ---
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 11, "bold"))
        style.configure("TEntry", font=("Segoe UI", 10))
        style.configure("TCheckbutton", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Error.TLabel", font=("Segoe UI", 10), foreground="red")
        
        # --- Frame chính (căn giữa) ---
        # Chúng ta tạo một frame con để giữ nội dung
        # và dùng pack(expand=True) để nó tự căn giữa
        center_frame = ttk.Frame(self)
        center_frame.pack(expand=True)

        # --- "login-header" ---
        ttk.Label(center_frame, text="Đăng nhập", style="Header.TLabel").pack(pady=10)
        ttk.Label(center_frame, text="Vui lòng nhập thông tin để truy cập").pack(pady=(0, 20))

        # --- "alert" (Khu vực thông báo lỗi) ---
        self.message_label = ttk.Label(center_frame, text="", style="Error.TLabel")
        self.message_label.pack(pady=(0, 10))

        # --- "login-form" (Frame cho form) ---
        form_frame = ttk.Frame(center_frame)
        form_frame.pack(fill=tk.X)

        # --- Trường Username ---
        ttk.Label(form_frame, text="Tên đăng nhập").pack(anchor="w")
        self.username_entry = ttk.Entry(form_frame)
        self.username_entry.pack(fill=tk.X, pady=(5, 15), ipady=4)

        # --- Trường Password ---
        ttk.Label(form_frame, text="Mật khẩu").pack(anchor="w")
        password_frame = ttk.Frame(form_frame)
        password_frame.pack(fill=tk.X, pady=(5, 10))
        self.password_entry = ttk.Entry(password_frame, show="*")
        self.password_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, ipady=4)
        self.toggle_btn = ttk.Button(password_frame, text="Hiện", 
                                     width=5, command=self.toggle_password)
        self.toggle_btn.pack(side=tk.LEFT, padx=(5, 0))

        # --- Tùy chọn (Remember me) ---
        self.remember_me_var = tk.BooleanVar(value=False)
        check = ttk.Checkbutton(form_frame, text="Ghi nhớ đăng nhập", 
                                variable=self.remember_me_var)
        check.pack(anchor="w", pady=(0, 20))

        # --- Nút "login-btn" ---
        self.login_btn = ttk.Button(form_frame, text="Đăng nhập", 
                                    style="TButton", command=self.attempt_login)
        self.login_btn.pack(fill=tk.X, ipady=8, pady=10)
        
        # Bind phím Enter (chúng ta bind vào 'master' - cửa sổ root)
        master.bind("<Return>", self.attempt_login)
        self.username_entry.focus()

    def toggle_password(self):
        if self.password_entry.cget('show') == '*':
            self.password_entry.config(show='')
            self.toggle_btn.config(text="Ẩn")
        else:
            self.password_entry.config(show='*')
            self.toggle_btn.config(text="Hiện")

    def attempt_login(self, event=None):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            self.show_error("Vui lòng nhập cả Tên và Mật khẩu!")
            return

        try:
            ok, result = database.verify_account(username, password)
            
            if ok:
                # ĐĂNG NHẬP THÀNH CÔNG
                self.logged_in_user = result
                # Gọi hàm callback đã được truyền vào
                self.on_login_success(self.logged_in_user) 
            else:
                # ĐĂNG NHẬP THẤT BẠI
                self.show_error(result)
                
        except Exception as e:
            self.show_error(f"Lỗi hệ thống: {e}")
            
    def show_error(self, message):
        self.message_label.config(text=message)