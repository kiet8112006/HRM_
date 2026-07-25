import logging
from faker import Faker
from database import get_connection
from config import *

# Thiết lập Logger để ghi nhận tiến trình và lỗi ra Console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

fake = Faker("vi_VN")

def seed_positions():
    logger.info("Bắt đầu khởi tạo dữ liệu mẫu cho bảng Positions...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    positions = [
        "Giám Đốc",
        "Trưởng Phòng",
        "Phó Phòng",
        "Quản Lý Dự Án",
        "Kỹ Sư Phần Mềm",
        "Chuyên Viên Nhân Sự",
        "Kế Toán Viên",
        "Chuyên Viên Marketing",
        "Nhân Viên Kinh Doanh",
        "Nhân Viên Hành Chính",
        "Nhân Viên Kho",
        "Chuyên Viên Hỗ Trợ Khách Hàng"
    ]
    
    try:
        inserted_count = 0
        for i, position_name in enumerate(positions, start=1):
            position_code = f"POS{i:03d}"
            description = f"Mô tả công việc cho vị trí {position_name}"
            status = "Active"
            is_deleted = 0  # Đồng bộ tên cột IsDeleted

            # Kiểm tra xem chức vụ đã tồn tại chưa để tránh ghi trùng dữ liệu
            cursor.execute("""
                SELECT COUNT(*) FROM Positions 
                WHERE PositionCode = ? OR PositionName = ?
            """, (position_code, position_name))
            
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO Positions (
                        PositionName, PositionCode, Description, Status, IsDeleted
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (position_name, position_code, description, status, is_deleted))
                
                inserted_count += 1
                logger.info(f"-> Thêm mới: [{position_code}] {position_name}")
            else:
                logger.warning(f"-> Bỏ qua: [{position_code}] {position_name} đã tồn tại.")

        # Commit toàn bộ giao dịch sau khi vòng lặp hoàn tất
        conn.commit()
        logger.info(f"Hoàn tất! Đã thêm thành công {inserted_count}/{len(positions)} chức vụ.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Đã có lỗi xảy ra trong quá trình seed dữ liệu Positions: {str(e)}", exc_info=True)
    finally:
        conn.close()
        logger.info("Đã đóng kết nối CSDL an toàn.")

if __name__ == "__main__":
    seed_positions()