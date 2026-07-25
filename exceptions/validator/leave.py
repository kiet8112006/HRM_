class LeaveValidationError(Exception):
    """Exception dùng riêng cho các lỗi Validation liên quan đến Nghỉ phép."""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)