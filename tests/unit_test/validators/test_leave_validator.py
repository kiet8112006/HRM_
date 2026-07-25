import pytest
from datetime import datetime, timedelta
from exceptions.validator.leave import LeaveValidationError

# Import các hàm và hằng số từ module validator (chỉnh đường dẫn nếu cần)
from validators.leave_validator import (
    ALLOWED_LEAVE_TYPES,
    ALLOWED_LEAVE_STATUSES,
    normalize_reason,
    normalize_reject_reason,
    validate_leave_type,
    validate_leave_status,
    validate_reason,
    validate_reject_reason,
    validate_leave_dates
)


# =====================================================================
# 1. TEST HÀM CHUẨN HÓA DỮ LIỆU (NORMALIZERS)
# =====================================================================

class TestLeaveNormalizers:

    def test_normalize_reason(self):
        assert normalize_reason("   Nghỉ   bệnh   cảm   cúm   ") == "Nghỉ bệnh cảm cúm"
        assert normalize_reason("") == ""
        assert normalize_reason(None) == ""

    def test_normalize_reject_reason(self):
        assert normalize_reject_reason("   Lý   do   không   hợp   lệ   ") == "Lý do không hợp lệ"
        assert normalize_reject_reason("") == ""
        assert normalize_reject_reason(None) == ""


# =====================================================================
# 2. TEST HÀM VALIDATE (RAISE EXCEPTION)
# =====================================================================

class TestLeaveValidatorsWithExceptions:

    # --- Test Leave Type ---
    def test_validate_leave_type_success(self):
        for leave_type in ALLOWED_LEAVE_TYPES:
            validate_leave_type(leave_type)

    def test_validate_leave_type_invalid(self):
        with pytest.raises(LeaveValidationError, match="Loại nghỉ phép không hợp lệ!"):
            validate_leave_type("Nghỉ đi du lịch")

        with pytest.raises(LeaveValidationError, match="Loại nghỉ phép không hợp lệ!"):
            validate_leave_type("")

        with pytest.raises(LeaveValidationError, match="Loại nghỉ phép không hợp lệ!"):
            validate_leave_type(None)

    # --- Test Leave Status ---
    def test_validate_leave_status_success(self):
        for status in ALLOWED_LEAVE_STATUSES:
            validate_leave_status(status)

    def test_validate_leave_status_invalid(self):
        with pytest.raises(LeaveValidationError, match="Trạng thái đơn nghỉ phép không hợp lệ!"):
            validate_leave_status("Đang xem xét")

        with pytest.raises(LeaveValidationError, match="Trạng thái đơn nghỉ phép không hợp lệ!"):
            validate_leave_status("")

    # --- Test Reason ---
    def test_validate_reason_success(self):
        validate_reason("Đi khám bệnh định kỳ")

    def test_validate_reason_empty(self):
        with pytest.raises(LeaveValidationError, match="Lý do nghỉ không được để trống!"):
            validate_reason("")

        with pytest.raises(LeaveValidationError, match="Lý do nghỉ không được để trống!"):
            validate_reason(None)

    def test_validate_reason_too_long(self):
        long_reason = "R" * 256
        with pytest.raises(LeaveValidationError, match="Lý do nghỉ tối đa 255 ký tự!"):
            validate_reason(long_reason)

    # --- Test Reject Reason ---
    def test_validate_reject_reason_not_rejected_status(self):
        """Khi trạng thái KHÔNG PHẢI 'Từ chối' -> Không bắt buộc nhập lý do từ chối"""
        validate_reject_reason("", "Đã duyệt")
        validate_reject_reason(None, "Chờ duyệt")

    def test_validate_reject_reason_rejected_status_success(self):
        """Khi trạng thái là 'Từ chối' và nhập lý do hợp lệ"""
        validate_reject_reason("Không đủ nhân sự dự phòng", "Từ chối")

    def test_validate_reject_reason_rejected_status_empty(self):
        """Trạng thái 'Từ chối' nhưng bỏ trống lý do -> Raise Exception"""
        with pytest.raises(LeaveValidationError, match="Lý do từ chối không được để trống!"):
            validate_reject_reason("", "Từ chối")

        with pytest.raises(LeaveValidationError, match="Lý do từ chối không được để trống!"):
            validate_reject_reason(None, "Từ chối")

    def test_validate_reject_reason_rejected_status_too_long(self):
        """Trạng thái 'Từ chối' và lý do quá 255 ký tự -> Raise Exception"""
        long_reject_reason = "X" * 256
        with pytest.raises(LeaveValidationError, match="Lý do từ chối tối đa 255 ký tự!"):
            validate_reject_reason(long_reject_reason, "Từ chối")

    # --- Test Leave Dates ---
    def test_validate_leave_dates_success(self):
        """Ngày nghỉ từ hôm nay và tổng số ngày <= 30 hợp lệ"""
        today = datetime.today().date()
        from_date = today
        to_date = today + timedelta(days=4) # Nghỉ 5 ngày
        
        total_days = validate_leave_dates(from_date, to_date)
        assert total_days == 5

    def test_validate_leave_dates_from_date_in_past(self):
        """Ngày bắt đầu nghỉ nhỏ hơn hôm nay -> Raise Exception"""
        yesterday = datetime.today().date() - timedelta(days=1)
        to_date = datetime.today().date() + timedelta(days=2)

        with pytest.raises(LeaveValidationError, match="Ngày bắt đầu nghỉ không được nhỏ hơn ngày hiện tại!"):
            validate_leave_dates(yesterday, to_date)

    def test_validate_leave_dates_to_date_before_from_date(self):
        """Ngày kết thúc nhỏ hơn ngày bắt đầu -> Raise Exception"""
        today = datetime.today().date()
        from_date = today + timedelta(days=3)
        to_date = today + timedelta(days=1)

        with pytest.raises(LeaveValidationError, match="Ngày kết thúc nghỉ không được nhỏ hơn ngày bắt đầu!"):
            validate_leave_dates(from_date, to_date)

    def test_validate_leave_dates_exceed_30_days(self):
        """Nghỉ quá 30 ngày (từ ngày 0 đến ngày 30 là 31 ngày) -> Raise Exception"""
        today = datetime.today().date()
        from_date = today
        to_date = today + timedelta(days=30) # Tổng = 31 ngày

        with pytest.raises(LeaveValidationError, match="Tổng số ngày nghỉ không được vượt quá 30 ngày!"):
            validate_leave_dates(from_date, to_date)