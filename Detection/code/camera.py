import os, time, threading, cv2, torch, numpy as np, tkinter as tk, textwrap
from ultralytics import YOLO
from tkinter import messagebox, simpledialog, filedialog
from tkinter import ttk
# Thêm các thư viện cho PIL (vẽ tiếng Việt)
from PIL import Image, ImageTk, ImageDraw, ImageFont 
import re 
from tkinter import Toplevel 
from datetime import datetime 

# --- Import các file code của bạn ---
import database 
import os

# (Các import lõi AI của bạn)
try:
    from recognition_engine import RecognitionEngine, UNKNOWN_NAME, iou_xyxy
    from behavior_analyzer import BieuCamAnalyzer
except ImportError as e:
    root_err = tk.Tk()
    root_err.withdraw()
    messagebox.showerror("Lỗi Import", f"Lỗi import trong camera.py: {e}\n\nHãy đảm bảo recognition_engine.py, behavior_analyzer.py ở cùng thư mục.")
    root_err.destroy()
    exit()

# ===== CẤU HÌNH (Đã chuyển từ app_main.py) =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH      = os.path.join(BASE_DIR, "..", "yolov8s-face-lindevs.pt")
VIDEO_PATH = "" 
FONT_PATH = os.path.join(BASE_DIR, "..", "arial.ttf")

# --- CẤU HÌNH FONT CHỮ TIẾNG VIỆT ---

VIEW_W, VIEW_H  = 640, 480
CONF_THRES      = 0.45
TARGET_FPS      = 30.0

RECOG_ENABLED   = True
RECOG_THRES     = 0.60
RECOG_EVERY_N   = 1
FACE_MARGIN     = 0.15
DB_PATH_DEFAULT = "faces_db.npz" 
LOOP_VIDEO      = False

OUT_VIDEO_DEFAULT = "video_output.mp4" 
# =====================

