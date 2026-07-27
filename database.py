import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_DATABASE")
    username = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={server};"
    f"DATABASE={database};"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"[ERROR] Lỗi kết nối SQL Server: {e}")
        raise