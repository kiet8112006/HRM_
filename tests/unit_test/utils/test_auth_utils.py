import pytest
from unittest.mock import patch
from flask import session, url_for
from werkzeug.security import generate_password_hash

# Import các hàm và decorator từ module của cậu (chỉnh lại đường dẫn import nếu cần)
from utils.auth import (
    hash_password,
    verify_password,
    login_required,
    role_required
)


# =====================================================================
# 1. TEST HÀM HASH VÀ VERIFY PASSWORD
# =====================================================================

class TestPasswordUtils:

    def test_hash_password(self):
        """Kiểm tra hàm băm mật khẩu trả về chuỗi hash hợp lệ"""
        raw_password = "MySecurePassword123"
        hashed = hash_password(raw_password)

        assert hashed != raw_password
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_verify_password_hashed_success(self):
        """Xác thực thành công với mật khẩu đã băm (Werkzeug hash)"""
        raw_password = "SecretPassword"
        hashed = generate_password_hash(raw_password)

        assert verify_password(raw_password, hashed) is True

    def test_verify_password_plaintext_fallback(self):
        """Xác thực thành công khi DB lưu chuỗi thuần (chưa băm)"""
        raw_password = "PlainPassword123"
        db_password = "PlainPassword123"  # Mật khẩu chưa băm trong DB

        assert verify_password(raw_password, db_password) is True

    def test_verify_password_incorrect(self):
        """Xác thực thất bại khi nhập sai mật khẩu"""
        raw_password = "WrongPassword"
        hashed = generate_password_hash("CorrectPassword")

        assert verify_password(raw_password, hashed) is False

    def test_verify_password_empty_or_none(self):
        """Trường hợp dữ liệu đầu vào rỗng hoặc None -> Trả về False"""
        assert verify_password("", "hashed_str") is False
        assert verify_password("plain_str", None) is False
        assert verify_password(None, None) is False

    def test_verify_password_exception_handling(self):
        """Trường hợp Werkzeug tung lỗi ngoại lệ -> Bắt exception và trả về False"""
        with patch("utils.auth.check_password_hash", side_effect=Exception("Invalid hash format")):
            # Băm chuỗi giả lập gây lỗi
            assert verify_password("password", "invalid_hash_string") is False


# =====================================================================
# 2. TEST DECORATORS (login_required & role_required)
# =====================================================================

class TestAuthDecorators:

    # --- Test login_required ---
    def test_login_required_unauthenticated(self, app):
        """Người dùng CHƯA đăng nhập -> Bị chuyển hướng về auth.login + Flash warning"""

        @login_required
        def dummy_view():
            return "OK", 200

        with app.test_request_context('/protected'):
            response = dummy_view()

            # Kiểm tra chuyển hướng về trang login
            assert response.status_code == 302
            assert response.location == url_for("auth.login")

            # Kiểm tra Flash message
            assert ("warning", "Vui lòng đăng nhập để tiếp tục.") in session['_flashes']

    def test_login_required_authenticated(self, app):
        """Người dùng ĐÃ đăng nhập -> Cho phép truy cập view"""

        @login_required
        def dummy_view():
            return "SUCCESS", 200

        with app.test_request_context('/protected'):
            session['user_id'] = 1  # Giả lập đã đăng nhập

            response, status_code = dummy_view()
            assert status_code == 200
            assert response == "SUCCESS"

    # --- Test role_required ---
    def test_role_required_unauthenticated(self, app):
        """Chưa đăng nhập -> Chuyển hướng về auth.login"""

        @role_required("Admin", "Manager")
        def admin_view():
            return "ADMIN_PAGE", 200

        with app.test_request_context('/admin'):
            response = admin_view()

            assert response.status_code == 302
            assert response.location == url_for("auth.login")
            assert ("warning", "Vui lòng đăng nhập để tiếp tục.") in session['_flashes']

    def test_role_required_unauthorized_role(self, app):
        """Đã đăng nhập nhưng SAI quyền -> Chuyển hướng về dashboard.home + Flash danger"""

        @role_required("Admin")
        def admin_view():
            return "ADMIN_PAGE", 200

        with app.test_request_context('/admin'):
            session['user_id'] = 2
            session['role'] = 'Employee'  # Quyền Nhân viên (Không có quyền Admin)

            response = admin_view()

            assert response.status_code == 302
            assert response.location == url_for("dashboard.home")
            assert ("danger", "Bạn không có quyền truy cập chức năng này.") in session['_flashes']

    def test_role_required_authorized_role(self, app):
        """Đã đăng nhập và ĐÚNG quyền -> Cho phép truy cập"""

        @role_required("Admin", "HR")
        def hr_view():
            return "HR_PAGE", 200

        with app.test_request_context('/hr'):
            session['user_id'] = 3
            session['role'] = 'HR'  # Quyền hợp lệ

            response, status_code = hr_view()
            assert status_code == 200
            assert response == "HR_PAGE"