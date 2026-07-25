from unittest.mock import MagicMock, patch
import pytest
import os
import sys

# Thêm thư mục gốc dự án (HRM_cũ) vào PYTHONPATH
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from unittest.mock import MagicMock, patch
import pytest

# Import app từ file app.py
from app import app as flask_app
# Import app từ file app.py
from app import app as flask_app


@pytest.fixture
def app():
    flask_app.config.update(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret-key",
        }
    )

    # Mock Flask-Caching để tránh lỗi khi gọi các hàm cached
    if hasattr(flask_app, "cache"):
        flask_app.cache.cached = lambda *args, **kwargs: lambda f: f

    yield flask_app


# 1. Client trắng (Dùng cho test Login, Forgot Password, Public routes)
@pytest.fixture
def client(app):
    return app.test_client()


# 2. Client đã đăng nhập (Dùng cho các test Dashboard, Employee, Salary,...)
@pytest.fixture
def authenticated_client(app):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["username"] = "admin_test"
        sess["role"] = "Admin"
    return client


# 3. Mock Database tổng quát (Mock ngay tại gốc database.py)
@pytest.fixture
def mock_db():
    with patch("database.get_connection") as mock_conn:
        conn_obj = MagicMock()
        cursor_obj = MagicMock()

        mock_conn.return_value = conn_obj
        conn_obj.cursor.return_value = cursor_obj

        yield cursor_obj, conn_obj