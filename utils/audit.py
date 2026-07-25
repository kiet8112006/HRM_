import logging
from flask import session, request
from database import get_connection

# Cấu hình logger cơ bản (nếu chưa cấu hình ở file app chính)
logger = logging.getLogger(__name__)

def log_activity(
    module,
    action,
    description,
    record_id=None
):
    conn = None
    try:
        user_id = session.get('user_id')
        username = session.get('username')
        role = session.get('role')
        ip_address = request.remote_addr
        
        # Đảm bảo user_agent luôn là string (đề phòng request không có user_agent)
        user_agent = request.user_agent.string if request.user_agent else None

        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO AuditLogs 
            (UserID, UserName, Role, Module, Action, RecordID, Description, IPAddress, UserAgent) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(query, (user_id, username, role, module, action, record_id, description, ip_address, user_agent))
        conn.commit()

    except Exception as e:
        # Ghi log lỗi ra Console/File log của hệ thống để Dev biết đường fix
        logger.error(f"Lỗi khi ghi AuditLog: {str(e)}", exc_info=True)
        
        # Rollback giao dịch nếu có lỗi xảy ra
        if conn:
            conn.rollback()

    finally:
        # Luôn luôn đóng kết nối Database dù có lỗi hay không
        if conn:
            conn.close()