# behavior_analyzer.py
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
        self.face_mesh = self.mp_face_mesh.FaceMesh(refine_landmarks=True)
        self.mp_draw = mp.solutions.drawing_utils

        # Landmark indices
        self.LEFT_EYE = [33, 160, 158, 133, 153, 144]
        self.RIGHT_EYE = [362, 385, 387, 263, 373, 380]
        self.MOUTH = [13, 14, 78, 308]

        # Head pose landmarks
        self.NOSE_TIP = 1; self.NOSE_BRIDGE = 6
        self.LEFT_EYE_CORNER = 33; self.RIGHT_EYE_CORNER = 263
        self.LEFT_MOUTH_CORNER = 61; self.RIGHT_MOUTH_CORNER = 291
        self.CHIN = 152; self.FOREHEAD = 10

        # Thresholds
        self.EAR_THRESH = 0.25
        self.MAR_THRESH_TALKING = 0.4
        self.MAR_THRESH_YAWN = 0.8
        self.HEAD_YAW_THRESH = 30
        self.HEAD_PITCH_THRESH = 20
        self.HEAD_ROLL_THRESH = 25

        # Times
        self.DROWSY_TIME_THRESH = 5.0
        self.SLEEPING_TIME_THRESH = 30.0
        self.TALKING_TIME_THRESH = 2.0
        self.TALKING_GRACE_PERIOD = 3.0
        self.YAWN_TIME_THRESH = 1.0

        # States
        self.eye_closed_start_time = None
        self.mouth_open_start_time = None
        self.talking_activity_start = None
        self.talking_confirmed = False
        self.last_talking_detected_time = None
        self.mouth_toggles = 0
        self.last_mouth_state = False
        self.mouth_activity_window = []
        self.mar_history = []

        self.drowsy_count = 0
        self.sleeping_count = 0
        self.yawn_count = 0
        self.talking_duration = 0
        self.session_start_time = time.time()
        self.state_history = []
        self.alerts_log = []
        # Optional behavior model (YOLO custom model 'best.pt')
        self.behavior_model = None
        self.behavior_names = []
        self.last_behaviors = []
        # throttle behavior inference to every N frames to reduce load
        self.behavior_frame_skip = 2
        self._behavior_frame_count = 0
        # try loading 'best.pt' from several common locations (code/, parent, weights/)
        try:
            if YOLO is not None:
                cand = [
                    os.path.join(os.path.dirname(__file__), 'best.pt'),
                    os.path.join(os.path.dirname(__file__), os.pardir, 'best.pt'),
                    os.path.join(os.path.dirname(__file__), os.pardir, 'weights', 'best.pt'),
                    os.path.join(os.path.dirname(__file__), os.pardir, 'weights', 'last.pt'),
                    # additional common/absolute paths (user-provided)
                    r"D:\Student Behaviour Detection.v6i.yolov8\runs\detect\exp_yolov8s_first\weights\best.pt",
                    r"D:\Student Behaviour Detection.v6i.yolov8\runs\detect\exp_yolov8s_first\weights\last.pt",
                    r"D:\Student Behaviour Detection.v6i.yolov8\yolov8s.pt",
                ]
                for p in cand:
                    p = os.path.normpath(p)
                    if os.path.exists(p):
                        try:
                            self.behavior_model = YOLO(p)
                            try:
                                # model.names may be dict or list
                                if isinstance(self.behavior_model.names, dict):
                                    # keep dict mapping for convenience
                                    self.behavior_names = self.behavior_model.names
                                else:
                                    # convert list to dict-like mapping
                                    self.behavior_names = {i: n for i, n in enumerate(self.behavior_model.names)}
                            except Exception:
                                self.behavior_names = {}
                            break
                        except Exception:
                            self.behavior_model = None
        except Exception:
            self.behavior_model = None

    @staticmethod
    def euclidean_dist(p1, p2): return math.dist(p1, p2)

    def eye_aspect_ratio(self, landmarks, eye_indices):
        p1, p2, p3, p4, p5, p6 = [landmarks[i] for i in eye_indices]
        return (self.euclidean_dist(p2, p6) + self.euclidean_dist(p3, p5)) / (2.0 * self.euclidean_dist(p1, p4))

    def mouth_aspect_ratio(self, landmarks, mouth_indices):
        top, bottom, left, right = [landmarks[i] for i in mouth_indices]
        return self.euclidean_dist(top, bottom) / self.euclidean_dist(left, right)

    
    def calculate_3d_head_pose(self, landmarks):
        nose_tip = landmarks[self.NOSE_TIP]
        left_eye = landmarks[self.LEFT_EYE_CORNER]; right_eye = landmarks[self.RIGHT_EYE_CORNER]
        chin = landmarks[self.CHIN]; forehead = landmarks[self.FOREHEAD]

        # yaw
        l = self.euclidean_dist(landmarks[self.LEFT_EYE_CORNER], nose_tip)
        r = self.euclidean_dist(landmarks[self.RIGHT_EYE_CORNER], nose_tip)
        yaw_angle = ((r - l) / (l + r)) * 45 if (l + r) > 0 else 0

        # pitch
        nf = abs(nose_tip[1] - forehead[1]); nc = abs(chin[1] - nose_tip[1])
        pitch_angle = ((nc - nf) / (nf + nc)) * 30 if (nf + nc) > 0 else 0

        # roll
        eye_line_angle = math.atan2(right_eye[1] - left_eye[1], right_eye[0] - left_eye[0])
        roll_angle = math.degrees(eye_line_angle)
        if roll_angle > 90: roll_angle -= 180
        elif roll_angle < -90: roll_angle += 180

        return {'yaw': yaw_angle, 'pitch': pitch_angle, 'roll': roll_angle}

    def analyze_head_orientation(self, head_pose, current_time):
        yaw, pitch, roll = head_pose['yaw'], head_pose['pitch'], head_pose['roll']
        alerts, head_states = [], []

        if abs(yaw) > self.HEAD_YAW_THRESH:
            alerts.append(f"QUAY DAU {'PHAI' if yaw>0 else 'TRAI'} ({abs(yaw):.1f}°)")
            head_states.append("TURNING_RIGHT" if yaw>0 else "TURNING_LEFT")
        if abs(pitch) > self.HEAD_PITCH_THRESH:
            alerts.append(f"{'NGANG' if pitch>0 else 'CUI'} DAU ({abs(pitch):.1f}°)")
            head_states.append("LOOKING_UP" if pitch>0 else "LOOKING_DOWN")
        if abs(roll) > self.HEAD_ROLL_THRESH:
            alerts.append(f"NGHIENG DAU {'PHAI' if roll>0 else 'TRAI'} ({abs(roll):.1f}°)")
            head_states.append("TILTING_RIGHT" if roll>0 else "TILTING_LEFT")

        if not alerts: head_states.append("HEAD_STRAIGHT")
        return {'alerts': alerts, 'states': head_states, 'angles': head_pose}

    def analyze_drowsiness(self, ear, t):
        if ear < self.EAR_THRESH:
            if self.eye_closed_start_time is None: self.eye_closed_start_time = t
            d = t - self.eye_closed_start_time
            if d >= self.SLEEPING_TIME_THRESH:
                self.sleeping_count += 1; self.log_alert("SLEEPING", f"NGU GUC! {d:.1f}s")
                return "SLEEPING", d
            elif d >= self.DROWSY_TIME_THRESH:
                self.drowsy_count += 1; self.log_alert("DROWSY", f"Mat nham {d:.1f}s")
                return "DROWSY", d
            else:
                return "EYES_CLOSING", d
        else:
            self.eye_closed_start_time = None
            return "EYES_OPEN", 0

    def analyze_mouth_activity(self, mar, t):
        is_open = mar > self.MAR_THRESH_TALKING
        is_wide = mar > self.MAR_THRESH_YAWN

        self.mar_history.append((t, mar))
        self.mar_history = [(tt, m) for tt, m in self.mar_history if t - tt <= 3.0]

        if len(self.mar_history) >= 10:
            recent = [m for tt, m in self.mar_history if t - tt <= 2.0]
            if len(recent) >= 5:
                mean = sum(recent) / len(recent)
                var = sum((m - mean)**2 for m in recent) / len(recent)
                if var > 0.002:
                    if self.talking_activity_start is None: self.talking_activity_start = t
                else:
                    self.talking_activity_start = None

        if is_open != self.last_mouth_state:
            self.mouth_activity_window.append(t)
            self.last_mouth_state = is_open
        self.mouth_activity_window = [tt for tt in self.mouth_activity_window if t - tt <= 3.0]
        recent_toggles = len([tt for tt in self.mouth_activity_window if t - tt <= 2.0])

        if is_wide:
            if self.mouth_open_start_time is None: self.mouth_open_start_time = t
            d = t - self.mouth_open_start_time
            if d >= self.YAWN_TIME_THRESH:
                self.yawn_count += 1; self.log_alert("YAWN", f"Ngap {d:.1f}s")
                return "YAWNING", d
            else:
                return "MOUTH_OPENING_WIDE", d
        else:
            self.mouth_open_start_time = None

        if self.talking_activity_start and t - self.talking_activity_start >= self.TALKING_TIME_THRESH:
            return "TALKING", t - self.talking_activity_start
        elif self.talking_activity_start:
            return "TALKING_DETECTED", t - self.talking_activity_start
        elif recent_toggles >= 3:
            if self.talking_activity_start is None: self.talking_activity_start = t
            return "TALKING_DETECTED", 0
        else:
            return ("MOUTH_OPEN" if is_open else "MOUTH_CLOSED"), 0

    def log_alert(self, alert_type, message):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.alerts_log.append({'time': ts, 'type': alert_type, 'message': message})

    def calculate_attention_score(self, eye_state, mouth_state, head_orientation=None):
        score = 100
        if eye_state[0] == "SLEEPING": score -= 120
        elif eye_state[0] == "DROWSY": score -= 80
        elif eye_state[0] == "EYES_CLOSING": score -= 40

        if mouth_state[0] == "TALKING": score -= 50
        elif mouth_state[0] == "TALKING_DETECTED": score -= 25
        elif mouth_state[0] == "YAWNING": score -= 40

        if head_orientation and head_orientation['states']:
            pen = 0
            for s in head_orientation['states']:
                if s in ["TURNING_LEFT", "TURNING_RIGHT"]: pen += 30
                elif s in ["LOOKING_UP", "LOOKING_DOWN"]: pen += 25
                elif s in ["TILTING_LEFT", "TILTING_RIGHT"]: pen += 15
            score -= min(pen, 50)
        return max(-100, min(100, score))

    def analyze_frame(self, frame, face_boxes=None):
        """Analyze a frame.

        If `face_boxes` (list of (x1,y1,x2,y2)) is provided, run per-face landmark analysis
        (head orientation, drowsiness via EAR, mouth activity via MAR) for each crop and
        optionally run the behavior model (12-class) on each crop. The 12-class outputs
        remain unchanged; per-face landmark-derived states are returned in `out['face_states']`.
        If `face_boxes` is None the prior whole-frame face-mesh + whole-frame behavior detection
        is executed (backward compatible).
        """
        t = time.time()
        h, w, _ = frame.shape

        out = {
            'face_detected': False, 'ear': 0, 'mar': 0,
            'eye_state': ("NO_FACE", 0),
            'mouth_state': ("NO_FACE", 0),
            'head_pose': {'yaw':0,'pitch':0,'roll':0},
            'head_orientation': {'alerts': [], 'states': [], 'angles': {}},
            'attention_score': 0,
            'alerts': ["KHONG PHAT HIEN KHUON MAT!"],
            'statistics': {
                'sleeping_count': self.sleeping_count,
                'drowsy_count': self.drowsy_count,
                'yawn_count': self.yawn_count,
                'session_time': t - self.session_start_time,
                'mouth_toggles': len(self.mouth_activity_window)
            }
        }

        # If face_boxes were provided, analyze each face crop individually
        if face_boxes:
            behs = []
            face_states = []
            for fb in face_boxes:
                try:
                    x1, y1, x2, y2 = [int(v) for v in fb]
                except Exception:
                    face_states.append(None); behs.append(None); continue
                # clamp
                x1 = max(0, min(w - 1, x1)); y1 = max(0, min(h - 1, y1))
                x2 = max(0, min(w, x2)); y2 = max(0, min(h, y2))
                if x2 <= x1 or y2 <= y1:
                    face_states.append(None); behs.append(None); continue
                crop = frame[y1:y2, x1:x2]

                # mediapipe on crop for landmark-derived states
                try:
                    rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                    rres = self.face_mesh.process(rgb_crop)
                except Exception:
                    rres = None

                fs = {'eye_state': ("NO_FACE", 0), 'mouth_state': ("NO_FACE", 0),
                      'head_orientation': {'alerts': [], 'states': [], 'angles': {}},
                      'attention_score': 0}

                if rres and getattr(rres, 'multi_face_landmarks', None):
                    fl = rres.multi_face_landmarks[0]
                    ch, cw = crop.shape[0], crop.shape[1]
                    landmarks = [(int(lm.x * cw) + x1, int(lm.y * ch) + y1) for lm in fl.landmark]
                    try:
                        left_ear = self.eye_aspect_ratio(landmarks, self.LEFT_EYE)
                        right_ear = self.eye_aspect_ratio(landmarks, self.RIGHT_EYE)
                        ear = (left_ear + right_ear) / 2.0
                    except Exception:
                        ear = 0
                    try:
                        mar = self.mouth_aspect_ratio(landmarks, self.MOUTH)
                    except Exception:
                        mar = 0
                    head_pose = self.calculate_3d_head_pose(landmarks)
                    head_orientation = self.analyze_head_orientation(head_pose, t)
                    eye_state = self.analyze_drowsiness(ear, t)
                    mouth_state = self.analyze_mouth_activity(mar, t)
                    attention_score = self.calculate_attention_score(eye_state, mouth_state, head_orientation)

                    fs = {'eye_state': eye_state, 'mouth_state': mouth_state,
                          'head_orientation': head_orientation, 'attention_score': attention_score,
                          'ear': ear, 'mar': mar}

                face_states.append(fs)

                # do NOT run the 12-class behavior model on the cropped face.
                # We will run the behavior detector once on the whole frame later
                # and map detections to faces (allowing multiple labels per face).
                behs.append(None)

            # run behavior detector once on whole frame and map detections to faces
            try:
                whole_behaviors = self._detect_behaviors(frame)
            except Exception:
                whole_behaviors = []

            out['behaviors'] = whole_behaviors
            out['face_states'] = face_states
            agg_alerts = []

            # Map whole-frame behavior detections to faces.
            # Policy:
            # 1) If any face center lies inside the detection box, assign the det to
            #    the nearest such face (by center distance).
            # 2) Else, if the face with maximum IoU has IoU >= IOU_THRESH, assign to it.
            # 3) Else, fallback to nearest face by center distance.
            # This guarantees each detection is assigned to exactly one face so that
            # the total number of assigned behaviors equals the number of detection boxes.
            IOU_THRESH = 0.20
            face_beh_map = {i: [] for i in range(len(face_states))}
            try:
                for det in whole_behaviors:
                    bx = det.get('xy', None)
                    if bx is None:
                        continue
                    bx_cx = (bx[0] + bx[2]) / 2.0; bx_cy = (bx[1] + bx[3]) / 2.0
                    assigned = None
                    # 1) find faces whose center is inside det box
                    inside_candidates = []
                    for i, fb in enumerate(face_boxes):
                        try:
                            fx_cx = (fb[0] + fb[2]) / 2.0; fx_cy = (fb[1] + fb[3]) / 2.0
                            if bx[0] <= fx_cx <= bx[2] and bx[1] <= fx_cy <= bx[3]:
                                d2 = (fx_cx - bx_cx)**2 + (fx_cy - bx_cy)**2
                                inside_candidates.append((i, d2))
                        except Exception:
                            continue
                    if inside_candidates:
                        inside_candidates.sort(key=lambda x: x[1])
                        assigned = inside_candidates[0][0]
                    else:
                        # 2) pick face with max IoU if it's large enough
                        best_i = None; best_iou = 0.0
                        for i, fb in enumerate(face_boxes):
                            try:
                                iou = self._bbox_iou(bx, fb)
                            except Exception:
                                iou = 0.0
                            if iou > best_iou:
                                best_iou = iou; best_i = i
                        if best_i is not None and best_iou >= IOU_THRESH:
                            assigned = best_i
                        else:
                            # 3) fallback to nearest face by center distance
                            best_dist = None; best_idx = None
                            for i, fb in enumerate(face_boxes):
                                try:
                                    fx_cx = (fb[0] + fb[2]) / 2.0; fx_cy = (fb[1] + fb[3]) / 2.0
                                    d2 = (fx_cx - bx_cx)**2 + (fx_cy - bx_cy)**2
                                    if best_dist is None or d2 < best_dist:
                                        best_dist = d2; best_idx = i
                                except Exception:
                                    continue
                            assigned = best_idx

                    if assigned is not None and 0 <= assigned < len(face_states):
                        face_beh_map[assigned].append(det)
                        det['face_index'] = assigned
                    else:
                        det['face_index'] = None
            except Exception:
                pass

            # attach behaviors and alerts to each face state
            for i, fs in enumerate(face_states):
                if not fs:
                    continue
                assigned_beh = face_beh_map.get(i, [])
                fs['behaviors'] = assigned_beh
                # primary behavior (highest confidence) if any
                try:
                    fs['behavior'] = max(assigned_beh, key=lambda x: x.get('conf', 0.0)) if assigned_beh else None
                except Exception:
                    fs['behavior'] = assigned_beh[0] if assigned_beh else None

                # build alerts specific to this face
                alerts_for_face = []
                es = fs.get('eye_state', ("", 0)); ms = fs.get('mouth_state', ("", 0))
                if es[0] == "SLEEPING": alerts_for_face.append(f"🚨 NGU GUC!!! ({es[1]:.1f}s)")
                elif es[0] == "DROWSY": alerts_for_face.append(f"BUON NGU! ({es[1]:.1f}s)")
                elif es[0] == "EYES_CLOSING": alerts_for_face.append(f"Mat dang nham... ({es[1]:.1f}s)")
                if ms[0] == "TALKING": alerts_for_face.append(f"NOI CHUYEN ({ms[1]:.1f}s)")
                elif ms[0] == "TALKING_DETECTED": alerts_for_face.append("Dang phat hien noi chuyen...")
                elif ms[0] == "YAWNING": alerts_for_face.append(f"NGAP ({ms[1]:.1f}s)")
                if fs.get('head_orientation') and fs['head_orientation'].get('alerts'):
                    alerts_for_face.extend(fs['head_orientation']['alerts'])

                fs['alerts'] = alerts_for_face
                if alerts_for_face:
                    for a in alerts_for_face:
                        agg_alerts.append(f"Face {i+1}: {a}")

            out['alerts'] = agg_alerts if agg_alerts else ["KHONG PHAT HIEN HINH THAI"]
            out['face_detected'] = any(1 for f in face_states if f and f.get('eye_state', ("NO_FACE",0))[0] != "NO_FACE")
            return out

        # fallback: no face_boxes provided -> use face-mesh based analysis + whole-frame behavior detection
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                landmarks = [(int(lm.x * w), int(lm.y * h)) for lm in face_landmarks.landmark]
                left_ear = self.eye_aspect_ratio(landmarks, self.LEFT_EYE)
                right_ear = self.eye_aspect_ratio(landmarks, self.RIGHT_EYE)
                ear = (left_ear + right_ear) / 2.0
                mar = self.mouth_aspect_ratio(landmarks, self.MOUTH)
                head_pose = self.calculate_3d_head_pose(landmarks)
                head_orientation = self.analyze_head_orientation(head_pose, t)
                eye_state = self.analyze_drowsiness(ear, t)
                mouth_state = self.analyze_mouth_activity(mar, t)
                attention_score = self.calculate_attention_score(eye_state, mouth_state, head_orientation)

                out.update({
                    'face_detected': True, 'ear': ear, 'mar': mar,
                    'eye_state': eye_state, 'mouth_state': mouth_state,
                    'head_pose': head_pose, 'head_orientation': head_orientation,
                    'attention_score': attention_score
                })

                alerts = []
                if ear < self.EAR_THRESH: alerts.append("Buon ngu (Mat nham)")
                if mar > 0.7: alerts.append("Ngap/Noi chuyen")
                if head_pose and abs(head_pose.get('yaw', 0)) > 30: alerts.append("Dau nghieng qua muc")

                if   eye_state[0] == "SLEEPING": alerts.append(f"🚨 NGU GUC!!! ({eye_state[1]:.1f}s)")
                elif eye_state[0] == "DROWSY":   alerts.append(f"BUON NGU! ({eye_state[1]:.1f}s)")
                elif eye_state[0] == "EYES_CLOSING": alerts.append(f"Mat dang nham... ({eye_state[1]:.1f}s)")
                if   mouth_state[0] == "TALKING": alerts.append(f"NOI CHUYEN ({mouth_state[1]:.1f}s)")
                elif mouth_state[0] == "TALKING_DETECTED": alerts.append("Dang phat hien noi chuyen...")
                elif mouth_state[0] == "YAWNING": alerts.append(f"NGAP ({mouth_state[1]:.1f}s)")

                if head_orientation['alerts']: alerts.extend(head_orientation['alerts'])
                out['alerts'] = alerts

                self.state_history.append({'timestamp': t, 'ear': ear, 'mar': mar, 'attention_score': attention_score})
                if len(self.state_history) > 300: self.state_history.pop(0)
                break  # lấy mặt đầu tiên
        # run optional behavior detector on the whole frame (if available)
        out['behaviors'] = self._detect_behaviors(frame)
        return out

    def draw_analysis_info(self, frame, result):
        # Minimal in-frame overlay: only show attention score (small) and statistics to avoid clutter.
        score = result.get('attention_score', 0)
        if score == 0:
            color = (128,128,128)
        elif score >= 50:
            color = (0,255,0)
        elif score >= 0:
            color = (0,255,255)
        elif score >= -50:
            color = (0,165,255)
        else:
            color = (0,0,255)
        cv2.putText(frame, f"Attention: {score}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # show compact statistics at bottom-left
        stats = result.get('statistics', {})
        sy = frame.shape[0] - 70
        try:
            sess = stats.get('session_time', 0)
            cv2.putText(frame, f"Session: {sess/60:.1f}min", (10, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1); sy += 18
            cv2.putText(frame, f"Sleeping: {stats.get('sleeping_count',0)}", (10, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1); sy += 18
            cv2.putText(frame, f"Drowsy: {stats.get('drowsy_count',0)}", (10, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1); sy += 18
            cv2.putText(frame, f"Yawns: {stats.get('yawn_count',0)}", (10, sy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)
        except Exception:
            pass
        # draw detected behaviors if any (draw boxes + labels)
        try:
            behs = result.get('behaviors', [])
            if behs:
                for det in behs:
                    try:
                        label = det.get('label', str(det))
                        conf = det.get('conf', 0.0)
                        x1, y1, x2, y2 = det.get('xy', (0,0,0,0))
                        # color by confidence
                        if conf > 0.7:
                            color = (0, 255, 0)
                        elif conf > 0.5:
                            color = (0, 255, 255)
                        else:
                            color = (0, 165, 255)
                        # draw rectangle (thicker)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                        # draw filled label background
                        txt = f"{label} {conf:.2f}"
                        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                        # ensure label box is inside frame
                        lx, ly = x1, max(0, y1 - th - 8)
                        cv2.rectangle(frame, (lx, ly), (lx + tw + 8, ly + th + 8), color, -1)
                        cv2.putText(frame, txt, (lx + 4, ly + th + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2)
                    except Exception:
                        continue
        except Exception:
            pass
        return frame

    def _bbox_iou(self, a, b):
        """Compute IoU between two boxes a and b. Boxes are (x1,y1,x2,y2)."""
        try:
            ax1, ay1, ax2, ay2 = a
            bx1, by1, bx2, by2 = b
            ix1 = max(ax1, bx1); iy1 = max(ay1, by1)
            ix2 = min(ax2, bx2); iy2 = min(ay2, by2)
            iw = max(0, ix2 - ix1); ih = max(0, iy2 - iy1)
            inter = iw * ih
            area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
            area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
            union = area_a + area_b - inter
            if union <= 0: return 0.0
            return float(inter) / float(union)
        except Exception:
            return 0.0

    def _detect_behaviors(self, frame):
        """Run the optional 12-class behavior model on the whole frame.
        Returns a list of detections [{'label', 'conf', 'xy'}]. Throttled by behavior_frame_skip.
        """
        beh = []
        if self.behavior_model is None:
            return []
        try:
            self._behavior_frame_count = (self._behavior_frame_count + 1) % self.behavior_frame_skip
            if self._behavior_frame_count == 0:
                bres = self.behavior_model(frame, conf=0.35, verbose=False)[0]
                if bres and getattr(bres, 'boxes', None):
                    boxes = bres.boxes
                    try:
                        iterable_boxes = list(boxes)
                    except Exception:
                        iterable_boxes = []
                    names = []
                    for i, b in enumerate(iterable_boxes):
                        try:
                            xy = b.xyxy[0].cpu().numpy() if hasattr(b.xyxy, 'cpu') or hasattr(b.xyxy, 'numpy') else b.xyxy[0]
                            x1, y1, x2, y2 = [int(v) for v in xy]
                        except Exception:
                            try:
                                xy_all = getattr(boxes, 'xyxy', None)
                                if xy_all is not None:
                                    arr = xy_all[i].cpu().numpy()
                                    x1, y1, x2, y2 = [int(v) for v in arr]
                                else:
                                    x1 = y1 = x2 = y2 = 0
                            except Exception:
                                x1 = y1 = x2 = y2 = 0
                        try:
                            conf = float(b.conf[0].cpu().numpy()) if hasattr(b.conf, 'cpu') or hasattr(b.conf, 'numpy') else float(b.conf[0])
                        except Exception:
                            try:
                                conf = float(getattr(boxes, 'conf', [])[i]) if getattr(boxes, 'conf', None) is not None else 0.0
                            except Exception:
                                conf = 0.0
                        try:
                            cls_idx = int(b.cls[0].cpu().numpy()) if hasattr(b.cls, 'cpu') or hasattr(b.cls, 'numpy') else int(b.cls[0])
                        except Exception:
                            try:
                                cls_idx = int(getattr(boxes, 'cls', [])[i])
                            except Exception:
                                cls_idx = None
                        if cls_idx is not None and cls_idx in self.behavior_names:
                            label = self.behavior_names[cls_idx]
                        else:
                            label = str(cls_idx)
                        names.append({'label': label, 'conf': conf, 'xy': (x1, y1, x2, y2)})
                    beh = names
                    self.last_behaviors = beh
            else:
                beh = self.last_behaviors
        except Exception:
            beh = self.last_behaviors
        return beh

    def get_session_report(self):
        session_time = time.time() - self.session_start_time
        return {
            'session_duration_minutes': session_time/60,
            'total_sleeping_episodes': self.sleeping_count,
            'total_drowsy_episodes': self.drowsy_count,
            'total_yawns': self.yawn_count,
            'alerts_log': self.alerts_log[-10:],
            'average_attention': np.mean([s['attention_score'] for s in self.state_history]) if self.state_history else 0
        }
