import time

# =============================================================================
# 1. CẤU HÌNH HẰNG SỐ (GIỮ NGUYÊN THEO YÊU CẦU)
# =============================================================================

# --- Thời gian & Điểm ---
HAND_RAISE_COOLDOWN = 30.0       # Giây giữa 2 lần cộng điểm giơ tay
GOOD_FOCUS_TARGET_TIME = 300.0   # 5 phút tập trung -> +1 điểm
GOOD_FOCUS_POINTS = 1

PHONE_FIRST_PENALTY_TIME = 0.0   # Phạt ngay lập tức
PHONE_REPEAT_PENALTY_TIME = 120.0 # Phạt tiếp sau mỗi 2 phút
PHONE_POINTS = -1

HEAD_TURN_FIRST_PENALTY_TIME = 60.0 # Phạt sau 1 phút quay đầu
HEAD_TURN_REPEAT_PENALTY_TIME = 120.0 # Phạt tiếp sau mỗi 2 phút
HEAD_TURN_POINTS = -1

SLEEPY_EYES_TRIGGER_TIME = 60.0   # 1 phút nhắm mắt -> coi là ngủ
SLEEP_FIRST_PENALTY_TIME = 180.0  # Phạt sau 3 phút ngủ
SLEEP_REPEAT_PENALTY_TIME = 180.0 # Phạt tiếp sau mỗi 3 phút
SLEEP_POINTS = -1

# [QUAN TRỌNG - MỚI] Ngưỡng chặn lỗi lag/nhảy ID
# Nếu khoảng cách giữa 2 lần cập nhật > 1.5s, ta coi như mất dấu -> Không tính giờ đoạn này
MAX_FRAME_INTERVAL = 1.5 

# --- Danh sách hành vi (Giữ nguyên) ---
ALL_BEHAVIOR_NAMES = [
    'reading', 'writing', 'upright',
    'hand-raising',
    'Using_phone', 'phone', 
    'sleep', 'bend',
    'HEAD_LEFT', 'HEAD_RIGHT',
    'EYES_CLOSING', 
    'head_tilt_left', 'head_tilt_right',
    'EYES_OPEN', 'HEAD_STRAIGHT' # Trạng thái bình thường
]

GOOD_BEHAVIORS = {'reading', 'writing', 'upright'}

BAD_BEHAVIORS_FOR_RESET = {
    'Using_phone', 'phone', 'sleep', 'bend'
    # Đã xóa HEAD_LEFT, HEAD_RIGHT, EYES_CLOSING theo yêu cầu cũ
}


# =============================================================================
# 2. CLASS QUẢN LÝ ĐIỂM (LOGIC ĐẦY ĐỦ)
# =============================================================================

