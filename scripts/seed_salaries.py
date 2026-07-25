import logging
import random
import time
from datetime import datetime

from database import get_connection
from scripts.config import NUM_SALARIES
from scripts.data.salaries import SALARY_STATUSES, BASE_SALARY_LEVELS

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


def seed_salaries():
    logger.info(f"Bắt đầu khởi tạo dữ liệu mẫu cho {NUM_SALARIES} Salaries...")
    start_time = time.time()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Kiểm tra dữ liệu khóa ngoại (Employees)
        employee_ids = get_active_employee_ids(cursor)
        if not employee_ids:
            logger.error("Không tìm thấy Employees hợp lệ! Vui lòng chạy seed_employees.py trước.")
            return

        # 2. Sinh tập dữ liệu bảng lương trong Bộ nhớ
        salaries_data = []
        used_employee_month_year = set()

        # Giới hạn phát sinh lương trong năm hiện tại và 2 năm gần nhất
        current_year = datetime.now().year
        years = [current_year - 1, current_year]
        months = list(range(1, 13))

        attempts = 0
        max_attempts = NUM_SALARIES * 5

        while len(salaries_data) < NUM_SALARIES and attempts < max_attempts:
            attempts += 1

            emp_id = random.choice(employee_ids)
            m = random.choice(months)
            y = random.choice(years)

            # Bỏ qua các tháng trong tương lai của năm hiện tại
            if y == current_year and m > datetime.now().month:
                continue

            # Đảm bảo 1 Nhân viên chỉ có 1 bảng lương trong 1 tháng/năm
            pair = (emp_id, m, y)
            if pair in used_employee_month_year:
                continue
            used_employee_month_year.add(pair)

            salary_code = f"SAL-{y}{m:02d}-{emp_id:04d}"
            
            # Tính toán các khoản lương & phụ cấp
            base_salary = random.choice(BASE_SALARY_LEVELS)
            bonus = round(random.choice([0.0, 500000.0, 1000000.0, 2000000.0, 5000000.0]), 2)
            allowance = round(random.choice([500000.0, 1000000.0, 1500000.0]), 2)
            overtime_pay = round(random.choice([0.0, 300000.0, 750000.0, 1200000.0]), 2)

            # Tính toán các khoản khấu trừ
            insurance = round(base_salary * 0.105, 2)  # 10.5% BHXH, BHYT, BHTN
            
            gross = base_salary + bonus + allowance + overtime_pay
            taxable_income = max(0.0, gross - insurance - 11000000.0)  # Giảm trừ gia cảnh 11M
            tax = round(taxable_income * 0.10, 2) if taxable_income > 0 else 0.0
            
            deduction = round(random.choice([0.0, 200000.0, 500000.0]), 2)  # Khấu trừ vi phạm/phạt

            # Tính Lương thực nhận (Net Salary)
            net_salary = round(gross - (insurance + tax + deduction), 2)

            status = random.choice(SALARY_STATUSES)
            payment_date = datetime(y, m, 28).date() if status == "Đã thanh toán" else None
            notes = f"Bảng lương tháng {m}/{y}"
            is_deleted = 0

            salaries_data.append((
                emp_id, base_salary, bonus, allowance, m, y,
                salary_code, overtime_pay, deduction, tax, insurance,
                net_salary, payment_date, status, notes, is_deleted
            ))

        # 3. Sử dụng executemany() chèn dữ liệu hàng loạt
        sql_insert = """
            INSERT INTO Salaries (
                EmployeeID, BaseSalary, Bonus, Allowance, [month], [year],
                SalaryCode, OvertimePay, Deduction, Tax, Insurance,
                NetSalary, PaymentDate, Status, Notes, IsDeleted
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        cursor.executemany(sql_insert, salaries_data)
        conn.commit()

        end_time = time.time()
        execution_time = round(end_time - start_time, 2)

        logger.info(f"Thành công! Đã thêm mới {len(salaries_data)} bản ghi Salaries vào CSDL.")
        logger.info(f"Tổng thời gian thực thi: {execution_time} giây.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Đã có lỗi xảy ra trong quá trình seed dữ liệu Salaries: {str(e)}", exc_info=True)
    finally:
        conn.close()
        logger.info("Đã đóng kết nối CSDL an toàn.")


if __name__ == "__main__":
    seed_salaries()