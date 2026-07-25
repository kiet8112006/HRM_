import logging
import random
import time
from datetime import datetime, timedelta
from faker import Faker

from database import get_connection
from scripts.config import NUM_EMPLOYEES
from scripts.data.employees import GENDERS, STATUSES, MARITAL_STATUSES, NATIONALITIES

# Thiết lập Logger ghi tiến trình
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

fake = Faker("vi_VN")


def get_active_department_and_position_ids(cursor):
    """Lấy danh sách ID phòng ban và chức vụ hợp lệ từ CSDL."""
    cursor.execute("SELECT DepartmentID FROM Departments WHERE IsDeleted = 0")
    dept_ids = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT PositionID FROM Positions WHERE IsDeleted = 0")
    pos_ids = [row[0] for row in cursor.fetchall()]

    return dept_ids, pos_ids


def seed_employees():
    logger.info(f"Bắt đầu khởi tạo dữ liệu mẫu cho {NUM_EMPLOYEES} Employees...")
    start_time = time.time()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Kiểm tra dữ liệu khóa ngoại (Departments & Positions)
        dept_ids, pos_ids = get_active_department_and_position_ids(cursor)
        if not dept_ids or not pos_ids:
            logger.error("Không tìm thấy Departments hoặc Positions hợp lệ! Vui lòng seed_departments và seed_positions trước.")
            return

        # 2. Sinh tập dữ liệu hàng loạt trong Bộ nhớ (Memory)
        employees_data = []
        used_emails = set()
        used_phones = set()
        used_citizen_ids = set()

        for i in range(1, NUM_EMPLOYEES + 1):
            gender = random.choice(GENDERS)
            
            # Sinh tên theo giới tính
            if gender == "Nam":
                full_name = fake.name_male()
            else:
                full_name = fake.name_female()

            # Ngày sinh (Từ 18 đến 60 tuổi)
            dob = fake.date_of_birth(minimum_age=18, maximum_age=60)
            
            # Ngày tuyển dụng (Sau khi đủ 18 tuổi và trước ngày hiện tại)
            min_hire_date = dob + timedelta(days=18 * 365)
            today = datetime.now().date()
            if min_hire_date >= today:
                hire_date = today
            else:
                hire_date = fake.date_between(start_date=min_hire_date, end_date=today)

            # Unique Email
            email = fake.unique.email()
            while email in used_emails:
                email = fake.unique.email()
            used_emails.add(email)

            # Unique Phone (10 chữ số bắt đầu bằng số 0)
            phone = f"0{random.randint(300000000, 999999999)}"
            while phone in used_phones:
                phone = f"0{random.randint(300000000, 999999999)}"
            used_phones.add(phone)

            # Unique CitizenID (CCCD 12 chữ số)
            citizen_id = f"{random.randint(100000000000, 999999999999)}"
            while citizen_id in used_citizen_ids:
                citizen_id = f"{random.randint(100000000000, 999999999999)}"
            used_citizen_ids.add(citizen_id)

            address = fake.address().replace("\n", ", ")
            nationality = random.choice(NATIONALITIES)
            marital_status = random.choice(MARITAL_STATUSES)
            emergency_contact = fake.name()
            emergency_phone = f"0{random.randint(300000000, 999999999)}"
            
            status = random.choice(STATUSES)
            dept_id = random.choice(dept_ids)
            pos_id = random.choice(pos_ids)
            manager_id = None
            is_deleted = 0

            # Gom thành Tuple tương ứng các tham số của câu INSERT
            employees_data.append((
                full_name, gender, dob, hire_date, email, phone, 
                dept_id, pos_id, manager_id, status, citizen_id, 
                address, nationality, marital_status, emergency_contact, 
                emergency_phone, is_deleted
            ))

        # 3. Sử dụng executemany() để Insert hàng loạt cực nhanh vào CSDL
        sql_insert = """
            INSERT INTO Employees (
                FullName, Gender, DOB, HireDate, Email, Phone, 
                DepartmentID, PositionID, ManagerID, Status, CitizenID, 
                Address, Nationality, MaritalStatus, EmergencyContact, 
                EmergencyPhone, IsDeleted
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor.executemany(sql_insert, employees_data)
        conn.commit()

        end_time = time.time()
        execution_time = round(end_time - start_time, 2)
        
        logger.info(f"Thành công! Đã thêm mới {len(employees_data)} bản ghi Employees vào CSDL.")
        logger.info(f"Tổng thời gian thực thi: {execution_time} giây.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Đã có lỗi xảy ra trong quá trình seed dữ liệu Employees: {str(e)}", exc_info=True)
    finally:
        conn.close()
        logger.info("Đã đóng kết nối CSDL an toàn.")


if __name__ == "__main__":
    seed_employees()