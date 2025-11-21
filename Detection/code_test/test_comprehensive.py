import pytest
import time
import os
from unittest.mock import patch, MagicMock
import tkinter as tk
from tkinter import ttk
import sys
import pandas as pd
import cv2
import numpy as np
from datetime import datetime

# --- CÀI ĐẶT ĐƯỜNG DẪN ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
code_dir = os.path.join(project_root, 'Detection', 'code')

if current_dir not in sys.path: sys.path.append(current_dir)
if project_root not in sys.path: sys.path.append(project_root)
if code_dir not in sys.path: sys.path.append(code_dir)

# --- IMPORT ULTRALYTICS (YOLO) ---
try:
    from ultralytics import YOLO
    print("[INFO] Đã import thành công Ultralytics YOLO.")
except ImportError:
    print("[WARNING] Không tìm thấy thư viện 'ultralytics'. Vui lòng cài đặt: pip install ultralytics")
    YOLO = None

# IMPORT CÁC CLASS GỐC
from profiler import SystemProfiler
from stability_profiler import StabilityProfiler

# --- IMPORT DATABASE MODULE (MySQL) ---
try:
    import database
    print("[INFO] Đã import thành công module 'database' (MySQL)")
except ImportError as e:
    print(f"[ERROR] Không thể import 'database.py'. Lỗi: {e}")
    database = None

# --- CẤU HÌNH TEST ---
TEST_USER = "a"
TEST_PASS = "123"
VIDEO_FPS = 30.0
OVERHEAD_MS = 10.0
CONF_THRESHOLD = 0.4 

