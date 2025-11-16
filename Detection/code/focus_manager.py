import time

# --- Định nghĩa hằng số thời gian (tính bằng giây) ---
HAND_RAISE_COOLDOWN = 30.0  # 30 giây
GOOD_FOCUS_TARGET_TIME = 300.0 # 5 phút (300 giây)
GOOD_FOCUS_POINTS = 1

PHONE_FIRST_PENALTY_TIME = 0.0 # Xảy ra ngay lập tức
PHONE_REPEAT_PENALTY_TIME = 120.0 # 2 phút
PHONE_POINTS = -1

HEAD_TURN_FIRST_PENALTY_TIME = 60.0 # 1 phút
HEAD_TURN_REPEAT_PENALTY_TIME = 120.0 # 2 phút
HEAD_TURN_POINTS = -1

SLEEPY_EYES_TRIGGER_TIME = 60.0 # 1 phút nhắm mắt
SLEEP_FIRST_PENALTY_TIME = 180.0 # 3 phút ngủ
SLEEP_REPEAT_PENALTY_TIME = 180.0 # 3 phút ngủ tiếp
SLEEP_POINTS = -1

# (Yêu cầu 1: Giữ nguyên)
ALL_BEHAVIOR_NAMES = [
    'reading', 'writing', 'upright',
    'hand-raising',
    'Using_phone', 'phone', 
    'sleep', 'bend',
    'HEAD_LEFT', 'HEAD_RIGHT',
    'EYES_CLOSING', 
    'head_tilt_left', 'head_tilt_right',
    'EYES_OPEN', 'HEAD_STRAIGHT' # <<< Thêm các trạng thái "bình thường"
]

# (Giữ nguyên)
GOOD_BEHAVIORS = {'reading', 'writing', 'upright'}

# (Yêu cầu 2: Giữ nguyên)
BAD_BEHAVIORS_FOR_RESET = {
    'Using_phone', 'phone', 'sleep', 'bend'
    # <<< ĐÃ XÓA 'HEAD_LEFT', 'HEAD_RIGHT', 'EYES_CLOSING'
}


