import pytest
from exceptions.validator.position import PositionValidationError

# Import các hàm từ module validator của cậu (chỉnh lại đường dẫn import nếu cần)
from validators.position_validator import (
    normalize_position_code,
    is_valid_position_code,
    normalize_position_name,
    is_valid_position_name,
    validate_position_code,
    validate_position_name,
    validate_position_level,
    validate_salary_range,
    validate_position_status,
    validate_position_description
)


# =====================================================================
# 1. TEST HÀM CHECKER & NORMALIZER
# =====================================================================

class TestPositionCheckerAndNormalizer:

    # --- Test Position Code ---
    def test_normalize_position_code(self):
        assert normalize_position_code("  dev01  ") == "DEV01"
        assert normalize_position_code("pm") == "PM"
        assert normalize_position_code(None) == ""

    def test_is_valid_position_code(self):
        assert is_valid_position_code("DEV") is True
        assert is_valid_position_code("DEV01") is True
        assert is_valid_position_code("MANAGER12") is True # 9 ký tự
        assert is_valid_position_code("dev") is False       # Chữ thường
        assert is_valid_position_code("D") is False         # Nhỏ hơn 2 ký tự
        assert is_valid_position_code("LONGPOSITIONCODE") is False # Dài hơn 10 ký tự
        assert is_valid_position_code("DEV-01") is False    # Chứa ký tự đặc biệt
        assert is_valid_position_code("") is False
        assert is_valid_position_code(None) is False

    # --- Test Position Name ---
    def test_normalize_position_name(self):
        assert normalize_position_name("   lập   trình   viên  ") == "Lập Trình Viên"
        assert normalize_position_name(None) == ""

    def test_is_valid_position_name(self):
        assert is_valid_position_name("Trưởng Phòng IT") is True
        assert is_valid_position_name("Lập trình viên Senior 01") is True
        assert is_valid_position_name("Senior Developer @") is False # Ký tự đặc biệt
        assert is_valid_position_name("") is False
        assert is_valid_position_name(None) is False


# =====================================================================
# 2. TEST HÀM VALIDATE (RAISE EXCEPTION)
# =====================================================================

class TestPositionValidatorsWithExceptions:

    # --- Test Code ---
    def test_validate_position_code_success(self):
        validate_position_code("PM01")

    def test_validate_position_code_empty(self):
        with pytest.raises(PositionValidationError, match="Mã chức vụ không được để trống!"):
            validate_position_code("")

    def test_validate_position_code_invalid(self):
        with pytest.raises(PositionValidationError, match="Mã chức vụ không hợp lệ!"):
            validate_position_code("pm_invalid")

    # --- Test Name ---
    def test_validate_position_name_success(self):
        validate_position_name("Quản Lý Dự Án")

    def test_validate_position_name_empty(self):
        with pytest.raises(PositionValidationError, match="Tên chức vụ không được để trống!"):
            validate_position_name("")

    def test_validate_position_name_invalid(self):
        with pytest.raises(PositionValidationError, match="Tên chức vụ không hợp lệ!"):
            validate_position_name("Dev #1")

    # --- Test Level ---
    def test_validate_position_level_success(self):
        assert validate_position_level("1") == 1
        assert validate_position_level("20") == 20
        assert validate_position_level(5) == 5

    def test_validate_position_level_invalid_type(self):
        with pytest.raises(PositionValidationError, match="Level cấp bậc phải là một số nguyên hợp lệ!"):
            validate_position_level("abc")

    def test_validate_position_level_out_of_range(self):
        with pytest.raises(PositionValidationError, match="Level cấp bậc phải nằm trong khoảng từ 1 đến 20!"):
            validate_position_level("0")

        with pytest.raises(PositionValidationError, match="Level cấp bậc phải nằm trong khoảng từ 1 đến 20!"):
            validate_position_level("21")

    # --- Test Salary Range ---
    def test_validate_salary_range_success(self):
        min_sal, max_sal = validate_salary_range("10000000", "20000000")
        assert min_sal == 10000000.0
        assert max_sal == 20000000.0

    def test_validate_salary_range_invalid_min_type(self):
        with pytest.raises(PositionValidationError, match="Lương tối thiểu phải là một số hợp lệ!"):
            validate_salary_range("invalid", "20000000")

    def test_validate_salary_range_invalid_max_type(self):
        with pytest.raises(PositionValidationError, match="Lương tối đa phải là một số hợp lệ!"):
            validate_salary_range("10000000", "invalid")

    def test_validate_salary_range_negative_min(self):
        with pytest.raises(PositionValidationError, match="Lương tối thiểu phải lớn hơn hoặc bằng 0!"):
            validate_salary_range("-5000000", "10000000")

    def test_validate_salary_range_negative_max(self):
        with pytest.raises(PositionValidationError, match="Lương tối đa phải lớn hơn hoặc bằng 0!"):
            validate_salary_range("0", "-1000000")

    def test_validate_salary_range_min_greater_than_max(self):
        with pytest.raises(PositionValidationError, match="Lương tối thiểu không được lớn hơn lương tối đa!"):
            validate_salary_range("30000000", "20000000")

    # --- Test Status ---
    def test_validate_position_status_success(self):
        validate_position_status("Hoạt động")
        validate_position_status("Ngừng hoạt động")

    def test_validate_position_status_invalid(self):
        with pytest.raises(PositionValidationError, match="Trạng thái không hợp lệ!"):
            validate_position_status("Active")  # Phải là tiếng Việt chuẩn như trong validator

    # --- Test Description ---
    def test_validate_position_description_success(self):
        validate_position_description(None)
        validate_position_description("")
        validate_position_description("Mô tả công việc quản lý dự án.")

    def test_validate_position_description_too_long(self):
        long_desc = "D" * 256
        with pytest.raises(PositionValidationError, match="Mô tả tối đa 255 ký tự!"):
            validate_position_description(long_desc)