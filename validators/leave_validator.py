from datetime import datetime
from exceptions.validator.leave import LeaveValidationError

ALLOWED_LEAVE_TYPES = [
    'Nghỉ phép năm', 
    'Nghỉ bệnh', 
    'Nghỉ không lương', 
    'Nghỉ thai sản', 
    'Nghỉ việc riêng'
]

ALLOWED_LEAVE_STATUSES = [
    'Chờ duyệt', 
    'Đã duyệt', 
    'Từ chối'
]

# =====================================================================
# 1. HÀM CHUẨN HÓA DỮ LIỆU (NORMALIZERS)
# =====================================================================
def normalize_reason(reason):
    if not reason:
        return ""
    return " ".join(reason.split())

def normalize_reject_reason(reject_reason):
    if not reject_reason:
        return ""
    return " ".join(reject_reason.split())


# =====================================================================
# 2. HÀM VALIDATE (RAISE LEAVE_VALIDATION_ERROR)
# =====================================================================
def validate_leave_type(leave_type):
    if not leave_type or leave_type not in ALLOWED_LEAVE_TYPES:
        raise LeaveValidationError('Loại nghỉ phép không hợp lệ!')

def validate_leave_status(status):
    if not status or status not in ALLOWED_LEAVE_STATUSES:
        raise LeaveValidationError('Trạng thái đơn nghỉ phép không hợp lệ!')

def validate_reason(reason):
    if not reason:
        raise LeaveValidationError('Lý do nghỉ không được để trống!')
    if len(reason) > 255:
        raise LeaveValidationError('Lý do nghỉ tối đa 255 ký tự!')

def validate_reject_reason(reject_reason, status):
    if status == 'Từ chối':
        if not reject_reason:
            raise LeaveValidationError('Lý do từ chối không được để trống!')
        if len(reject_reason) > 255:
            raise LeaveValidationError('Lý do từ chối tối đa 255 ký tự!')

def validate_leave_dates(from_date, to_date):
    today = datetime.today().date()
    if from_date < today:
        raise LeaveValidationError('Ngày bắt đầu nghỉ không được nhỏ hơn ngày hiện tại!')
    if to_date < from_date:
        raise LeaveValidationError('Ngày kết thúc nghỉ không được nhỏ hơn ngày bắt đầu!')
    
    total_days = (to_date - from_date).days + 1
    if total_days > 30:
        raise LeaveValidationError('Tổng số ngày nghỉ không được vượt quá 30 ngày!')
    return total_days