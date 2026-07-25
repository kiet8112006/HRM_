import pytest
from datetime import datetime, timedelta
from exceptions.validator.employee import EmployeeValidationError

# Import các hàm từ module validator của cậu (chỉnh lại đường dẫn import nếu cần)
from validators.employee_validator import (
    is_valid_name, is_valid_phone, is_valid_email, is_valid_citizenid, is_valid_nationality, calculate_age,
    normalize_name, normalize_email, normalize_phone, normalize_address, normalize_nationality, normalize_citizenid,
    validate_name, validate_phone, validate_email, validate_citizenid,
    validate_emergency_contact, validate_emergency_phone, validate_address, validate_nationality,
    validate_dob, validate_hiredate
)


# =====================================================================
# 1. TEST HÀM KIỂM TRA (BOOLEAN CHECKERS)
# =====================================================================

class TestBooleanCheckers:

    def test_is_valid_name(self):
        assert is_valid_name("Nguyễn Văn A") is True
        assert is_valid_name("Trần Thị Bích") is True
        assert is_valid_name("nguyễn văn a") is False  # Không viết hoa chữ cái đầu
        assert is_valid_name("Nguyễn") is False        # Chỉ có 1 từ
        assert is_valid_name("Nguyễn123") is False    # Chứa số
        assert is_valid_name("") is False

    def test_is_valid_phone(self):
        assert is_valid_phone("0987654321") is True
        assert is_valid_phone("0123456789") is True
        assert is_valid_phone("1234567890") is False  # Không bắt đầu bằng 0
        assert is_valid_phone("098765432") is False   # Thiếu số (9 số)
        assert is_valid_phone("09876543210") is False # Thừa số (11 số)
        assert is_valid_phone("098765432a") is False  # Chứa chữ
        assert is_valid_phone(None) is False

    def test_is_valid_email(self):
        assert is_valid_email("user@example.com") is True
        assert is_valid_email("test.user@domain.vn") is True
        assert is_valid_email("user@domain") is False     # Thiếu TLD (.com, .vn)
        assert is_valid_email("userdomain.com") is False  # Thiếu @
        assert is_valid_email(None) is False

    def test_is_valid_citizenid(self):
        assert is_valid_citizenid("012345678901") is True
        assert is_valid_citizenid("12345678901") is False   # 11 số
        assert is_valid_citizenid("1234567890123") is False # 13 số
        assert is_valid_citizenid("01234567890a") is False  # Chứa chữ
        assert is_valid_citizenid(None) is False

    def test_is_valid_nationality(self):
        assert is_valid_nationality("Việt Nam") is True
        assert is_valid_nationality("Koreans") is True
        assert is_valid_nationality("Việt Nam 123") is False # Chứa số
        assert is_valid_nationality(None) is False

    def test_calculate_age(self):
        today = datetime.today().date()
        dob_20 = today.replace(year=today.year - 20)
        assert calculate_age(dob_20) == 20


# =====================================================================
# 2. TEST HÀM CHUẨN HÓA DỮ LIỆU (NORMALIZERS)
# =====================================================================

class TestNormalizers:

    def test_normalize_name(self):
        assert normalize_name("  nguyễn   văn   a  ") == "Nguyễn Văn A"
        assert normalize_name("") == ""

    def test_normalize_email(self):
        assert normalize_email("   User@Example.COM  ") == "user@example.com"
        assert normalize_email(None) == ""

    def test_normalize_phone(self):
        assert normalize_phone("  0987-654-321 ") == "0987654321"
        assert normalize_phone(None) == ""

    def test_normalize_address(self):
        assert normalize_address("   123  Lê   Lợi,   Q1  ") == "123 Lê Lợi, Q1"
        assert normalize_address("") == ""

    def test_normalize_nationality(self):
        assert normalize_nationality("  việt   nam  ") == "Việt Nam"
        assert normalize_nationality(None) == ""

    def test_normalize_citizenid(self):
        assert normalize_citizenid("  012345678901  ") == "012345678901"
        assert normalize_citizenid(None) == ""


# =====================================================================
# 3. TEST HÀM VALIDATE (RAISE EXCEPTION)
# =====================================================================

