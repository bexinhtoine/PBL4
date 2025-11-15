import tkinter as tk
from tkinter import ttk, messagebox
import database
from datetime import datetime

class ChiTietFrame(tk.Frame):
    """
    Màn hình chi tiết buổi học
    Hiển thị thông tin buổi học và danh sách học sinh tham gia
    """
    def __init__(self, parent, user_info, seasion_id, on_navigate):
        """
        parent: Widget cha
        user_info: Thông tin người dùng
        seasion_id: ID buổi học cần xem chi tiết
        on_navigate: Callback để quay lại lịch sử
        """
        super().__init__(parent, bg='#f0f0f0')
        self.parent = parent
        self.user_info = user_info
        self.seasion_id = seasion_id
        self.on_navigate = on_navigate
        self.seasion_info = None
        
        self.create_widgets()
        self.load_session_info()
        self.load_focus_records()
    
    def create_widgets(self):
        """Tạo giao diện chi tiết buổi học"""
        
        # === HEADER ===
        header_frame = tk.Frame(self, bg='#2c3e50', height=80)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)
        
        # Nút quay lại
        btn_back = tk.Button(
            header_frame,
            text="← Quay lại lịch sử",
            font=('Arial', 10),
            bg='#34495e',
            fg='black',
            cursor='hand2',
            command=lambda: self.on_navigate('lichsu'),
            relief=tk.FLAT,
            padx=15,
            pady=5
        )
        btn_back.place(x=20, y=25)
        
        # Tiêu đề
        self.title_label = tk.Label(
            header_frame,
            text="CHI TIẾT BUỔI HỌC",
            font=('Arial', 20, 'bold'),
            bg='#2c3e50',
            fg='white'
        )
        self.title_label.pack(pady=25)
        
        # === THÔNG TIN BUỔI HỌC ===
        info_frame = tk.LabelFrame(
            self,
            text="Thông tin buổi học",
            font=('Arial', 12, 'bold'),
            bg='white',
            fg='#2c3e50',
            padx=20,
            pady=15
        )
        info_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
        
        # Grid layout cho thông tin
        info_grid = tk.Frame(info_frame, bg='white')
        info_grid.pack(fill=tk.BOTH, expand=True)
        
        # Labels cho thông tin
        labels_text = [
            "ID buổi học:",
            "Lớp:",
            "Thời gian bắt đầu:",
            "Thời gian kết thúc:",
            "Ngày tạo:"
        ]
        
        self.info_labels = {}
        
        for idx, label_text in enumerate(labels_text):
            # Label tiêu đề
            tk.Label(
                info_grid,
                text=label_text,
                font=('Arial', 10, 'bold'),
                bg='white',
                fg='#34495e',
                anchor='w'
            ).grid(row=idx, column=0, sticky='w', padx=(0, 20), pady=8)
            
            # Label giá trị
            value_label = tk.Label(
                info_grid,
                text="Đang tải...",
                font=('Arial', 10),
                bg='white',
                fg='#2c3e50',
                anchor='w'
            )
            value_label.grid(row=idx, column=1, sticky='w', pady=8)
            
            self.info_labels[label_text] = value_label
        
        # === TOOLBAR ===
        toolbar_frame = tk.Frame(self, bg='#ecf0f1', height=50)
        toolbar_frame.pack(fill=tk.X, padx=20, pady=10)
        toolbar_frame.pack_propagate(False)
        
        # Tiêu đề bảng
        tk.Label(
            toolbar_frame,
            text="Danh sách điểm danh & đánh giá tập trung",
            font=('Arial', 11, 'bold'),
            bg='#ecf0f1',
            fg='#2c3e50'
        ).pack(side=tk.LEFT, padx=20, pady=10)
        
        # Nút làm mới
        btn_refresh = tk.Button(
            toolbar_frame,
            text="🔄 Làm mới",
            font=('Arial', 10),
            bg='#3498db',
            fg='black',
            cursor='hand2',
            command=self.load_focus_records,
            relief=tk.RAISED,
            padx=15,
            pady=5
        )
        btn_refresh.pack(side=tk.RIGHT, padx=20, pady=10)
        
        # === TREEVIEW (BẢNG DỮ LIỆU FOCUS RECORD) ===
        table_frame = tk.Frame(self, bg='white')
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Scrollbars
        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        
        # Treeview
        columns = ('STT', 'Tên học sinh', 'Lớp', 'Có mặt', 'Điểm tập trung', 'Đánh giá', 'Ghi chú')
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
        self.tree.heading('STT', text='STT')
        self.tree.heading('Tên học sinh', text='Tên học sinh')
        self.tree.heading('Lớp', text='Lớp')
        self.tree.heading('Có mặt', text='Có mặt')
        self.tree.heading('Điểm tập trung', text='Điểm tập trung')
        self.tree.heading('Đánh giá', text='Đánh giá')
        self.tree.heading('Ghi chú', text='Ghi chú')
        
        # Độ rộng cột
        self.tree.column('STT', width=50, anchor='center')
        self.tree.column('Tên học sinh', width=200, anchor='w')
        self.tree.column('Lớp', width=100, anchor='center')
        self.tree.column('Có mặt', width=80, anchor='center')
        self.tree.column('Điểm tập trung', width=120, anchor='center')
        self.tree.column('Đánh giá', width=120, anchor='center')
        self.tree.column('Ghi chú', width=250, anchor='w')
        
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
                       font=('Arial', 10, 'bold'))
        
        # Màu cho các hàng
        self.tree.tag_configure('present', background='#d5f4e6')  # Xanh nhạt
        self.tree.tag_configure('absent', background='#fadbd8')   # Đỏ nhạt
        self.tree.tag_configure('oddrow', background='#f9f9f9')
        self.tree.tag_configure('evenrow', background='#ffffff')
        
        # === THỐNG KÊ ===
        stats_frame = tk.Frame(self, bg='#ecf0f1', height=60)
        stats_frame.pack(fill=tk.X, padx=20, pady=(10, 20))
        stats_frame.pack_propagate(False)
        
        # Container cho các label thống kê
        stats_container = tk.Frame(stats_frame, bg='#ecf0f1')
        stats_container.pack(expand=True)
        
        # Tổng số học sinh
        self.total_label = tk.Label(
            stats_container,
            text="Tổng: 0",
            font=('Arial', 10, 'bold'),
            bg='#ecf0f1',
            fg='#2c3e50'
        )
        self.total_label.pack(side=tk.LEFT, padx=15)
        
        # Có mặt
        self.present_label = tk.Label(
            stats_container,
            text="Có mặt: 0",
            font=('Arial', 10, 'bold'),
            bg='#ecf0f1',
            fg='#27ae60'
        )
        self.present_label.pack(side=tk.LEFT, padx=15)
        
        # Vắng mặt
        self.absent_label = tk.Label(
            stats_container,
            text="Vắng: 0",
            font=('Arial', 10, 'bold'),
            bg='#ecf0f1',
            fg='#e74c3c'
        )
        self.absent_label.pack(side=tk.LEFT, padx=15)
        
        # Điểm TB
        self.avg_label = tk.Label(
            stats_container,
            text="Điểm TB: 0",
            font=('Arial', 10, 'bold'),
            bg='#ecf0f1',
            fg='#3498db'
        )
        self.avg_label.pack(side=tk.LEFT, padx=15)
    
    def load_session_info(self):
        """Tải thông tin buổi học"""
        try:
            conn = database.get_db_connection()
            if conn is None:
                messagebox.showerror("Lỗi", "Không thể kết nối database")
                return
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT seasion_id, class_name, start_time, end_time, created_at
                FROM seasion
                WHERE seasion_id = %s
            """, (self.seasion_id,))
            
            self.seasion_info = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not self.seasion_info:
                messagebox.showerror("Lỗi", "Không tìm thấy buổi học!")
                self.on_navigate('lichsu')
                return
            
            # Cập nhật thông tin lên giao diện
            self.info_labels["ID buổi học:"].config(text=str(self.seasion_info['seasion_id']))
            self.info_labels["Lớp:"].config(text=self.seasion_info['class_name'])
            
            start_time = self.seasion_info['start_time'].strftime('%Y-%m-%d %H:%M:%S') if self.seasion_info['start_time'] else 'N/A'
            end_time = self.seasion_info['end_time'].strftime('%Y-%m-%d %H:%M:%S') if self.seasion_info['end_time'] else 'N/A'
            created_at = self.seasion_info['created_at'].strftime('%Y-%m-%d %H:%M:%S') if self.seasion_info['created_at'] else 'N/A'
            
            self.info_labels["Thời gian bắt đầu:"].config(text=start_time)
            self.info_labels["Thời gian kết thúc:"].config(text=end_time)
            self.info_labels["Ngày tạo:"].config(text=created_at)
            
            # Cập nhật tiêu đề
            self.title_label.config(text=f"CHI TIẾT BUỔI HỌC - {self.seasion_info['class_name']}")
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tải thông tin buổi học:\n{e}")
    
    def load_focus_records(self):
        """Tải danh sách điểm danh và đánh giá tập trung"""
        # Xóa dữ liệu cũ
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            conn = database.get_db_connection()
            if conn is None:
                messagebox.showerror("Lỗi", "Không thể kết nối database")
                return
            
            cursor = conn.cursor(dictionary=True)
            
            # Join với bảng student để lấy thông tin học sinh
            cursor.execute("""
                SELECT 
                    fr.record_id,
                    fr.student_id,
                    s.name as student_name,
                    s.class_name,
                    fr.appear,
                    fr.focus_point,
                    fr.rate,
                    fr.note
                FROM focus_record fr
                INNER JOIN student s ON fr.student_id = s.student_id
                WHERE fr.seasion_id = %s
                ORDER BY s.name
            """, (self.seasion_id,))
            
            records = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Thống kê
            total = len(records)
            present = sum(1 for r in records if r['appear'])
            absent = total - present
            
            # Tính điểm TB (chỉ tính học sinh có mặt)
            if present > 0:
                avg_focus = sum(r['focus_point'] for r in records if r['appear']) / present
            else:
                avg_focus = 0
            
            # Thêm vào Treeview
            for idx, record in enumerate(records, start=1):
                appear_text = "✓" if record['appear'] else "✗"
                
                # Chọn tag dựa vào có mặt hay không
                if record['appear']:
                    tag = 'present'
                else:
                    tag = 'absent'
                
                self.tree.insert('', 'end', values=(
                    idx,
                    record['student_name'],
                    record['class_name'],
                    appear_text,
                    record['focus_point'],
                    record['rate'],
                    record['note'] if record['note'] else ''
                ), tags=(tag,))
            
            # Cập nhật thống kê
            self.total_label.config(text=f"Tổng: {total}")
            self.present_label.config(text=f"Có mặt: {present}")
            self.absent_label.config(text=f"Vắng: {absent}")
            self.avg_label.config(text=f"Điểm TB: {avg_focus:.1f}")
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tải dữ liệu:\n{e}")


# Test frame
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test Chi Tiết Frame")
    root.geometry("1200x800")
    
    test_user = {"username": "admin"}
    
    def test_navigate(page):
        print(f"Điều hướng đến: {page}")
    
    # Test với seasion_id = 1 (nếu có trong database)
    frame = ChiTietFrame(root, test_user, 1, test_navigate)
    frame.pack(fill=tk.BOTH, expand=True)
    
    root.mainloop()
