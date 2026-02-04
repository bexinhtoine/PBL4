import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import database
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

class ThongKeFrame(tk.Frame):
    """
    Màn hình thống kê học sinh
    """
    def __init__(self, parent, user_info, on_navigate):
        """
        parent: Widget cha
        user_info: Thông tin người dùng đã đăng nhập
        on_navigate: Callback để chuyển trang
        """
        super().__init__(parent, bg='#f0f0f0')
        self.parent = parent
        self.user_info = user_info
        self.on_navigate = on_navigate
        
        self.current_class = None
        self.current_period = 7  # Mặc định 7 ngày
        
        # Cấu hình matplotlib để hiển thị tiếng Việt
        plt.rcParams['font.family'] = 'DejaVu Sans'
        
        self.create_widgets()
        self.load_classes()
    
    def create_widgets(self):
        """Tạo giao diện thống kê"""
        
        # === HEADER ===
        header_frame = tk.Frame(self, bg='#2c3e50', height=80)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)
        
        # Tiêu đề
        title_label = tk.Label(
            header_frame,
            text="📊 THỐNG KÊ HỌC SINH",
            font=('Arial', 18, 'bold'),
            bg='#2c3e50',
            fg='white'
        )
        title_label.place(x=20, rely=0.5, anchor='w')
        
        # Nút quay lại
        btn_back = tk.Button(
            header_frame,
            text="← Quay lại",
            font=('Arial', 10),
            bg='#95a5a6',
            fg='black',
            cursor='hand2',
            command=lambda: self.on_navigate('home'),
            relief=tk.RAISED,
            padx=15,
            pady=5
        )
        btn_back.place(relx=0.95, rely=0.5, anchor='e')
        
        # === NOTEBOOK (TABS) ===
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 20))
        
        # Tab 1: Thống kê học sinh
        self.student_tab = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(self.student_tab, text='📚 Thống kê học sinh')
        
        # Tab 2: Thống kê buổi học
        self.session_tab = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(self.session_tab, text='📅 Thống kê buổi học')
        
        # Tạo giao diện cho từng tab
        self.create_student_tab()
        self.create_session_tab()
    
    def create_student_tab(self):
        """Tạo giao diện tab thống kê học sinh"""
        
        # === FILTER FRAME ===
        filter_frame = tk.Frame(self.student_tab, bg='white', relief=tk.RAISED, bd=2)
        filter_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Dòng 1: Chọn lớp và thời gian
        row1_frame = tk.Frame(filter_frame, bg='white')
        row1_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Chọn lớp
        tk.Label(
            row1_frame,
            text="Lớp:",
            font=('Arial', 11),
            bg='white'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.class_combo = ttk.Combobox(
            row1_frame,
            font=('Arial', 11),
            width=20,
            state='readonly'
        )
        self.class_combo.pack(side=tk.LEFT, padx=(0, 30))
        self.class_combo.bind('<<ComboboxSelected>>', self.on_filter_change)
        
        # Chọn khoảng thời gian
        tk.Label(
            row1_frame,
            text="Khoảng thời gian:",
            font=('Arial', 11),
            bg='white'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.period_combo = ttk.Combobox(
            row1_frame,
            font=('Arial', 11),
            width=15,
            state='readonly',
            values=['7 ngày', '30 ngày', '90 ngày', 'Tất cả']
        )
        self.period_combo.current(0)
        self.period_combo.pack(side=tk.LEFT, padx=(0, 20))
        self.period_combo.bind('<<ComboboxSelected>>', self.on_filter_change)
        
        # Nút làm mới
        btn_refresh = tk.Button(
            row1_frame,
            text="🔄 Làm mới",
            font=('Arial', 10),
            bg='#3498db',
            fg='black',
            cursor='hand2',
            command=self.on_filter_change,
            relief=tk.RAISED,
            padx=10,
            pady=3
        )
        btn_refresh.pack(side=tk.LEFT)
        
        # Dòng 2: Tìm kiếm học sinh
        row2_frame = tk.Frame(filter_frame, bg='white')
        row2_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(
            row2_frame,
            text="🔍 Tìm kiếm học sinh:",
            font=('Arial', 11),
            bg='white'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        
        self.search_entry = tk.Entry(
            row2_frame,
            textvariable=self.search_var,
            font=('Arial', 11),
            width=30
        )
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Nút xóa tìm kiếm
        btn_clear_search = tk.Button(
            row2_frame,
            text="✕ Xóa",
            font=('Arial', 9),
            bg='#e74c3c',
            fg='black',
            cursor='hand2',
            command=self.clear_search,
            relief=tk.RAISED,
            padx=8,
            pady=2
        )
        btn_clear_search.pack(side=tk.LEFT)
        
        # === MAIN CONTENT ===
        main_frame = tk.Frame(self.student_tab, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Chia làm 2 cột
        left_frame = tk.Frame(main_frame, bg='#f0f0f0')
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        right_frame = tk.Frame(main_frame, bg='#f0f0f0')
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # === LEFT: TOP HỌC SINH ===
        top_frame = tk.Frame(left_frame, bg='white', relief=tk.RAISED, bd=2)
        top_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        tk.Label(
            top_frame,
            text="🏆 TOP HỌC SINH XUẤT SẮC",
            font=('Arial', 13, 'bold'),
            bg='white',
            fg='#2c3e50'
        ).pack(pady=10)
        
        # Treeview cho top học sinh
        tree_frame = tk.Frame(top_frame, bg='white')
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        columns = ('rank', 'name', 'sessions', 'avg_focus', 'attendance_rate')
        self.top_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='headings',
            height=12
        )
        
        self.top_tree.heading('rank', text='Hạng')
        self.top_tree.heading('name', text='Họ tên')
        self.top_tree.heading('sessions', text='Số buổi')
        self.top_tree.heading('avg_focus', text='Điểm TB')
        self.top_tree.heading('attendance_rate', text='Số lần có mặt')
        
        self.top_tree.column('rank', width=40, anchor='center')      # Giảm nhẹ rank
        self.top_tree.column('name', width=220, anchor='w')          # Tăng width từ 150 -> 220
        self.top_tree.column('sessions', width=70, anchor='center')  # Giảm nhẹ sessions
        self.top_tree.column('avg_focus', width=80, anchor='center')
        self.top_tree.column('attendance_rate', width=100, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.top_tree.yview)
        self.top_tree.configure(yscrollcommand=scrollbar.set)
        
        self.top_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Lưu danh sách học sinh đầy đủ để lọc
        self.all_students = []
        
        # === LEFT BOTTOM: THỐNG KÊ TỔNG QUAN ===
        stats_frame = tk.Frame(left_frame, bg='white', relief=tk.RAISED, bd=2)
        stats_frame.pack(fill=tk.X)
        
        tk.Label(
            stats_frame,
            text="📈 THỐNG KÊ TỔNG QUAN",
            font=('Arial', 13, 'bold'),
            bg='white',
            fg='#2c3e50'
        ).pack(pady=10)
        
        self.stats_text = tk.Text(
            stats_frame,
            font=('Arial', 10),
            bg='white',
            height=8,
            relief=tk.FLAT,
            state='disabled'
        )
        self.stats_text.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # === RIGHT: BIỂU ĐỒ ===
        chart_frame = tk.Frame(right_frame, bg='white', relief=tk.RAISED, bd=2)
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            chart_frame,
            text="📊 BIỂU ĐỒ PHÂN BỐ MỨC ĐỘ TẬP TRUNG",
            font=('Arial', 13, 'bold'),
            bg='white',
            fg='#2c3e50'
        ).pack(pady=10)
        
        # Container cho biểu đồ
        self.chart_container = tk.Frame(chart_frame, bg='white')
        self.chart_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
    
    def create_session_tab(self):
        """Tạo giao diện tab thống kê buổi học"""
        
        # === FILTER FRAME ===
        filter_frame = tk.Frame(self.session_tab, bg='white', relief=tk.RAISED, bd=2)
        filter_frame.pack(fill=tk.X, padx=20, pady=10)
        
        row_frame = tk.Frame(filter_frame, bg='white')
        row_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Chọn lớp (dùng chung với student tab)
        tk.Label(
            row_frame,
            text="Lớp:",
            font=('Arial', 11),
            bg='white'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.session_class_combo = ttk.Combobox(
            row_frame,
            font=('Arial', 11),
            width=20,
            state='readonly'
        )
        self.session_class_combo.pack(side=tk.LEFT, padx=(0, 30))
        self.session_class_combo.bind('<<ComboboxSelected>>', self.on_session_filter_change)
        
        # Chọn khoảng thời gian
        tk.Label(
            row_frame,
            text="Khoảng thời gian:",
            font=('Arial', 11),
            bg='white'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.session_period_combo = ttk.Combobox(
            row_frame,
            font=('Arial', 11),
            width=15,
            state='readonly',
            values=['7 ngày', '30 ngày', '90 ngày', 'Tất cả']
        )
        self.session_period_combo.current(0)
        self.session_period_combo.pack(side=tk.LEFT, padx=(0, 20))
        self.session_period_combo.bind('<<ComboboxSelected>>', self.on_session_filter_change)
        
        # Sắp xếp theo
        tk.Label(
            row_frame,
            text="Sắp xếp:",
            font=('Arial', 11),
            bg='white'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.sort_combo = ttk.Combobox(
            row_frame,
            font=('Arial', 11),
            width=15,
            state='readonly',
            values=['Thời gian mới nhất', 'Thời gian cũ nhất', 'Điểm TB cao nhất', 'Điểm TB thấp nhất']
        )
        self.sort_combo.current(0)
        self.sort_combo.pack(side=tk.LEFT, padx=(0, 20))
        self.sort_combo.bind('<<ComboboxSelected>>', self.on_session_filter_change)
        
        # Nút làm mới
        btn_refresh = tk.Button(
            row_frame,
            text="🔄 Làm mới",
            font=('Arial', 10),
            bg='#3498db',
            fg='black',
            cursor='hand2',
            command=self.on_session_filter_change,
            relief=tk.RAISED,
            padx=10,
            pady=3
        )
        btn_refresh.pack(side=tk.LEFT)
        
        # === MAIN CONTENT ===
        main_frame = tk.Frame(self.session_tab, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Chia làm 2 cột
        left_frame = tk.Frame(main_frame, bg='#f0f0f0')
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        right_frame = tk.Frame(main_frame, bg='#f0f0f0')
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # === LEFT: DANH SÁCH BUỔI HỌC ===
        session_frame = tk.Frame(left_frame, bg='white', relief=tk.RAISED, bd=2)
        session_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        tk.Label(
            session_frame,
            text="📅 DANH SÁCH BUỔI HỌC",
            font=('Arial', 13, 'bold'),
            bg='white',
            fg='#2c3e50'
        ).pack(pady=10)
        
        # Treeview cho danh sách buổi học
        tree_frame = tk.Frame(session_frame, bg='white')
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        columns = ('date', 'time', 'total_students', 'present', 'avg_score', 'rating')
        self.session_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='headings',
            height=12
        )
        
        self.session_tree.heading('date', text='Ngày')
        self.session_tree.heading('time', text='Thời gian')
        self.session_tree.heading('total_students', text='Sĩ số')
        self.session_tree.heading('present', text='Có mặt')
        self.session_tree.heading('avg_score', text='Điểm TB')
        self.session_tree.heading('rating', text='Đánh giá')
        
        self.session_tree.column('date', width=100, anchor='center')
        self.session_tree.column('time', width=120, anchor='center')
        self.session_tree.column('total_students', width=70, anchor='center')
        self.session_tree.column('present', width=70, anchor='center')
        self.session_tree.column('avg_score', width=80, anchor='center')
        self.session_tree.column('rating', width=100, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.session_tree.yview)
        self.session_tree.configure(yscrollcommand=scrollbar.set)
        
        self.session_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # === LEFT BOTTOM: THỐNG KÊ TỔNG QUAN ===
        stats_frame = tk.Frame(left_frame, bg='white', relief=tk.RAISED, bd=2)
        stats_frame.pack(fill=tk.X)
        
        tk.Label(
            stats_frame,
            text="📈 THỐNG KÊ TỔNG QUAN",
            font=('Arial', 13, 'bold'),
            bg='white',
            fg='#2c3e50'
        ).pack(pady=10)
        
        self.session_stats_text = tk.Text(
            stats_frame,
            font=('Arial', 10),
            bg='white',
            height=8,
            relief=tk.FLAT,
            state='disabled'
        )
        self.session_stats_text.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # === RIGHT: BIỂU ĐỒ ===
        chart_frame = tk.Frame(right_frame, bg='white', relief=tk.RAISED, bd=2)
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            chart_frame,
            text="📊 PHÂN BỐ BUỔI HỌC THEO MỨC ĐỘ",
            font=('Arial', 13, 'bold'),
            bg='white',
            fg='#2c3e50'
        ).pack(pady=10)
        
        # Container cho biểu đồ
        self.session_chart_container = tk.Frame(chart_frame, bg='white')
        self.session_chart_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
    
    def load_classes(self):
        """Load danh sách các lớp từ database"""
        conn = database.get_db_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT class_name FROM student ORDER BY class_name")
            classes = [row[0] for row in cursor.fetchall()]
            
            if classes:
                self.class_combo['values'] = classes
                self.class_combo.current(0)
                self.current_class = classes[0]
                
                # Cập nhật cho session tab
                self.session_class_combo['values'] = classes
                self.session_class_combo.current(0)
                
                self.load_statistics()
                self.load_session_statistics()
            else:
                messagebox.showinfo("Thông báo", "Chưa có dữ liệu học sinh trong hệ thống")
                
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tải danh sách lớp: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def on_filter_change(self, event=None):
        """Xử lý khi thay đổi bộ lọc"""
        self.current_class = self.class_combo.get()
        period_text = self.period_combo.get()
        
        # Chuyển đổi text sang số ngày
        if period_text == '7 ngày':
            self.current_period = 7
        elif period_text == '30 ngày':
            self.current_period = 30
        elif period_text == '90 ngày':
            self.current_period = 90
        else:
            self.current_period = None  # Tất cả
        
        self.load_statistics()
    
    def load_statistics(self):
        """Load dữ liệu thống kê"""
        if not self.current_class:
            return
        
        conn = database.get_db_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Tính toán khoảng thời gian
            date_filter = ""
            if self.current_period:
                start_date = datetime.now() - timedelta(days=self.current_period)
                date_filter = f"AND s.start_time >= '{start_date.strftime('%Y-%m-%d')}'"
            
            # Query top học sinh
# --- CHỈNH SỬA QUERY TOP HỌC SINH ---
            # Logic cũ: ELSE NULL (Vắng mặt không bị chia trung bình)
            # Logic mới: ELSE 0 (Vắng mặt tính là 0 điểm và vẫn chia trung bình)
            query_top = f"""
            SELECT 
                st.student_id,
                st.name,
                COUNT(DISTINCT f.seasion_id) as total_sessions,
                ROUND(AVG(CASE WHEN f.appear = 1 THEN f.focus_point ELSE 0 END), 1) as avg_focus, 
SUM(CASE WHEN f.appear = 1 THEN 1 ELSE 0 END) as attendance_rate            FROM student st
            LEFT JOIN focus_record f ON st.student_id = f.student_id
            LEFT JOIN seasion s ON f.seasion_id = s.seasion_id
            WHERE st.class_name = %s {date_filter}
            GROUP BY st.student_id, st.name
            HAVING total_sessions > 0
            ORDER BY avg_focus DESC, attendance_rate DESC
            LIMIT 20
            """
            
            cursor.execute(query_top, (self.current_class,))
            top_students = cursor.fetchall()
            
            # Lưu danh sách đầy đủ để lọc
            self.all_students = top_students
            
            # Hiển thị danh sách học sinh
            self.display_top_students(top_students)
            
            # --- CHỈNH SỬA QUERY THỐNG KÊ TỔNG QUAN ---
            # Cũng áp dụng logic ELSE 0 cho avg_focus_all
            query_stats = f"""
            SELECT 
                COUNT(DISTINCT s.seasion_id) as total_sessions,
                COUNT(DISTINCT st.student_id) as total_students,
                COUNT(CASE WHEN f.appear = 1 THEN 1 END) as total_attendance,
                ROUND(AVG(CASE WHEN f.appear = 1 THEN f.focus_point ELSE 0 END), 1) as avg_focus_all,
                COUNT(CASE WHEN f.rate = 'Cao độ' THEN 1 END) as count_cao_do,
                COUNT(CASE WHEN f.rate = 'Tốt' THEN 1 END) as count_tot,
                COUNT(CASE WHEN f.rate = 'Trung bình' THEN 1 END) as count_trung_binh,
                COUNT(CASE WHEN f.rate = 'Thấp' THEN 1 END) as count_thap
            FROM seasion s
            LEFT JOIN focus_record f ON s.seasion_id = f.seasion_id
            LEFT JOIN student st ON f.student_id = st.student_id
            WHERE s.class_name = %s {date_filter}
            """
            cursor.execute(query_stats, (self.current_class,))
            stats = cursor.fetchone()
            
            # Hiển thị thống kê tổng quan
            self.display_general_stats(stats)
            
            # Hiển thị biểu đồ
            self.display_chart(stats)
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tải thống kê: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cursor.close()
            conn.close()
    
    def display_top_students(self, students):
        """Hiển thị danh sách top học sinh"""
        # Xóa dữ liệu cũ
        for item in self.top_tree.get_children():
            self.top_tree.delete(item)
        
        # Thêm dữ liệu mới
        for rank, student in enumerate(students, start=1):
            avg_focus = student['avg_focus'] if student['avg_focus'] else 0
            attendance = student['attendance_rate'] if student['attendance_rate'] else 0
            
            # Thêm biểu tượng cho top 3
            rank_display = rank
            if rank == 1:
                rank_display = "🥇"
            elif rank == 2:
                rank_display = "🥈"
            elif rank == 3:
                rank_display = "🥉"
            
            self.top_tree.insert(
                '',
                'end',
                values=(
                    rank_display,
                    student['name'],
                    student['total_sessions'],
                    f"{avg_focus:.1f}",
                    int(attendance)
                ),
                tags=(f"rank_{rank}",)
            )
        
        # Tô màu cho top 3
        self.top_tree.tag_configure('rank_1', background='#ffd700')
        self.top_tree.tag_configure('rank_2', background='#c0c0c0')
        self.top_tree.tag_configure('rank_3', background='#cd7f32')
    
    def on_search_change(self, *args):
        """Xử lý khi thay đổi nội dung tìm kiếm"""
        search_text = self.search_var.get().strip().lower()
        
        if not search_text:
            # Nếu không có từ khóa, hiển thị tất cả
            self.display_top_students(self.all_students)
        else:
            # Lọc học sinh theo tên
            filtered_students = [
                student for student in self.all_students
                if search_text in student['name'].lower()
            ]
            self.display_top_students(filtered_students)
    
    def clear_search(self):
        """Xóa nội dung tìm kiếm"""
        self.search_var.set('')
        self.search_entry.focus()
    
    def display_general_stats(self, stats):
        """Hiển thị thống kê tổng quan"""
        self.stats_text.config(state='normal')
        self.stats_text.delete('1.0', 'end')
        
        if not stats or stats['total_sessions'] == 0:
            self.stats_text.insert('end', "Chưa có dữ liệu trong khoảng thời gian này.")
            self.stats_text.config(state='disabled')
            return
        
        total_sessions = stats['total_sessions'] or 0
        total_students = stats['total_students'] or 0
        total_attendance = stats['total_attendance'] or 0
        avg_focus = stats['avg_focus_all'] or 0
        
        # Tính tỷ lệ có mặt
        if total_sessions > 0 and total_students > 0:
            attendance_rate = (total_attendance * 100.0) / (total_sessions * total_students)
        else:
            attendance_rate = 0
        
        period_text = self.period_combo.get()
        
        stats_content = f"""
📅 Khoảng thời gian: {period_text}
🏫 Lớp: {self.current_class}

📊 Số liệu:
  • Tổng số buổi học: {total_sessions}
  • Tổng số học sinh: {total_students}
  • Tổng lượt có mặt: {total_attendance}
  • Tỷ lệ có mặt trung bình: {attendance_rate:.1f}%
  • Điểm tập trung trung bình: {avg_focus:.1f}/100

🎯 Phân loại mức độ tập trung:
  • Cao độ: {stats['count_cao_do']} lượt
  • Tốt: {stats['count_tot']} lượt
  • Trung bình: {stats['count_trung_binh']} lượt
  • Thấp: {stats['count_thap']} lượt
        """
        
        self.stats_text.insert('end', stats_content)
        self.stats_text.config(state='disabled')
    
    def display_chart(self, stats):
        """Hiển thị biểu đồ phân bố"""
        # Xóa biểu đồ cũ
        for widget in self.chart_container.winfo_children():
            widget.destroy()
        
        if not stats or stats['total_sessions'] == 0:
            tk.Label(
                self.chart_container,
                text="Chưa có dữ liệu để hiển thị biểu đồ",
                font=('Arial', 11),
                bg='white',
                fg='gray'
            ).pack(expand=True)
            return
        
        # Dữ liệu cho biểu đồ
        categories = ['Cao độ', 'Tốt', 'Trung bình', 'Thấp']
        values = [
            stats['count_cao_do'] or 0,
            stats['count_tot'] or 0,
            stats['count_trung_binh'] or 0,
            stats['count_thap'] or 0
        ]
        colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c']
        
        # Tạo biểu đồ
        fig = Figure(figsize=(6, 4), facecolor='white')
        ax = fig.add_subplot(111)
        
        bars = ax.bar(categories, values, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
        
        # Thêm giá trị lên đầu mỗi cột
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f'{int(value)}',
                ha='center',
                va='bottom',
                fontweight='bold',
                fontsize=10
            )
        
        ax.set_ylabel('Số lượt', fontsize=11, fontweight='bold')
        ax.set_xlabel('Mức độ tập trung', fontsize=11, fontweight='bold')
        ax.set_title('Phân bố mức độ tập trung', fontsize=12, fontweight='bold', pad=15)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Điều chỉnh layout
        fig.tight_layout(pad=2)
        
        # Nhúng biểu đồ vào Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def on_session_filter_change(self, event=None):
        """Xử lý khi thay đổi bộ lọc của tab buổi học"""
        self.load_session_statistics()
    
    def load_session_statistics(self):
        """Load dữ liệu thống kê buổi học"""
        current_class = self.session_class_combo.get()
        if not current_class:
            return
        
        period_text = self.session_period_combo.get()
        
        # Chuyển đổi text sang số ngày
        if period_text == '7 ngày':
            current_period = 7
        elif period_text == '30 ngày':
            current_period = 30
        elif period_text == '90 ngày':
            current_period = 90
        else:
            current_period = None  # Tất cả
        
        # Lấy tùy chọn sắp xếp
        sort_text = self.sort_combo.get()
        
        conn = database.get_db_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Tính toán khoảng thời gian
            date_filter = ""
            if current_period:
                start_date = datetime.now() - timedelta(days=current_period)
                date_filter = f"AND s.start_time >= '{start_date.strftime('%Y-%m-%d')}'"
            
            # Xác định ORDER BY
            if sort_text == 'Thời gian mới nhất':
                order_by = "ORDER BY s.start_time DESC"
            elif sort_text == 'Thời gian cũ nhất':
                order_by = "ORDER BY s.start_time ASC"
            elif sort_text == 'Điểm TB cao nhất':
                order_by = "ORDER BY avg_score DESC, s.start_time DESC"
            else:  # Điểm TB thấp nhất
                order_by = "ORDER BY avg_score ASC, s.start_time DESC"
            
            # Query danh sách buổi học với điểm trung bình
            query_sessions = f"""
            SELECT 
                s.start_time,
                s.end_time,
                COUNT(DISTINCT st.student_id) as total_students,
                SUM(CASE WHEN f.appear = 1 THEN 1 ELSE 0 END) as present_count,
                ROUND(AVG(CASE WHEN f.appear = 1 THEN f.focus_point ELSE NULL END), 1) as avg_score
            FROM seasion s
            LEFT JOIN student st ON st.class_name = s.class_name
            LEFT JOIN focus_record f ON f.seasion_id = s.seasion_id AND f.student_id = st.student_id
            WHERE s.class_name = %s {date_filter}
            GROUP BY s.start_time, s.end_time
            {order_by}
            """
            
            cursor.execute(query_sessions, (current_class,))
            sessions = cursor.fetchall()
            
            # Hiển thị danh sách buổi học
            self.display_sessions(sessions)
            
            # Query thống kê phân loại buổi học
            query_stats = f"""
            SELECT 
                COUNT(*) as total_sessions,
                (SELECT COUNT(DISTINCT student_id) FROM student WHERE class_name = %s) as total_students,
                ROUND(AVG(session_avg), 1) as overall_avg,
                SUM(CASE WHEN session_avg >= 80 THEN 1 ELSE 0 END) as excellent_sessions,
                SUM(CASE WHEN session_avg >= 60 AND session_avg < 80 THEN 1 ELSE 0 END) as good_sessions,
                SUM(CASE WHEN session_avg >= 40 AND session_avg < 60 THEN 1 ELSE 0 END) as average_sessions,
                SUM(CASE WHEN session_avg < 40 THEN 1 ELSE 0 END) as poor_sessions
            FROM (
                SELECT 
                    ROUND(AVG(CASE WHEN f.appear = 1 THEN f.focus_point ELSE NULL END), 1) as session_avg
                FROM seasion s
                LEFT JOIN student st ON st.class_name = s.class_name
                LEFT JOIN focus_record f ON f.seasion_id = s.seasion_id AND f.student_id = st.student_id
                WHERE s.class_name = %s {date_filter}
                GROUP BY s.start_time, s.end_time
            ) as session_scores
            """
            
            cursor.execute(query_stats, (current_class, current_class))
            stats = cursor.fetchone()
            
            # Hiển thị thống kê tổng quan
            self.display_session_stats(stats, period_text, current_class)
            
            # Hiển thị biểu đồ
            self.display_session_chart(stats)
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tải thống kê buổi học: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cursor.close()
            conn.close()
    
    def display_sessions(self, sessions):
        """Hiển thị danh sách buổi học"""
        # Xóa dữ liệu cũ
        for item in self.session_tree.get_children():
            self.session_tree.delete(item)
        
        # Thêm dữ liệu mới
        for session in sessions:
            avg_score = session['avg_score'] if session['avg_score'] else 0
            
            # Đánh giá buổi học dựa trên điểm TB
            if avg_score >= 80:
                rating = "Cao độ"
                tag = 'excellent'
            elif avg_score >= 60:
                rating = "Tốt"
                tag = 'good'
            elif avg_score >= 40:
                rating = "Trung bình"
                tag = 'average'
            else:
                rating = "Thấp"
                tag = 'poor'
            
            # Format thời gian từ datetime
            date_str = session['start_time'].strftime('%Y-%m-%d') if session['start_time'] else '-'
            start = session['start_time'].strftime('%H:%M') if session['start_time'] else '-'
            end = session['end_time'].strftime('%H:%M') if session['end_time'] else '-'
            time_str = f"{start} - {end}"
            
            self.session_tree.insert(
                '',
                'end',
                values=(
                    date_str,
                    time_str,
                    session['total_students'],
                    session['present_count'],
                    f"{avg_score:.1f}",
                    rating
                ),
                tags=(tag,)
            )
        
        # Cấu hình màu
        self.session_tree.tag_configure('excellent', background='#d5f4e6')
        self.session_tree.tag_configure('good', background='#d6eaf8')
        self.session_tree.tag_configure('average', background='#fef5e7')
        self.session_tree.tag_configure('poor', background='#fadbd8')
    
    def display_session_stats(self, stats, period_text, class_name):
        """Hiển thị thống kê tổng quan buổi học"""
        self.session_stats_text.config(state='normal')
        self.session_stats_text.delete('1.0', 'end')
        
        if not stats or stats['total_sessions'] == 0:
            self.session_stats_text.insert('end', "Chưa có dữ liệu trong khoảng thời gian này.")
            self.session_stats_text.config(state='disabled')
            return
        
        total_sessions = stats['total_sessions'] or 0
        total_students = stats['total_students'] or 0
        overall_avg = stats['overall_avg'] or 0
        excellent = stats['excellent_sessions'] or 0
        good = stats['good_sessions'] or 0
        average = stats['average_sessions'] or 0
        poor = stats['poor_sessions'] or 0
        
        stats_content = f"""
📅 Khoảng thời gian: {period_text}
🏫 Lớp: {class_name}

📊 Số liệu:
  • Tổng số buổi học: {total_sessions}
  • Sĩ số lớp: {total_students} học sinh
  • Điểm tập trung TB tổng thể: {overall_avg:.1f}/100

🎯 Phân loại buổi học theo điểm TB:
  • Cao độ (≥80): {excellent} buổi
  • Tốt (60-79): {good} buổi
  • Trung bình (40-59): {average} buổi
  • Thấp (<40): {poor} buổi
        """
        
        self.session_stats_text.insert('end', stats_content)
        self.session_stats_text.config(state='disabled')
    
    def display_session_chart(self, stats):
        """Hiển thị biểu đồ phân bố buổi học"""
        # Xóa biểu đồ cũ
        for widget in self.session_chart_container.winfo_children():
            widget.destroy()
        
        if not stats or stats['total_sessions'] == 0:
            tk.Label(
                self.session_chart_container,
                text="Chưa có dữ liệu để hiển thị biểu đồ",
                font=('Arial', 11),
                bg='white',
                fg='gray'
            ).pack(expand=True)
            return
        
        # Dữ liệu cho biểu đồ
        categories = ['Cao độ', 'Tốt', 'Trung bình', 'Thấp']
        values = [
            stats['excellent_sessions'] or 0,
            stats['good_sessions'] or 0,
            stats['average_sessions'] or 0,
            stats['poor_sessions'] or 0
        ]
        colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c']
        
        # Tạo biểu đồ
        fig = Figure(figsize=(6, 4), facecolor='white')
        ax = fig.add_subplot(111)
        
        bars = ax.bar(categories, values, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
        
        # Thêm giá trị lên đầu mỗi cột
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f'{int(value)}',
                ha='center',
                va='bottom',
                fontweight='bold',
                fontsize=10
            )
        
        ax.set_ylabel('Số buổi', fontsize=11, fontweight='bold')
        ax.set_xlabel('Mức độ (theo điểm TB)', fontsize=11, fontweight='bold')
        ax.set_title('Phân bố buổi học theo mức độ', fontsize=12, fontweight='bold', pad=15)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Điều chỉnh layout
        fig.tight_layout(pad=2)
        
        # Nhúng biểu đồ vào Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.session_chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


# Test frame nếu chạy riêng file này
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test Thống Kê Frame")
    root.geometry("1200x800")
    
    # Mock user info và callback
    test_user = {"username": "admin"}
    
    def test_navigate(page):
        print(f"Điều hướng đến: {page}")
    
    frame = ThongKeFrame(root, test_user, test_navigate)
    frame.pack(fill=tk.BOTH, expand=True)
    
    root.mainloop()
