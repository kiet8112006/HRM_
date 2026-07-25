import logging
import random
import time
from datetime import datetime, timedelta

from database import get_connection
from scripts.config import NUM_LEAVE_REQUESTS
from scripts.data.leave_requests import (
    LEAVE_TYPES,
    LEAVE_STATUSES,
    REASONS,
    APPROVERS
)

# Thiết lập Logger ghi tiến trình
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def get_active_employee_ids(cursor):
    """Lấy danh sách EmployeeID hợp lệ từ CSDL."""
    cursor.execute("SELECT EmployeeID FROM Employees WHERE IsDeleted = 0")
    return [row[0] for row in cursor.fetchall()]


def seed_leave_requests():
    logger.info(f"Bắt đầu khởi tạo dữ liệu mẫu cho {NUM_LEAVE_REQUESTS} LeaveRequests...")
    start_time = time.time()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Kiểm tra dữ liệu khóa ngoại (Employees)
        employee_ids = get_active_employee_ids(cursor)
        if not employee_ids:
            logger.error("Không tìm thấy Employees hợp lệ! Vui lòng chạy seed_employees.py trước.")
            return

        leave_requests_data = []

        # Giới hạn ngày xin nghỉ trong khoảng 90 ngày gần đây đến 30 ngày tới
        today = datetime.now().date()
        start_range = today - timedelta(days=90)

        # 2. Sinh tập dữ liệu đơn nghỉ phép trong bộ nhớ
        for i in range(1, NUM_LEAVE_REQUESTS + 1):
            emp_id = random.choice(employee_ids)
            leave_code = f"LR-{datetime.now().year}-{i:05d}"
            leave_type = random.choice(LEAVE_TYPES)
            reason = random.choice(REASONS)

            # Tính toán ngày bắt đầu & số ngày nghỉ
            from_date = start_range + timedelta(days=random.randint(0, 120))
            duration = random.randint(1, 5)  # Nghỉ từ 1 đến 5 ngày
            to_date = from_date + timedelta(days=duration - 1)
            total_days = duration

            # Ngày nộp đơn (AppliedDate) trước ngày nghỉ từ 1 - 7 ngày
            applied_date = from_date - timedelta(days=random.randint(1, 7))

            status = random.choice(LEAVE_STATUSES)

            # Logic Người duyệt & Ngày duyệt dựa theo Trạng thái
            if status in ["Đã duyệt", "Từ chối"]:
                approved_by = random.choice(APPROVERS)
                approved_date = applied_date + timedelta(days=random.randint(1, 2))
                if approved_date > today:
                    approved_date = today
            else:
                approved_by = None
                approved_date = None

            attachment = f"NghiPhep_{leave_code}.pdf" if random.random() < 0.3 else None
            description = f"Đơn xin {leave_type.lower()} của nhân viên ID {emp_id}"
            is_deleted = 0

            leave_requests_data.append((
                emp_id, from_date, to_date, reason, status,
                leave_code, total_days, attachment, applied_date,
                approved_by, approved_date, description, leave_type, is_deleted
            ))

        # 3. Sử dụng executemany() chèn dữ liệu hàng loạt
        sql_insert = """
            INSERT INTO LeaveRequests (
                EmployeeID, FromDate, ToDate, Reason, Status,
                LeaveCode, TotalDays, Attachment, AppliedDate,
                ApprovedBy, ApprovedDate, Description, LeaveType, IsDeleted
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        cursor.executemany(sql_insert, leave_requests_data)
        conn.commit()

        end_time = time.time()
        execution_time = round(end_time - start_time, 2)

        logger.info(f"Thành công! Đã thêm mới {len(leave_requests_data)} bản ghi LeaveRequests vào CSDL.")
        logger.info(f"Tổng thời gian thực thi: {execution_time} giây.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Đã có lỗi xảy ra trong quá trình seed dữ liệu LeaveRequests: {str(e)}", exc_info=True)
    finally:
        conn.close()
        logger.info("Đã đóng kết nối CSDL an toàn.")


if __name__ == "__main__":
    seed_leave_requests()