class TestAdvancedPerformance:

    def simulate_delay(self, root, seconds=0.5):
        end_time = time.time() + seconds
        while time.time() < end_time:
            root.update()
            time.sleep(0.01)

    def _setup_login_widgets(self, login_frame):
        entries = []
        def find_entries_recursive(parent):
            for widget in parent.winfo_children():
                if isinstance(widget, (tk.Entry, ttk.Entry)):
                    entries.append(widget)
                elif isinstance(widget, (tk.Frame, ttk.Frame, tk.LabelFrame)):
                    find_entries_recursive(widget)
        find_entries_recursive(login_frame)
        
        if len(entries) >= 2:
            login_frame.username_entry = entries[0]
            login_frame.password_entry = entries[1]
        
        buttons = []
        def find_buttons_recursive(parent):
            for widget in parent.winfo_children():
                if isinstance(widget, (tk.Button, ttk.Button)):
                    buttons.append(widget)
                elif isinstance(widget, (tk.Frame, ttk.Frame, tk.LabelFrame)):
                    find_buttons_recursive(widget)
        find_buttons_recursive(login_frame)
        
        login_button = next((btn for btn in buttons if btn.cget('text') == 'Đăng nhập'), None)
        if login_button: login_frame.login_btn = login_button
        elif buttons: login_frame.login_btn = buttons[-1]
        else: 
            print("[WARN] Không tìm thấy nút đăng nhập, mock click.")

    # --- HÀM TÌM FILE MODEL ---
    def _find_model_path(self, filename='best.pt'):
        search_paths = [
            os.path.join(project_root, filename),
            os.path.join(project_root, 'weights', filename),
            os.path.join(code_dir, filename),
            os.path.join(current_dir, filename),
            r"D:\Student Behaviour Detection.v6i.yolov8\runs\detect\exp_yolov8s_first\weights\best.pt",
            r"D:\STUDY_YOLOV8 - Copy\STUDY_YOLOV8 - Copy - Copy\best.pt"
        ]
        for p in search_paths:
            if os.path.exists(p):
                return p
        return None

    # --- LOGIC TÍNH TOÁN IOU (DÙNG CHO TRACKING) ---
    def _calculate_iou(self, box1, box2):
        """Tính Intersection over Union giữa 2 box"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        union = area1 + area2 - intersection
        return intersection / union if union > 0 else 0

    # --- LOGIC GHÉP CẶP BEHAVIOR (BOX TRONG BOX) ---
    def _calculate_overlap_ratio(self, face_box, behavior_box):
        try:
            fx1, fy1, fx2, fy2 = face_box
            bx1, by1, bx2, by2 = behavior_box
            
            ix1 = max(fx1, bx1)
            iy1 = max(fy1, by1)
            ix2 = min(fx2, bx2)
            iy2 = min(fy2, by2)
            
            iw = max(0, ix2 - ix1)
            ih = max(0, iy2 - iy1)
            intersection = iw * ih
            face_area = (fx2 - fx1) * (fy2 - fy1)
            
            return intersection / face_area if face_area > 0 else 0.0
        except: return 0.0

    def _map_behaviors_to_faces(self, face_boxes, behavior_detections):
        mapping = {}
        if not face_boxes or not behavior_detections: return mapping

        for beh in behavior_detections:
            beh_box = beh['xy']
            best_face_idx = -1
            max_overlap = 0.0

            for idx, f_box in enumerate(face_boxes):
                ratio = self._calculate_overlap_ratio(f_box, beh_box)
                if ratio > max_overlap:
                    max_overlap = ratio
                    best_face_idx = idx
            
            if max_overlap > 0.3 and best_face_idx != -1:
                if best_face_idx not in mapping:
                    mapping[best_face_idx] = beh
                else:
                    curr_beh = mapping[best_face_idx]
                    if beh['conf'] > curr_beh['conf']:
                         mapping[best_face_idx] = beh
        return mapping

    # --- TEST FUNCTION CHÍNH ---
    def test_full_video_performance(self, app_context, real_video_path, setup_database):
        root, app = app_context
        
        print(f"\n--- BẮT ĐẦU TEST: MYSQL + REAL YOLO MODEL (best.pt) ---")

        # 1. LOAD BEHAVIOR MODEL
        behavior_model = None
        if YOLO:
            model_path = self._find_model_path('best.pt')
            if model_path:
                print(f" [Info] Loading Behavior Model from: {model_path}")
                try:
                    behavior_model = YOLO(model_path)
                    print(" [SUCCESS] Behavior Model loaded successfully!")
                except Exception as e:
                    print(f" [ERROR] Failed to load model: {e}")
            else:
                print(" [WARNING] Không tìm thấy file 'best.pt'. Sẽ không có Behavior Box.")
        else:
            print(" [ERROR] YOLO library not found.")

        # 2. CHECK MYSQL
        if database:
            try:
                all_students = database.get_all_students()
                print(f" [SUCCESS] Kết nối MySQL OK. Tổng số học sinh: {len(all_students)}")
            except Exception as e:
                print(f" [ERROR] Lỗi truy vấn MySQL: {e}")

        # CẤU HÌNH MÀU SẮC
        COLOR_BEHAVIOR_BOX = (0, 255, 0)   # Green
        COLOR_FACE_BOX = (0, 255, 0)       # Green
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_dir = os.path.join(project_root, 'debug_frames', f'RealModel_Run_{timestamp_str}')
        if not os.path.exists(debug_dir): os.makedirs(debug_dir)

        # [LOGIN & NAVIGATE]
        self.simulate_delay(root, 0.5)
        login_frame = app.current_frame
        self._setup_login_widgets(login_frame)
        
        if hasattr(login_frame, 'username_entry') and hasattr(login_frame, 'password_entry'):
            login_frame.username_entry.insert(0, TEST_USER)
            login_frame.password_entry.insert(0, TEST_PASS)
            if hasattr(login_frame, 'login_btn'):
                login_frame.login_btn.invoke()
            else:
                print("Skip click login btn")
        
        self.simulate_delay(root, 1.0)
        
        if hasattr(app.current_frame, 'on_navigate'):
            app.current_frame.on_navigate('camera')
        else:
             app.show_frame('CameraFrame')

        self.simulate_delay(root, 1.0)
        camera_screen = app.current_frame
        camera_screen.db_module = database 

        with patch('tkinter.messagebox.askyesno', return_value=True):
            with patch('tkinter.filedialog.askopenfilename', return_value=real_video_path):
                if hasattr(camera_screen, 'btn_select_video'): camera_screen.btn_select_video.invoke()
                else: camera_screen.select_video_file()
        self.simulate_delay(root, 1.0)

        # [SETUP PROFILER]
        profiler = SystemProfiler()
        stability_profiler = StabilityProfiler(video_fps=VIDEO_FPS)
        camera_screen.test_stats = {"detect_ms": 0, "logic_ms": 0, "behaviors": [], "face_labels": []}

        # Patch YOLO
        original_yolo = camera_screen.model.__call__
        def tracked_yolo(*args, **kwargs):
            t0 = time.time()
            res = original_yolo(*args, **kwargs)
            camera_screen.test_stats["detect_ms"] = (time.time() - t0) * 1000
            return res
        camera_screen.model.__call__ = tracked_yolo

        # --- [NEW] CẤU TRÚC TRACKER ---
        # active_tracks = { track_id: {'box': [x,y,x,y], 'lost_frames': 0} }
        active_tracks = {}
        next_track_id = 1
        IOU_MATCH_THRESH = 0.3 # Ngưỡng IoU để coi là cùng 1 người
        
        # Patch Analyzer
        original_analyze = camera_screen.analyzer.analyze_frame
        
        def tracked_analyze(frame, face_boxes=None):
            nonlocal next_track_id, active_tracks

            t0 = time.time()
            res = original_analyze(frame, face_boxes)
            camera_screen.test_stats["logic_ms"] = (time.time() - t0) * 1000
            
            debug_frame = frame.copy()
            frame_idx = getattr(camera_screen, 'frame_count', 0)
            
            labels_for_report = []
            beh_for_report = []

            # --- A. CHẠY MODEL HÀNH VI THẬT ---
            real_behavior_detections = []
            if behavior_model is not None:
                try:
                    results = behavior_model.predict(frame, conf=CONF_THRESHOLD, verbose=False)
                    if results and len(results) > 0:
                        res_obj = results[0]
                        boxes = res_obj.boxes
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                            conf = float(box.conf[0].cpu().numpy())
                            cls_id = int(box.cls[0].cpu().numpy())
                            label = res_obj.names[cls_id] if cls_id in res_obj.names else str(cls_id)
                            real_behavior_detections.append({
                                'label': label, 'conf': conf, 'xy': [x1, y1, x2, y2]
                            })
                except Exception as e:
                    print(f"Lỗi khi chạy behavior_model: {e}")
            
            # --- B. GHÉP CẶP ---
            face_to_beh_map = self._map_behaviors_to_faces(face_boxes, real_behavior_detections)

            # --- C. TRACKING LOGIC (TẠO ID MỚI KHI RỚT TRACKER) ---
            # Quan trọng: Thu thập boxes cùng với Original Index để map đúng khi hiển thị
            current_frame_boxes = [] # List of tuples: (original_idx, box_coords)
            
            if res.get('face_states'):
                for idx, fs in enumerate(res['face_states']):
                    box = fs.get('box')
                    
                    # Logic Fallback: Nếu không có box trong state, thử lấy từ input face_boxes
                    # Điều này phải KHỚP với logic vẽ bên dưới để đảm bảo tính nhất quán
                    if box is None and face_boxes is not None and idx < len(face_boxes):
                         box = face_boxes[idx]
                    
                    if box is not None:
                        current_frame_boxes.append((idx, list(map(int, box))))
            
            # Mapping từ Original Index (idx) -> Track ID
            box_idx_to_track_id = {}
            matched_track_ids = set()

            # Thuật toán Greedy Matching bằng IoU
            # Duyệt qua từng box mới, tìm track cũ khớp nhất
            for original_idx, new_box in current_frame_boxes:
                best_iou = 0
                best_tid = -1
                
                for tid, t_data in active_tracks.items():
                    if tid in matched_track_ids: continue # Track đã được match với box khác
                    iou = self._calculate_iou(new_box, t_data['box'])
                    if iou > best_iou:
                        best_iou = iou
                        best_tid = tid
                
                if best_iou > IOU_MATCH_THRESH:
                    # Match thành công: Giữ nguyên ID cũ
                    matched_track_ids.add(best_tid)
                    box_idx_to_track_id[original_idx] = best_tid
                    active_tracks[best_tid]['box'] = new_box
                    active_tracks[best_tid]['lost_frames'] = 0
                else:
                    # Không match: Tạo ID mới (Tăng STT)
                    box_idx_to_track_id[original_idx] = next_track_id
                    active_tracks[next_track_id] = {'box': new_box, 'lost_frames': 0}
                    matched_track_ids.add(next_track_id)
                    next_track_id += 1

            # Xóa các track không tìm thấy (Rớt tracker -> Xóa luôn để lần sau gặp tạo ID mới)
            tids_to_remove = [tid for tid in active_tracks if tid not in matched_track_ids]
            for tid in tids_to_remove:
                del active_tracks[tid]

            # --- D. VẼ VÀ HIỂN THỊ ---
            if res.get('face_states'):
                for idx, fs in enumerate(res['face_states']):
                    
                    # Lấy Track ID bằng index gốc (đã fix mapping)
                    track_id = box_idx_to_track_id.get(idx, "?")
                    
                    # Lấy Tên từ DB (nếu có)
                    recognized_id = fs.get('recognized_id')
                    short_name = "Unknown"
                    if recognized_id and str(recognized_id).lower() != "unknown":
                         try:
                            st_info = database.get_student_by_id(int(str(recognized_id)))
                            if st_info:
                                full_name = st_info.get('name', 'NoName')
                                short_name = full_name.split()[-1] if full_name else "NoName"
                            else:
                                short_name = f"DB:{recognized_id}"
                         except: pass

                    # Hiển thị: STT (Tracker) | Tên
                    display_text = f"STT:{track_id} | {short_name}"
                    labels_for_report.append(display_text)

                    # Vẽ Box
                    assigned_beh = face_to_beh_map.get(idx)
                    face_box = fs.get('box')
                    if face_box is None and face_boxes is not None: face_box = face_boxes[idx]

                    if face_box is not None:
                        fx1, fy1, fx2, fy2 = map(int, face_box)
                        
                        # Vẽ Hành vi
                        if assigned_beh:
                            beh_label = assigned_beh['label']
                            beh_conf = assigned_beh['conf']
                            bx1, by1, bx2, by2 = map(int, assigned_beh['xy'])
                            beh_text = f"{beh_label} {beh_conf:.2f}"
                            beh_for_report.append(beh_label)
                            
                            cv2.rectangle(debug_frame, (bx1, by1), (bx2, by2), COLOR_BEHAVIOR_BOX, 2)
                            (tw, th), _ = cv2.getTextSize(beh_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                            cv2.rectangle(debug_frame, (bx1, by1 - th - 10), (bx1 + tw + 10, by1), COLOR_BEHAVIOR_BOX, -1)
                            cv2.putText(debug_frame, beh_text, (bx1 + 5, by1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,0), 2)
                        else:
                            beh_for_report.append("normal")

                        # Vẽ Mặt & STT
                        cv2.rectangle(debug_frame, (fx1, fy1), (fx2, fy2), COLOR_FACE_BOX, 2)
                        cv2.putText(debug_frame, display_text, (fx1, fy1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            camera_screen.test_stats["behaviors"] = beh_for_report
            camera_screen.test_stats["face_labels"] = labels_for_report
            
            file_name = f"frame_{frame_idx:05d}.jpg"
            cv2.imwrite(os.path.join(debug_dir, file_name), debug_frame)
            return res
            
        camera_screen.analyzer.analyze_frame = tracked_analyze

        # CHẠY VIDEO TRONG 15 GIÂY
        start_time = time.time()
        prev_frame = 0
        print(" [Step 5/8] Đang thu thập dữ liệu (15 giây)...")
        while time.time() - start_time < 15: 
            self.simulate_delay(root, 0.01)
            if not camera_screen.running: break
            curr_frame = getattr(camera_screen, 'frame_count', 0)
            if curr_frame > prev_frame:
                profiler.capture_frame_stats(
                    frame_idx=curr_frame, 
                    detect_ms=camera_screen.test_stats["detect_ms"], 
                    analyze_ms=camera_screen.test_stats["logic_ms"], 
                    overhead_ms=OVERHEAD_MS, 
                    total_ms=camera_screen.test_stats["detect_ms"] + camera_screen.test_stats["logic_ms"] + OVERHEAD_MS, 
                    num_faces=len(camera_screen.test_stats["face_labels"]),
                    face_labels=camera_screen.test_stats["face_labels"],
                    behaviors_detected=camera_screen.test_stats["behaviors"],
                    video_time_seconds=curr_frame / VIDEO_FPS 
                )
                stability_profiler.update_frame_detection(curr_frame, camera_screen.test_stats["face_labels"])
                prev_frame = curr_frame

        print(" [Step 6/8] Dừng video và xuất báo cáo...")
        
        with patch('google.generativeai.GenerativeModel.generate_content') as mock_gen:
            mock_gen.return_value.text = "Mock Summary: Hoàn tất test với Model thật."
            camera_screen.stop()
        
        current_dir_test = os.path.dirname(os.path.abspath(__file__))
        reports_dir = os.path.abspath(os.path.join(current_dir_test, '..', '..', 'reports'))
        if not os.path.exists(reports_dir): os.makedirs(reports_dir)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        profiler.export_excel(os.path.join(reports_dir, f'Performance_Breakdown_Report_{timestamp}.xlsx'))
        stability_profiler.export_excel(os.path.join(reports_dir, f'Stability_Tracking_Report_{timestamp}.xlsx'), prev_frame)
        print(f"\n[KẾT QUẢ] Hoàn tất. Ảnh Debug tại: {debug_dir}")