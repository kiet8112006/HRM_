import logging
import random
import time
from datetime import datetime, timedelta
from faker import Faker

from database import get_connection
from scripts.config import NUM_CONTRACTS
from scripts.data.contracts import (
    CONTRACT_TYPES,
    CONTRACT_STATUSES,
    WORK_LOCATIONS,
    SIGNERS,
    BASIC_SALARIES
)

# Thiết lập Logger ghi tiến trình
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

fake = Faker("vi_VN")


def get_active_employees_with_dept_and_pos(cursor):
    """Lấy danh sách Employee kèm DepartmentID và PositionID từ CSDL."""
    cursor.execute("""
        SELECT EmployeeID, DepartmentID, PositionID, HireDate 
        FROM Employees 
        WHERE IsDeleted = 0
    """)
    return cursor.fetchall()


def seed_contracts():
    logger.info(f"Bắt đầu khởi tạo dữ liệu mẫu cho {NUM_CONTRACTS} Contracts...")
    start_time = time.time()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Lấy danh sách nhân viên hợp lệ
        employees = get_active_employees_with_dept_and_pos(cursor)
        if not employees:
            logger.error("Không tìm thấy Employees hợp lệ! Vui lòng chạy seed_employees.py trước.")
            return

        contracts_data = []
        used_contract_codes = set()

        # 2. Sinh dữ liệu Hợp đồng trong bộ nhớ
        for i in range(1, NUM_CONTRACTS + 1):
            emp = random.choice(employees)
            emp_id, dept_id, pos_id, hire_date = emp[0], emp[1], emp[2], emp[3]

            # Mã và số hợp đồng Unique
            contract_code = f"HD-{i:05d}"
            contract_number = f"HDLD/{datetime.now().year}/{i:04d}"

            contract_type = random.choice(CONTRACT_TYPES)
            
            # Tính toán ngày hợp đồng dựa trên HireDate của nhân viên
            if isinstance(hire_date, str):
                hire_date = datetime.strptime(hire_date, "%Y-%m-%d").date()
            
            start_date = hire_date if hire_date else datetime.now().date()
            sign_date = start_date - timedelta(days=random.randint(1, 7))

            # Logic thời hạn hợp đồng & Thời gian thử việc
            if contract_type == "Hợp đồng thử việc":
                probation_months = 2
                end_date = start_date + timedelta(days=60)
            elif "12 tháng" in contract_type:
                probation_months = 2
                end_date = start_date + timedelta(days=365)
            elif "36 tháng" in contract_type:
                probation_months = 2
                end_date = start_date + timedelta(days=365 * 3)
            else:  # Không xác định thời hạn
                probation_months = 0
                end_date = None

            status = random.choice(CONTRACT_STATUSES)
            basic_salary = random.choice(BASIC_SALARIES)
            work_location = random.choice(WORK_LOCATIONS)
            signer = random.choice(SIGNERS)
            contract_file = f"HD_{contract_code}.pdf"
            description = f"Hợp đồng lao động loại {contract_type} cho nhân viên ID {emp_id}"
            is_deleted = 0

            contracts_data.append((
                emp_id, contract_type, start_date, end_date, status,
                contract_code, contract_number, basic_salary, work_location,
                dept_id, pos_id, signer, sign_date, probation_months,
                contract_file, description, is_deleted
            ))

        # 3. Sử dụng executemany() để insert hàng loạt
        sql_insert = """
            INSERT INTO Contracts (
                EmployeeID, ContractType, StartDate, EndDate, Status,
                ContractCode, ContractNumber, BasicSalary, WorkLocation,
                DepartmentID, PositionID, Signer, SignDate, ProbationMonths,
                ContractFile, Description, IsDeleted
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        cursor.executemany(sql_insert, contracts_data)
        conn.commit()

        end_time = time.time()
        execution_time = round(end_time - start_time, 2)

        logger.info(f"Thành công! Đã thêm mới {len(contracts_data)} bản ghi Contracts vào CSDL.")
        logger.info(f"Tổng thời gian thực thi: {execution_time} giây.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Đã có lỗi xảy ra trong quá trình seed dữ liệu Contracts: {str(e)}", exc_info=True)
    finally:
        conn.close()
        logger.info("Đã đóng kết nối CSDL an toàn.")


if __name__ == "__main__":
    seed_contracts()