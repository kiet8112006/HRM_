import logging
import random
import time
from datetime import datetime, timedelta, time as dtime

from database import get_connection
from scripts.config import NUM_ATTENDANCES
from scripts.data.attendance import (
    ATTENDANCE_STATUSES,
    CHECKIN_METHODS,
    APPROVAL_STATUSES
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


def seed_attendance():
    logger.info(f"Bắt đầu khởi tạo dữ liệu mẫu cho {NUM_ATTENDANCES} Attendance...")
    start_time = time.time()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Kiểm tra dữ liệu khóa ngoại (Employees)
        employee_ids = get_active_employee_ids(cursor)
        if not employee_ids:
            logger.error("Không tìm thấy Employees hợp lệ! Vui lòng chạy seed_employees.py trước.")
            return

        # 2. Sinh tập dữ liệu chấm công trong Bộ nhớ
        attendance_data = []
        used_employee_date_pairs = set()

        # Giới hạn ngày chấm công trong khoảng 60 ngày gần đây
        today = datetime.now().date()
        start_date = today - timedelta(days=60)

        attempts = 0
        max_attempts = NUM_ATTENDANCES * 5  # Tránh vòng lặp vô tận khi trùng ngày

        while len(attendance_data) < NUM_ATTENDANCES and attempts < max_attempts:
            attempts += 1
            
            emp_id = random.choice(employee_ids)
            random_days = random.randint(0, 60)
            att_date = start_date + timedelta(days=random_days)

            # Đảm bảo 1 Nhân viên chỉ chấm công 1 lần trong 1 ngày
            pair = (emp_id, att_date)
            if pair in used_employee_date_pairs:
                continue
            used_employee_date_pairs.add(pair)

            status = random.choice(ATTENDANCE_STATUSES)
            shift_id = 1  # Ca hành chính mặc định
            checkin_method = random.choice(CHECKIN_METHODS)
            approval_status = random.choice(APPROVAL_STATUSES)
            notes = None
            is_deleted = 0

            # Xử lý logic thời gian dựa trên Trạng thái chấm công
            if status == "Có mặt":
                # Check-in đúng giờ (07:45 - 08:00)
                checkin_minute = random.randint(45, 59)
                checkin_time = dtime(7, checkin_minute)
                
                # Check-out (17:00 - 17:30)
                checkout_minute = random.randint(0, 30)
                checkout_time = dtime(17, checkout_minute)

                working_hours = 8.0
                overtime_hours = round(random.choice([0.0, 0.5, 1.0, 1.5, 2.0]), 2)
                late_minutes = 0
                early_leave_minutes = 0

            elif status == "Đi trễ":
                # Check-in trễ (08:05 - 09:00)
                checkin_hour = 8 if random.random() < 0.8 else 9
                checkin_minute = random.randint(5, 59) if checkin_hour == 8 else random.randint(0, 30)
                checkin_time = dtime(checkin_hour, checkin_minute)

                checkout_time = dtime(17, random.randint(0, 15))

                # Tính phút trễ (so với mốc 08:00)
                late_minutes = (checkin_hour - 8) * 60 + checkin_minute
                working_hours = round(8.0 - (late_minutes / 60.0), 2)
                overtime_hours = 0.0
                early_leave_minutes = 0
                notes = f"Đi trễ {late_minutes} phút"

            else:  # "Nghỉ"
                checkin_time = None
                checkout_time = None
                working_hours = 0.0
                overtime_hours = 0.0
                late_minutes = 0
                early_leave_minutes = 0
                notes = "Nghỉ có phép / Không phép"

            attendance_data.append((
                emp_id, att_date, checkin_time, checkout_time, status,
                shift_id, working_hours, overtime_hours, late_minutes,
                early_leave_minutes, checkin_method, approval_status,
                notes, is_deleted
            ))

        # 3. Sử dụng executemany() chèn dữ liệu hàng loạt
        sql_insert = """
            INSERT INTO Attendance (
                EmployeeID, Date, CheckInTime, CheckOutTime, Status,
                ShiftID, WorkingHours, OvertimeHours, LateMinutes,
                EarlyLeaveMinutes, CheckInMethod, ApprovalStatus,
                Notes, IsDeleted
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        cursor.executemany(sql_insert, attendance_data)
        conn.commit()

        end_time = time.time()
        execution_time = round(end_time - start_time, 2)

        logger.info(f"Thành công! Đã thêm mới {len(attendance_data)} bản ghi Attendance vào CSDL.")
        logger.info(f"Tổng thời gian thực thi: {execution_time} giây.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Đã có lỗi xảy ra trong quá trình seed dữ liệu Attendance: {str(e)}", exc_info=True)
    finally:
        conn.close()
        logger.info("Đã đóng kết nối CSDL an toàn.")


if __name__ == "__main__":
    seed_attendance()