# ===================================================================
# LỚP HỘP THOẠI TÙY CHỈNH (Không thay đổi)
# ===================================================================
class EnrollmentDialog(simpledialog.Dialog):
    """Hộp thoại tùy chỉnh để nhập thông tin sinh viên."""
    
    def __init__(self, parent, title="Đăng ký học sinh mới"):
        self.result = None
        Toplevel.__init__(self, parent) 
        self.transient(parent)
        if title:
            self.title(title)
        self.parent = parent
        self.result = None
        
        body = tk.Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=15, pady=15)
        
        self.buttonbox()
        
        self.grab_set()
        if not self.initial_focus:
            self.initial_focus = self
            
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.geometry(f"+{parent.winfo_rootx()+50}+{parent.winfo_rooty()+50}")
        self.initial_focus.focus_set()
        self.wait_window(self)

    def body(self, master):
        master.grid_columnconfigure(1, weight=1)
        
        # 1. Họ và tên
        tk.Label(master, text="Họ và tên:").grid(row=0, column=0, sticky='w', pady=2)
        self.e_name = tk.Entry(master, width=30)
        self.e_name.grid(row=0, column=1, columnspan=2, sticky='we', padx=5)

        # 3. Giới tính (Chuyển lên row 1)
        tk.Label(master, text="Giới tính:").grid(row=1, column=0, sticky='w', pady=2)
        self.v_gender = tk.StringVar(master)
        self.v_gender.set("Nam") # Giá trị mặc định
        gender_options = ["Nam", "Nữ", "Khác"]
        self.om_gender = ttk.Combobox(master, textvariable=self.v_gender, values=gender_options, state='readonly', width=10)
        self.om_gender.grid(row=1, column=1, sticky='w', padx=5)

        # 4. Ngày sinh (Chuyển lên row 2)
        tk.Label(master, text="Ngày sinh:").grid(row=2, column=0, sticky='w', pady=2)
        self.e_birthday = tk.Entry(master, width=12)
        self.e_birthday.insert(0, "YYYY-MM-DD")
        self.e_birthday.grid(row=2, column=1, sticky='w', padx=5)

        return self.e_name 

    def validate(self):
        self.name = self.e_name.get().strip()
        self.gender = self.v_gender.get()
        self.birthday = self.e_birthday.get().strip()

        if not self.name:
            messagebox.showerror("Lỗi", "Họ và tên không được để trống.", parent=self)
            return 0
        
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', self.birthday):
            messagebox.showerror("Lỗi", "Định dạng ngày sinh không hợp lệ. \nPhải là YYYY-MM-DD (ví dụ: 2000-01-30).", parent=self)
            return 0
        
        try:
            datetime.strptime(self.birthday, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("Lỗi", "Ngày sinh không hợp lệ (ví dụ: 2000-02-31 là sai).", parent=self)
            return 0
            
        return 1

    def apply(self):
        self.result = {
            "name": self.name,
            "gender": self.gender,
            "birthday": self.birthday
        }
# ===================================================================
# KẾT THÚC LỚP DIALOG
# ===================================================================


class Camera(ttk.Frame):
    """
    Đây là lớp Màn hình chính
    """
    def __init__(self, master, user_info):
        
        super().__init__(master, padding=10)
        self.pack(fill=tk.BOTH, expand=True) 
        
        self.user_info = user_info 
        username = self.user_info.get('username', 'User')

        self.root = master 
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        top_frame = tk.Frame(self)
        top_frame.pack(fill="both", expand=True, padx=8, pady=8)

        self.left_panel = tk.Label(top_frame)
        self.left_panel.pack(side="left")
        self.left_panel.bind("<Button-1>", self.on_click_face)

        self.info_frame = tk.Frame(top_frame)
        self.info_frame.pack(side="right", padx=(8,0), fill="y")

        # --- THÊM CỘT ID VÀO BẢNG ---
        cols = ("ID", "No", "Name", "Eyes", "Mouth", "Head", "Behavior", "Alerts")
        self.info_tree = ttk.Treeview(self.info_frame, columns=cols, show='headings', height=24)
        col_w = [50, 40, 160, 120, 120, 140, 160, 340] 
        for c, w in zip(cols, col_w):
            self.info_tree.heading(c, text=c)
            self.info_tree.column(c, width=w, anchor='w')
        # --- KẾT THÚC THÊM CỘT ID ---

        self.info_vscroll = tk.Scrollbar(self.info_frame, orient='vertical', command=self.info_tree.yview)
        self.info_tree.configure(yscrollcommand=self.info_vscroll.set)
        self.info_vscroll.pack(side='right', fill='y')
        self.info_tree.pack(side='left', fill='both')
        
        try:
            self.info_tree.tag_configure('row_even', background='#e8f7e8', foreground='#000000')
            self.info_tree.tag_configure('row_odd', background='#FFFFFF', foreground='#000000')
            self.info_tree.tag_configure('has_alert', foreground='#8B0000')
            self.info_tree.tag_configure('continuation', foreground='#333333')
        except Exception:
            pass

        btnf = tk.Frame(self)
        btnf.pack(pady=4)
        
        # === THAY ĐỔI NÚT BẤM (ĐÃ SỬA) ===
        
        # 1. Nút "Chọn video" MỚI
        self.btn_select_video = tk.Button(btnf, text="Chọn video", command=self.select_video_file)
        self.btn_select_video.pack(side="left", padx=5)
        
        # 2. Nút "Phát/Dừng" (thay thế nút "Phát video" cũ)
        self.btn_video = tk.Button(btnf, text="Phát Video", command=self.toggle_play_pause)
        self.btn_video.pack(side="left", padx=5)
        self.btn_video.config(state="disabled") # Bắt đầu ở trạng thái bị vô hiệu hóa
        
        # 3. Các nút khác giữ nguyên
        tk.Button(btnf, text="Ghi video", command=self.toggle_record).pack(side="left", padx=5)
        tk.Button(btnf, text="Đăng ký khuôn mặt", command=self.enroll_one).pack(side="left", padx=5)
        
        self.btn_webcam = tk.Button(btnf, text="Mở Webcam", command=self.toggle_webcam)
        self.btn_webcam.pack(side="left", padx=5)
        # Nút Webcam luôn ở trạng thái "normal" (sửa lỗi)
        
        tk.Button(btnf, text="Thoát", command=self.on_close).pack(side="left", padx=5)
        # === KẾT THÚC THAY ĐỔI NÚT BẤM ===

        self.status = tk.Label(self, text=f"Trạng thái: Sẵn sàng. Chào, {username}!", anchor="w")
        self.status.pack(fill="x", padx=8, pady=(0,8))

        self.cap = None
        self.running = False
        self.mode = 'idle' 
        self.period = 1.0/TARGET_FPS
        
        # --- BIẾN TRẠNG THÁI MỚI ---
        self.paused = False # Trạng thái Tạm dừng
        self.video_file_path = None # Lưu đường dẫn video đã chọn
        # --- KẾT THÚC BIẾN MỚI ---
        
        self.frame_lock = threading.Lock(); self.latest_frame = None
        self.det_lock = threading.Lock(); self.last_boxes=[]; self.last_scores=[]
        
        self.id_lock  = threading.Lock()
        self.last_names = [] 
        self.last_confs = []
        self.last_student_ids = [] 
        self.id_to_name_cache = {} 

        self.frame_count = 0
        self.force_recog_frames = 0; self.sticky = None; self.enrolling = False
        self.writer=None; self.recording=False; self.out_fps=TARGET_FPS; 
        self.out_path=OUT_VIDEO_DEFAULT 
        
        self.capture_thread_handle = None
        self.infer_thread_handle = None

        self.model = self.load_model(MODEL_PATH)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.recog = RecognitionEngine(self.device, recog_thres=RECOG_THRES, face_margin=FACE_MARGIN)
        self.analyzer = BieuCamAnalyzer()

        try:
            self.pil_font = ImageFont.truetype(FONT_PATH, 16) 
        except IOError:
            messagebox.showwarning("Lỗi Font", f"Không tìm thấy file font: {FONT_PATH}\n\nChữ tiếng Việt sẽ hiển thị lỗi.")
            self.pil_font = ImageFont.load_default() 
        
        db_path_full = os.path.join(BASE_DIR, DB_PATH_DEFAULT)
        if os.path.exists(db_path_full):
            try:
                self.recog.load_db(db_path_full)
                self.set_status(f"Đã tải DB: {DB_PATH_DEFAULT} (N={len(self.recog.names)})")
            except Exception as e:
                messagebox.showerror("Lỗi Tải DB", f"Lỗi khi tải {DB_PATH_DEFAULT}:\n{e}")
                self.set_status(f"Lỗi tải DB. (N={len(self.recog.names)})")
        else:
            self.set_status(f"Sẵn sàng. Không tìm thấy {DB_PATH_DEFAULT}. DB trống.")
        
        self.last_analysis = None
        self.root.after(16, self.gui_loop)

    def set_status(self, t): 
        if self.status:
            self.status.config(text=f"Trạng thái: {t}")

    def load_model(self, path):
        if not os.path.exists(path):
            messagebox.showerror("Lỗi", f"Không tìm thấy model: {path}"); self.root.destroy()
            return None
            
        m = YOLO(path)
        if torch.cuda.is_available():
            m.to("cuda"); 
        else: self.set_status("Model CPU")
        try: m.fuse()
        except: pass
        return m

    # --- CÁC HÀM CONTROL VIDEO/WEBCAM (ĐÃ VIẾT LẠI) ---
    
    def select_video_file(self):
        """Hàm này chỉ MỞ file dialog để CHỌN video."""
        # Nếu đang chạy webcam hoặc video khác, dừng lại
        if self.mode != 'idle':
            self.stop() 

        video_file_path = filedialog.askopenfilename(
            title="Chọn file video",
            filetypes=[("Video files", "*.mp4 *.avi *.mkv *.mov"), ("All files", "*.*")]
        )
        if not video_file_path: 
            return 

        self.video_file_path = video_file_path # Lưu đường dẫn
        self.start_video_stream() # Bắt đầu phát video

    def start_video_stream(self):
        """Hàm này MỞ video từ self.video_file_path và BẮT ĐẦU các luồng."""
        if not self.video_file_path:
            messagebox.showerror("Lỗi", "Chưa chọn file video.")
            return

        try:
            self.cap = cv2.VideoCapture(self.video_file_path)
            if not self.cap.isOpened():
                messagebox.showerror("Lỗi", f"Không mở được video: {self.video_file_path}"); return

            self.out_path = os.path.join(
                os.path.dirname(self.video_file_path), 
                os.path.splitext(os.path.basename(self.video_file_path))[0] + "_output.mp4"
            )

            fps = self.cap.get(cv2.CAP_PROP_FPS)
            if fps and fps > 1e-3:
                self.period = 1.0 / fps; self.out_fps = fps
                self.set_status(f"Đang phát: {os.path.basename(self.video_file_path)} ({fps:.1f} FPS)")
            else:
                self.period = 1.0 / TARGET_FPS; self.out_fps = TARGET_FPS
                self.set_status(f"Đang phát: {os.path.basename(self.video_file_path)} (dùng {TARGET_FPS:.1f} FPS)")

            self.running = True  # Bật cờ cho các luồng
            self.paused = False  # Bắt đầu ở trạng thái phát
            self.mode = 'video' 
            
            # Cập nhật trạng thái nút
            self.btn_video.config(text="Dừng Video", state="normal") # Kích hoạt nút Dừng
            self.btn_select_video.config(text="Đổi video") 
            # SỬA LỖI: Không vô hiệu hóa nút webcam
            self.btn_webcam.config(state="normal") 

            # Khởi động các luồng
            self.capture_thread_handle = threading.Thread(target=self.capture_thread, daemon=True)
            self.capture_thread_handle.start()
            self.infer_thread_handle = threading.Thread(target=self.infer_thread, daemon=True)
            self.infer_thread_handle.start()
            
        except Exception as e:
            messagebox.showerror("Lỗi Video", f"Lỗi không xác định khi mở video:\n{e}")
            if self.cap: self.cap.release(); self.cap = None

    def toggle_play_pause(self):
        """Hàm này xử lý PHÁT/DỪNG (Play/Pause) video đang mở."""
        if not self.running or self.mode != 'video':
            return # Không làm gì nếu video chưa chạy

        if self.paused:
            # --- LOGIC PHÁT (RESUME) ---
            
            is_at_end = False
            if self.cap:
                current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                total_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
                if current_frame >= total_frames - 1:
                    is_at_end = True
            
            if is_at_end:
                # Nếu đã kết thúc, tua lại từ đầu
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.set_status(f"Phát lại: {os.path.basename(self.video_file_path)}")
            else:
                self.set_status(f"Đang phát: {os.path.basename(self.video_file_path)}")

            self.paused = False # Bỏ tạm dừng
            self.btn_video.config(text="Dừng Video")

        else:
            # --- LOGIC DỪNG (PAUSE) ---
            self.paused = True
            self.btn_video.config(text="Phát Video")
            self.set_status("Đã tạm dừng video")
    
    def toggle_webcam(self):
        """Hàm này bật/tắt webcam."""
        if self.mode == 'webcam':
            self.stop()
        else:
            # Nếu đang ở chế độ video (đang phát hoặc tạm dừng), dừng nó lại
            if self.mode == 'video':
                self.stop()
            self.start_webcam()

    def start_webcam(self):
        """Hàm này chỉ khởi động webcam."""
        try:
            self.cap = cv2.VideoCapture(0) 
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(1)
                if not self.cap.isOpened():
                        messagebox.showerror("Lỗi Webcam", "Không mở được webcam (đã thử index 0 và 1).")
                        return

            self.period = 1.0 / TARGET_FPS
            self.out_fps = TARGET_FPS
            self.set_status(f"Đang chạy: Webcam (dùng {TARGET_FPS:.1f} FPS)")
            self.out_path = "webcam_output.mp4"
            self.running = True
            self.mode = 'webcam' 
            self.paused = False # Đảm bảo không bị tạm dừng
            
            # Cập nhật trạng thái nút
            self.btn_webcam.config(text="Dừng Webcam") 
            # Vô hiệu hóa các nút video
            self.btn_video.config(state="disabled", text="Phát Video")
            self.btn_select_video.config(state="disabled")

            self.capture_thread_handle = threading.Thread(target=self.capture_thread, daemon=True)
            self.capture_thread_handle.start()
            self.infer_thread_handle = threading.Thread(target=self.infer_thread, daemon=True)
            self.infer_thread_handle.start()
            
        except Exception as e:
            messagebox.showerror("Lỗi Webcam", f"Lỗi không xác định khi mở webcam:\n{e}")
            if self.cap: self.cap.release(); self.cap = None

    def stop(self):
        """Hàm dừng chung, reset mọi thứ về trạng thái ban đầu."""
        self.running = False 
        
        try:
            if self.capture_thread_handle is not None and self.capture_thread_handle.is_alive():
                self.capture_thread_handle.join(timeout=1.5) 
        except Exception as e:
            print(f"Lỗi khi join luồng capture: {e}")
            
        try:
            if self.infer_thread_handle is not None and self.infer_thread_handle.is_alive():
                self.infer_thread_handle.join(timeout=1.0) 
        except Exception as e:
            print(f"Lỗi khi join luồng infer: {e}")

        self.mode = 'idle' 
        self.paused = False # Reset trạng thái tạm dừng
        self.video_file_path = None # Xóa đường dẫn video
        
        # Reset trạng thái các nút về ban đầu (ĐÃ SỬA)
        self.btn_video.config(text="Phát Video", state="disabled") # Vô hiệu hóa
        self.btn_webcam.config(text="Mở Webcam", state="normal") # Kích hoạt
        self.btn_select_video.config(text="Chọn video", state="normal") # Kích hoạt

        self.set_status("Đã dừng")
        
        if self.cap: 
            self.cap.release()
            self.cap = None
            
        self._close_writer()
        self.recording = False
        
        self.capture_thread_handle = None
        self.infer_thread_handle = None

    # === KẾT THÚC CÁC HÀM CONTROL ===

    
    # Threads
    def capture_thread(self):
        """Luồng đọc frame (ĐÃ SỬA cho logic Play/Pause)."""
        while self.running and self.cap:
            try:
                # --- LOGIC TẠM DỪNG (PAUSE) MỚI ---
                if self.paused:
                    time.sleep(0.05) # Ngủ một chút khi đang tạm dừng
                    continue # Bỏ qua phần còn lại của vòng lặp và lặp lại
                # --- KẾT THÚC LOGIC TẠM DỪNG ---
                
                t0 = time.time()
                ok, f = self.cap.read()
                
                if not ok:
                    # Nếu video kết thúc
                    if self.mode == 'video' and self.cap:
                        # Tự động tạm dừng và chờ người dùng bấm "Phát Lại"
                        self.root.after(0, self._handle_video_end) # Cập nhật GUI an toàn
                        
                        # Giữ luồng này "sống" nhưng ở trạng thái tạm dừng
                        while self.paused and self.running:
                            time.sleep(0.05)
                        
                        # Nếu self.running = False (bấm stop), vòng lặp while bên ngoài sẽ thoát
                        # Nếu self.paused = False (bấm Phát Lại), logic trong toggle_play_pause
                        # đã tua video, chúng ta chỉ cần 'continue' để đọc frame mới
                        if self.running:
                            continue 
                        else:
                            break
                    else: 
                        # Webcam hỏng hoặc lỗi không xác định
                        self.running = False 
                        break
                
                if self.mode == 'webcam':
                    f = cv2.flip(f, 1) 
                    
                f = cv2.resize(f, (VIEW_W, VIEW_H))
                with self.frame_lock: self.latest_frame = f.copy()
                
                dt = time.time()-t0
                if dt < self.period: 
                    time.sleep(self.period-dt)
            except Exception as e:
                print(f"Lỗi trong capture_thread: {e}")
                self.running = False
                
    def _handle_video_end(self):
        """Hàm hỗ trợ: Cập nhật GUI khi video kết thúc (gọi từ luồng khác)."""
        if self.mode == 'video':
            self.paused = True
            self.btn_video.config(text="Phát Lại")
            self.set_status("Video đã kết thúc. Bấm 'Phát Lại' để xem lại.")
            
    # ===================================================================
    # LUỒNG INFER_THREAD (Không thay đổi)
    # ===================================================================
    def infer_thread(self):
        while self.running:
            frame = None 
            
            # --- Logic TẠM DỪNG MỚI cho infer_thread ---
            if self.paused:
                time.sleep(0.05)
                continue
            # --- Hết ---
            
            try:
                with self.frame_lock:
                    if self.latest_frame is not None:
                            frame = self.latest_frame.copy()
                
                if frame is None:
                    time.sleep(0.005)
                    continue

                if self.model is None:
                    time.sleep(0.01); continue
                    
                self.frame_count += 1
                res = self.model(frame, conf=CONF_THRES, verbose=False)[0]
                boxes  = res.boxes.xyxy.cpu().numpy().astype(int) if res.boxes else np.zeros((0,4), dtype=int)
                scores = res.boxes.conf.cpu().numpy().tolist()     if res.boxes else []

                names = []
                confs = []
                student_ids = []
                
                force_now = self.force_recog_frames > 0
                if RECOG_ENABLED and len(boxes)>0 and (force_now or (self.frame_count % RECOG_EVERY_N == 0)):
                    embs, idx = self.recog.embed_batch(frame, boxes)
                    
                    pn, pc = [UNKNOWN_NAME]*len(boxes), [0.0]*len(boxes)
                    if embs is not None:
                        pred_names_or_ids, pred_confs = self.recog.predict_batch(embs)
                        for k,i in enumerate(idx): 
                            pn[i] = pred_names_or_ids[k]
                            pc[i] = pred_confs[k]

                    names = [UNKNOWN_NAME] * len(boxes)
                    confs = pc
                    student_ids = [None] * len(boxes)

                    for i, id_str in enumerate(pn):
                        if id_str != UNKNOWN_NAME:
                            try:
                                student_id = int(id_str) # Chuyển "123" -> 123
                                student_ids[i] = student_id
                                
                                if student_id in self.id_to_name_cache:
                                    names[i] = self.id_to_name_cache[student_id]
                                else:
                                    student_info = database.get_student_by_id(student_id)
                                    if student_info:
                                        name = student_info['name']
                                        names[i] = name
                                        self.id_to_name_cache[student_id] = name # Lưu cache
                                    else:
                                        names[i] = f"ID_{id_str}_NOT_FOUND" 
                                        self.id_to_name_cache[student_id] = names[i]
                            except ValueError:
                                names[i] = id_str 
                                student_ids[i] = None 
                else:
                    with self.id_lock:
                        if len(self.last_names) == len(boxes):
                            names = self.last_names[:]
                            confs = self.last_confs[:]
                            student_ids = self.last_student_ids[:]
                        else:
                            names = [UNKNOWN_NAME] * len(boxes)
                            confs = [0.0] * len(boxes)
                            student_ids = [None] * len(boxes)

                if self.force_recog_frames>0: self.force_recog_frames-=1

                if self.sticky is not None and len(boxes)>0 and self.sticky.get('ttl',0)>0:
                    sbox=self.sticky['box']
                    sname=self.sticky['name'] # Tên (Nguyễn Văn A)
                    sid = self.sticky.get('id')  # ID (123)
                    
                    best_i,best_iou=-1,0.0
                    for i,b in enumerate(boxes):
                        iou=iou_xyxy(tuple(b), tuple(sbox))
                        if iou>best_iou: best_i,best_iou=i,iou
                    if best_i>=0 and best_iou>=0.3:
                        names[best_i] = sname # Ghi đè Tên
                        student_ids[best_i] = sid # Ghi đè ID
                        confs[best_i] = 1.0
                        self.sticky['ttl']-=1

                with self.det_lock:
                    self.last_boxes=boxes; self.last_scores=scores
                with self.id_lock:
                    self.last_names = names
                    self.last_confs = confs
                    self.last_student_ids = student_ids 

                
                fb = [tuple(map(int, b)) for b in boxes] if len(boxes) > 0 else None
                self.last_analysis = self.analyzer.analyze_frame(frame, face_boxes=fb)
                
            except Exception as e:
                print(f"Lỗi nghiêm trọng trong infer_thread: {e}")
                self.last_analysis = None


    
    # ===================================================================
    # HÀM GUI_LOOP (Không thay đổi)
    # ===================================================================
    def gui_loop(self):
        frame=None
        with self.frame_lock:
            if self.latest_frame is not None: frame=self.latest_frame.copy()
        
        # Sửa logic hiển thị khi tạm dừng
        if frame is None:
            if not self.running:
                self.left_panel.config(text="Sẵn sàng. Hãy 'Chọn video' hoặc 'Mở Webcam'.", image=None)
            elif self.paused:
                 self.left_panel.config(text="Đã tạm dừng. Bấm 'Phát Video' để tiếp tục.", image=None)
            else:
                self.left_panel.config(text="Đang tải...", image=None)
            
            self.root.after(16, self.gui_loop)
            return

        with self.det_lock, self.id_lock:
            boxes=list(self.last_boxes); scores=list(self.last_scores)
            names=list(self.last_names); confs=list(self.last_confs)
            student_ids = list(self.last_student_ids) 

        
        # --- LOGIC VẼ (Dùng PIL) ---
        img_pil = None
        draw = None
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(frame_rgb)
            draw = ImageDraw.Draw(img_pil)
        except Exception as e:
            print(f"Lỗi chuyển đổi PIL: {e}")
            img_pil = None 
            
        for i, ((x1,y1,x2,y2), detc) in enumerate(zip(boxes, scores)):
            name = names[i] if i < len(names) else UNKNOWN_NAME
            simc = confs[i] if i < len(confs) else 0.0
            student_id = student_ids[i] if i < len(student_ids) else None
            
            color=(0,255,0) if name!=UNKNOWN_NAME else (0,0,255)
            
            display_name = name.split(" ")[-1] if name != UNKNOWN_NAME else UNKNOWN_NAME
            id_str = str(student_id) if student_id else '?'
            text_to_draw = f"ID: {id_str} | {display_name} {simc:.2f}"

            cv2.rectangle(frame,(x1,y1),(x2,y2),color,2)
            
            if img_pil and draw and self.pil_font:
                try:
                    frame_rgb_with_rect = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img_pil = Image.fromarray(frame_rgb_with_rect)
                    draw = ImageDraw.Draw(img_pil)
                    
                    draw.text((x1 + 2, max(0, y1 - 20)), text_to_draw, font=self.pil_font, fill=color)
                    
                    frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
                except Exception as e:
                    print(f"Lỗi PIL draw: {e}")
                    cv2.putText(frame, f"ID: {id_str} | {display_name} {simc:.2f}",
                                (x1, max(20,y1-8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            else:
                 cv2.putText(frame, f"ID: {id_str} | {display_name} {simc:.2f}",
                                (x1, max(20,y1-8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        # --- KẾT THÚC LOGIC VẼ ---

        if self.last_analysis is not None:
            frame = self.analyzer.draw_analysis_info(frame, self.last_analysis)

        if self.recording and self.writer is not None:
            try:
                self.writer.write(frame)
            except Exception as e:
                print(f"Lỗi khi ghi frame: {e}")
                self.toggle_record() 

        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        imgtk = ImageTk.PhotoImage(Image.fromarray(img))
        self.left_panel.imgtk = imgtk; self.left_panel.config(image=imgtk, text=None) 

        # --- CẬP NHẬT TREEVIEW (Không thay đổi) ---
        try:
            analysis = self.last_analysis if self.last_analysis is not None else {}
            face_states = analysis.get('face_states', []) if isinstance(analysis, dict) else []
            behs = analysis.get('behaviors', []) if isinstance(analysis, dict) else []

            try:
                for item in self.info_tree.get_children():
                    self.info_tree.delete(item)

                for i, name in enumerate(names):
                    student_id = student_ids[i] if i < len(student_ids) else None
                    id_str = str(student_id) if student_id else ''
                    
                    fs = face_states[i] if i < len(face_states) else None
                    
                    beh_list = []
                    if fs and 'behaviors' in fs and fs['behaviors']: beh_list = fs['behaviors']
                    elif fs and 'behavior' in fs and fs['behavior'] is not None: beh_list = [fs['behavior']]
                    elif i < len(behs) and behs[i] is not None: beh_list = [behs[i]]
                    try:
                        beh_label = ", ".join(f"{b.get('label','')} {b.get('conf',0.0):.2f}" for b in beh_list) if beh_list else ''
                    except Exception: beh_label = ''

                    eye_txt = "NO_FACE"; mouth_txt = "NO_FACE"; head_txt = ""; alerts_txt = ""
                    if fs:
                        eye_txt = fs.get('eye_state', ("NO_FACE", 0))[0]
                        mouth_txt = fs.get('mouth_state', ("NO_FACE", 0))[0]
                        head_states = fs.get('head_orientation', {}).get('states', [])
                        head_txt = ",".join(head_states) if head_states else 'HEAD_STRAIGHT'
                        alerts_for_face = fs.get('alerts', []) if fs.get('alerts') is not None else []
                        alerts_txt = ", ".join(alerts_for_face)

                    beh_txt = beh_label
                    row_tag = 'row_even' if (i % 2) == 0 else 'row_odd'
                    MAX_ALERT_COL_CHARS = 80
                    alert_chunks = []
                    if alerts_txt:
                        try:
                            wrapped = textwrap.wrap(alerts_txt, width=MAX_ALERT_COL_CHARS)
                            alert_chunks = wrapped if wrapped else [alerts_txt]
                        except Exception:
                            parts = [p.strip() for p in alerts_txt.split(',') if p.strip()]
                            cur = ''
                            for p in parts:
                                if not cur: cur = p
                                elif len(cur) + 2 + len(p) <= MAX_ALERT_COL_CHARS: cur = cur + ', ' + p
                                else: alert_chunks.append(cur); cur = p
                            if cur: alert_chunks.append(cur)
                    else:
                        alert_chunks = []

                    first_alert = alert_chunks[0] if alert_chunks else ''
                    
                    values = (id_str, str(i+1), name, eye_txt, mouth_txt, head_txt, beh_txt, first_alert)
                    tags = [row_tag]
                    if first_alert:
                        tags.append('has_alert')
                    self.info_tree.insert('', 'end', values=values, tags=tuple(tags))

                    for ac in alert_chunks[1:]:
                        cont_vals = ('', '', '', '', '', '', '', ac) 
                        cont_tags = [row_tag, 'continuation', 'has_alert']
                        self.info_tree.insert('', 'end', values=cont_vals, tags=tuple(cont_tags))
            except Exception:
                pass
        except Exception as e:
            # print(f"Lỗi GUI loop: {e}")
            pass
        # --- HẾT SỬA TREEVIEW ---
        
        self.root.after(16, self.gui_loop)

    # ===================================================================
    # CÁC HÀM CÒN LẠI (Không thay đổi)
    # ===================================================================
    
    def enroll_one(self):
        with self.det_lock:
            if len(self.last_boxes)==0:
                messagebox.showwarning("Thông báo","Chưa thấy khuôn mặt nào."); return
        self.enrolling=True; self.set_status("CLICK vào khuôn mặt để đăng ký...")

    def on_click_face(self, event):
        if not self.enrolling: return
        x,y=int(event.x),int(event.y)
        
        with self.det_lock, self.frame_lock:
            boxes=list(self.last_boxes)
            frame=self.latest_frame.copy() if self.latest_frame is not None else None
        
        if frame is None or len(boxes)==0:
            self.set_status("Chưa có frame/không có mặt."); self.enrolling=False; return
            
        chosen, area=-1, -1
        for i,(x1,y1,x2,y2) in enumerate(boxes):
            if x1<=x<=x2 and y1<=y<=y2:
                a=(x2-x1)*(y2-y1)
                if a>area: area=a; chosen=i
                
        if chosen<0:
            self.set_status("Không trúng khuôn mặt nào."); return

        self.enrolling = False 
        box = boxes[chosen]

        # --- BƯỚC 1: HIỂN THỊ HỘP THOẠI MỚI (Đã cải tiến) ---
        dialog = EnrollmentDialog(self.root)
        info = dialog.result 

        if info is None: 
            self.set_status("Hủy đăng ký."); return
            
        name = info['name']
        gender = info['gender']
        birthday = info['birthday']
        class_name = "lớp A" 

        self.set_status(f"Đang xử lý đăng ký cho {name}...")

        # --- BƯỚC 2: TRÍCH XUẤT EMBEDDING ---
        emb, idx = self.recog.embed_batch(frame, np.array([box]))
        if emb is None:
            messagebox.showerror("Lỗi", "Không trích xuất được embedding. \nHãy thử lại với góc mặt rõ hơn.")
            self.set_status("Lỗi trích xuất embedding."); return
        
        face_embedding = emb[0] 

        # --- BƯỚC 3: LƯU HỌC SINH VÀO CSDL MYSQL ĐỂ LẤY ID ---
        new_student_id, msg = database.add_student(name, class_name, gender, birthday, avartar_url=None)

        if new_student_id is None:
            messagebox.showerror("Lỗi CSDL", f"Không thể tạo học sinh:\n{msg}")
            self.set_status("Lỗi CSDL khi tạo học sinh."); return

        # --- BƯỚC 4: LƯU ẢNH CROP (SỬ DỤNG ID MỚI) ---
        face_path = None 
        try:
            (x1,y1,x2,y2) = box
            face_crop = frame[y1:y2, x1:x2]
            
            face_dir = os.path.splitext(DB_PATH_DEFAULT)[0] + "_images"
            os.makedirs(face_dir, exist_ok=True) 
            
            face_path_rel = os.path.join(face_dir, f"face_{new_student_id}.jpg")
            face_path_abs = os.path.join(BASE_DIR, face_path_rel) 
            cv2.imwrite(face_path_abs, face_crop)
            
            face_path = face_path_rel
            
            database.update_student_avatar(new_student_id, face_path)
            
        except Exception as e:
            messagebox.showerror("Lỗi Lưu Ảnh", f"Không thể lưu ảnh crop: {e}")

        # --- BƯỚC 5: LIÊN KẾT EMBEDDING TRONG CSDL ---
        embedding_name = f"student_{new_student_id}"
        ok, msg = database.link_face_embedding(new_student_id, embedding_name, face_path)
        if not ok:
           messagebox.showwarning("Lỗi CSDL", f"Lỗi khi liên kết embedding: {msg}")

        # --- BƯỚC 6: LƯU VÀO FILE .NPZ (LƯU ID THAY VÌ TÊN) ---
        self.recog.add_face(str(new_student_id), face_embedding) 
        
        try:
            db_path_full = os.path.join(BASE_DIR, DB_PATH_DEFAULT)
            self.recog.save_db(db_path_full) 
            self.set_status(f"Đã đăng ký & lưu: {name} (ID: {new_student_id}) (gallery={len(self.recog.names)})")
            
            self.id_to_name_cache[new_student_id] = name
            
        except Exception as e:
            messagebox.showerror("Lỗi Lưu DB", f"Đăng ký thành công, nhưng lỗi khi lưu file .npz:\n{e}")
            self.set_status(f"Đăng ký: {name} (ID: {new_student_id}) - LỖI LƯU FILE .NPZ")
        
        self.sticky={'box':box, 'name':name, 'id': new_student_id, 'ttl':30}
        self.force_recog_frames=20
    
    # --- HẾT HÀM ON_CLICK_FACE ---

    # Recording
    def _open_writer(self, path, fps):
        fourcc=cv2.VideoWriter_fourcc(*'mp4v')
        self.writer=cv2.VideoWriter(path, fourcc, float(fps), (VIEW_W, VIEW_H))
        if not self.writer.isOpened():
            self.writer.release(); self.writer=None
            raise RuntimeError("Không mở được VideoWriter.")

    def _close_writer(self):
        if self.writer is not None:
            try: self.writer.release()
            except: pass
            self.writer=None

    def toggle_record(self):
        if not self.running:
             messagebox.showwarning("Thông báo", "Phải bật video hoặc webcam trước khi ghi.")
             return
             
        if not self.recording:
            path=filedialog.asksaveasfilename(defaultextension=".mp4", initialfile=self.out_path,
                                             filetypes=[("MP4","*.mp4"),("AVI","*.avi"),("All","*.*")])
            if not path: return
            
            self.out_path=path 
            try: self._open_writer(self.out_path, self.out_fps)
            except Exception as e: messagebox.showerror("Lỗi", str(e)); return
            self.recording=True; self.set_status(f"ĐANG GHI: {self.out_path}")
        else:
            self._close_writer(); self.recording=False
            self.set_status(f"Đã dừng ghi. Lưu tại: {self.out_path}")

    # on_close
    def on_close(self, force=False): 
        if force:
            print("Đang đóng camera (bắt buộc)...")
            self.stop() 
            try: self.destroy() 
            except Exception: pass
            return

        if messagebox.askokcancel("Thoát", "Bạn có chắc muốn thoát ứng dụng?"):
            print("Đang đóng ứng dụng...")
            self.stop() 
            try:
                if hasattr(self, 'root') and self.root is not None:
                    self.root.after(100, self.root.destroy) 
            except Exception as e:
                print(f"Lỗi khi đóng cửa sổ root: {e}")
                if hasattr(self, 'root') and self.root is not None:
                    try: self.root.destroy()
                    except: pass