import logging
import time
from datetime import datetime
from werkzeug.security import generate_password_hash

from database import get_connection
from scripts.data.users import DEFAULT_USERS

# Thiết lập Logger ghi tiến trình
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def seed_users():
    logger.info("Bắt đầu khởi tạo tài khoản mẫu cho bảng Users...")
    start_time = time.time()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        inserted_count = 0
        now = datetime.now()

        for u in DEFAULT_USERS:
            # Kiểm tra xem Username đã tồn tại chưa để tránh trùng lặp
            cursor.execute("SELECT COUNT(*) FROM Users WHERE Username = ?", (u["Username"],))
            if cursor.fetchone()[0] == 0:
                # Hash mật khẩu an toàn theo chuẩn hệ thống
                password_hash = generate_password_hash(u["Password"])

                cursor.execute("""
                    INSERT INTO Users (
                        Username, PasswordHash, FullName, Email, 
                        Role, IsActive, CreatedAt, LastLogin
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    u["Username"], password_hash, u["FullName"], u["Email"],
                    u["Role"], u["IsActive"], now, None
                ))
                inserted_count += 1
                logger.info(f"-> Thêm mới User: [{u['Role']}] {u['Username']} (Pass: {u['Password']})")
            else:
                logger.warning(f"-> Bỏ qua: Username '{u['Username']}' đã tồn tại.")

        conn.commit()
        end_time = time.time()
        execution_time = round(end_time - start_time, 2)

        logger.info(f"Thành công! Đã khởi tạo {inserted_count} tài khoản vào CSDL.")
        logger.info(f"Tổng thời gian thực thi: {execution_time} giây.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Đã có lỗi xảy ra trong quá trình seed Users: {str(e)}", exc_info=True)
    finally:
        conn.close()
        logger.info("Đã đóng kết nối CSDL an toàn.")


if __name__ == "__main__":
    seed_users()