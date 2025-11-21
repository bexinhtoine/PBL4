import time
import psutil
import pandas as pd
import os
from openpyxl.utils import get_column_letter
from datetime import timedelta 

class SystemProfiler:
    def __init__(self):
        self.data_records = []
        self.process = psutil.Process(os.getpid())
        
    def capture_frame_stats(self, frame_idx, detect_ms, analyze_ms, overhead_ms, total_ms, num_faces, face_labels, behaviors_detected, video_time_seconds=None):
        """
        Ghi lại thông số của 1 frame, bao gồm breakdown thời gian.
        
        Các thành phần thời gian (ms):
        - detect_ms: Thời gian Dò Khuôn Mặt (YOLO).
        - analyze_ms: Thời gian Phân Tích Logic (Xử lý hậu kỳ, phân tích hành vi).
        - overhead_ms: Thời gian Khác/Render. Đây là thời gian giả định/ước tính cho
                       các tác vụ không phải AI như Đọc/Giải mã frame, Vẽ hộp bao/nhãn 
                       lên frame, và Render (hiển thị) frame lên giao diện.
        - face_labels: Danh sách các ID/tên khuôn mặt (bao gồm tên thật từ database).
        """
        
        cpu_usage = self.process.cpu_percent()
        ram_usage = self.process.memory_info().rss / (1024 * 1024) # MB
        
        # --- CHUYỂN ĐỔI THỜI GIAN GHI TỪ SECONDS SANG HH:MM:SS ---
        if video_time_seconds is not None:
            total_seconds = int(video_time_seconds)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            time_str = time.strftime("%H:%M:%S")

        # --- CẤU TRÚC CỘT CHI TIẾT ---
        record = {
            "ID Frame": frame_idx,
            "Tổng Thời Gian Xử Lý (ms)": round(total_ms, 2),
            "FPS Tức Thời": round(1000 / total_ms, 1) if total_ms > 0 else 0,
            "TG Dò Khuôn Mặt (ms)": round(detect_ms, 2), # Giữ lại để tính Tổng Hợp
            "TG Phân Tích Logic (ms)": round(analyze_ms, 2),
            "TG Khác/Render (ms)": round(overhead_ms, 2),
            "Số Khuôn Mặt": num_faces,
            "Danh Sách Khuôn Mặt": str(face_labels),
            "Hành Vi Phát Hiện": str(behaviors_detected), 
            "CPU Sử Dụng (%)": cpu_usage,
            "RAM Sử Dụng (MB)": round(ram_usage, 2),
            "Thời Gian Ghi": time_str
        }
        self.data_records.append(record)

    def export_excel(self, report_path):
        """Xuất báo cáo ra file Excel và định dạng đẹp."""
        if not self.data_records:
            print("Không có dữ liệu để xuất báo cáo.")
            return None

        df = pd.DataFrame(self.data_records)
        
        # --- DỮ LIỆU BÁO CÁO TỔNG HỢP ---
        summary_data = {
            "Chỉ Số Đo Lường": [
                "Tổng Số Frame Đã Xử Lý",
                "FPS Trung Bình",
                "FPS Thấp Nhất (Lag nhất)",
                "Độ Trễ Trung Bình (ms)",
                "Độ Trễ Cao Nhất (ms)",
                "TG Dò Khuôn Mặt TB (ms)", # Giữ lại ở TỔNG HỢP
                "TG Phân Tích Logic TB (ms)",
                "TG Khác/Render TB (ms)",    
                "CPU Sử Dụng Trung Bình (%)",
                "RAM Sử Dụng Cao Nhất (MB)",
                "Tổng Số Khuôn Mặt Phát Hiện"
            ],
            "Giá Trị": [
                len(df),
                round(df["FPS Tức Thời"].mean(), 2) if not df.empty else 0,
                round(df["FPS Tức Thời"].min(), 2) if not df.empty else 0,
                round(df["Tổng Thời Gian Xử Lý (ms)"].mean(), 2) if not df.empty else 0,
                round(df["Tổng Thời Gian Xử Lý (ms)"].max(), 2) if not df.empty else 0,
                round(df["TG Dò Khuôn Mặt (ms)"].mean(), 2) if not df.empty else 0,
                round(df["TG Phân Tích Logic (ms)"].mean(), 2) if not df.empty else 0,
                round(df["TG Khác/Render (ms)"].mean(), 2) if not df.empty else 0,
                round(df["CPU Sử Dụng (%)"].mean(), 2) if not df.empty else 0,
                round(df["RAM Sử Dụng (MB)"].max(), 2) if not df.empty else 0,
                df["Số Khuôn Mặt"].sum() if not df.empty else 0
            ]
        }
        df_summary = pd.DataFrame(summary_data)

        # CỘT CẦN BÁO CÁO CHI TIẾT (ĐÃ LOẠI BỎ TG DÒ KHUÔN MẶT theo yêu cầu)
        columns_to_export = [
            "ID Frame",
            "Tổng Thời Gian Xử Lý (ms)",
            "FPS Tức Thời",
            "TG Phân Tích Logic (ms)",
            "TG Khác/Render (ms)",
            "Số Khuôn Mặt",
            "Danh Sách Khuôn Mặt",
            "Hành Vi Phát Hiện",
            "CPU Sử Dụng (%)",
            "RAM Sử Dụng (MB)",
            "Thời Gian Ghi"
        ]

        # Ghi ra Excel và chỉnh độ rộng cột
        with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
            # Sheet Tóm tắt
            df_summary.to_excel(writer, sheet_name='Tong_Hop', index=False)
            self._adjust_column_width(writer.sheets['Tong_Hop'])
            
            # Sheet Chi tiết
            df[columns_to_export].to_excel(writer, sheet_name='Chi_Tiet_Frame', index=False)
            self._adjust_column_width(writer.sheets['Chi_Tiet_Frame'])
            
        print(f"\n[Report] Đã xuất báo cáo Excel tiếng Việt tại: {report_path}")
        return df

    def _adjust_column_width(self, worksheet):
        """Hàm tự động giãn cách ô Excel"""
        for column in worksheet.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 4)
            worksheet.column_dimensions[column_letter].width = adjusted_width