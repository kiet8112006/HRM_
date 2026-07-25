import logging
import random
import time
from datetime import datetime, timedelta

from database import get_connection
from scripts.data.audit_logs import MODULES, ACTIONS, IP_ADDRESSES, USER_AGENTS

# Thiết lập Logger ghi tiến trình
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def get_active_users(cursor):
    """Lấy danh sách User hợp lệ từ CSDL."""
    cursor.execute("SELECT UserID, Username, Role FROM Users")
    return cursor.fetchall()


def seed_audit_logs():
    logger.info("Bắt đầu khởi tạo dữ liệu mẫu cho bảng AuditLogs...")
    start_time = time.time()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        users = get_active_users(cursor)
        if not users:
            logger.error("Không tìm thấy Users hợp lệ! Vui lòng chạy seed_users.py trước.")
            return

        audit_logs_data = []
        now = datetime.now()

        # Sinh 50 bản ghi nhật ký trong 30 ngày gần nhất
        for i in range(1, 51):
            user = random.choice(users)
            user_id, username, role = user[0], user[1], user[2]

            action = random.choice(ACTIONS)
            module = random.choice(MODULES) if action not in ["LOGIN", "LOGOUT"] else "Auth"
            record_id = random.randint(1, 100) if action not in ["LOGIN", "LOGOUT"] else None

            # Sinh mô tả tự động theo hành động
            if action == "LOGIN":
                description = f"Người dùng {username} đã đăng nhập thành công vào hệ thống."
            elif action == "LOGOUT":
                description = f"Người dùng {username} đã đăng xuất khỏi hệ thống."
            elif action == "CREATE":
                description = f"Tạo mới bản ghi ID {record_id} trong module {module}."
            elif action == "UPDATE":
                description = f"Cập nhật thông tin bản ghi ID {record_id} trong module {module}."
            elif action == "DELETE":
                description = f"Xóa mềm bản ghi ID {record_id} trong module {module}."
            else:  # EXPORT
                description = f"Xuất báo cáo dữ liệu từ module {module} sang file Excel."

            ip_address = random.choice(IP_ADDRESSES)
            user_agent = random.choice(USER_AGENTS)
            created_at = now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23), minutes=random.randint(0, 59))

            audit_logs_data.append((
                user_id, username, role, module, action,
                record_id, description, ip_address, user_agent, created_at
            ))

        # Sử dụng executemany() chèn dữ liệu hàng loạt
        sql_insert = """
            INSERT INTO AuditLogs (
                UserID, Username, Role, Module, Action,
                RecordID, Description, IPAddress, UserAgent, CreatedAt
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        cursor.executemany(sql_insert, audit_logs_data)
        conn.commit()

        end_time = time.time()
        execution_time = round(end_time - start_time, 2)

        logger.info(f"Thành công! Đã thêm mới {len(audit_logs_data)} bản ghi AuditLogs vào CSDL.")
        logger.info(f"Tổng thời gian thực thi: {execution_time} giây.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Đã có lỗi xảy ra trong quá trình seed AuditLogs: {str(e)}", exc_info=True)
    finally:
        conn.close()
        logger.info("Đã đóng kết nối CSDL an toàn.")


if __name__ == "__main__":
    seed_audit_logs()