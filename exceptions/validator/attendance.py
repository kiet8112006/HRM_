# exceptions/validator/attendance.py

class AttendanceValidationError(Exception):
    """Exception dùng chung cho các lỗi validate dữ liệu Chấm công (Attendance)."""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class AttendanceDuplicateError(AttendanceValidationError):
    """Exception dành riêng cho lỗi nhân viên đã chấm công trong cùng một ngày."""
    pass