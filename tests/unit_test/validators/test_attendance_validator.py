import pytest
from datetime import date
from exceptions.validator.attendance import AttendanceValidationError

# Import các hàm từ module validator (chỉnh đường dẫn import nếu cần)
from validators.attandance_validator import (
    calculate_working_hours,
    calculate_late_minutes,
    calculate_early_leave_minutes,
    validate_attendance_date,
    validate_attendance_status,
    validate_approval_status,
    validate_checkin_method,
    validate_notes,
    validate_checkin_checkout_times
)


# =====================================================================
# 1. TEST HÀM HELPER TÍNH TOÁN (CHECKERS & CALCULATORS)
# =====================================================================

class TestAttendanceCalculators:

    def test_calculate_working_hours(self):
        """Tính số giờ làm việc dựa trên checkin và checkout"""
        # Làm từ 08:00 đến 17:00 (9 tiếng)
        assert calculate_working_hours("08:00", "17:00") == 9.0
        # Làm từ 08:30 đến 12:15 (3.75 tiếng)
        assert calculate_working_hours("08:30:00", "12:15:00") == 3.75
        # Trường hợp thiếu checkin hoặc checkout
        assert calculate_working_hours(None, "17:00") == 0.0
        assert calculate_working_hours("08:00", None) == 0.0

    def test_calculate_late_minutes(self):
        """Tính số phút đi trễ (mốc chuẩn 08:00)"""
        # Đúng giờ hoặc sớm hơn
        assert calculate_late_minutes("08:00") == 0
        assert calculate_late_minutes("07:45") == 0
        # Đi trễ 15 phút
        assert calculate_late_minutes("08:15") == 15
        # Không có checkin
        assert calculate_late_minutes(None) == 0

    def test_calculate_early_leave_minutes(self):
        """Tính số phút về sớm (mốc chuẩn 17:00)"""
        # Đúng giờ hoặc muộn hơn
        assert calculate_early_leave_minutes("17:00") == 0
        assert calculate_early_leave_minutes("17:30") == 0
        # Về sớm 30 phút
        assert calculate_early_leave_minutes("16:30") == 30
        # Không có checkout
        assert calculate_early_leave_minutes(None) == 0


# =====================================================================
# 2. TEST HÀM VALIDATE (RAISE EXCEPTION)
# =====================================================================

class TestAttendanceValidatorsWithExceptions:

    # --- Validate Attendance Date ---
    def test_validate_attendance_date_success(self):
        today = date(2026, 3, 20)
        validate_attendance_date(date(2026, 3, 20), today) # Hôm nay
        validate_attendance_date(date(2026, 3, 19), today) # Trong quá khứ

    def test_validate_attendance_date_future(self):
        today = date(2026, 3, 20)
        future_date = date(2026, 3, 21)
        with pytest.raises(AttendanceValidationError, match="Không thể chấm công trong tương lai!"):
            validate_attendance_date(future_date, today)

    # --- Validate Attendance Status ---
    def test_validate_attendance_status_success(self):
        validate_attendance_status("Có mặt")
        validate_attendance_status("Đi trễ")
        validate_attendance_status("Vắng")

    def test_validate_attendance_status_invalid(self):
        with pytest.raises(AttendanceValidationError, match="Trạng thái chấm công không hợp lệ!"):
            validate_attendance_status("Nghỉ phép")

    # --- Validate Approval Status ---
    def test_validate_approval_status_success(self):
        validate_approval_status("Chờ duyệt")
        validate_approval_status("Đã duyệt")
        validate_approval_status("Từ chối")

    def test_validate_approval_status_invalid(self):
        with pytest.raises(AttendanceValidationError, match="Trạng thái duyệt không hợp lệ!"):
            validate_approval_status("Đã hủy")

    # --- Validate Checkin Method ---
    def test_validate_checkin_method_success(self):
        methods = ["FaceID", "Fingerprint", "QR Code", "GPS", "Manual"]
        for method in methods:
            validate_checkin_method(method)

    def test_validate_checkin_method_invalid(self):
        with pytest.raises(AttendanceValidationError, match="Phương thức chấm công không hợp lệ!"):
            validate_checkin_method("RFID Card")

    # --- Validate Notes ---
    def test_validate_notes_success(self):
        validate_notes(None)
        validate_notes("")
        validate_notes("Đi công tác bên ngoài")

    def test_validate_notes_too_long(self):
        long_notes = "N" * 256
        with pytest.raises(AttendanceValidationError, match="Ghi chú tối đa 255 ký tự!"):
            validate_notes(long_notes)

    # --- Validate Checkin/Checkout Times & Calculations ---
    def test_validate_checkin_checkout_times_absent_status(self):
        """Khi trạng thái là 'Vắng' -> Trả về kết quả rỗng/bằng 0 mà không cần checkin/checkout"""
        res = validate_checkin_checkout_times(None, None, "Vắng")
        assert res == (None, None, 0, 0, 0, 0)

    def test_validate_checkin_checkout_times_success(self):
        """Chấm công bình thường: Checkin 08:15, Checkout 18:00 (Làm 9.75h, OT 1.75h, Trễ 15p, Về sớm 0p)"""
        checkin, checkout, working_h, ot_h, late_m, early_m = validate_checkin_checkout_times("08:15", "18:00", "Đi trễ")
        
        assert checkin == "08:15"
        assert checkout == "18:00"
        assert working_h == 9.75
        assert ot_h == 1.75
        assert late_m == 15
        assert early_m == 0

    def test_validate_checkin_checkout_times_missing_checkin(self):
        with pytest.raises(AttendanceValidationError, match="Phải nhập giờ vào!"):
            validate_checkin_checkout_times("", "17:00", "Có mặt")

    def test_validate_checkin_checkout_times_missing_checkout(self):
        with pytest.raises(AttendanceValidationError, match="Phải nhập giờ ra!"):
            validate_checkin_checkout_times("08:00", None, "Có mặt")

    def test_validate_checkin_checkout_times_invalid_format(self):
        with pytest.raises(AttendanceValidationError, match="Định dạng thời gian không hợp lệ"):
            validate_checkin_checkout_times("8 o clock", "17:00", "Có mặt")

    def test_validate_checkin_checkout_times_checkout_before_checkin(self):
        """Giờ ra nhỏ hơn hoặc bằng giờ vào -> Raise Exception"""
        with pytest.raises(AttendanceValidationError, match="Giờ ra phải sau giờ vào!"):
            validate_checkin_checkout_times("17:00", "08:00", "Có mặt")

        with pytest.raises(AttendanceValidationError, match="Giờ ra phải sau giờ vào!"):
            validate_checkin_checkout_times("08:00", "08:00", "Có mặt")

    def test_validate_checkin_checkout_times_exceed_max_hours(self):
        """Số giờ làm việc vượt quá 16 tiếng (Ví dụ: 06:00 đến 23:00 là 17 tiếng)"""
        with pytest.raises(AttendanceValidationError, match="Số giờ làm việc không được vượt quá 16 tiếng!"):
            validate_checkin_checkout_times("06:00", "23:00", "Có mặt")