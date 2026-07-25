# Nội dung file extensions.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Khởi tạo instance trống ở đây để tránh bị vòng lặp import
limiter = Limiter(key_func=get_remote_address)