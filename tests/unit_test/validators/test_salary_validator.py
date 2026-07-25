import pytest
from datetime import datetime, timedelta
from exceptions.validator.salary import SalaryValidationError

# Import các hàm và hằng số từ module validator (chỉnh lại đường dẫn nếu cần)
from validators.salary_validator import (
    ALLOWED_SALARY_STATUSES,
    calculate_net_salary,
    validate_salary_components,
    validate_month_year,
    validate_payment_date,
    validate_salary_status
)


# =====================================================================
# 1. TEST HÀM TÍNH TOÁN & CHUẨN HÓA DỮ LIỆU
# =====================================================================

class TestSalaryCalculation:

    def test_calculate_net_salary(self):
        """Kiểm tra công thức: Net = (Base + Bonus + Allowance + Overtime) - (Deduction + Tax + Insurance)"""
        # (10m + 2m + 1m + 500k) - (500k + 1m + 1m) = 13.5m - 2.5m = 11m
        net = calculate_net_salary(
            base_salary=10000000,
            bonus=2000000,
            allowance=1000000,
            overtime_pay=500000,
            deduction=500000,
            tax=1000000,
            insurance=1000000
        )
        assert net == 11000000.0


# =====================================================================
# 2. TEST HÀM VALIDATE (RAISE EXCEPTION)
# =====================================================================

class TestSalaryValidatorsWithExceptions:

    # --- Test Salary Components & Net Salary ---
    def test_validate_salary_components_success(self):
        """Validate các thành phần lương thành công và trả về Net Salary chính xác"""
        net = validate_salary_components(
            base_salary=10000000,
            bonus=1000000,
            allowance=500000,
            overtime_pay=0,
            deduction=200000,
            tax=500000,
            insurance=800000
        )
        assert net == 10000000 + 1000000 + 500000 - (200000 + 500000 + 800000)

    def test_validate_salary_components_base_salary_zero_or_negative(self):
        """Lương cơ bản <= 0 -> Raise Exception"""
        with pytest.raises(SalaryValidationError, match="Lương cơ bản phải lớn hơn 0!"):
            validate_salary_components(0, 0, 0, 0, 0, 0, 0)

        with pytest.raises(SalaryValidationError, match="Lương cơ bản phải lớn hơn 0!"):
            validate_salary_components(-5000000, 0, 0, 0, 0, 0, 0)

    def test_validate_salary_components_negative_values(self):
        """Khoản phụ/khấu trừ/thuế bị âm -> Raise Exception"""
        # Bonus âm
        with pytest.raises(SalaryValidationError, match="Các khoản tiền thưởng, phụ cấp, khấu trừ, thuế không được âm!"):
            validate_salary_components(10000000, -100000, 0, 0, 0, 0, 0)

        # Tax âm
        with pytest.raises(SalaryValidationError, match="Các khoản tiền thưởng, phụ cấp, khấu trừ, thuế không được âm!"):
            validate_salary_components(10000000, 0, 0, 0, 0, -500000, 0)

    def test_validate_salary_components_net_salary_negative(self):
        """Khấu trừ + Thuế lớn hơn tổng thu nhập dẫn đến Net Salary < 0 -> Raise Exception"""
        with pytest.raises(SalaryValidationError, match="Lương thực nhận không được nhỏ hơn 0!"):
            validate_salary_components(
                base_salary=5000000,
                bonus=0,
                allowance=0,
                overtime_pay=0,
                deduction=6000000, # Khấu trừ lớn hơn lương cơ bản
                tax=0,
                insurance=0
            )

    # --- Test Month & Year ---
    def test_validate_month_year_success(self):
        """Tháng từ 1-12 và năm từ 2020-2100 hợp lệ"""
        validate_month_year(1, 2020)
        validate_month_year(12, 2100)
        validate_month_year(6, 2026)

    def test_validate_month_invalid(self):
        """Tháng < 1 hoặc > 12 -> Raise Exception"""
        with pytest.raises(SalaryValidationError, match="Tháng phải từ 1 đến 12!"):
            validate_month_year(0, 2026)

        with pytest.raises(SalaryValidationError, match="Tháng phải từ 1 đến 12!"):
            validate_month_year(13, 2026)

    def test_validate_year_invalid(self):
        """Năm < 2020 hoặc > 2100 -> Raise Exception"""
        with pytest.raises(SalaryValidationError, match="Năm không hợp lệ"):
            validate_month_year(5, 2019)

        with pytest.raises(SalaryValidationError, match="Năm không hợp lệ"):
            validate_month_year(5, 2101)

    # --- Test Payment Date ---
    def test_validate_payment_date_success(self):
        """Ngày trả lương bằng hoặc nhỏ hơn hôm nay hợp lệ"""
        today = datetime.today().date()
        yesterday = today - timedelta(days=1)
        
        validate_payment_date(today)
        validate_payment_date(yesterday)

    def test_validate_payment_date_future(self):
        """Ngày trả lương ở tương lai -> Raise Exception"""
        tomorrow = datetime.today().date() + timedelta(days=1)
        with pytest.raises(SalaryValidationError, match="Ngày trả lương không được lớn hơn ngày hiện tại!"):
            validate_payment_date(tomorrow)

    # --- Test Status ---
    def test_validate_salary_status_success(self):
        """Trạng thái nằm trong ALLOWED_SALARY_STATUSES"""
        for status in ALLOWED_SALARY_STATUSES:
            validate_salary_status(status)

    def test_validate_salary_status_invalid(self):
        """Trạng thái không nằm trong danh sách cho phép -> Raise Exception"""
        with pytest.raises(SalaryValidationError, match="Trạng thái thanh toán không hợp lệ!"):
            validate_salary_status("Đang xử lý")