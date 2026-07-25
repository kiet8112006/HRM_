from datetime import datetime
from exceptions.validator.salary import SalaryValidationError

ALLOWED_SALARY_STATUSES = ['Chưa thanh toán', 'Đã thanh toán']

# =====================================================================
# 1. HÀM TÍNH TOÁN & CHUẨN HÓA DỮ LIỆU
# =====================================================================
def calculate_net_salary(base_salary, bonus, allowance, overtime_pay, deduction, tax, insurance):
    """Tính lương thực nhận (Net Salary)."""
    return (base_salary + bonus + allowance + overtime_pay) - (deduction + tax + insurance)


# =====================================================================
# 2. HÀM VALIDATE (RAISE SALARY_VALIDATION_ERROR)
# =====================================================================
def validate_salary_components(base_salary, bonus, allowance, overtime_pay, deduction, tax, insurance):
    """Validate các khoản lương và số tiền."""
    if base_salary <= 0:
        raise SalaryValidationError('Lương cơ bản phải lớn hơn 0!')
    
    if any(val < 0 for val in [bonus, allowance, overtime_pay, deduction, tax, insurance]):
        raise SalaryValidationError('Các khoản tiền thưởng, phụ cấp, khấu trừ, thuế không được âm!')

    net_salary = calculate_net_salary(base_salary, bonus, allowance, overtime_pay, deduction, tax, insurance)
    if net_salary < 0:
        raise SalaryValidationError('Lương thực nhận không được nhỏ hơn 0!')
    
    return net_salary

def validate_month_year(month, year):
    """Validate tháng và năm tính lương."""
    if month < 1 or month > 12:
        raise SalaryValidationError('Tháng phải từ 1 đến 12!')
    if year < 2020 or year > 2100:
        raise SalaryValidationError('Năm không hợp lệ (từ 2020 đến 2100)!')

def validate_payment_date(payment_date):
    """Validate ngày thanh toán lương."""
    today = datetime.today().date()
    if payment_date > today:
        raise SalaryValidationError('Ngày trả lương không được lớn hơn ngày hiện tại!')

def validate_salary_status(status):
    """Validate trạng thái thanh toán."""
    if status not in ALLOWED_SALARY_STATUSES:
        raise SalaryValidationError('Trạng thái thanh toán không hợp lệ!')