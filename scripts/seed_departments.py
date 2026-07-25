import logging
from faker import Faker
from database import get_connection
from config import *
from scripts.data.departments import DEPARTMENTS, STATUSES

# Thiết lập Logger để ghi nhận tiến trình và lỗi ra Console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

fake = Faker("vi_VN")

def seed_departments():
    logger.info("Bắt đầu khởi tạo dữ liệu mẫu cho bảng Departments...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        inserted_count = 0
        for i, department_name in enumerate(DEPARTMENTS, start=1):
            department_code = f"DP{i:03d}"
            location = fake.city()
            description = f"Đây là {department_name}"
            status = "Active"  # Mặc định tạo mới là Active
            manager_id = None
            is_deleted = 0

            # Kiểm tra xem phòng ban đã tồn tại chưa để tránh trùng lặp
            cursor.execute("""
                SELECT COUNT(*) FROM Departments 
                WHERE DepartmentCode = ? OR DepartmentName = ?
            """, (department_code, department_name))
            
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO Departments (
                        DepartmentName, ManagerID, DepartmentCode, Description, Location, Status, IsDeleted
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (department_name, manager_id, department_code, description, location, status, is_deleted))
                
                inserted_count += 1
                logger.info(f"-> Thêm mới: [{department_code}] {department_name} - {location}")
            else:
                logger.warning(f"-> Bỏ qua: [{department_code}] {department_name} đã tồn tại.")

        # Commit toàn bộ giao dịch sau khi lặp xong
        conn.commit()
        logger.info(f"Hoàn tất! Đã thêm thành công {inserted_count}/{len(DEPARTMENTS)} phòng ban.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Đã có lỗi xảy ra trong quá trình seed dữ liệu Departments: {str(e)}", exc_info=True)
    finally:
        conn.close()
        logger.info("Đã đóng kết nối CSDL an toàn.")

if __name__ == "__main__":
    seed_departments()