import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import database
from datetime import datetime
from PIL import Image, ImageTk
import os

class HocSinhFrame(tk.Frame):
    """
    Màn hình quản lý học sinh
    Chức năng: Xem danh sách, cập nhật, xóa (không có tạo mới)
    """
    def __init__(self, parent, user_info, on_navigate):
        """
        parent: Widget cha
        user_info: Thông tin người dùng
        on_navigate: Callback để quay về trang chủ
        """
        super().__init__(parent, bg='#f0f0f0')
        self.parent = parent
        self.user_info = user_info
        self.on_navigate = on_navigate
        
        self.create_widgets()
        self.load_students()
    
    def create_widgets(self):
        """Tạo giao diện quản lý học sinh"""
        
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
            text="QUẢN LÝ HỌC SINH",
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
            command=self.load_students,
            relief=tk.RAISED,
            padx=15,
            pady=5
        )
        btn_refresh.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Tìm kiếm
        tk.Label(
            toolbar_frame,
            text="Tìm kiếm:",
            font=('Arial', 10),
            bg='#ecf0f1'
        ).pack(side=tk.LEFT, padx=(20, 5), pady=10)
        
        self.search_entry = tk.Entry(
            toolbar_frame,
            font=('Arial', 10),
            width=25
        )
        self.search_entry.pack(side=tk.LEFT, pady=10)
        self.search_entry.bind('<KeyRelease>', lambda e: self.search_students())
        
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
        
        # Lọc theo lớp
        tk.Label(
            toolbar_frame,
            text="Lớp:",
            font=('Arial', 10),
            bg='#ecf0f1'
        ).pack(side=tk.LEFT, padx=(20, 5), pady=10)
        
        self.class_filter = ttk.Combobox(
            toolbar_frame,
            font=('Arial', 10),
            width=15,
            state='readonly'
        )
        self.class_filter.pack(side=tk.LEFT, pady=10)
        self.class_filter.bind('<<ComboboxSelected>>', lambda e: self.filter_by_class())
        
        # === TREEVIEW (BẢNG DỮ LIỆU) ===
        table_frame = tk.Frame(self, bg='white')
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbars
        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        
        # Treeview
        columns = ('ID', 'Họ tên', 'Lớp', 'Giới tính', 'Ngày sinh', 'Ngày tạo')
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
        self.tree.heading('Họ tên', text='Họ tên')
        self.tree.heading('Lớp', text='Lớp')
        self.tree.heading('Giới tính', text='Giới tính')
        self.tree.heading('Ngày sinh', text='Ngày sinh')
        self.tree.heading('Ngày tạo', text='Ngày tạo')
        
        # Độ rộng cột
        self.tree.column('ID', width=60, anchor='center')
        self.tree.column('Họ tên', width=200, anchor='w')
        self.tree.column('Lớp', width=120, anchor='center')
        self.tree.column('Giới tính', width=100, anchor='center')
        self.tree.column('Ngày sinh', width=120, anchor='center')
        self.tree.column('Ngày tạo', width=180, anchor='center')
        
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
                       font=('Arial', 11, 'bold'))
        
        # Màu xen kẽ cho các hàng
        self.tree.tag_configure('oddrow', background='#f9f9f9')
        self.tree.tag_configure('evenrow', background='#ffffff')
        
        # === ACTION BUTTONS ===
        action_frame = tk.Frame(self, bg='#ecf0f1', height=60)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        action_frame.pack_propagate(False)
        
        btn_update = tk.Button(
            action_frame,
            text="✏️ Cập nhật",
            font=('Arial', 11, 'bold'),
            bg='#f39c12',
            fg='black',
            cursor='hand2',
            command=self.update_student,
            relief=tk.RAISED,
            padx=20,
            pady=10
        )
        btn_update.pack(side=tk.LEFT, padx=10, pady=10)
        
        btn_delete = tk.Button(
            action_frame,
            text="🗑 Xóa",
            font=('Arial', 11, 'bold'),
            bg='#e74c3c',
            fg='black',
            cursor='hand2',
            command=self.delete_student,
            relief=tk.RAISED,
            padx=20,
            pady=10
        )
        btn_delete.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Thống kê
        self.stats_label = tk.Label(
            action_frame,
            text="Tổng số học sinh: 0",
            font=('Arial', 10),
            bg='#ecf0f1',
            fg='#2c3e50'
        )
        self.stats_label.pack(side=tk.RIGHT, padx=20, pady=10)
    
    def load_students(self):
        """Tải danh sách học sinh từ database"""
        # Xóa dữ liệu cũ
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            # Lấy dữ liệu từ database
            students = database.get_all_students()
            
            # Lấy danh sách lớp để làm filter
            classes = set()
            
            # Thêm vào Treeview
            for idx, student in enumerate(students):
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
                
                # Format ngày
                birthday = student['birthday'].strftime('%Y-%m-%d') if student['birthday'] else ''
                created_at = student['created_at'].strftime('%Y-%m-%d %H:%M') if student['created_at'] else ''
                
                self.tree.insert('', 'end', values=(
                    student['student_id'],
                    student['name'],
                    student['class_name'],
                    student['gender'],
                    birthday,
                    created_at
                ), tags=(tag,))
                
                # Thêm vào danh sách lớp
                classes.add(student['class_name'])
            
            # Cập nhật combobox lọc lớp
            class_list = ['Tất cả'] + sorted(list(classes))
            self.class_filter['values'] = class_list
            self.class_filter.current(0)
            
            # Cập nhật thống kê
            self.stats_label.config(text=f"Tổng số học sinh: {len(students)}")
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tải dữ liệu:\n{e}")
    
    def search_students(self):
        """Tìm kiếm học sinh theo tên"""
        search_text = self.search_entry.get().strip().lower()
        
        # Xóa dữ liệu hiện tại
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            students = database.get_all_students()
            
            # Lọc theo search text
            if search_text:
                students = [s for s in students if search_text in s['name'].lower()]
            
            # Lọc theo lớp nếu đang chọn
            selected_class = self.class_filter.get()
            if selected_class and selected_class != 'Tất cả':
                students = [s for s in students if s['class_name'] == selected_class]
            
            # Thêm vào Treeview
            for idx, student in enumerate(students):
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
                
                birthday = student['birthday'].strftime('%Y-%m-%d') if student['birthday'] else ''
                created_at = student['created_at'].strftime('%Y-%m-%d %H:%M') if student['created_at'] else ''
                
                self.tree.insert('', 'end', values=(
                    student['student_id'],
                    student['name'],
                    student['class_name'],
                    student['gender'],
                    birthday,
                    created_at
                ), tags=(tag,))
            
            # Cập nhật thống kê
            self.stats_label.config(text=f"Tổng số học sinh: {len(students)}")
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi tìm kiếm:\n{e}")
    
    def filter_by_class(self):
        """Lọc học sinh theo lớp"""
        selected_class = self.class_filter.get()
        
        # Xóa dữ liệu hiện tại
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            students = database.get_all_students()
            
            # Lọc theo lớp
            if selected_class and selected_class != 'Tất cả':
                students = [s for s in students if s['class_name'] == selected_class]
            
            # Lọc theo search text nếu có
            search_text = self.search_entry.get().strip().lower()
            if search_text:
                students = [s for s in students if search_text in s['name'].lower()]
            
            # Thêm vào Treeview
            for idx, student in enumerate(students):
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
                
                birthday = student['birthday'].strftime('%Y-%m-%d') if student['birthday'] else ''
                created_at = student['created_at'].strftime('%Y-%m-%d %H:%M') if student['created_at'] else ''
                
                self.tree.insert('', 'end', values=(
                    student['student_id'],
                    student['name'],
                    student['class_name'],
                    student['gender'],
                    birthday,
                    created_at
                ), tags=(tag,))
            
            # Cập nhật thống kê
            self.stats_label.config(text=f"Tổng số học sinh: {len(students)}")
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi lọc:\n{e}")
    
    def clear_search(self):
        """Xóa ô tìm kiếm và tải lại toàn bộ"""
        self.search_entry.delete(0, tk.END)
        self.class_filter.current(0)
        self.load_students()
    
    def update_student(self):
        """Cập nhật thông tin học sinh"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một học sinh để cập nhật!")
            return
        
        # Lấy thông tin học sinh
        item = self.tree.item(selected[0])
        student_id = item['values'][0]
        
        # Lấy thông tin chi tiết từ database
        student = database.get_student_by_id(student_id)
        if not student:
            messagebox.showerror("Lỗi", "Không tìm thấy học sinh!")
            return
        
        # Mở dialog cập nhật
        self.open_update_dialog(student)
    
    def open_update_dialog(self, student):
        """Mở dialog để cập nhật thông tin học sinh"""
        dialog = tk.Toplevel(self)
        dialog.title("Cập nhật thông tin học sinh")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        dialog.grab_set()  # Modal
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (400 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Main frame
        main_frame = tk.Frame(dialog, bg='white', padx=30, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        tk.Label(
            main_frame,
            text="CẬP NHẬT THÔNG TIN HỌC SINH",
            font=('Arial', 14, 'bold'),
            bg='white',
            fg='#2c3e50'
        ).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Các trường thông tin
        fields = [
            ("Họ tên:", student['name']),
            ("Lớp:", student['class_name']),
            ("Ngày sinh (YYYY-MM-DD):", student['birthday'].strftime('%Y-%m-%d') if student['birthday'] else '')
        ]
        
        entries = {}
        
        for idx, (label_text, default_value) in enumerate(fields, start=1):
            tk.Label(
                main_frame,
                text=label_text,
                font=('Arial', 10),
                bg='white',
                anchor='w'
            ).grid(row=idx, column=0, sticky='w', pady=10)
            
            entry = tk.Entry(main_frame, font=('Arial', 10), width=30)
            entry.insert(0, default_value)
            entry.grid(row=idx, column=1, pady=10, padx=(10, 0))
            
            entries[label_text] = entry
        
        # Giới tính (Combobox)
        tk.Label(
            main_frame,
            text="Giới tính:",
            font=('Arial', 10),
            bg='white',
            anchor='w'
        ).grid(row=4, column=0, sticky='w', pady=10)
        
        gender_var = tk.StringVar(value=student['gender'])
        gender_combo = ttk.Combobox(
            main_frame,
            textvariable=gender_var,
            values=['Nam', 'Nữ', 'Khác'],
            font=('Arial', 10),
            width=28,
            state='readonly'
        )
        gender_combo.grid(row=4, column=1, pady=10, padx=(10, 0))
        
        # Buttons
        btn_frame = tk.Frame(main_frame, bg='white')
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(20, 0))
        
        def save_update():
            """Lưu thông tin cập nhật"""
            try:
                # Lấy giá trị
                name = entries["Họ tên:"].get().strip()
                class_name = entries["Lớp:"].get().strip()
                birthday_str = entries["Ngày sinh (YYYY-MM-DD):"].get().strip()
                gender = gender_var.get()
                
                # Validate
                if not name or not class_name or not birthday_str or not gender:
                    messagebox.showwarning("Cảnh báo", "Vui lòng điền đầy đủ thông tin!")
                    return
                
                # Validate ngày
                try:
                    datetime.strptime(birthday_str, '%Y-%m-%d')
                except ValueError:
                    messagebox.showerror("Lỗi", "Định dạng ngày sinh không hợp lệ!\nVui lòng nhập theo định dạng YYYY-MM-DD")
                    return
                
                # Cập nhật database
                conn = database.get_db_connection()
                if conn is None:
                    messagebox.showerror("Lỗi", "Không thể kết nối database")
                    return
                
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE student 
                    SET name = %s, class_name = %s, gender = %s, birthday = %s
                    WHERE student_id = %s
                """, (name, class_name, gender, birthday_str, student['student_id']))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                messagebox.showinfo("Thành công", "Cập nhật thông tin thành công!")
                dialog.destroy()
                self.load_students()
                
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể cập nhật:\n{e}")
        
        btn_save = tk.Button(
            btn_frame,
            text="💾 Lưu",
            font=('Arial', 11, 'bold'),
            bg='#27ae60',
            fg='black',
            cursor='hand2',
            command=save_update,
            padx=30,
            pady=8
        )
        btn_save.pack(side=tk.LEFT, padx=10)
        
        btn_cancel = tk.Button(
            btn_frame,
            text="✖ Hủy",
            font=('Arial', 11, 'bold'),
            bg='#95a5a6',
            fg='black',
            cursor='hand2',
            command=dialog.destroy,
            padx=30,
            pady=8
        )
        btn_cancel.pack(side=tk.LEFT, padx=10)
    
    def delete_student(self):
        """Xóa học sinh"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một học sinh để xóa!")
            return
        
        # Lấy thông tin học sinh
        item = self.tree.item(selected[0])
        student_id = item['values'][0]
        student_name = item['values'][1]
        
        # Xác nhận xóa
        confirm = messagebox.askyesno(
            "Xác nhận xóa",
            f"Bạn có chắc chắn muốn xóa học sinh:\n\n"
            f"ID: {student_id}\n"
            f"Họ tên: {student_name}\n\n"
            f"Lưu ý: Tất cả dữ liệu liên quan sẽ bị xóa!"
        )
        
        if not confirm:
            return
        
        try:
            success, message = database.delete_student(student_id)
            
            if success:
                messagebox.showinfo("Thành công", message)
                self.load_students()
            else:
                messagebox.showerror("Lỗi", message)
                
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xóa học sinh:\n{e}")


# Test frame
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test Học Sinh Frame")
    root.geometry("1200x700")
    
    test_user = {"username": "admin"}
    
    def test_navigate(page):
        print(f"Điều hướng đến: {page}")
    
    frame = HocSinhFrame(root, test_user, test_navigate)
    frame.pack(fill=tk.BOTH, expand=True)
    
    root.mainloop()
