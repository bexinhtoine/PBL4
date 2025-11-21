import pandas as pd
from datetime import datetime
import time
import os

class StabilityProfiler:
    """
    Lớp dùng để theo dõi độ ổn định (Detection/Tracking Stability) của từng khuôn mặt
    theo thời gian video.
    """
    def __init__(self, video_fps=30.0):
        self.video_fps = video_fps
        # Thêm biến lưu thời gian của một khung hình (dùng để sửa lỗi duration = 0)
        self.frame_duration_s = 1.0 / video_fps
        # Lưu trữ trạng thái hiện tại của từng khuôn mặt đang được theo dõi
        # Key: face_id (ID CSDL/Tracker ID)
        # Value: {"start_frame": int, "last_frame": int, "is_active": bool, "last_lost_time_s": float}
        self.active_trackers = {} 
        # Danh sách các sự kiện hoàn chỉnh (Loss/End/Reappeared)
        self.finished_events = [] 

    def _frame_to_time(self, frame_id):
        """Chuyển ID Frame sang thời gian video (giây)."""
        return frame_id / self.video_fps

    def update_frame_detection(self, frame_id, detected_face_ids):
        """
        Cập nhật trạng thái theo dõi trong khung hình hiện tại.
        - detected_face_ids: List of unique IDs/Labels (ID CSDL/Tracker ID) in the current frame.
        """
        current_time_s = self._frame_to_time(frame_id)
        
        # 1. Xử lý các khuôn mặt hiện đang BỊ MẤT
        inactive_ids = list(self.active_trackers.keys())
        for face_id in inactive_ids:
            tracker = self.active_trackers[face_id]
            if tracker["is_active"] and face_id not in detected_face_ids:
                # Khuôn mặt vừa bị mất trong frame này: Ghi nhận chuỗi theo dõi VỪA KẾT THÚC
                
                # SỬA LỖI TÍNH DURATION: Khoảng thời gian từ lúc bắt đầu đến khung hình cuối cùng được thấy,
                # cộng thêm thời gian của một khung hình (vì last_frame là thời điểm bắt đầu của khung hình đó)
                
                # Tính tổng số khung hình được theo dõi liên tục (last_frame - start_frame + 1)
                frame_count = tracker["last_frame"] - tracker["start_frame"] + 1
                duration = frame_count * self.frame_duration_s

                self.finished_events.append({
                    "Face ID": face_id,
                    "TG Bắt Đầu Chuỗi (s)": round(self._frame_to_time(tracker["start_frame"]), 3),
                    "TG Kết Thúc Chuỗi (s)": round(self._frame_to_time(tracker["last_frame"]) + self.frame_duration_s, 3), # Thời điểm kết thúc chuỗi (cuối frame cuối)
                    "Tổng TG Theo Dõi Liên Tục (s)": round(duration, 3), 
                    "TG Bị Mất (s)": 0.0,
                    "Trạng Thái": "BOX_LOST (Mất Theo Dõi)",
                    "Thời Gian Sự Kiện (s)": round(current_time_s, 3)
                })
                tracker["is_active"] = False # Đánh dấu là đã mất
                # Lưu thời điểm bắt đầu bị mất (sau khi kết thúc chuỗi theo dõi trước đó)
                tracker["last_lost_time_s"] = self._frame_to_time(tracker["last_frame"]) + self.frame_duration_s
                
        # 2. Xử lý các khuôn mặt MỚI hoặc ĐƯỢC PHÁT HIỆN LẠI
        for face_id in detected_face_ids:
            if face_id not in self.active_trackers:
                # Khuôn mặt MỚI (Khởi tạo lần đầu)
                self.active_trackers[face_id] = {
                    "start_frame": frame_id,
                    "last_frame": frame_id,
                    "is_active": True,
                    "last_lost_time_s": 0.0
                }
            else:
                tracker = self.active_trackers[face_id]
                if not tracker["is_active"]:
                    # Khuôn mặt PHÁT HIỆN LẠI (Tái xuất hiện)
                    
                    # CẬP NHẬT: Tính thời gian bị mất (LOST DURATION)
                    time_lost = current_time_s - tracker["last_lost_time_s"]
                    
                    self.finished_events.append({
                        "Face ID": face_id,
                        # Ghi lại TG Bắt Đầu và Kết Thúc của chuỗi theo dõi ngay trước đó (để tham khảo)
                        "TG Bắt Đầu Chuỗi (s)": round(self._frame_to_time(tracker["start_frame"]), 3), 
                        "TG Kết Thúc Chuỗi (s)": round(tracker["last_lost_time_s"], 3),
                        "Tổng TG Theo Dõi Liên Tục (s)": 0.0, 
                        "TG Bị Mất (s)": round(time_lost, 3), # THỜI GIAN BỊ MẤT ĐÃ TÍNH
                        "Trạng Thái": "REAPPEARED (Tái Xuất Hiện)",
                        "Thời Gian Sự Kiện (s)": round(current_time_s, 3)
                    })
                    
                    # Bắt đầu chuỗi theo dõi liên tục mới
                    tracker["start_frame"] = frame_id 
                
                # Cập nhật frame cuối cùng và trạng thái
                tracker["last_frame"] = frame_id
                tracker["is_active"] = True

    def finalize_session(self, final_frame_id):
        """Kết thúc session và ghi lại các khuôn mặt còn đang hoạt động."""
        final_time_s = self._frame_to_time(final_frame_id)
        
        for face_id, tracker in self.active_trackers.items():
            if tracker["is_active"]:
                # Khuôn mặt còn hoạt động khi session kết thúc
                frame_count = tracker["last_frame"] - tracker["start_frame"] + 1
                duration = frame_count * self.frame_duration_s

                self.finished_events.append({
                    "Face ID": face_id,
                    "TG Bắt Đầu Chuỗi (s)": round(self._frame_to_time(tracker["start_frame"]), 3),
                    "TG Kết Thúc Chuỗi (s)": round(final_time_s, 3), 
                    "Tổng TG Theo Dõi Liên Tục (s)": round(duration, 3),
                    "TG Bị Mất (s)": 0.0,
                    "Trạng Thái": "SESSION_END (Kết Thúc Session)",
                    "Thời Gian Sự Kiện (s)": round(final_time_s, 3)
                })
                
        # Tạo DataFrame báo cáo sự kiện
        events_df = pd.DataFrame(self.finished_events)
        
        # --- TÓM TẮT TỔNG THỜI GIAN THEO DÕI LIÊN TỤC ---
        # Chỉ tính Tổng TG Theo Dõi Liên Tục (s) > 0 (tức là các chuỗi theo dõi thành công)
        summary = events_df.groupby('Face ID')['Tổng TG Theo Dõi Liên Tục (s)'].sum().reset_index()
        summary = summary.rename(columns={'Tổng TG Theo Dõi Liên Tục (s)': 'Tổng TG Phát Hiện Lũy Kế (s)'})
        
        return events_df, summary # Trả về cả Dataframe sự kiện và Dataframe tóm tắt

    def export_excel(self, file_path, final_frame_id):
        """Xuất báo cáo chi tiết và tóm tắt ra 2 sheet Excel."""
        events_df, summary_df = self.finalize_session(final_frame_id)
        
        if events_df.empty:
            print("LỖI: Không có dữ liệu độ ổn định để xuất.")
            return None

        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Sheet 1: Báo cáo Chi tiết Sự kiện
                events_df.to_excel(writer, sheet_name='ChiTiet_SuKien_Tracking', index=False)
                
                # Sheet 2: Tóm tắt tổng thời gian được theo dõi
                summary_df.to_excel(writer, sheet_name='TongKet_OnDinh', index=False)
                
            print(f"\n[Report] Đã xuất báo cáo độ ổn định tại: {file_path}")
            return events_df
        except Exception as e:
            print(f"Lỗi khi xuất file Excel độ ổn định: {e}")
            return None