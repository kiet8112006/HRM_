import pytest

# Import các hàm từ module validator (chỉnh đường dẫn import nếu cần)
from validators.auth_validator import (
    validate_username,
    validate_password,
    validate_confirm_password,
    validate_old_password,
    validate_new_password
)


# =====================================================================
# 1. TEST VALIDATE USERNAME
# =====================================================================

class TestValidateUsername:

    def test_validate_username_success(self):
        """Username hợp lệ (>= 4 ký tự sau khi strip)"""
        assert validate_username("admin") is None
        assert validate_username("   user123   ") is None

    def test_validate_username_empty(self):
        """Username rỗng hoặc chỉ chứa khoảng trắng"""
        assert validate_username("") == "Tên đăng nhập không được để trống."
        assert validate_username("   ") == "Tên đăng nhập không được để trống."

    def test_validate_username_too_short(self):
        """Username dưới 4 ký tự"""
        assert validate_username("abc") == "Tên đăng nhập phải có ít nhất 4 ký tự."
        assert validate_username("  a  ") == "Tên đăng nhập phải có ít nhất 4 ký tự."


# =====================================================================
# 2. TEST VALIDATE PASSWORD
# =====================================================================

class TestValidatePassword:

    def test_validate_password_success(self):
        """Mật khẩu hợp lệ (>= 6 ký tự)"""
        assert validate_password("123456") is None
        assert validate_password("secure_pass_123") is None

    def test_validate_password_empty(self):
        """Mật khẩu rỗng"""
        assert validate_password("") == "Mật khẩu không được để trống."

    def test_validate_password_too_short(self):
        """Mật khẩu dưới 6 ký tự"""
        assert validate_password("12345") == "Mật khẩu phải từ 6 ký tự."


# =====================================================================
# 3. TEST VALIDATE CONFIRM PASSWORD
# =====================================================================

class TestValidateConfirmPassword:

    def test_validate_confirm_password_success(self):
        """Xác nhận mật khẩu trùng khớp với mật khẩu gốc"""
        assert validate_confirm_password("Password123", "Password123") is None

    def test_validate_confirm_password_empty(self):
        """Xác nhận mật khẩu rỗng"""
        assert validate_confirm_password("Password123", "") == "Xác nhận mật khẩu không được để trống."

    def test_validate_confirm_password_mismatch(self):
        """Xác nhận mật khẩu không trùng khớp"""
        assert validate_confirm_password("Password123", "Password456") == "Xác nhận mật khẩu không khớp."


# =====================================================================
# 4. TEST VALIDATE OLD PASSWORD
# =====================================================================

class TestValidateOldPassword:

    def test_validate_old_password_success(self):
        """Mật khẩu hiện tại hợp lệ"""
        assert validate_old_password("old_pass123") is None

    def test_validate_old_password_empty(self):
        """Mật khẩu hiện tại rỗng"""
        assert validate_old_password("") == "Mật khẩu hiện tại không được để trống."


# =====================================================================
# 5. TEST VALIDATE NEW PASSWORD
# =====================================================================

class TestValidateNewPassword:

    def test_validate_new_password_success(self):
        """Mật khẩu mới hợp lệ (>= 6 ký tự)"""
        assert validate_new_password("new_pass123") is None

    def test_validate_new_password_empty(self):
        """Mật khẩu mới rỗng"""
        assert validate_new_password("") == "Mật khẩu mới không được để trống."

    def test_validate_new_password_too_short(self):
        """Mật khẩu mới dưới 6 ký tự"""
        assert validate_new_password("12345") == "Mật khẩu mới phải có ít nhất 6 ký tự."