class TestValidatorsWithExceptions:

    # --- Test Name ---
    def test_validate_name_success(self):
        validate_name("Nguyễn Văn A") # Không nhảy exception là thành công

    def test_validate_name_empty(self):
        with pytest.raises(EmployeeValidationError, match="Họ và tên không được để trống!"):
            validate_name("")

    def test_validate_name_invalid_format(self):
        with pytest.raises(EmployeeValidationError, match="Vui lòng nhập đúng tên theo cú pháp"):
            validate_name("nguyễn văn a")

    # --- Test Phone ---
    def test_validate_phone_success(self):
        validate_phone("0987654321")

    def test_validate_phone_invalid(self):
        with pytest.raises(EmployeeValidationError, match="Số điện thoại phải gồm đúng 10 chữ số"):
            validate_phone("12345")

    # --- Test Email ---
    def test_validate_email_success(self):
        validate_email("test@gmail.com")

    def test_validate_email_empty(self):
        with pytest.raises(EmployeeValidationError, match="Email không được để trống!"):
            validate_email("")

    def test_validate_email_contains_space(self):
        with pytest.raises(EmployeeValidationError, match="Email không được chứa khoảng trắng!"):
            validate_email("user @gmail.com")

    def test_validate_email_invalid_format(self):
        with pytest.raises(EmployeeValidationError, match="Email không hợp lệ!"):
            validate_email("usergmail.com")

    # --- Test CitizenID ---
    def test_validate_citizenid_success(self):
        validate_citizenid("012345678901")

    def test_validate_citizenid_invalid(self):
        with pytest.raises(EmployeeValidationError, match="CCCD phải gồm đúng 12 chữ số!"):
            validate_citizenid("123456789")

    # --- Test Emergency Contact ---
    def test_validate_emergency_contact_success(self):
        validate_emergency_contact("Trần Thị B")

    def test_validate_emergency_contact_empty(self):
        with pytest.raises(EmployeeValidationError, match="Người liên hệ khẩn cấp không được để trống!"):
            validate_emergency_contact("")

    def test_validate_emergency_contact_invalid(self):
        with pytest.raises(EmployeeValidationError, match="Tên người liên hệ khẩn cấp không hợp lệ!"):
            validate_emergency_contact("trần B")

    def test_validate_emergency_phone_invalid(self):
        with pytest.raises(EmployeeValidationError, match="Số điện thoại khẩn cấp không hợp lệ"):
            validate_emergency_phone("0987")

    # --- Test Address & Nationality ---
    def test_validate_address_empty(self):
        with pytest.raises(EmployeeValidationError, match="Địa chỉ không được để trống!"):
            validate_address("")

    def test_validate_address_too_long(self):
        long_address = "A" * 256
        with pytest.raises(EmployeeValidationError, match="Địa chỉ tối đa 255 ký tự!"):
            validate_address(long_address)

    def test_validate_nationality_invalid(self):
        with pytest.raises(EmployeeValidationError, match="Quốc tịch chỉ được chứa chữ cái!"):
            validate_nationality("Việt Nam 123")

    # --- Test Date of Birth & Hire Date ---
    def test_validate_dob_future_date(self):
        future_date = datetime.today().date() + timedelta(days=1)
        with pytest.raises(EmployeeValidationError, match="Ngày sinh không được lớn hơn ngày hiện tại!"):
            validate_dob(future_date)

    def test_validate_dob_under_18(self):
        under_18_date = datetime.today().date() - timedelta(days=365 * 17)
        with pytest.raises(EmployeeValidationError, match="Nhân viên phải đủ 18 tuổi!"):
            validate_dob(under_18_date)

    def test_validate_hiredate_before_dob(self):
        today = datetime.today().date()
        dob = today - timedelta(days=365 * 20)
        hiredate = dob - timedelta(days=10) # Ngày tuyển dụng trước ngày sinh
        with pytest.raises(EmployeeValidationError, match="Ngày tuyển dụng không được nhỏ hơn ngày sinh!"):
            validate_hiredate(dob, hiredate)

    def test_validate_hiredate_future(self):
        today = datetime.today().date()
        dob = today - timedelta(days=365 * 20)
        future_hiredate = today + timedelta(days=1)
        with pytest.raises(EmployeeValidationError, match="Ngày tuyển dụng không được lớn hơn ngày hiện tại!"):
            validate_hiredate(dob, future_hiredate)