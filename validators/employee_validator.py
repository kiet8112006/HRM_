import re
from datetime import datetime
from exceptions.validator.employee import EmployeeValidationError

# =====================================================================
# 1. HÀM KIỂM TRA (BOOLEAN CHECKERS)
# =====================================================================

def is_valid_name(name):
    """Kiểm tra tên đúng định dạng in hoa chữ cái đầu mỗi từ."""
    if not name:
        return False
    pattern = r"^([A-ZÀ-Ỹ][a-zà-ỹ]*)(\s[A-ZÀ-Ỹ][a-zà-ỹ]*)+$"
    return bool(re.fullmatch(pattern, name.strip()))

def is_valid_phone(phone):
    """Kiểm tra số điện thoại gồm 10 chữ số và bắt đầu bằng 0."""
    if not phone:
        return False
    pattern = r"^0\d{9}$"
    return bool(re.fullmatch(pattern, phone))

def is_valid_email(email):
    """Kiểm tra định dạng email chuẩn."""
    if not email:
        return False
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return bool(re.fullmatch(pattern, email))

def is_valid_citizenid(citizenid):
    """Kiểm tra CCCD gồm đúng 12 chữ số."""
    if not citizenid:
        return False
    pattern = r'^\d{12}$'
    return bool(re.fullmatch(pattern, citizenid))

def is_valid_nationality(nationality):
    """Kiểm tra quốc tịch chỉ chứa chữ cái và khoảng trắng."""
    if not nationality:
        return False
    pattern = r"^[A-Za-zÀ-Ỹà-ỹ\s]+$"
    return bool(re.fullmatch(pattern, nationality.strip()))

def calculate_age(dob):
    """Tính tuổi từ ngày sinh."""
    today = datetime.today().date()
    return (
        today.year
        - dob.year
        - ((today.month, today.day) < (dob.month, dob.day))
    )


# =====================================================================
# 2. HÀM CHUẨN HÓA DỮ LIỆU (NORMALIZERS)
# =====================================================================

def normalize_name(name):
    if not name:
        return ""
    return " ".join(name.split()).title()

def normalize_email(email):
    if not email:
        return ""
    return email.strip().lower()

def normalize_phone(phone):
    if not phone:
        return ""
    return phone.strip().replace(" ", "").replace("-", "")

def normalize_address(address):
    if not address:
        return ""
    return " ".join(address.split())

def normalize_nationality(nationality):
    if not nationality:
        return ""
    return " ".join(nationality.split()).title()

def normalize_citizenid(citizenid):
    if not citizenid:
        return ""
    return citizenid.strip()


# =====================================================================
# 3. HÀM VALIDATE (THAY BẰNG RAISE EXCEPTION)
# =====================================================================

def validate_name(name):
    if not name:
        raise EmployeeValidationError('Họ và tên không được để trống!')
    if not is_valid_name(name):
        raise EmployeeValidationError('Vui lòng nhập đúng tên theo cú pháp: Nguyễn Văn A')

def validate_phone(phone):
    if not is_valid_phone(phone):
        raise EmployeeValidationError('Số điện thoại phải gồm đúng 10 chữ số và bắt đầu bằng số 0!')

def validate_email(email):
    if not email:
        raise EmployeeValidationError('Email không được để trống!')
    if ' ' in email:
        raise EmployeeValidationError('Email không được chứa khoảng trắng!')
    if not is_valid_email(email):
        raise EmployeeValidationError('Email không hợp lệ!')

def validate_citizenid(citizenid):
    if not is_valid_citizenid(citizenid):
        raise EmployeeValidationError('CCCD phải gồm đúng 12 chữ số!')

def validate_emergency_contact(name):
    if not name:
        raise EmployeeValidationError('Người liên hệ khẩn cấp không được để trống!')
    if not is_valid_name(name):
        raise EmployeeValidationError('Tên người liên hệ khẩn cấp không hợp lệ!')

def validate_emergency_phone(phone):
    if not is_valid_phone(phone):
        raise EmployeeValidationError('Số điện thoại khẩn cấp không hợp lệ (phải gồm 10 số và bắt đầu bằng số 0)!')

def validate_address(address):
    if not address:
        raise EmployeeValidationError('Địa chỉ không được để trống!')
    if len(address) > 255:
        raise EmployeeValidationError('Địa chỉ tối đa 255 ký tự!')

def validate_nationality(nationality):
    if not nationality:
        raise EmployeeValidationError('Quốc tịch không được để trống!')
    if not is_valid_nationality(nationality):
        raise EmployeeValidationError('Quốc tịch chỉ được chứa chữ cái!')

def validate_dob(dob):
    today = datetime.today().date()
    if dob > today:
        raise EmployeeValidationError("Ngày sinh không được lớn hơn ngày hiện tại!")
    if calculate_age(dob) < 18:
        raise EmployeeValidationError("Nhân viên phải đủ 18 tuổi!")

def validate_hiredate(dob, hiredate):
    today = datetime.today().date()
    if hiredate < dob:
        raise EmployeeValidationError("Ngày tuyển dụng không được nhỏ hơn ngày sinh!")
    if hiredate > today:
        raise EmployeeValidationError("Ngày tuyển dụng không được lớn hơn ngày hiện tại!")