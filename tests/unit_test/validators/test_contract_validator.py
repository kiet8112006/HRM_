import pytest
from datetime import date
from exceptions.validator.contract import ContractValidationError

# Import các hàm từ module validator (chỉnh đường dẫn import nếu cần)
from validators.contract_validator import (
    normalize_contract_number,
    is_valid_contract_number,
    normalize_work_location,
    normalize_signer,
    is_valid_signer,
    validate_contract_code,
    validate_contract_number,
    validate_basic_salary,
    validate_probation_months,
    validate_work_location,
    validate_signer,
    validate_contract_description,
    validate_contract_dates
)


# =====================================================================
# 1. TEST HÀM CHECKER & NORMALIZER
# =====================================================================

class TestContractCheckerAndNormalizer:

    # --- Contract Number ---
    def test_normalize_contract_number(self):
        assert normalize_contract_number("  hd-2026/001  ") == "HD-2026/001"
        assert normalize_contract_number("") == ""
        assert normalize_contract_number(None) == ""

    def test_is_valid_contract_number(self):
        assert is_valid_contract_number("HD-001/2026") is True
        assert is_valid_contract_number("CONTRACT/123") is True
        assert is_valid_contract_number("123") is True              # 3 ký tự
        assert is_valid_contract_number("HD") is False               # Nhỏ hơn 3 ký tự
        assert is_valid_contract_number("A" * 31) is False           # Lớn hơn 30 ký tự
        assert is_valid_contract_number("HD-001@2026") is False     # Chứa ký tự đặc biệt không cho phép (@)
        assert is_valid_contract_number("") is False
        assert is_valid_contract_number(None) is False

    # --- Work Location & Signer ---
    def test_normalize_work_location(self):
        assert normalize_work_location("   Tầng   5,  Tòa nhà  A  ") == "Tầng 5, Tòa nhà A"
        assert normalize_work_location("") == ""
        assert normalize_work_location(None) == ""

    def test_normalize_signer(self):
        assert normalize_signer("   nguyễn   văn   a  ") == "Nguyễn Văn A"
        assert normalize_signer("") == ""
        assert normalize_signer(None) == ""

    def test_is_valid_signer(self):
        assert is_valid_signer("Nguyễn Văn A") is True
        assert is_valid_signer("nguyễn văn a") is False  # Không viết hoa đầu từ
        assert is_valid_signer("Nguyễn") is False        # Chỉ có 1 từ
        assert is_valid_signer("") is False
        assert is_valid_signer(None) is False


# =====================================================================
# 2. TEST HÀM VALIDATE (RAISE EXCEPTION)
# =====================================================================

class TestContractValidatorsWithExceptions:

    # --- Validate Code ---
    def test_validate_contract_code_success(self):
        validate_contract_code("HD_LABOR_001")

    def test_validate_contract_code_empty(self):
        with pytest.raises(ContractValidationError, match="Mã hợp đồng không được để trống!"):
            validate_contract_code("")

    def test_validate_contract_code_too_long(self):
        long_code = "C" * 51
        with pytest.raises(ContractValidationError, match="Mã hợp đồng tối đa 50 ký tự!"):
            validate_contract_code(long_code)

    # --- Validate Contract Number ---
    def test_validate_contract_number_success(self):
        validate_contract_number("HD-2026/ABC")

    def test_validate_contract_number_empty(self):
        with pytest.raises(ContractValidationError, match="Số hợp đồng không được để trống!"):
            validate_contract_number("")

    def test_validate_contract_number_invalid(self):
        with pytest.raises(ContractValidationError, match="Số hợp đồng không hợp lệ"):
            validate_contract_number("HD#01")

    # --- Validate Basic Salary ---
    def test_validate_basic_salary_success(self):
        assert validate_basic_salary("15000000") == 15000000.0
        assert validate_basic_salary(0) == 0.0

    def test_validate_basic_salary_invalid_type(self):
        with pytest.raises(ContractValidationError, match="Lương cơ bản phải là một số hợp lệ!"):
            validate_basic_salary("abc")

    def test_validate_basic_salary_negative(self):
        with pytest.raises(ContractValidationError, match="Lương cơ bản phải lớn hơn hoặc bằng 0!"):
            validate_basic_salary("-1000")

    # --- Validate Probation Months ---
    def test_validate_probation_months_success(self):
        assert validate_probation_months("") == 0
        assert validate_probation_months(None) == 0
        assert validate_probation_months("2") == 2
        assert validate_probation_months(6) == 6

    def test_validate_probation_months_invalid_type(self):
        with pytest.raises(ContractValidationError, match="Số tháng thử việc phải là số nguyên!"):
            validate_probation_months("abc")

    def test_validate_probation_months_out_of_range(self):
        with pytest.raises(ContractValidationError, match="Số tháng thử việc phải từ 0 đến 12 tháng!"):
            validate_probation_months("-1")

        with pytest.raises(ContractValidationError, match="Số tháng thử việc phải từ 0 đến 12 tháng!"):
            validate_probation_months("13")

    # --- Validate Work Location ---
    def test_validate_work_location_success(self):
        validate_work_location(None)
        validate_work_location("Trụ sở chính")

    def test_validate_work_location_too_long(self):
        long_loc = "L" * 101
        with pytest.raises(ContractValidationError, match="Địa điểm làm việc tối đa 100 ký tự!"):
            validate_work_location(long_loc)

    # --- Validate Signer ---
    def test_validate_signer_success(self):
        validate_signer(None)
        validate_signer("")
        validate_signer("Trần Văn B")

    def test_validate_signer_invalid(self):
        with pytest.raises(ContractValidationError, match="Tên người ký không hợp lệ"):
            validate_signer("trần văn b")

    # --- Validate Contract Description ---
    def test_validate_contract_description_success(self):
        validate_contract_description(None)
        validate_contract_description("Hợp đồng lao động xác định thời hạn 1 năm.")

    def test_validate_contract_description_too_long(self):
        long_desc = "D" * 256
        with pytest.raises(ContractValidationError, match="Mô tả hợp đồng tối đa 255 ký tự!"):
            validate_contract_description(long_desc)

    # --- Validate Contract Dates ---
    def test_validate_contract_dates_success(self):
        # Hợp đồng xác định thời hạn
        start, end = validate_contract_dates("2026-01-01", "2026-12-31")
        assert start == date(2026, 1, 1)
        assert end == date(2026, 12, 31)

        # Hợp đồng không xác định thời hạn (end_date là None/rỗng)
        start_unlimited, end_unlimited = validate_contract_dates("2026-01-01", "")
        assert start_unlimited == date(2026, 1, 1)
        assert end_unlimited is None

    def test_validate_contract_dates_invalid_start_format(self):
        with pytest.raises(ContractValidationError, match="Ngày bắt đầu không hợp lệ!"):
            validate_contract_dates("01-01-2026", "2026-12-31")

    def test_validate_contract_dates_invalid_end_format(self):
        with pytest.raises(ContractValidationError, match="Ngày kết thúc không hợp lệ!"):
            validate_contract_dates("2026-01-01", "2026/12/31")

    def test_validate_contract_dates_end_before_start(self):
        with pytest.raises(ContractValidationError, match="Ngày kết thúc hợp đồng không được nhỏ hơn ngày bắt đầu!"):
            validate_contract_dates("2026-06-01", "2026-01-01")