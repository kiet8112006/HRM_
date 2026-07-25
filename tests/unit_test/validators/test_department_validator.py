import pytest
from exceptions.validator.department import DepartmentValidationError

# Import các hàm từ module validator của cậu (chỉnh lại đường dẫn nếu cần)
from validators.department_validator import (
    is_valid_department_code,
    normalize_department_code,
    is_valid_department_name,
    normalize_department_name,
    validate_department_code,
    validate_department_name,
    validate_description,
    validate_location,
    validate_status
)


# =====================================================================
# 1. TEST HÀM CHECKER & NORMALIZER
# =====================================================================

class TestDepartmentCheckerAndNormalizer:

    # --- Test Code ---
    def test_is_valid_department_code(self):
        assert is_valid_department_code("IT") is True
        assert is_valid_department_code("HRM") is True
        assert is_valid_department_code("MARKETING") is True  # 9 ký tự
        assert is_valid_department_code("it") is False        # Không in hoa
        assert is_valid_department_code("A") is False         # Ít hơn 2 ký tự
        assert is_valid_department_code("VERYLONGDEPARTMENTCODE") is False # Dài quá 10 ký tự
        assert is_valid_department_code("IT_01") is False     # Chứa ký tự đặc biệt
        assert is_valid_department_code("") is False

    def test_normalize_department_code(self):
        assert normalize_department_code("  it  ") == "IT"
        assert normalize_department_code("hrm") == "HRM"
        assert normalize_department_code(None) == ""

    # --- Test Name ---
    def test_is_valid_department_name(self):
        assert is_valid_department_name("Phòng Công Nghệ Thông Tin") is True
        assert is_valid_department_name("Phòng IT 01") is True
        assert is_valid_department_name("Phòng @IT") is False  # Chứa ký tự đặc biệt @
        assert is_valid_department_name("") is False

    def test_normalize_department_name(self):
        assert normalize_department_name("   phòng   công   nghệ  ") == "Phòng Công Nghệ"
        assert normalize_department_name(None) == ""


# =====================================================================
# 2. TEST HÀM VALIDATE (RAISE EXCEPTION)
# =====================================================================

class TestDepartmentValidatorsWithExceptions:

    # --- Validate Code ---
    def test_validate_department_code_success(self):
        validate_department_code("IT")
        validate_department_code("MARKETING")

    def test_validate_department_code_empty(self):
        with pytest.raises(DepartmentValidationError, match="Mã phòng ban không được để trống!"):
            validate_department_code("")

    def test_validate_department_code_invalid(self):
        with pytest.raises(DepartmentValidationError, match="Mã phòng ban chỉ được gồm 2-10 chữ in hoa"):
            validate_department_code("it_invalid")

    # --- Validate Name ---
    def test_validate_department_name_success(self):
        validate_department_name("Phòng Nhân Sự")

    def test_validate_department_name_empty(self):
        with pytest.raises(DepartmentValidationError, match="Tên phòng ban không được để trống!"):
            validate_department_name("")

    def test_validate_department_name_too_short(self):
        with pytest.raises(DepartmentValidationError, match="Tên phòng ban phải có ít nhất 3 ký tự!"):
            validate_department_name("IT")

    def test_validate_department_name_too_long(self):
        long_name = "Phòng " + "A" * 100
        with pytest.raises(DepartmentValidationError, match="Tên phòng ban tối đa 100 ký tự!"):
            validate_department_name(long_name)

    def test_validate_department_name_invalid_chars(self):
        with pytest.raises(DepartmentValidationError, match="Tên phòng ban không hợp lệ!"):
            validate_department_name("Phòng Nhân Sự #1")

    # --- Validate Description ---
    def test_validate_description_success(self):
        validate_description(None)
        validate_description("")
        validate_description("Mô tả hợp lệ cho phòng ban")

    def test_validate_description_too_long(self):
        long_desc = "D" * 256
        with pytest.raises(DepartmentValidationError, match="Mô tả tối đa 255 ký tự!"):
            validate_description(long_desc)

    # --- Validate Location ---
    def test_validate_location_success(self):
        validate_location(None)
        validate_location("Tầng 5, Tòa nhà A")

    def test_validate_location_too_long(self):
        long_location = "L" * 101
        with pytest.raises(DepartmentValidationError, match="Địa điểm tối đa 100 ký tự!"):
            validate_location(long_location)

    # --- Validate Status ---
    def test_validate_status_success(self):
        validate_status("Active")
        validate_status("Inactive")

    def test_validate_status_invalid(self):
        with pytest.raises(DepartmentValidationError, match="Trạng thái không hợp lệ!"):
            validate_status("Pending")