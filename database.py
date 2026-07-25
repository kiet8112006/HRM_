import os
import pyodbc
from unittest.mock import MagicMock

def get_connection():
    # Lấy thông tin từ Environment
    server = os.getenv('DB_SERVER', 'localhost')
    database = os.getenv('DB_NAME', '')
    user = os.getenv('DB_USER', '')
    password = os.getenv('DB_PASSWORD', '')
    driver = os.getenv('DB_DRIVER', '{ODBC Driver 17 for SQL Server}')

    conn_str = f"DRIVER={driver};SERVER={server};DATABASE={database};UID={user};PWD={password};TrustServerCertificate=yes;Connection Timeout=3;"

    try:
        # Thử kết nối thật với Timeout ngắn (3 giây)
        return pyodbc.connect(conn_str)
    except Exception as e:
        print(f"[WARNING] Database connection failed: {e}. Switching to Mock Connection.")
        
        # Nếu lỗi (như trên Render không nối về local được), tạo Dummy Object giả lập DB
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        # Cấu hình giá trị mặc định cho các câu query đếm/lấy dữ liệu
        mock_cursor.fetchone.return_value = (0, "Admin", "hash", "Admin Demo", "Admin", True)
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        
        return mock_conn