import logging
from database import get_connection

# Thiết lập Logger ghi nhận quá trình clear database
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def clear_database():
    logger.info("🔥 Bắt đầu tiến trình xóa sạch dữ liệu trong CSDL...")
    
    conn = get_connection()
    cursor = conn.cursor()

    # Thứ tự xóa bảng: Xóa bảng CON (phụ thuộc FK) trước -> Xóa bảng CHA sau
    tables_to_clear = [
        "AuditLogs",       # Nhật ký thao tác
        "Notifications",   # Thông báo hệ thống
        "Attendance",      # Chấm công (phụ thuộc Employees)
        "LeaveRequests",   # Đơn nghỉ phép (phụ thuộc Employees)
        "Salaries",        # Bảng lương (phụ thuộc Employees)
        "Contracts",       # Hợp đồng (phụ thuộc Employees, Departments, Positions)
        "Employees",       # Nhân viên (phụ thuộc Departments, Positions, Users)
        "Positions",       # Chức vụ
        "Departments",     # Phòng ban
        "Users"            # Tài khoản người dùng
    ]

    try:
        # 1. Tắt tạm thời kiểm tra khóa ngoại (Foreign Key) để tránh lỗi dính dấp liên kết khi xóa
        cursor.execute("EXEC sp_msforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL'")

        for table in tables_to_clear:
            # Xóa toàn bộ dữ liệu trong bảng
            cursor.execute(f"DELETE FROM {table}")
            
            # Reset lại giá trị ID tự tăng (IDENTITY) về 0 (nếu bảng có cột IDENTITY)
            try:
                cursor.execute(f"DBCC CHECKIDENT ('{table}', RESEED, 0)")
            except Exception:
                # Bỏ qua nếu bảng không có cột IDENTITY
                pass

            logger.info(f" -> Đã xóa sạch dữ liệu và reset ID cho bảng: [{table}]")

        # 2. Bật lại kiểm tra khóa ngoại (Foreign Key) sau khi hoàn tất
        cursor.execute("EXEC sp_msforeachtable 'ALTER TABLE ? CHECK CONSTRAINT ALL'")

        # Commit toàn bộ thao tác
        conn.commit()
        logger.info("🎉 HOÀN TẤT! Toàn bộ CSDL đã được làm sạch an toàn.")

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Đã xảy ra lỗi trong quá trình clear CSDL: {str(e)}", exc_info=True)
    finally:
        conn.close()
        logger.info("🔒 Đã đóng kết nối CSDL an toàn.")

if __name__ == "__main__":
    clear_database()