import re
from exceptions.validator.position import PositionValidationError

# =====================================================================
# 1. HÀM CHECKER & NORMALIZER
# =====================================================================

def normalize_position_code(code):
    if not code:
        return ""
    return code.strip().upper()

def is_valid_position_code(code):
    if not code:
        return False
    pattern = r"^[A-Z0-9]{2,10}$"
    return bool(re.fullmatch(pattern, code.strip()))

def normalize_position_name(name):
    if not name:
        return ""
    return " ".join(name.split()).title()

def is_valid_position_name(name):
    if not name:
        return False
    pattern = r"^[A-Za-zÀ-Ỹà-ỹ0-9\s]+$"
    return bool(re.fullmatch(pattern, name.strip()))


# =====================================================================
# 2. HÀM VALIDATE (RAISE EXCEPTION)
# =====================================================================

def validate_position_code(code):
    if not code:
        raise PositionValidationError('Mã chức vụ không được để trống!')
    if not is_valid_position_code(code):
        raise PositionValidationError('Mã chức vụ không hợp lệ! (Chỉ gồm 2-10 ký tự chữ in hoa hoặc số)')

def validate_position_name(name):
    if not name:
        raise PositionValidationError('Tên chức vụ không được để trống!')
    if not is_valid_position_name(name):
        raise PositionValidationError('Tên chức vụ không hợp lệ!')

def validate_position_level(level_str):
    try:
        level = int(level_str)
        if level < 1 or level > 20:
            raise PositionValidationError('Level cấp bậc phải nằm trong khoảng từ 1 đến 20!')
        return level
    except (ValueError, TypeError):
        raise PositionValidationError('Level cấp bậc phải là một số nguyên hợp lệ!')

def validate_salary_range(min_salary_str, max_salary_str):
    try:
        min_salary = float(min_salary_str)
    except (ValueError, TypeError):
        raise PositionValidationError('Lương tối thiểu phải là một số hợp lệ!')

    try:
        max_salary = float(max_salary_str)
    except (ValueError, TypeError):
        raise PositionValidationError('Lương tối đa phải là một số hợp lệ!')

    if min_salary < 0:
        raise PositionValidationError('Lương tối thiểu phải lớn hơn hoặc bằng 0!')
    if max_salary < 0:
        raise PositionValidationError('Lương tối đa phải lớn hơn hoặc bằng 0!')
    if min_salary > max_salary:
        raise PositionValidationError('Lương tối thiểu không được lớn hơn lương tối đa!')

    return min_salary, max_salary

def validate_position_status(status):
    if status not in ['Hoạt động', 'Ngừng hoạt động']:
        raise PositionValidationError('Trạng thái không hợp lệ!')

def validate_position_description(description):
    if description and len(description.strip()) > 255:
        raise PositionValidationError('Mô tả tối đa 255 ký tự!')