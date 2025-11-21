import cv2, math, time, datetime, os
import numpy as np
import mediapipe as mp

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None

class BieuCamAnalyzer:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=5, 
            refine_landmarks=True, 
            min_detection_confidence=0.5, 
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils

        # Landmark indices
        self.LEFT_EYE = [33, 160, 158, 133, 153, 144]
        self.RIGHT_EYE = [362, 385, 387, 263, 373, 380]

        # Head pose landmarks
        self.NOSE_TIP = 1
        self.LEFT_EYE_CORNER = 33
        self.RIGHT_EYE_CORNER = 263
        self.CHIN = 152
        self.FOREHEAD = 10 

        # Thresholds
        self.EAR_THRESH = 0.25
        self.HEAD_YAW_THRESH = 40 
        self.HEAD_ROLL_THRESH = 25 

        # Times
        self.DROWSY_TIME_THRESH = 5.0
        self.SLEEPING_TIME_THRESH = 30.0

        # States
        self.eye_closed_start_time = {} 
        self.drowsy_count = 0
        self.sleeping_count = 0
        self.yawn_count = 0
        self.session_start_time = time.time()
        self.alerts_log = []
        
        # Optional behavior model (YOLO)
        self.behavior_model = None
        self.behavior_names = []
        self.last_behaviors = []
        self.behavior_frame_skip = 2
        self._behavior_frame_count = 0
        
        # Load Model
        try:
            if YOLO is not None:
                cand = [
                    os.path.join(os.path.dirname(__file__), 'best.pt'),
                    os.path.join(os.path.dirname(__file__), os.pardir, 'best.pt'),
                    os.path.join(os.path.dirname(__file__), os.pardir, 'weights', 'best.pt'),
                    r"D:\Student Behaviour Detection.v6i.yolov8\runs\detect\exp_yolov8s_first\weights\best.pt",
                    r"D:\Student Behaviour Detection.v6i.yolov8\yolov8s.pt",
                ]
                for p in cand:
                    p = os.path.normpath(p)
                    if os.path.exists(p):
                        try:
                            self.behavior_model = YOLO(p)
                            try:
                                if isinstance(self.behavior_model.names, dict):
                                    self.behavior_names = self.behavior_model.names
                                else:
                                    self.behavior_names = {i: n for i, n in enumerate(self.behavior_model.names)}
                            except Exception:
                                self.behavior_names = {}
                            print(f"Loaded behavior model: {p}")
                            break
                        except Exception:
                            self.behavior_model = None
        except Exception:
            self.behavior_model = None

    @staticmethod
    def euclidean_dist(p1, p2): 
        try: return math.dist(p1, p2)
        except AttributeError: return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def eye_aspect_ratio(self, landmarks, eye_indices):
        p1, p2, p3, p4, p5, p6 = [landmarks[i] for i in eye_indices]
        return (self.euclidean_dist(p2, p6) + self.euclidean_dist(p3, p5)) / (2.0 * self.euclidean_dist(p1, p4) + 1e-6)

    def calculate_head_pose(self, landmarks):
        try:
            nose_tip = landmarks[self.NOSE_TIP]
            left_eye_c = landmarks[self.LEFT_EYE_CORNER]
            right_eye_c = landmarks[self.RIGHT_EYE_CORNER]
            l = self.euclidean_dist(left_eye_c, nose_tip)
            r = self.euclidean_dist(right_eye_c, nose_tip)
            yaw_angle = ((r - l) / (r + l + 1e-6)) * 90 
            
            p_left_eye = (landmarks[self.LEFT_EYE_CORNER][0], landmarks[self.LEFT_EYE_CORNER][1])
            p_right_eye = (landmarks[self.RIGHT_EYE_CORNER][0], landmarks[self.RIGHT_EYE_CORNER][1])
            delta_y = p_right_eye[1] - p_left_eye[1]
            delta_x = p_right_eye[0] - p_left_eye[0]
            if delta_x == 0: delta_x = 1e-6
            roll_angle = math.atan2(delta_y, delta_x) * (180 / math.pi)
            return {'yaw': yaw_angle, 'pitch': 0, 'roll': roll_angle}
        except Exception:
            return {'yaw': 0, 'pitch': 0, 'roll': 0}

    def analyze_head_orientation(self, head_pose, current_time):
        yaw = head_pose.get('yaw', 0)
        roll = head_pose.get('roll', 0)
        alerts, head_states = [], []
        if yaw > self.HEAD_YAW_THRESH:
            alerts.append(f"QUAY DAU PHAI ({yaw:.1f}°)")
            head_states.append("HEAD_RIGHT")
        elif yaw < -self.HEAD_YAW_THRESH:
            alerts.append(f"QUAY DAU TRAI ({abs(yaw):.1f}°)")
            head_states.append("HEAD_LEFT")
        if roll > self.HEAD_ROLL_THRESH:
            alerts.append(f"NGHIENG DAU TRAI ({roll:.1f}°)")
            head_states.append("HEAD_TILT_LEFT")
        elif roll < -self.HEAD_ROLL_THRESH:
            alerts.append(f"NGHIENG DAU PHAI ({abs(roll):.1f}°)")
            head_states.append("HEAD_TILT_RIGHT")
        if not head_states:
            head_states.append("HEAD_STRAIGHT")
        return {'alerts': alerts, 'states': head_states, 'angles': head_pose}

    def analyze_drowsiness(self, ear, t, face_id):
        if face_id not in self.eye_closed_start_time:
            self.eye_closed_start_time[face_id] = None
        if ear < self.EAR_THRESH:
            if self.eye_closed_start_time[face_id] is None: 
                self.eye_closed_start_time[face_id] = t
            d = t - self.eye_closed_start_time[face_id]
            if d >= self.SLEEPING_TIME_THRESH:
                self.sleeping_count += 1; self.log_alert("SLEEPING", f"NGU GUC! {d:.1f}s")
                return "SLEEPING", d
            elif d >= self.DROWSY_TIME_THRESH:
                self.drowsy_count += 1; self.log_alert("DROWSY", f"Mat nham {d:.1f}s")
                return "DROWSY", d
            else:
                return "EYES_CLOSING", d
        else:
            self.eye_closed_start_time[face_id] = None
            return "EYES_OPEN", 0

    def log_alert(self, alert_type, message):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.alerts_log.append({'time': ts, 'type': alert_type, 'message': message})

    def calculate_attention_score(self, eye_state, head_orientation=None):
        score = 100
        if eye_state[0] == "SLEEPING": score -= 120
        elif eye_state[0] == "DROWSY": score -= 80
        elif eye_state[0] == "EYES_CLOSING": score -= 40
        if head_orientation and head_orientation['states']:
            pen = 0
            for s in head_orientation['states']:
                if s in ["HEAD_LEFT", "HEAD_RIGHT", "HEAD_TILT_LEFT", "HEAD_TILT_RIGHT"]: 
                    pen += 30
            score -= min(pen, 50)
        return max(-100, min(100, score))

    @staticmethod
    def _get_box_center(box):
        try:
            x1, y1, x2, y2 = [int(v) for v in box]
            return ((x1 + x2) / 2, (y1 + y2) / 2)
        except Exception:
            return None

    # --- HÀM MỚI: TÍNH TỈ LỆ CHỒNG LẤN (Overlap Ratio) ---
    @staticmethod
    def _calculate_overlap_ratio(face_box, behavior_box):
        """
        Tính tỉ lệ diện tích khuôn mặt nằm TRONG box hành vi.
        Trả về: (Diện tích giao nhau / Diện tích khuôn mặt)
        """
        try:
            fx1, fy1, fx2, fy2 = face_box
            bx1, by1, bx2, by2 = behavior_box

            # Tọa độ vùng giao nhau
            ix1 = max(fx1, bx1)
            iy1 = max(fy1, by1)
            ix2 = min(fx2, bx2)
            iy2 = min(fy2, by2)

            iw = max(0, ix2 - ix1)
            ih = max(0, iy2 - iy1)
            intersection_area = iw * ih

            # Diện tích khuôn mặt (Face Area)
            face_area = (fx2 - fx1) * (fy2 - fy1)

            if face_area <= 0: return 0.0
            
            # Tỉ lệ chồng lấn trên diện tích mặt
            return intersection_area / face_area
        except Exception:
            return 0.0

    # =============================================================================
    # HÀM CHÍNH: ANALYZE FRAME (LOGIC ĐÃ SỬA ĐỔI MẠNH MẼ)
    # =============================================================================
    def analyze_frame(self, frame, face_boxes=None):
        t = time.time()
        h, w, _ = frame.shape

        out = {
            'face_detected': False,
            'alerts': ["KHONG PHAT HIEN KHUON MAT!"],
            'statistics': { 'sleeping_count': self.sleeping_count, 'drowsy_count': self.drowsy_count, 'yawn_count': 0, 'session_time': t - self.session_start_time },
            'face_states': [], 
            'behaviors': [] 
        }
        
        # 1. Detect behaviors (YOLO)
        try:
            whole_behaviors = self._detect_behaviors(frame)
        except Exception:
            whole_behaviors = []
        out['behaviors'] = whole_behaviors 

        if not face_boxes:
            return out

        # 2. Run FaceMesh
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        mesh_landmarks_list = []
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                landmarks = [(int(lm.x * w), int(lm.y * h)) for lm in face_landmarks.landmark]
                mesh_landmarks_list.append(landmarks)
        
        # ---------------------------------------------------------------------
        # 4. LOGIC GÁN HÀNH VI (SỬA ĐỔI: TÌM NGƯỜI PHÙ HỢP NHẤT CHO MỖI HÀNH VI)
        # ---------------------------------------------------------------------
        face_beh_map = {i: [] for i in range(len(face_boxes))}

        # Duyệt qua từng hành vi được phát hiện
        for beh in whole_behaviors:
            try:
                beh_box = beh.get('xy', None)
                if beh_box is None: continue
                beh_center = self._get_box_center(beh_box)
                if beh_center is None: continue

                best_face_idx = -1
                max_overlap_ratio = 0.0
                min_dist = float('inf')
                closest_face_idx_by_dist = -1

                # So sánh hành vi này với TẤT CẢ khuôn mặt để tìm người "chính chủ"
                for i, f_box in enumerate(face_boxes):
                    # 1. Tính tỉ lệ chồng lấn (Khuôn mặt nằm trong hành vi bao nhiêu %?)
                    ratio = self._calculate_overlap_ratio(f_box, beh_box)
                    
                    if ratio > max_overlap_ratio:
                        max_overlap_ratio = ratio
                        best_face_idx = i  # Ứng cử viên số 1 (theo diện tích)

                    # 2. Tính khoảng cách (Dự phòng)
                    f_center = self._get_box_center(f_box)
                    if f_center:
                        dist = self.euclidean_dist(beh_center, f_center)
                        if dist < min_dist:
                            min_dist = dist
                            closest_face_idx_by_dist = i

                # --- QUYẾT ĐỊNH GÁN ---
                # Ngưỡng 0.3: Nếu mặt nằm trong box hành vi > 30%, chắc chắn là của người đó.
                # Ưu tiên tuyệt đối cho Overlap Ratio.
                if max_overlap_ratio > 0.3: 
                    # Gán cho người có tỉ lệ chồng lấn cao nhất
                    if best_face_idx != -1:
                        face_beh_map[best_face_idx].append(beh)
                else:
                    # Nếu không ai nằm trong box hành vi (hiếm gặp, hoặc hành vi ở xa),
                    # mới dùng khoảng cách tâm.
                    if closest_face_idx_by_dist != -1:
                        face_beh_map[closest_face_idx_by_dist].append(beh)

            except Exception as e:
                print(f"Lỗi gán hành vi: {e}")
                continue

        # ---------------------------------------------------------------------
        # 5. TÍNH TOÁN TRẠNG THÁI FACE (Giữ nguyên)
        # ---------------------------------------------------------------------
        face_states = []
        face_centers = [self._get_box_center(fb) for fb in face_boxes]
        
        for i, fb in enumerate(face_boxes):
            face_center = face_centers[i]
            if face_center is None: continue

            best_landmarks = None
            min_lm_dist = float('inf')
            for landmarks in mesh_landmarks_list:
                try:
                    nose_tip = landmarks[self.NOSE_TIP]
                    dist = self.euclidean_dist(nose_tip, face_center)
                    if dist < min_lm_dist:
                        min_lm_dist = dist
                        best_landmarks = landmarks
                except Exception: continue
            
            if min_lm_dist > 100: best_landmarks = None

            fs = {'eye_state': ("NO_FACE", 0), 
                  'head_orientation': {'alerts': [], 'states': ["NO_FACE"], 'angles': {}}, 
                  'attention_score': 0, 'alerts': [], 'behaviors': []}
            
            face_id = f"face_{i}" 

            if best_landmarks:
                try:
                    left_ear = self.eye_aspect_ratio(best_landmarks, self.LEFT_EYE)
                    right_ear = self.eye_aspect_ratio(best_landmarks, self.RIGHT_EYE)
                    ear = (left_ear + right_ear) / 2.0
                    
                    head_pose = self.calculate_head_pose(best_landmarks) 
                    head_orientation = self.analyze_head_orientation(head_pose, t)
                    eye_state = self.analyze_drowsiness(ear, t, face_id)
                    attention_score = self.calculate_attention_score(eye_state, head_orientation)

                    fs.update({
                        'eye_state': eye_state, 
                        'head_orientation': head_orientation, 
                        'attention_score': attention_score,
                        'ear': ear, 
                    })
                    if eye_state[0] == "SLEEPING": fs['alerts'].append(f"🚨 NGU GUC!!! ({eye_state[1]:.1f}s)")
                    elif eye_state[0] == "DROWSY": fs['alerts'].append(f"BUON NGU! ({eye_state[1]:.1f}s)")
                    if head_orientation['alerts']:
                        fs['alerts'].extend(head_orientation['alerts'])
                except Exception as e:
                    print(f"Lỗi phân tích landmarks: {e}")
            
            fs['behaviors'] = face_beh_map.get(i, [])
            face_states.append(fs)
        
        out['face_states'] = face_states
        out['face_detected'] = len(face_states) > 0
        agg_alerts = [a for fs in face_states if fs for a in fs['alerts']]
        out['alerts'] = agg_alerts if agg_alerts else ["KHONG PHAT HIEN HINH THAI"]
        return out

    def draw_analysis_info(self, frame, result):
        stats = result.get('statistics', {})
        sy = frame.shape[0] - 70
        try:
            sess = stats.get('session_time', 0)
            cv2.putText(frame, f"Session: {sess/60:.1f}min", (10, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1); sy += 18
            cv2.putText(frame, f"Sleeping: {stats.get('sleeping_count',0)}", (10, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1); sy += 18
            cv2.putText(frame, f"Drowsy: {stats.get('drowsy_count',0)}", (10, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1); sy += 18
        except Exception: pass
        
        try:
            behs = result.get('behaviors', [])
            if behs:
                for det in behs:
                    try:
                        label = det.get('label', str(det))
                        conf = det.get('conf', 0.0)
                        x1, y1, x2, y2 = det.get('xy', (0,0,0,0)) 
                        if conf > 0.7: color = (0, 255, 0)
                        elif conf > 0.5: color = (0, 255, 255)
                        else: color = (0, 165, 255)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                        txt = f"{label} {conf:.2f}"
                        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                        lx, ly = x1, max(0, y1 - th - 8)
                        cv2.rectangle(frame, (lx, ly), (lx + tw + 8, ly + th + 8), color, -1)
                        cv2.putText(frame, txt, (lx + 4, ly + th + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2)
                    except Exception: continue
        except Exception: pass
        return frame

    def _detect_behaviors(self, frame):
        beh = []
        if self.behavior_model is None: return []
        try:
            self._behavior_frame_count = (self._behavior_frame_count + 1) % self.behavior_frame_skip
            if self._behavior_frame_count == 0:
                bres = self.behavior_model(frame, conf=0.35, verbose=False)[0]
                if bres and getattr(bres, 'boxes', None):
                    boxes = bres.boxes
                    names_list = []
                    for i, b in enumerate(list(boxes)):
                        try:
                            xy = b.xyxy[0].cpu().numpy()
                            x1, y1, x2, y2 = [int(v) for v in xy] 
                            conf = float(b.conf[0].cpu().numpy())
                            cls_idx = int(b.cls[0].cpu().numpy())
                            if cls_idx in self.behavior_names: label = self.behavior_names[cls_idx]
                            else: label = str(cls_idx)
                            names_list.append({'label': label, 'conf': conf, 'xy': (x1, y1, x2, y2)}) 
                        except Exception: continue 
                    beh = names_list
                    self.last_behaviors = beh
            else: beh = self.last_behaviors
        except Exception: beh = self.last_behaviors
        return beh

    def get_session_report(self):
        session_time = time.time() - self.session_start_time
        return {
            'session_duration_minutes': session_time/60,
            'total_sleeping_episodes': self.sleeping_count,
            'total_drowsy_episodes': self.drowsy_count,
            'alerts_log': self.alerts_log[-10:],
        }