# exceptions/validator/employee.py

class EmployeeValidationError(Exception):
    """Exception gốc dùng cho các lỗi validate dữ liệu Nhân viên."""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class EmployeeDuplicateError(EmployeeValidationError):
    """Dùng khi phát hiện trùng dữ liệu (Email, CCCD, Phone) trong DB."""
    pass