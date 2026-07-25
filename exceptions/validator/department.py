# exceptions/validator/department.py

class DepartmentValidationError(Exception):
    """Exception dùng chung cho các lỗi validate dữ liệu thuộc về Phòng ban (Department)."""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class DepartmentDuplicateError(DepartmentValidationError):
    """Exception dành riêng cho lỗi trùng lặp Mã phòng ban hoặc Tên phòng ban."""
    pass