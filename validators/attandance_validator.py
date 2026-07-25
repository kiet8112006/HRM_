from datetime import datetime
from exceptions.validator.attendance import AttendanceValidationError

# =====================================================================
# 1. HÀM CHECKER & HELPER (Thêm kiểm tra None an toàn)
# =====================================================================

def calculate_working_hours(checkin, checkout):
    if not checkin or not checkout:
        return 0.0
    checkin_time = datetime.strptime(str(checkin)[:5], "%H:%M")
    checkout_time = datetime.strptime(str(checkout)[:5], "%H:%M")
    working_hours = (checkout_time - checkin_time).seconds / 3600
    return round(working_hours, 2)

def calculate_late_minutes(checkin):
    if not checkin:
        return 0
    standard_time = datetime.strptime("08:00", "%H:%M")
    checkin_time = datetime.strptime(str(checkin)[:5], "%H:%M")
    if checkin_time <= standard_time:
        return 0
    return int((checkin_time - standard_time).seconds / 60)

def calculate_early_leave_minutes(checkout):
    if not checkout:
        return 0
    end_time = datetime.strptime("17:00", "%H:%M")
    checkout_time = datetime.strptime(str(checkout)[:5], "%H:%M")
    if checkout_time >= end_time:
        return 0
    return int((end_time - checkout_time).seconds / 60)

# =====================================================================
# 2. HÀM VALIDATE (RAISE EXCEPTION)
# =====================================================================

def validate_attendance_date(attendance_date, today):
    if attendance_date > today:
        raise AttendanceValidationError('Không thể chấm công trong tương lai!')

def validate_attendance_status(status):
    valid_statuses = ["Có mặt", "Đi trễ", "Vắng"]
    if status not in valid_statuses:
        raise AttendanceValidationError('Trạng thái chấm công không hợp lệ!')

def validate_approval_status(approval_status):
    valid_approvals = ["Chờ duyệt", "Đã duyệt", "Từ chối"]
    if approval_status not in valid_approvals:
        raise AttendanceValidationError('Trạng thái duyệt không hợp lệ!')

def validate_checkin_method(method):
    valid_methods = ["FaceID", "Fingerprint", "QR Code", "GPS", "Manual"]
    if method not in valid_methods:
        raise AttendanceValidationError('Phương thức chấm công không hợp lệ!')

def validate_notes(notes):
    if notes and len(notes.strip()) > 255:
        raise AttendanceValidationError('Ghi chú tối đa 255 ký tự!')

def validate_checkin_checkout_times(checkin, checkout, status):
    if status == "Vắng":
        return None, None, 0, 0, 0, 0

    if not checkin:
        raise AttendanceValidationError('Phải nhập giờ vào!')
    if not checkout:
        raise AttendanceValidationError('Phải nhập giờ ra!')

    try:
        checkin_time = datetime.strptime(str(checkin)[:5], "%H:%M")
        checkout_time = datetime.strptime(str(checkout)[:5], "%H:%M")
    except ValueError:
        raise AttendanceValidationError('Định dạng thời gian không hợp lệ (HH:MM)!')

    if checkout_time <= checkin_time:
        raise AttendanceValidationError('Giờ ra phải sau giờ vào!')

    working_hours = round((checkout_time - checkin_time).seconds / 3600, 2)
    if working_hours > 16:
        raise AttendanceValidationError('Số giờ làm việc không được vượt quá 16 tiếng!')

    late_minutes = calculate_late_minutes(checkin)
    early_leave_minutes = calculate_early_leave_minutes(checkout)
    overtime_hours = round(working_hours - 8, 2) if working_hours > 8 else 0

    return checkin, checkout, working_hours, overtime_hours, late_minutes, early_leave_minutes