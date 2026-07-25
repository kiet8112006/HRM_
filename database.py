import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection():
    # Lấy chuỗi kết nối từ biến môi trường DATABASE_URL
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        raise ValueError("DATABASE_URL chưa được thiết lập trong Environment Variables!")
        
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"[ERROR] Lỗi kết nối PostgreSQL: {e}")
        raise e