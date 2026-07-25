import logging
import time

# Import hàm clear database
from scripts.clear_database import clear_database

# Import các hàm seed dữ liệu từ các file tương ứng
from scripts.seed_users import seed_users
from scripts.seed_departments import seed_departments
from scripts.seed_positions import seed_positions
from scripts.seed_employees import seed_employees
from scripts.seed_contracts import seed_contracts
from scripts.seed_salaries import seed_salaries
from scripts.seed_attendance import seed_attendance
from scripts.seed_leave_requests import seed_leave_requests
from scripts.seed_notifications import seed_notifications
from scripts.seed_audit_logs import seed_audit_logs

# Thiết lập Logger để theo dõi toàn bộ tiến trình
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def run_all_seeders():
    start_time = time.time()
    logger.info("==================================================")
    logger.info("🚀 BẮT ĐẦU TIẾN TRÌNH REFRESH & SEED DỮ LIỆU HỆ THỐNG HRM")
    logger.info("==================================================")

    try:
        # Bước 0: Xóa sạch dữ liệu cũ
        logger.info("\n--- BƯỚC 0: CLEAR DATABASE ---")
        clear_database()

        # Bước 1 -> N: Nạp dữ liệu theo đúng thứ tự phụ thuộc (FK)
        logger.info("\n--- BƯỚC 1: SEED USERS ---")
        seed_users()

        logger.info("\n--- BƯỚC 2: SEED DEPARTMENTS ---")
        seed_departments()

        logger.info("\n--- BƯỚC 3: SEED POSITIONS ---")
        seed_positions()

        logger.info("\n--- BƯỚC 4: SEED EMPLOYEES ---")
        seed_employees()

        logger.info("\n--- BƯỚC 5: SEED CONTRACTS ---")
        seed_contracts()

        logger.info("\n--- BƯỚC 6: SEED SALARIES ---")
        seed_salaries()

        logger.info("\n--- BƯỚC 7: SEED ATTENDANCE ---")
        seed_attendance()

        logger.info("\n--- BƯỚC 8: SEED LEAVE REQUESTS ---")
        seed_leave_requests()

        logger.info("\n--- BƯỚC 9: SEED NOTIFICATIONS ---")
        seed_notifications()

        logger.info("\n--- BƯỚC 10: SEED AUDIT LOGS ---")
        seed_audit_logs()

        execution_time = round(time.time() - start_time, 2)
        logger.info("\n==================================================")
        logger.info(f"🎉 TẤT CẢ DỮ LIỆU ĐÃ ĐƯỢC SEED THÀNH CÔNG TRONG {execution_time} GIÂY!")
        logger.info("==================================================")

    except Exception as e:
        logger.error(f"❌ Tiến trình Seed thất bại giữa chừng: {str(e)}", exc_info=True)

if __name__ == "__main__":
    run_all_seeders()