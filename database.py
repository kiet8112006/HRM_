import pyodbc
import os

def get_connection():
    # Sử dụng IP host.docker.internal kèm tên Instance SQLEXPRESS
    server = os.environ.get("DB_SERVER", r"host.docker.internal\SQLEXPRESS")
    database = os.environ.get("DB_DATABASE", "HRM_IS")
    user = os.environ.get("DB_USER", "sa")
    password = os.environ.get("DB_PASSWORD", "123456")
    
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"Encrypt=no;"  # Tắt bắt buộc mã hóa SSL để tránh lỗi cert nội bộ
    )
        
    return pyodbc.connect(conn_str)