# exceptions/validator/contract.py

class ContractValidationError(Exception):
    """Exception dùng chung cho các lỗi validate dữ liệu Hợp đồng (Contract)."""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class ContractDuplicateError(ContractValidationError):
    """Exception dành riêng cho lỗi trùng lặp Mã hợp đồng."""
    pass