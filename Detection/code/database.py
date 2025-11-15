import mysql.connector
from mysql.connector import Error, IntegrityError
import os
from datetime import datetime

# ===================================================================
# 1. CẤU HÌNH KẾT NỐI MYSQL
# !! QUAN TRỌNG: Hãy thay đổi các giá trị này !!
# ===================================================================
DB_CONFIG = {
    'host': 'localhost',        # Hoặc IP của server MySQL
    'user': 'root',  # Tên user MySQL của bạn
    'password': '', # Mật khẩu của user
    'database': 'giamsatatt' # Tên database bạn đã tạo
}
# ===================================================================

def get_db_connection():
    """Tạo kết nối CSDL MySQL."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Lỗi kết nối MySQL: {e}")
        return None

def init_db():
    """
    Hàm này tạo tất cả các bảng CSDL (nếu chúng chưa tồn tại)
    dựa trên Django models của bạn.
    """
    print(f"Kiểm tra/Khởi tạo CSDL MySQL: {DB_CONFIG['database']}...")
    conn = get_db_connection()
    if conn is None:
        print("Không thể kết nối CSDL. Dừng khởi tạo.")
        return
        
    cursor = conn.cursor()

    try:
        # === 1. Bảng Student (từ model Student) ===
        # student_id là AutoField (tự tăng)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS student (
            student_id  INT PRIMARY KEY AUTO_INCREMENT,
            name        VARCHAR(100) NOT NULL,
            class_name  VARCHAR(100) NOT NULL,
            gender      ENUM('Nam', 'Nữ', 'Khác') NOT NULL,
            birthday    DATE NOT NULL, -- Dùng kiểu DATE
            avartar_url VARCHAR(255),
            created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_student_class (class_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # === 2. Bảng Account (từ model Account) ===
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS account (
            id          INT PRIMARY KEY AUTO_INCREMENT,
            username    VARCHAR(100) UNIQUE NOT NULL,
            password    VARCHAR(255) NOT NULL, -- Nhớ hash mật khẩu
            created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # === 3. Bảng Seasion (từ model Seasion) ===
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS seasion (
            seasion_id  INT PRIMARY KEY AUTO_INCREMENT,
            class_name  VARCHAR(100) NOT NULL,
            start_time  DATETIME NOT NULL,
            end_time    DATETIME NOT NULL,
            created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_seasion_class (class_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # === 4. Bảng FaceEmbedding (từ model FaceEmbedding) ===
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS face_embedding (
            face_id         INT PRIMARY KEY AUTO_INCREMENT,
            student_id      INT UNIQUE NOT NULL, -- Liên kết 1-1
            embedding_name  VARCHAR(255) NOT NULL,
            face_image      VARCHAR(255), -- Lưu đường dẫn file ảnh
            registered_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES student (student_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # === 5. Bảng FocusRecord (từ model FocusRecord) ===
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS focus_record (
            record_id   BIGINT PRIMARY KEY AUTO_INCREMENT,
            seasion_id  INT NOT NULL,
            student_id  INT NOT NULL,
            appear      BOOLEAN NOT NULL DEFAULT TRUE, -- 1 (True) 0 (False)
            focus_point INT NOT NULL DEFAULT 0,
            rate        ENUM('Cao độ', 'Tốt', 'Trung bình', 'Thấp') NOT NULL,
            note        TEXT,
            ts_created  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (seasion_id) REFERENCES seasion (seasion_id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES student (student_id) ON DELETE CASCADE,
            INDEX idx_focus_seasion_student (seasion_id, student_id),
            INDEX idx_focus_rate (rate)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        conn.commit()
        print("Kiểm tra/Khởi tạo CSDL hoàn tất.")
        
    except Error as e:
        print(f"Lỗi khi khởi tạo bảng: {e}")
        conn.rollback() # Hoàn tác nếu có lỗi
    finally:
        cursor.close()
        conn.close()


# ===================================================================
# CÁC HÀM CRUD (TKINTER SẼ GỌI CÁC HÀM NÀY)
# (Đã cập nhật để dùng MySQL Connector)
# ===================================================================

# --- Các hàm CRUD cho Student ---

def get_all_students():
    """Lấy tất cả học sinh (thay thế Student.objects.all())."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return []
        # dictionary=True để trả về kết quả dạng dict
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM student ORDER BY class_name, name")
        students = cursor.fetchall()
        return students
    except Error as e:
        print(f"Lỗi khi lấy danh sách học sinh: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_student_by_id(student_db_id):
    """Lấy một học sinh bằng ID (thay thế Student.objects.get(pk=...))."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return None
        cursor = conn.cursor(dictionary=True)
        # Dùng %s làm placeholder
        cursor.execute("SELECT * FROM student WHERE student_id = %s", (student_db_id,))
        student = cursor.fetchone()
        return student # Trả về dict hoặc None
    except Error as e:
        print(f"Lỗi khi lấy học sinh (ID: {student_db_id}): {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def add_student(name, class_name, gender, birthday_str, avartar_url=None):
    """
    Thêm học sinh mới và TRẢ VỀ ID MỚI ĐƯỢC TẠO.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return None, "Lỗi kết nối CSDL"
        
        # Kiểm tra định dạng ngày sinh
        try:
            # Chuyển đổi chuỗi YYYY-MM-DD sang đối tượng date
            datetime.strptime(birthday_str, '%Y-%m-%d').date()
        except ValueError:
            return None, "Định dạng ngày sinh không hợp lệ. Phải là YYYY-MM-DD."

        cursor = conn.cursor()
        sql = """INSERT INTO student (name, class_name, gender, birthday, avartar_url) 
                 VALUES (%s, %s, %s, %s, %s)"""
        params = (name, class_name, gender, birthday_str, avartar_url)
        cursor.execute(sql, params)
        
        conn.commit()
        new_id = cursor.lastrowid # Lấy ID tự tăng vừa được tạo
        
        # Trả về ID và thông báo thành công
        return new_id, f"Thêm thành công (ID: {new_id})" 
        
    except IntegrityError as e:
        if conn: conn.rollback()
        return None, f"Lỗi trùng lặp dữ liệu: {e}"
    except Error as e:
        if conn: conn.rollback()
        return None, f"Lỗi MySQL: {e}"
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def update_student_avatar(student_db_id, avartar_url):
    """Cập nhật đường dẫn ảnh đại diện cho một học sinh đã có."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return False, "Lỗi kết nối CSDL"
        cursor = conn.cursor()
        sql = """UPDATE student SET avartar_url = %s
                 WHERE student_id = %s"""
        params = (avartar_url, student_db_id)
        cursor.execute(sql, params)
        
        conn.commit()
        return True, "Cập nhật avatar thành công"
    except Error as e:
        if conn: conn.rollback()
        return False, f"Lỗi MySQL khi cập nhật avatar: {e}"
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def delete_student(student_db_id):
    """Xóa học sinh (thay thế student.delete())."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return False, "Lỗi kết nối CSDL"
        cursor = conn.cursor()
        cursor.execute("DELETE FROM student WHERE student_id = %s", (student_db_id,))
        conn.commit()
        return True, "Xóa thành công"
    except Error as e:
        if conn: conn.rollback()
        return False, f"Lỗi MySQL: {e}"
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# --- Các hàm CRUD cho Account ---

def verify_account(username, plain_password):
    """Kiểm tra đăng nhập (thay thế cho logic login_view)."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return False, "Lỗi kết nối CSDL"
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM account WHERE username = %s", (username,))
        account = cursor.fetchone()
        
        if not account:
            return False, "Tài khoản không tồn tại"
            
        # TODO: Thay thế bằng check_password (ví dụ: dùng bcrypt)
        # import bcrypt
        # hashed_pw = account['password'].encode('utf-8')
        # if bcrypt.checkpw(plain_password.encode('utf-8'), hashed_pw):
        
        # Logic TẠM THỜI (giống code cũ của bạn)
        if account['password'] == plain_password:
            return True, account # Trả về dict thông tin tài khoản
        else:
            return False, "Sai mật khẩu"
            
    except Error as e:
        print(f"Lỗi khi xác thực tài khoản: {e}")
        return False, "Lỗi máy chủ CSDL"
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# --- Các hàm CRUD cho FaceEmbedding ---

def link_face_embedding(student_db_id, embedding_name, face_image_path):
    """Đăng ký khuôn mặt (thay thế logic trong register_face)."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return False, "Lỗi kết nối CSDL"
        cursor = conn.cursor()
        
        # Lấy thời gian hiện tại để gửi vào CSDL
        now = datetime.now() 
        
        # --- SỬA CÂU SQL VÀ PARAMS ---
        # Thêm 'updated_at' vào cả phần INSERT
        sql = """INSERT INTO face_embedding (student_id, embedding_name, face_image, registered_at, updated_at) 
                 VALUES (%s, %s, %s, %s, %s)
                 ON DUPLICATE KEY UPDATE 
                 embedding_name = VALUES(embedding_name), 
                 face_image = VALUES(face_image),
                 updated_at = %s;""" # Cập nhật 'updated_at' khi 'ON DUPLICATE'
        
        # Sửa 'params' để có 6 giá trị (5 cho INSERT, 1 cho UPDATE)
        params = (student_db_id, embedding_name, face_image_path, now, now, now) 
        cursor.execute(sql, params)
        
        conn.commit()
        return True, "Liên kết khuôn mặt thành công"
        
    except IntegrityError as e:
        conn.rollback()
        return False, f"Lỗi khóa ngoại: Student ID {student_db_id} không tồn tại. {e}"
    except Error as e:
        if conn: conn.rollback()
        return False, f"Lỗi MySQL: {e}"
    finally:
        if cursor: cursor.close()
        if conn: conn.close()