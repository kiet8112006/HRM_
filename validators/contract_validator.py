import re
from exceptions.validator.contract import ContractValidationError
from datetime import datetime
# =====================================================================
# 1. HÀM CHECKER & NORMALIZER
# =====================================================================

def normalize_contract_number(contract_number):
    if not contract_number:
        return ""
    return contract_number.strip().upper()

def is_valid_contract_number(contract_number):
    if not contract_number:
        return False
    pattern = r"^[A-Z0-9/-]{3,30}$"
    return bool(re.fullmatch(pattern, contract_number.strip()))

def normalize_work_location(location):
    if not location:
        return ""
    return " ".join(location.split())

def normalize_signer(signer):
    if not signer:
        return ""
    return " ".join(signer.split()).title()

def is_valid_signer(signer):
    if not signer:
        return False
    pattern = r"^([A-ZÀ-Ỹ][a-zà-ỹ]*)(\s[A-ZÀ-Ỹ][a-zà-ỹ]*)+$"
    return bool(re.fullmatch(pattern, signer.strip()))


# =====================================================================
# 2. HÀM VALIDATE (RAISE EXCEPTION)
# =====================================================================

def validate_contract_code(code):
    if not code:
        raise ContractValidationError('Mã hợp đồng không được để trống!')
    if len(code.strip()) > 50:
        raise ContractValidationError('Mã hợp đồng tối đa 50 ký tự!')

def validate_contract_number(number):
    if not number:
        raise ContractValidationError('Số hợp đồng không được để trống!')
    if not is_valid_contract_number(number):
        raise ContractValidationError('Số hợp đồng không hợp lệ (Chỉ gồm ký tự chữ, số, gạch ngang/chéo, độ dài 3-30)!')

def validate_basic_salary(salary_str):
    try:
        salary = float(salary_str)
        if salary < 0:
            raise ContractValidationError('Lương cơ bản phải lớn hơn hoặc bằng 0!')
        return salary
    except (ValueError, TypeError):
        raise ContractValidationError('Lương cơ bản phải là một số hợp lệ!')

def validate_probation_months(months_str):
    if not months_str:
        return 0
    try:
        months = int(months_str)
        if months < 0 or months > 12:
            raise ContractValidationError('Số tháng thử việc phải từ 0 đến 12 tháng!')
        return months
    except (ValueError, TypeError):
        raise ContractValidationError('Số tháng thử việc phải là số nguyên!')

def validate_work_location(location):
    if location and len(location.strip()) > 100:
        raise ContractValidationError('Địa điểm làm việc tối đa 100 ký tự!')

def validate_signer(signer):
    if signer and not is_valid_signer(signer):
        raise ContractValidationError('Tên người ký không hợp lệ (Viết hoa chữ cái đầu mỗi từ)!')

def validate_contract_description(description):
    if description and len(description.strip()) > 255:
        raise ContractValidationError('Mô tả hợp đồng tối đa 255 ký tự!')

def validate_contract_dates(start_date_str, end_date_str):
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ContractValidationError('Ngày bắt đầu không hợp lệ!')

    end_date = None
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            raise ContractValidationError('Ngày kết thúc không hợp lệ!')

        if end_date < start_date:
            raise ContractValidationError('Ngày kết thúc hợp đồng không được nhỏ hơn ngày bắt đầu!')

    return start_date, end_date