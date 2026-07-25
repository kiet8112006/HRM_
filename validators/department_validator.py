import re
from exceptions.validator.department import DepartmentValidationError

# =====================================================================
# 1. HÀM CHECKER & NORMALIZER
# =====================================================================

def is_valid_department_code(code):
    if not code:
        return False
    pattern = r"^[A-Z]{2,10}$"
    return bool(re.fullmatch(pattern, code.strip()))

def normalize_department_code(code):
    if not code:
        return ""
    return code.strip().upper()

def is_valid_department_name(name):
    if not name:
        return False
    pattern = r"^[A-Za-zÀ-Ỹà-ỹ0-9\s]+$"
    return bool(re.fullmatch(pattern, name.strip()))

def normalize_department_name(name):
    if not name:
        return ""
    return " ".join(name.split()).title()

# =====================================================================
# 2. HÀM VALIDATE (RAISE EXCEPTION)
# =====================================================================

def validate_department_code(code):
    if not code:
        raise DepartmentValidationError('Mã phòng ban không được để trống!')
    if not is_valid_department_code(code):
        raise DepartmentValidationError('Mã phòng ban chỉ được gồm 2-10 chữ in hoa. Ví dụ: IT, HR, SALE')

def validate_department_name(name):
    if not name:
        raise DepartmentValidationError('Tên phòng ban không được để trống!')
    if len(name) < 3:
        raise DepartmentValidationError('Tên phòng ban phải có ít nhất 3 ký tự!')
    if len(name) > 100:
        raise DepartmentValidationError('Tên phòng ban tối đa 100 ký tự!')
    if not is_valid_department_name(name):
        raise DepartmentValidationError('Tên phòng ban không hợp lệ!')

def validate_description(description):
    if description and len(description) > 255:
        raise DepartmentValidationError('Mô tả tối đa 255 ký tự!')

def validate_location(location):
    if location and len(location) > 100:
        raise DepartmentValidationError('Địa điểm tối đa 100 ký tự!')

def validate_status(status):
    if status not in ['Active', 'Inactive']:
        raise DepartmentValidationError('Trạng thái không hợp lệ!')