class FocusScoreManager:
    """
    Quản lý điểm tập trung, xử lý logic cộng/trừ điểm và timer hành vi.
    """
    def __init__(self, base_score=10):
        self.students = {}
        self.base_score = base_score
        
        self.ALL_BEHAVIORS = ALL_BEHAVIOR_NAMES
        self.GOOD_BEHAVIORS = GOOD_BEHAVIORS
        self.BAD_BEHAVIORS_FOR_RESET = BAD_BEHAVIORS_FOR_RESET

    def _get_student_state(self, student_id):
        """
        Khởi tạo hoặc lấy trạng thái của học sinh.
        """
        if student_id not in self.students:
            current_time = time.time() 
            new_state = {
                'score': self.base_score,
                'last_update_time': current_time, 
                
                # --- Timer cho Quy tắc CỘNG điểm ---
                'last_hand_raise_time': 0.0,
                'is_currently_raising_hand': False,
                'good_focus_cumulative_time': 0.0, # Timer cộng dồn 5 phút
                
                # --- Timer cho Quy tắc TRỪ điểm ---
                'phone_start_time': 0.0,
                'last_phone_penalty_time': 0.0,
                
                'head_turn_start_time': 0.0,
                'last_head_turn_penalty_time': 0.0,
                
                'sleepy_eyes_start_time': 0.0,   # Timer xác định có đang ngủ gật không
                'sleep_pose_start_time': 0.0,    # Timer tính thời gian phạt ngủ
                'last_sleep_penalty_time': 0.0,
                
                # Logs cho AI summary
                'session_logs': [] 
            }
            
            # Khởi tạo timer riêng cho từng hành vi trong danh sách
            for behavior_name in self.ALL_BEHAVIORS:
                new_state[f"{behavior_name}_timer_session"] = 0.0
                
            self.students[student_id] = new_state
            
        return self.students[student_id]

    def get_student_score(self, student_id):
        if student_id in self.students:
            return self.students[student_id]['score']
        return self.base_score

    def get_student_timers(self, student_id):
        """Lấy toàn bộ timer để hiển thị lên UI"""
        student_data = self.students.get(student_id)
        
        # Nếu chưa có dữ liệu, trả về dict 0
        if student_data is None:
            timers_dict = {key: 0.0 for key in self.ALL_BEHAVIORS}
            timers_dict['good_focus'] = 0.0
            return timers_dict

        timers_dict = {}
        for behavior_name in self.ALL_BEHAVIORS:
            timer_key = f"{behavior_name}_timer_session"
            timers_dict[behavior_name] = student_data.get(timer_key, 0.0)
            
        # Thêm timer good_focus riêng
        timers_dict['good_focus'] = student_data.get('good_focus_cumulative_time', 0.0)
        return timers_dict

    def get_student_full_logs(self, student_id):
        state = self._get_student_state(student_id)
        return state.get('session_logs', [])

    # =========================================================================
    # HÀM UPDATE CHÍNH (CORE LOGIC)
    # =========================================================================
    def update_student_score(self, student_id, behaviors_list, head_state, eye_state, current_time=None):
        
        if current_time is None:
            current_time = time.time()
            
        state = self._get_student_state(student_id)
        new_points = 0
        
        # Danh sách chứa (timestamp, message, point_change)
        log_tuples = []

        # --- BƯỚC 1: TÍNH TOÁN THỜI GIAN & XỬ LÝ LAG (FIX LỖI NHẢY ĐIỂM) ---
        delta_time = 0
        if state['last_update_time'] > 0:
            delta_time = current_time - state['last_update_time']
        
        # [QUAN TRỌNG] Nếu delta_time quá lớn (do mất dấu, lag, hoặc swap ID)
        # -> Reset delta_time về 0 để tránh cộng dồn thời gian sai lệch.
        if delta_time > MAX_FRAME_INTERVAL:
            delta_time = 0 
            
        state['last_update_time'] = current_time

        # --- BƯỚC 2: XÁC ĐỊNH CÁC TRẠNG THÁI HIỆN TẠI ---
        behavior_labels = set(behaviors_list)
        if head_state != 'NO_FACE': behavior_labels.add(head_state)
        if eye_state != 'NO_FACE': behavior_labels.add(eye_state)

        # Kiểm tra các cờ (Flags)
        is_good_focus = any(b in behavior_labels for b in self.GOOD_BEHAVIORS)
        is_phone = any(b in behavior_labels for b in ['Using_phone', 'phone'])
        is_head_turn = (head_state == 'HEAD_LEFT' or head_state == 'HEAD_RIGHT')
        
        # Xử lý Logic Ngủ (Gồm nhắm mắt lâu HOẶC cúi gục)
        is_sleepy_eyes_event = (eye_state == 'EYES_CLOSING')
        is_confirmed_sleepy = False
        
        if is_sleepy_eyes_event:
            if state['sleepy_eyes_start_time'] == 0:
                state['sleepy_eyes_start_time'] = current_time
            elif current_time - state['sleepy_eyes_start_time'] > SLEEPY_EYES_TRIGGER_TIME:
                is_confirmed_sleepy = True # Nhắm mắt quá 60s -> Xác nhận ngủ
        else:
            state['sleepy_eyes_start_time'] = 0 # Mở mắt -> Reset timer nhắm mắt
            
        is_bend_event = any(b in behavior_labels for b in ['sleep', 'bend'])
        is_sleep_pose = is_bend_event or is_confirmed_sleepy

        # Kiểm tra hành vi gây Reset chuỗi 5 phút
        is_bad_event_for_reset = bool(behavior_labels.intersection(self.BAD_BEHAVIORS_FOR_RESET))


        # --- BƯỚC 3: CẬP NHẬT TIMERS HÀNH VI (Thống kê) ---
        for behavior_name in self.ALL_BEHAVIORS:
            timer_key = f"{behavior_name}_timer_session"
            if behavior_name in behavior_labels:
                # Chỉ cộng khi hành vi đang diễn ra
                state[timer_key] = state.get(timer_key, 0.0) + delta_time

        # Logic Reset Timer đối lập (Mắt & Đầu)
        if eye_state == 'EYES_OPEN':
            state['EYES_CLOSING_timer_session'] = 0.0
        elif eye_state == 'EYES_CLOSING':
            state['EYES_OPEN_timer_session'] = 0.0
            
        if head_state == 'HEAD_STRAIGHT':
            state['HEAD_LEFT_timer_session'] = 0.0
            state['HEAD_RIGHT_timer_session'] = 0.0
        elif is_head_turn:
            state['HEAD_STRAIGHT_timer_session'] = 0.0
            if head_state == 'HEAD_LEFT': state['HEAD_RIGHT_timer_session'] = 0.0
            else: state['HEAD_LEFT_timer_session'] = 0.0


        # --- BƯỚC 4: XỬ LÝ QUY TẮC TẬP TRUNG 5 PHÚT (GOOD FOCUS) ---
        if is_bad_event_for_reset:
            # Nếu gặp hành vi xấu (điện thoại, ngủ) -> Reset chuỗi 5 phút
            if state['good_focus_cumulative_time'] > 0:
                log_tuples.append((current_time, "Mất chuỗi tập trung (do làm việc riêng)", 0))
            state['good_focus_cumulative_time'] = 0.0
            
        elif is_good_focus:
            # Nếu đang tập trung -> Cộng dồn thời gian
            state['good_focus_cumulative_time'] += delta_time
            
            if state['good_focus_cumulative_time'] >= GOOD_FOCUS_TARGET_TIME:
                new_points += GOOD_FOCUS_POINTS
                log_tuples.append((current_time, f"+{GOOD_FOCUS_POINTS} (Đủ 5p tập trung)", GOOD_FOCUS_POINTS))
                state['good_focus_cumulative_time'] = 0.0 # Reset sau khi cộng điểm để tính chuỗi mới


        # --- BƯỚC 5: XỬ LÝ CỘNG ĐIỂM GIƠ TAY ---
        if 'hand-raising' in behavior_labels:
            if not state['is_currently_raising_hand']: # Chỉ tính khi bắt đầu giơ
                if current_time - state['last_hand_raise_time'] > HAND_RAISE_COOLDOWN:
                    new_points += 1
                    log_tuples.append((current_time, "+1 (Phát biểu)", 1))
                    state['last_hand_raise_time'] = current_time
                state['is_currently_raising_hand'] = True
        else:
            # Nếu bỏ tay xuống, reset cờ (nhưng giữ cooldown timer)
            if state['is_currently_raising_hand']:
                state['is_currently_raising_hand'] = False
                state['last_hand_raise_time'] = current_time


        # --- BƯỚC 6: XỬ LÝ TRỪ ĐIỂM (PENALTIES) ---

        # 6.1. Dùng điện thoại
        if is_phone:
            if state['phone_start_time'] == 0:
                # Bắt đầu vi phạm -> Phạt ngay (First Penalty)
                state['phone_start_time'] = current_time
                state['last_phone_penalty_time'] = current_time
                new_points += PHONE_POINTS
                log_tuples.append((current_time, f"{PHONE_POINTS} (Dùng ĐT)", PHONE_POINTS))
            else:
                # Đang vi phạm -> Kiểm tra phạt lặp lại (Repeat Penalty)
                if (current_time - state['last_phone_penalty_time']) > PHONE_REPEAT_PENALTY_TIME:
                    new_points += PHONE_POINTS
                    log_tuples.append((current_time, f"{PHONE_POINTS} (Vẫn dùng ĐT 2p)", PHONE_POINTS))
                    state['last_phone_penalty_time'] = current_time
        else:
            # Ngừng vi phạm -> Reset timer
            state['phone_start_time'] = 0
            state['last_phone_penalty_time'] = 0

        # 6.2. Quay đầu (Head Turn)
        if is_head_turn:
            if state['head_turn_start_time'] == 0:
                state['head_turn_start_time'] = current_time
                state['last_head_turn_penalty_time'] = current_time
            else:
                duration = current_time - state['head_turn_start_time']
                time_since_last = current_time - state['last_head_turn_penalty_time']
                
                # Trường hợp 1: Vi phạm đủ lâu để phạt lần đầu
                if duration > HEAD_TURN_FIRST_PENALTY_TIME and \
                   state['last_head_turn_penalty_time'] == state['head_turn_start_time']:
                    new_points += HEAD_TURN_POINTS
                    log_tuples.append((current_time, f"{HEAD_TURN_POINTS} (Quay đầu >1p)", HEAD_TURN_POINTS))
                    state['last_head_turn_penalty_time'] = current_time
                
                # Trường hợp 2: Vi phạm tiếp diễn (Repeat Penalty)
                elif time_since_last > HEAD_TURN_REPEAT_PENALTY_TIME:
                    new_points += HEAD_TURN_POINTS
                    log_tuples.append((current_time, f"{HEAD_TURN_POINTS} (Vẫn quay đầu 2p)", HEAD_TURN_POINTS))
                    state['last_head_turn_penalty_time'] = current_time
        else:
            state['head_turn_start_time'] = 0
            state['last_head_turn_penalty_time'] = 0

        # 6.3. Ngủ (Sleep/Bend/Closed Eyes)
        if is_sleep_pose:
            if state['sleep_pose_start_time'] == 0:
                state['sleep_pose_start_time'] = current_time
                state['last_sleep_penalty_time'] = current_time
            else:
                duration = current_time - state['sleep_pose_start_time']
                time_since_last = current_time - state['last_sleep_penalty_time']

                # Phạt lần đầu
                if duration > SLEEP_FIRST_PENALTY_TIME and \
                   state['last_sleep_penalty_time'] == state['sleep_pose_start_time']:
                    new_points += SLEEP_POINTS
                    log_tuples.append((current_time, f"{SLEEP_POINTS} (Ngủ gật >3p)", SLEEP_POINTS))
                    state['last_sleep_penalty_time'] = current_time
                
                # Phạt tiếp diễn
                elif time_since_last > SLEEP_REPEAT_PENALTY_TIME:
                    new_points += SLEEP_POINTS
                    log_tuples.append((current_time, f"{SLEEP_POINTS} (Vẫn ngủ 3p)", SLEEP_POINTS))
                    state['last_sleep_penalty_time'] = current_time
        else:
            state['sleep_pose_start_time'] = 0
            state['last_sleep_penalty_time'] = 0


        # --- BƯỚC 7: CẬP NHẬT ĐIỂM VÀ TRẢ VỀ KẾT QUẢ ---
        if new_points != 0:
            state['score'] += new_points
            
        # Lưu log vào state (để AI summary dùng sau này)
        if log_tuples:
            state['session_logs'].extend(log_tuples)
            
        # Chỉ lấy nội dung log để hiển thị UI ngay lập tức
        log_messages = [msg for ts, msg, change in log_tuples]
        
        return new_points, log_messages