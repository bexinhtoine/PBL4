# camera_mode.py
import time, threading, cv2, numpy as np, torch, tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from PIL import Image, ImageTk
from ultralytics import YOLO

from recognition_engine import RecognitionEngine, UNKNOWN_NAME, iou_xyxy
from behavior_analyzer import BieuCamAnalyzer

MODEL_PATH     = "yolov8s-face-lindevs.pt"
CAM_INDEX      = 0
VIEW_W, VIEW_H = 640, 480
CONF_THRES     = 0.5
TARGET_FPS     = 30.0
RECOG_EVERY_N  = 2
OUT_VIDEO_NAME = "camera_annot.mp4"

class CameraApp(tk.Toplevel):
    def __init__(self, master, recog_engine: RecognitionEngine, model_path=MODEL_PATH):
        super().__init__(master)
        self.title("Webcam Face Recognition")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.panel = tk.Label(self); self.panel.pack(padx=8, pady=8)
        btnf = tk.Frame(self); btnf.pack(pady=4)
        self.btn = tk.Button(btnf, text="Bật camera", command=self.toggle); self.btn.pack(side="left", padx=5)
        tk.Button(btnf, text="Đăng ký khuôn mặt", command=self.enroll_one).pack(side="left", padx=5)
        tk.Button(btnf, text="Lưu DB", command=self.save_db).pack(side="left", padx=5)
        tk.Button(btnf, text="Tải DB", command=self.load_db).pack(side="left", padx=5)
        tk.Button(btnf, text="Xóa DB", command=self.clear_db).pack(side="left", padx=5)
        tk.Button(btnf, text="Ghi video", command=self.toggle_record).pack(side="left", padx=5)
        tk.Button(btnf, text="Đóng", command=self.on_close).pack(side="left", padx=5)
        self.status = tk.Label(self, text="Trạng thái: Sẵn sàng", anchor="w")
        self.status.pack(fill="x", padx=8, pady=(0,8))

        self.cap = None; self.running = False
        self.frame_lock = threading.Lock(); self.latest_frame = None
        self.det_lock = threading.Lock(); self.last_boxes = []; self.last_scores = []
        self.id_lock = threading.Lock(); self.last_names = []; self.last_confs = []
        self.frame_count = 0

        self.writer = None; self.recording = False; self.out_path = OUT_VIDEO_NAME

        self.model  = self._load_model(model_path)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.recog  = recog_engine
        self.analyzer = BieuCamAnalyzer()
        self.last_analysis = None

        self.after(int(1000/TARGET_FPS), self.gui_loop)

    def _load_model(self, path):
        m = YOLO(path)
        if torch.cuda.is_available():
            m.to("cuda"); self._set_status("Model GPU (Webcam)")
        else:
            self._set_status("Model CPU (Webcam)")
        try: m.fuse()
        except: pass
        return m

    def _set_status(self, txt): self.status.config(text=f"Trạng thái: {txt}")

    def toggle(self):
        if self.running: self.stop()
        else: self.start()

    def start(self):
        self.cap = cv2.VideoCapture(CAM_INDEX, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(CAM_INDEX, cv2.CAP_MSMF)
        if not self.cap.isOpened():
            messagebox.showerror("Lỗi", "Không mở được camera."); return
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, VIEW_W)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, VIEW_H)
        self.running = True
        self.btn.config(text="Tắt camera")
        self._set_status("Camera ON")
        threading.Thread(target=self.capture_thread, daemon=True).start()
        threading.Thread(target=self.infer_thread, daemon=True).start()

    def stop(self):
        self.running = False
        self.btn.config(text="Bật camera")
        self._set_status("Camera OFF")
        if self.cap:
            self.cap.release(); self.cap = None
        self._close_writer(); self.recording = False

    def capture_thread(self):
        period = 1.0/TARGET_FPS
        while self.running and self.cap:
            t0 = time.time()
            ok, f = self.cap.read()
            if not ok:
                time.sleep(0.01); continue
            f = cv2.resize(f, (VIEW_W, VIEW_H))
            with self.frame_lock: self.latest_frame = f.copy()
            dt = time.time() - t0
            if dt < period: time.sleep(period - dt)

    def infer_thread(self):
        while self.running:
            with self.frame_lock:
                frame = None if self.latest_frame is None else self.latest_frame.copy()
            if frame is None:
                time.sleep(0.01); continue

            self.frame_count += 1
            res = self.model(frame, conf=CONF_THRES, verbose=False)[0]
            boxes  = res.boxes.xyxy.cpu().numpy().astype(int) if res.boxes else np.zeros((0,4), dtype=int)
            scores = res.boxes.conf.cpu().numpy().tolist()    if res.boxes else []
            names, confs = [], []

            if len(boxes) > 0 and (self.frame_count % RECOG_EVERY_N == 0):
                embs, idx = self.recog.embed_batch(frame, boxes)
                if embs is not None:
                    pn, pc = self.recog.predict_batch(embs)
                    names = [UNKNOWN_NAME]*len(boxes); confs = [0.0]*len(boxes)
                    for k, i in enumerate(idx):
                        names[i] = pn[k]; confs[i] = pc[k]
                else:
                    names = [UNKNOWN_NAME]*len(boxes); confs = [0.0]*len(boxes)
            else:
                with self.id_lock:
                    if len(self.last_names) == len(boxes):
                        names = self.last_names[:]; confs = self.last_confs[:]
                    else:
                        names = [UNKNOWN_NAME]*len(boxes); confs = [0.0]*len(boxes)

            with self.det_lock:
                self.last_boxes = boxes; self.last_scores = scores
            with self.id_lock:
                self.last_names = names; self.last_confs = confs

            self.last_analysis = self.analyzer.analyze_frame(frame)

    def gui_loop(self):
        frame = None
        with self.frame_lock:
            if self.latest_frame is not None:
                frame = self.latest_frame.copy()
        if frame is not None:
            with self.det_lock, self.id_lock:
                for i, ((x1,y1,x2,y2), sc) in enumerate(zip(self.last_boxes, self.last_scores)):
                    name = self.last_names[i] if i < len(self.last_names) else UNKNOWN_NAME
                    conf = self.last_confs[i] if i < len(self.last_confs) else 0.0
                    color = (0,255,0) if name != UNKNOWN_NAME else (0,0,255)
                    cv2.rectangle(frame, (x1,y1),(x2,y2), color, 2)
                    cv2.putText(frame, f"{name} {conf:.2f} | det {sc:.2f}",
                                (x1, max(20, y1-8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            if self.last_analysis is not None:
                frame = self.analyzer.draw_analysis_info(frame, self.last_analysis)

            if self.recording and self.writer is not None:
                self.writer.write(frame)

            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            imgtk = ImageTk.PhotoImage(Image.fromarray(img))
            self.panel.imgtk = imgtk; self.panel.config(image=imgtk)

        self.after(int(1000/TARGET_FPS), self.gui_loop)

    def enroll_one(self):
        with self.frame_lock:
            if self.latest_frame is None:
                messagebox.showwarning("Thông báo", "Chưa có khung hình."); return
            frame = self.latest_frame.copy()
        with self.det_lock:
            if len(self.last_boxes) == 0:
                messagebox.showwarning("Thông báo", "Không thấy khuôn mặt để đăng ký."); return
            areas = [(x2-x1)*(y2-y1) for (x1,y1,x2,y2) in self.last_boxes]
            idx = int(np.argmax(areas)); box = self.last_boxes[idx]

        name = simpledialog.askstring("Đăng ký", "Nhập tên:", parent=self)
        if not name: return
        emb, valid_idx = self.recog.embed_batch(frame, np.array([box]))
        if emb is None:
            messagebox.showerror("Lỗi", "Không trích xuất được embedding."); return
        self.recog.add_face(name, emb[0])
        self._set_status(f"Đăng ký: {name} (gallery={len(self.recog.names)})")

    def save_db(self):
        if self.recog.embs is None or len(self.recog.names) == 0:
            messagebox.showwarning("Thông báo", "DB rỗng, không có gì để lưu."); return
        path = filedialog.asksaveasfilename(defaultextension=".npz", initialfile="faces_db.npz",
                                            filetypes=[("NPZ","*.npz")], parent=self)
        if not path: return
        try:
            self.recog.save_db(path); self._set_status(f"Đã lưu DB: {path}")
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def load_db(self):
        path = filedialog.askopenfilename(defaultextension=".npz", initialfile="faces_db.npz",
                                          filetypes=[("NPZ","*.npz")], parent=self)
        if not path: return
        try:
            self.recog.load_db(path)
            self._set_status(f"Đã tải DB: {path} (N={len(self.recog.names)})")
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def clear_db(self):
        self.recog.embs = None; self.recog.names = []
        self._set_status("Đã xóa DB trong bộ nhớ.")

    def _open_writer(self, path, fps=TARGET_FPS):
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(path, fourcc, float(fps), (VIEW_W, VIEW_H))
        if not self.writer.isOpened():
            self.writer.release(); self.writer = None
            raise RuntimeError("Không mở được VideoWriter.")

    def _close_writer(self):
        if self.writer is not None:
            try: self.writer.release()
            except: pass
            self.writer = None

    def toggle_record(self):
        if not self.recording:
            path = filedialog.asksaveasfilename(defaultextension=".mp4",
                                                initialfile=self.out_path,
                                                filetypes=[("MP4","*.mp4"),("AVI","*.avi"),("All","*.*")],
                                                parent=self)
            if not path: return
            self.out_path = path
            try:
                self._open_writer(self.out_path, TARGET_FPS)
            except Exception as e:
                messagebox.showerror("Lỗi", str(e)); return
            self.recording = True; self._set_status(f"ĐANG GHI: {self.out_path}")
        else:
            self._close_writer(); self.recording = False
            self._set_status(f"Đã dừng ghi. Lưu tại: {self.out_path}")

    def on_close(self):
        self.stop()
        self.destroy()
