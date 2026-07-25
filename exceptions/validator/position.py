# exceptions/validator/position.py

class PositionValidationError(Exception):
    """Exception dùng chung cho các lỗi validate dữ liệu thuộc về Chức vụ (Position)."""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class PositionDuplicateError(PositionValidationError):
    """Exception dành riêng cho lỗi trùng lặp Mã chức vụ hoặc Tên chức vụ."""
    pass