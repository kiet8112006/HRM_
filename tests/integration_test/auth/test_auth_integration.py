from unittest.mock import MagicMock, patch
from utils.auth import hash_password
import pytest


# =====================================================================
# 1. INTEGRATION TEST: Luồng Đăng nhập đầy đủ
# =====================================================================
@patch("routes.auth.get_connection")
def test_integration_login_flow_success(mock_get_conn, client):
    raw_password = "MySecurePassword123!"
    real_hashed_password = hash_password(raw_password)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Giả lập DB trả về user hợp lệ
    mock_cursor.fetchone.return_value = (
        10,
        "test_user",
        real_hashed_password,
        "Test User",
        "Manager",
        True,
    )

    response = client.post(
        "/login",
        data={"username": "test_user", "password": raw_password},
        follow_redirects=True,
    )

    # 1. Chuyển hướng thành công về trang chủ "/"
    assert response.status_code == 200
    assert response.request.path == "/"

    # 2. Session lưu đúng thông tin
    with client.session_transaction() as sess:
        assert sess.get("user_id") == 10
        assert sess.get("username") == "test_user"
        assert sess.get("role") == "Manager"

# =====================================================================
# 2. INTEGRATION TEST: Tích hợp Validation
# =====================================================================
def test_integration_login_validation_empty_input(client):
    response = client.post(
        "/login", data={"username": "", "password": ""}, follow_redirects=True
    )

    assert response.request.path == "/login"

    with client.session_transaction() as sess:
        assert "user_id" not in sess


# =====================================================================
# 3. INTEGRATION TEST: Luồng Đổi mật khẩu & Đăng xuất
# =====================================================================
@patch("routes.auth.get_connection")  # Patch trực tiếp tại routes.auth
def test_integration_change_password_and_logout(
    mock_get_conn, authenticated_client
):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    old_password = "OldPassword123!"
    old_hash = hash_password(old_password)
    mock_cursor.fetchone.return_value = (old_hash,)

    # 1. Đổi mật khẩu
    response = authenticated_client.post(
        "/change-password",
        data={
            "old_password": old_password,
            "new_password": "NewPassword456!",
            "confirm_password": "NewPassword456!",
        },
        follow_redirects=True,
    )

    # Đổi thành công sẽ đưa về trang login
    assert response.request.path == "/login"

    with authenticated_client.session_transaction() as sess:
        assert "user_id" not in sess

    # 2. Đăng xuất
    logout_response = authenticated_client.get("/logout", follow_redirects=True)
    assert logout_response.request.path == "/login"