class FocusScoreManager:
    """
    Quản lý điểm tập trung VÀ THỜI GIAN HÀNH VI cho nhiều học sinh.
    """
    def __init__(self, base_score=10):
        self.students = {}
        self.base_score = base_score
        
        self.ALL_BEHAVIORS = ALL_BEHAVIOR_NAMES
        self.GOOD_BEHAVIORS = GOOD_BEHAVIORS
        self.BAD_BEHAVIORS_FOR_RESET = BAD_BEHAVIORS_FOR_RESET

    def _get_student_state(self, student_id):
        """
        Lấy hoặc tạo trạng thái mặc định cho một học sinh.
        """
        if student_id not in self.students:
            current_time = time.time() 
            new_state = {
                'score': self.base_score,
                'last_update_time': current_time, 
                
                # Trạng thái quy tắc CỘNG điểm
                'last_hand_raise_time': 0.0,
                'is_currently_raising_hand': False,
                'good_focus_cumulative_time': 0.0, # <<< Đây là timer 5 phút
                
                # Trạng thái quy tắc TRỪ điểm
                'phone_start_time': 0.0,
                'last_phone_penalty_time': 0.0,
                'head_turn_start_time': 0.0,
                'last_head_turn_penalty_time': 0.0,
                
                'sleepy_eyes_start_time': 0.0,
                'sleep_pose_start_time': 0.0, 
                'last_sleep_penalty_time': 0.0,
                
                # [THÊM] Nơi lưu trữ logs cho AI
                'session_logs': [] 
            }
            
            # Khởi tạo các timer HÀNH VI (KHÔNG bao gồm 3 hành vi tốt)
            for behavior_name in self.ALL_BEHAVIORS:
                # Suffix '_timer_session' để lưu thời gian (giây) CỦA PHIÊN HIỆN TẠI
                new_state[f"{behavior_name}_timer_session"] = 0.0
                
            self.students[student_id] = new_state
            
        return self.students[student_id]

    def get_student_score(self, student_id):
        if student_id in self.students:
            return self.students[student_id]['score']
        return self.base_score
        
    def get_behavior_totals(self, student_id):
        return self.get_student_timers(student_id) 
        
    def get_current_behavior_duration(self, student_id, current_time):
        return None, 0

    # (Yêu cầu 3: Giữ nguyên)
    def get_student_timers(self, student_id):
        """
        Lấy TẤT CẢ các timers (giây) cho một sinh viên.
        Bao gồm các timer hành vi (như EYES_CLOSING) VÀ 1 timer "good_focus".
        """
        student_data = self.students.get(student_id)
        
        if student_data is None:
            timers_dict = {key: 0.0 for key in self.ALL_BEHAVIORS}
            timers_dict['good_focus'] = 0.0 # Thêm timer 5 phút
            return timers_dict

        # Xây dựng dict trả về
        timers_dict = {}
        for behavior_name in self.ALL_BEHAVIORS:
            timer_key = f"{behavior_name}_timer_session"
            timers_dict[behavior_name] = student_data.get(timer_key, 0.0)
            
        # Thêm timer 5 phút (good_focus_cumulative_time) vào dict
        # camera.py sẽ tìm key 'good_focus' này
        timers_dict['good_focus'] = student_data.get('good_focus_cumulative_time', 0.0)
            
        return timers_dict

    # [THÊM] Hàm mới để cung cấp logs cho AI (yêu cầu của camera.py)
    def get_student_full_logs(self, student_id):
        """
        Trả về danh sách đầy đủ các log (tuples) cho session của học sinh.
        Được gọi bởi camera.py -> finalize_session -> ai_summarizer
        """
        state = self._get_student_state(student_id)
        return state.get('session_logs', [])

    def update_student_score(self, student_id, behaviors_list, head_state, eye_state, current_time=None):
        """
        Hàm chính để cập nhật điểm cho một học sinh dựa trên trạng thái hiện tại.
        """
        
        if current_time is None:
            current_time = time.time()
            
        state = self._get_student_state(student_id)
        new_points = 0
        
        # [SỬA] Đổi tên: log_messages (chỉ text) -> log_tuples (text + data)
        log_tuples = []

        # --- 0. Tính Delta Time (Thời gian từ lần cập nhật trước) ---
        delta_time = 0
        if state['last_update_time'] > 0:
            delta_time = current_time - state['last_update_time']
        state['last_update_time'] = current_time

        # --- 1. Định nghĩa các trạng thái (dựa trên list) ---
        behavior_labels = set(behaviors_list)
        # Thêm trạng thái từ BieuCamAnalyzer (trừ khi nó là 'NO_FACE')
        if head_state != 'NO_FACE':
            behavior_labels.add(head_state)
        if eye_state != 'NO_FACE':
            behavior_labels.add(eye_state)

        # (Phần logic kiểm tra trạng thái này đã đúng, giữ nguyên)
        is_good_focus = any(b in behavior_labels for b in self.GOOD_BEHAVIORS)
        is_phone = any(b in behavior_labels for b in ['Using_phone', 'phone'])
        is_head_turn = (head_state == 'HEAD_LEFT' or head_state == 'HEAD_RIGHT')
        
        is_sleepy_eyes_event = (eye_state == 'EYES_CLOSING') 
        is_eyes_open_event = (eye_state == 'EYES_OPEN') # [SỬA] Thêm
        is_head_straight_event = (head_state == 'HEAD_STRAIGHT') # [SỬA] Thêm
        
        is_confirmed_sleepy = False
        if is_sleepy_eyes_event:
            if state['sleepy_eyes_start_time'] == 0:
                state['sleepy_eyes_start_time'] = current_time
            if current_time - state['sleepy_eyes_start_time'] > SLEEPY_EYES_TRIGGER_TIME:
                is_confirmed_sleepy = True
        else:
            state['sleepy_eyes_start_time'] = 0 # Reset timer 1 phút
            
        is_bend_event = any(b in behavior_labels for b in ['sleep', 'bend'])
        is_sleep_pose = is_bend_event or is_confirmed_sleepy
        
        is_bad_event_for_reset = bool(behavior_labels.intersection(self.BAD_BEHAVIORS_FOR_RESET))

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!! [SỬA] LOGIC MỚI - CỘNG/RESET TIMER HÀNH VI           !!!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        # --- 2A. CỘNG DỒN TẤT CẢ TIMER HÀNH VI (Các timer riêng lẻ) ---
        for behavior_name in self.ALL_BEHAVIORS:
            timer_key = f"{behavior_name}_timer_session"
            
            if behavior_name in behavior_labels: 
                # Nếu hành vi ĐANG diễn ra -> Cộng dồn
                state[timer_key] = state.get(timer_key, 0.0) + delta_time
            # else:
            #   <ĐÃ XÓA logic reset tại đây>
            #   (Chúng ta muốn giữ tổng thời gian, không phải reset về 0)
        
        # [SỬA] Thêm logic reset lẫn nhau cho MẮT và ĐẦU
        if is_eyes_open_event:
            state['EYES_CLOSING_timer_session'] = 0.0
        elif is_sleepy_eyes_event:
            state['EYES_OPEN_timer_session'] = 0.0
            
        if is_head_straight_event:
            state['HEAD_LEFT_timer_session'] = 0.0
            state['HEAD_RIGHT_timer_session'] = 0.0
        elif is_head_turn:
            state['HEAD_STRAIGHT_timer_session'] = 0.0
            if head_state == 'HEAD_LEFT':
                state['HEAD_RIGHT_timer_session'] = 0.0
            else: # Must be HEAD_RIGHT
                state['HEAD_LEFT_timer_session'] = 0.0

        # --- 2B. XỬ LÝ RESET TIMER 5 PHÚT (Rule 2 Reset - Logic này đúng) ---
        if is_bad_event_for_reset:
            if state['good_focus_cumulative_time'] > 0:
                # [SỬA] Tạo log tuple
                log_tuples.append((current_time, "Reset time tập trung (do mất tập trung)", 0))
            state['good_focus_cumulative_time'] = 0.0
            
        # --- 2C. XỬ LÝ CỘNG DỒN 5 PHÚT (Rule 2 - Logic này đúng) ---
        elif is_good_focus: 
            state['good_focus_cumulative_time'] += delta_time
            
            if state['good_focus_cumulative_time'] >= GOOD_FOCUS_TARGET_TIME:
                new_points += GOOD_FOCUS_POINTS
                # [SỬA] Tạo log tuple
                log_tuples.append((current_time, f"+{GOOD_FOCUS_POINTS} (Tập trung 5p)", GOOD_FOCUS_POINTS))
                state['good_focus_cumulative_time'] = 0.0 # Reset timer 5 phút

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!! KẾT THÚC SỬA LOGIC CỘNG DỒN/RESET                  !!!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


        # --- 3. Xử lý quy tắc CỘNG điểm (Giơ tay - Rule 1) ---
        if 'hand-raising' in behavior_labels:
            if not state['is_currently_raising_hand']:
                if current_time - state['last_hand_raise_time'] > HAND_RAISE_COOLDOWN:
                    new_points += 1
                    # [SỬA] Tạo log tuple
                    log_tuples.append((current_time, f"+1 (Giơ tay)", 1))
                    state['last_hand_raise_time'] = current_time 
                state['is_currently_raising_hand'] = True
        else:
            if state['is_currently_raising_hand']:
                state['is_currently_raising_hand'] = False
                state['last_hand_raise_time'] = current_time 
            
        
        # --- 4. Xử lý quy tắc TRỪ điểm ---
        
        # Quy tắc 3: Dùng điện thoại
        if is_phone:
            if state['phone_start_time'] == 0:
                state['phone_start_time'] = current_time
                state['last_phone_penalty_time'] = current_time
                new_points += PHONE_POINTS
                # [SỬA] Tạo log tuple
                log_tuples.append((current_time, f"{PHONE_POINTS} (Sử dụng ĐT)", PHONE_POINTS))
            else:
                time_since_last_penalty = current_time - state['last_phone_penalty_time']
                if time_since_last_penalty > PHONE_REPEAT_PENALTY_TIME:
                    new_points += PHONE_POINTS
                    # [SỬA] Tạo log tuple
                    log_tuples.append((current_time, f"{PHONE_POINTS} (Tiếp tục dùng ĐT 2p)", PHONE_POINTS))
                    state['last_phone_penalty_time'] = current_time
        else:
            state['phone_start_time'] = 0
            state['last_phone_penalty_time'] = 0
            
        # Quy tắc 4: Quay đầu (HEAD_LEFT / HEAD_RIGHT)
        if is_head_turn:
            if state['head_turn_start_time'] == 0:
                state['head_turn_start_time'] = current_time
                state['last_head_turn_penalty_time'] = current_time 
            else:
                duration = current_time - state['head_turn_start_time']
                time_since_last_penalty = current_time - state['last_head_turn_penalty_time']

                if duration > HEAD_TURN_FIRST_PENALTY_TIME and \
                   state['last_head_turn_penalty_time'] == state['head_turn_start_time']:
                    new_points += HEAD_TURN_POINTS
                    # [SỬA] Tạo log tuple
                    log_tuples.append((current_time, f"{HEAD_TURN_POINTS} (Quay đầu > 1p)", HEAD_TURN_POINTS))
                    state['last_head_turn_penalty_time'] = current_time
                
                elif time_since_last_penalty > HEAD_TURN_REPEAT_PENALTY_TIME:
                    new_points += HEAD_TURN_POINTS
                    # [SỬA] Tạo log tuple
                    log_tuples.append((current_time, f"{HEAD_TURN_POINTS} (Tiếp tục quay đầu 2p)", HEAD_TURN_POINTS))
                    state['last_head_turn_penalty_time'] = current_time
        else:
            state['head_turn_start_time'] = 0
            state['last_head_turn_penalty_time'] = 0
            
        # Quy tắc 5: Ngủ (đã tính 'is_sleep_pose' ở trên)
        if is_sleep_pose:
            if state['sleep_pose_start_time'] == 0:
                state['sleep_pose_start_time'] = current_time
                state['last_sleep_penalty_time'] = current_time
            else:
                duration = current_time - state['sleep_pose_start_time']
                time_since_last_penalty = current_time - state['last_sleep_penalty_time']

                if duration > SLEEP_FIRST_PENALTY_TIME and \
                   state['last_sleep_penalty_time'] == state['sleep_pose_start_time']:
                    new_points += SLEEP_POINTS
                    # [SỬA] Tạo log tuple
                    log_tuples.append((current_time, f"{SLEEP_POINTS} (Ngủ > 3p)", SLEEP_POINTS))
                    state['last_sleep_penalty_time'] = current_time
                    
                elif time_since_last_penalty > SLEEP_REPEAT_PENALTY_TIME:
                    new_points += SLEEP_POINTS
                    # [SỬA] Tạo log tuple
                    log_tuples.append((current_time, f"{SLEEP_POINTS} (Tiếp tục ngủ 3p)", SLEEP_POINTS))
                    state['last_sleep_penalty_time'] = current_time
        else:
            state['sleep_pose_start_time'] = 0
            state['last_sleep_penalty_time'] = 0

        # --- 5. Cập nhật điểm và lưu log ---
        if new_points != 0:
            state['score'] += new_points
            
        # [THÊM] Lưu log tuples vào state để AI sử dụng
        if log_tuples:
            state['session_logs'].extend(log_tuples)
            
        # Trả về log messages (chỉ là chuỗi) cho GUI (nếu cần)
        log_messages = [msg for ts, msg, change in log_tuples]
        return new_points, log_messages