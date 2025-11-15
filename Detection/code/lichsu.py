import tkinter as tk
from tkinter import ttk, messagebox
import database
from datetime import datetime

class LichSuFrame(tk.Frame):
    """
    Màn hình lịch sử các buổi học
    Cho phép xem danh sách, xóa và xem chi tiết
    """
    def __init__(self, parent, user_info, on_navigate, on_view_detail):
        """
        parent: Widget cha
        user_info: Thông tin người dùng
        on_navigate: Callback để quay về trang chủ hoặc chuyển trang
        on_view_detail: Callback để xem chi tiết buổi học (nhận tham số: seasion_id)
        """
        super().__init__(parent, bg='#f0f0f0')
        self.parent = parent
        self.user_info = user_info
        self.on_navigate = on_navigate
        self.on_view_detail = on_view_detail
        
        self.create_widgets()
        self.load_sessions()
    
    def create_widgets(self):
        """Tạo giao diện lịch sử"""
        
        # === HEADER ===
        header_frame = tk.Frame(self, bg='#2c3e50', height=80)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)
        
        # Nút quay lại
        btn_back = tk.Button(
            header_frame,
            text="← Quay lại",
            font=('Arial', 10),
            bg='#34495e',
            fg='black',
            cursor='hand2',
            command=lambda: self.on_navigate('home'),
            relief=tk.FLAT,
            padx=15,
            pady=5
        )
        btn_back.place(x=20, y=25)
        
        # Tiêu đề
        title_label = tk.Label(
            header_frame,
            text="LỊCH SỬ CÁC BUỔI HỌC",
            font=('Arial', 20, 'bold'),
            bg='#2c3e50',
            fg='white'
        )
        title_label.pack(pady=25)
        
        # === TOOLBAR ===
        toolbar_frame = tk.Frame(self, bg='#ecf0f1', height=50)
        toolbar_frame.pack(fill=tk.X, padx=10, pady=10)
        toolbar_frame.pack_propagate(False)
        
        # Nút làm mới
        btn_refresh = tk.Button(
            toolbar_frame,
            text="🔄 Làm mới",
            font=('Arial', 10),
            bg='#3498db',
            fg='black',
            cursor='hand2',
            command=self.load_sessions,
            relief=tk.RAISED,
            padx=15,
            pady=5
        )
        btn_refresh.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Tìm kiếm theo lớp
        tk.Label(
            toolbar_frame,
            text="Tìm lớp:",
            font=('Arial', 10),
            bg='#ecf0f1'
        ).pack(side=tk.LEFT, padx=(20, 5), pady=10)
        
        self.search_entry = tk.Entry(
            toolbar_frame,
            font=('Arial', 10),
            width=20
        )
        self.search_entry.pack(side=tk.LEFT, pady=10)
        self.search_entry.bind('<KeyRelease>', lambda e: self.search_sessions())
        
        btn_clear_search = tk.Button(
            toolbar_frame,
            text="✖ Xóa",
            font=('Arial', 9),
            bg='#95a5a6',
            fg='black',
            cursor='hand2',
            command=self.clear_search,
            relief=tk.RAISED,
            padx=10,
            pady=5
        )
        btn_clear_search.pack(side=tk.LEFT, padx=5, pady=10)
        
        # === TREEVIEW (BẢNG DỮ LIỆU) ===
        table_frame = tk.Frame(self, bg='white')
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbars
        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        
        # Treeview
        columns = ('ID', 'Lớp', 'Thời gian bắt đầu', 'Thời gian kết thúc', 'Ngày tạo')
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            selectmode='browse'
        )
        
        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)
        
        # Định nghĩa cột
        self.tree.heading('ID', text='ID')
        self.tree.heading('Lớp', text='Lớp')
        self.tree.heading('Thời gian bắt đầu', text='Thời gian bắt đầu')
        self.tree.heading('Thời gian kết thúc', text='Thời gian kết thúc')
        self.tree.heading('Ngày tạo', text='Ngày tạo')
        
        # Độ rộng cột
        self.tree.column('ID', width=60, anchor='center')
        self.tree.column('Lớp', width=150, anchor='w')
        self.tree.column('Thời gian bắt đầu', width=200, anchor='center')
        self.tree.column('Thời gian kết thúc', width=200, anchor='center')
        self.tree.column('Ngày tạo', width=200, anchor='center')
        
        # Pack
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Style cho Treeview
        style = ttk.Style()
        style.configure("Treeview",
                       font=('Arial', 10),
                       rowheight=30)
        style.configure("Treeview.Heading",
                       font=('Arial', 11, 'bold'),
                       background='#34495e',
                       foreground='white')
        
        # Màu xen kẽ cho các hàng
        self.tree.tag_configure('oddrow', background='#f9f9f9')
        self.tree.tag_configure('evenrow', background='#ffffff')
        
        # === ACTION BUTTONS ===
        action_frame = tk.Frame(self, bg='#ecf0f1', height=60)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        action_frame.pack_propagate(False)
        
        btn_view_detail = tk.Button(
            action_frame,
            text="👁 Xem chi tiết",
            font=('Arial', 11, 'bold'),
            bg='#3498db',
            fg='black',
            cursor='hand2',
            command=self.view_detail,
            relief=tk.RAISED,
            padx=20,
            pady=10
        )
        btn_view_detail.pack(side=tk.LEFT, padx=10, pady=10)
        
        btn_delete = tk.Button(
            action_frame,
            text="🗑 Xóa buổi học",
            font=('Arial', 11, 'bold'),
            bg='#e74c3c',
            fg='black',
            cursor='hand2',
            command=self.delete_session,
            relief=tk.RAISED,
            padx=20,
            pady=10
        )
        btn_delete.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Thống kê
        self.stats_label = tk.Label(
            action_frame,
            text="Tổng số buổi học: 0",
            font=('Arial', 10),
            bg='#ecf0f1',
            fg='#2c3e50'
        )
        self.stats_label.pack(side=tk.RIGHT, padx=20, pady=10)
    
    def load_sessions(self):
        """Tải danh sách các buổi học từ database"""
        # Xóa dữ liệu cũ
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            # Lấy dữ liệu từ database
            conn = database.get_db_connection()
            if conn is None:
                messagebox.showerror("Lỗi", "Không thể kết nối database")
                return
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT seasion_id, class_name, start_time, end_time, created_at
                FROM seasion
                ORDER BY created_at DESC
            """)
            sessions = cursor.fetchall()
            
            # Thêm vào Treeview
            for idx, session in enumerate(sessions):
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
                
                # Format datetime
                start_time = session['start_time'].strftime('%Y-%m-%d %H:%M:%S') if session['start_time'] else ''
                end_time = session['end_time'].strftime('%Y-%m-%d %H:%M:%S') if session['end_time'] else ''
                created_at = session['created_at'].strftime('%Y-%m-%d %H:%M:%S') if session['created_at'] else ''
                
                self.tree.insert('', 'end', values=(
                    session['seasion_id'],
                    session['class_name'],
                    start_time,
                    end_time,
                    created_at
                ), tags=(tag,))
            
            # Cập nhật thống kê
            self.stats_label.config(text=f"Tổng số buổi học: {len(sessions)}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tải dữ liệu:\n{e}")
    
    def search_sessions(self):
        """Tìm kiếm buổi học theo tên lớp"""
        search_text = self.search_entry.get().strip().lower()
        
        # Xóa dữ liệu hiện tại
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            conn = database.get_db_connection()
            if conn is None:
                return
            
            cursor = conn.cursor(dictionary=True)
            
            if search_text:
                # Tìm kiếm với LIKE
                cursor.execute("""
                    SELECT seasion_id, class_name, start_time, end_time, created_at
                    FROM seasion
                    WHERE LOWER(class_name) LIKE %s
                    ORDER BY created_at DESC
                """, (f'%{search_text}%',))
            else:
                # Hiển thị tất cả
                cursor.execute("""
                    SELECT seasion_id, class_name, start_time, end_time, created_at
                    FROM seasion
                    ORDER BY created_at DESC
                """)
            
            sessions = cursor.fetchall()
            
            # Thêm vào Treeview
            for idx, session in enumerate(sessions):
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
                
                start_time = session['start_time'].strftime('%Y-%m-%d %H:%M:%S') if session['start_time'] else ''
                end_time = session['end_time'].strftime('%Y-%m-%d %H:%M:%S') if session['end_time'] else ''
                created_at = session['created_at'].strftime('%Y-%m-%d %H:%M:%S') if session['created_at'] else ''
                
                self.tree.insert('', 'end', values=(
                    session['seasion_id'],
                    session['class_name'],
                    start_time,
                    end_time,
                    created_at
                ), tags=(tag,))
            
            # Cập nhật thống kê
            self.stats_label.config(text=f"Tổng số buổi học: {len(sessions)}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi tìm kiếm:\n{e}")
    
    def clear_search(self):
        """Xóa ô tìm kiếm và tải lại toàn bộ"""
        self.search_entry.delete(0, tk.END)
        self.load_sessions()
    
    def view_detail(self):
        """Xem chi tiết buổi học đã chọn"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một buổi học!")
            return
        
        # Lấy ID buổi học
        item = self.tree.item(selected[0])
        seasion_id = item['values'][0]
        
        # Gọi callback
        self.on_view_detail(seasion_id)
    
    def delete_session(self):
        """Xóa buổi học đã chọn"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một buổi học để xóa!")
            return
        
        # Lấy thông tin buổi học
        item = self.tree.item(selected[0])
        seasion_id = item['values'][0]
        class_name = item['values'][1]
        
        # Xác nhận xóa
        confirm = messagebox.askyesno(
            "Xác nhận xóa",
            f"Bạn có chắc chắn muốn xóa buổi học:\n\n"
            f"ID: {seasion_id}\n"
            f"Lớp: {class_name}\n\n"
            f"Lưu ý: Tất cả dữ liệu điểm danh và tập trung liên quan sẽ bị xóa!"
        )
        
        if not confirm:
            return
        
        try:
            conn = database.get_db_connection()
            if conn is None:
                messagebox.showerror("Lỗi", "Không thể kết nối database")
                return
            
            cursor = conn.cursor()
            
            # Xóa buổi học (CASCADE sẽ tự động xóa focus_record)
            cursor.execute("DELETE FROM seasion WHERE seasion_id = %s", (seasion_id,))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            messagebox.showinfo("Thành công", "Đã xóa buổi học thành công!")
            
            # Tải lại danh sách
            self.load_sessions()
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xóa buổi học:\n{e}")


# Test frame
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test Lịch Sử Frame")
    root.geometry("1200x700")
    
    test_user = {"username": "admin"}
    
    def test_navigate(page):
        print(f"Điều hướng đến: {page}")
    
    def test_view_detail(seasion_id):
        print(f"Xem chi tiết buổi học ID: {seasion_id}")
    
    frame = LichSuFrame(root, test_user, test_navigate, test_view_detail)
    frame.pack(fill=tk.BOTH, expand=True)
    
    root.mainloop()
