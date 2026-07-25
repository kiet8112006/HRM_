import logging
import random
import time
from datetime import datetime, timedelta

from database import get_connection
from scripts.data.notifications import SAMPLE_NOTIFICATIONS, NOTIFICATION_TYPES

# Thiết lập Logger ghi tiến trình
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def seed_notifications():
    logger.info("Bắt đầu khởi tạo dữ liệu mẫu cho bảng Notifications...")
    start_time = time.time()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        notifications_data = []
        now = datetime.now()

        # 1. Thêm các thông báo cố định quan trọng
        for n in SAMPLE_NOTIFICATIONS:
            created_at = now - timedelta(hours=random.randint(1, 48))
            is_read = random.choice([0, 1])
            receiver_id = None

            notifications_data.append((
                n["Title"], n["Message"], n["Type"], n["ReceiverRole"],
                receiver_id, n["Url"], is_read, created_at
            ))

        # 2. Sinh thêm các thông báo ngẫu nhiên khác
        roles = ["Admin", "Manager", "User", None]
        for i in range(1, 15):
            role = random.choice(roles)
            ntype = random.choice(NOTIFICATION_TYPES)
            created_at = now - timedelta(days=random.randint(1, 15), hours=random.randint(1, 12))
            is_read = 0 if i <= 5 else 1  # Giữ vài thông báo chưa đọc (unread)
            
            title = f"Thông báo hệ thống #{i}"
            message = f"Nội dung cập nhật thông tin tự động cho nhóm quyền {role if role else 'Tất cả'}."
            url = "/notifications"

            notifications_data.append((
                title, message, ntype, role, None, url, is_read, created_at
            ))

        # 3. Sử dụng executemany() chèn dữ liệu hàng loạt
        sql_insert = """
            INSERT INTO Notifications (
                Title, Message, Type, ReceiverRole, ReceiverID, Url, IsRead, CreatedAt
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        cursor.executemany(sql_insert, notifications_data)
        conn.commit()

        end_time = time.time()
        execution_time = round(end_time - start_time, 2)

        logger.info(f"Thành công! Đã thêm mới {len(notifications_data)} bản ghi Notifications vào CSDL.")
        logger.info(f"Tổng thời gian thực thi: {execution_time} giây.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Đã có lỗi xảy ra trong quá trình seed Notifications: {str(e)}", exc_info=True)
    finally:
        conn.close()
        logger.info("Đã đóng kết nối CSDL an toàn.")


if __name__ == "__main__":
    seed_notifications()