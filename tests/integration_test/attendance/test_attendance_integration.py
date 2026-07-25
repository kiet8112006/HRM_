from unittest.mock import MagicMock, patch
from datetime import date
import pytest


# =====================================================================
# INTEGRATION TEST: LUỒNG CHẤM CÔNG (ATTENDANCE POST FLOW)
# =====================================================================
@patch("routes.attendance.log_activity")
@patch("routes.attendance.create_notification")
@patch("routes.attendance.validate_checkin_checkout_times")
@patch("routes.attendance.validate_attendance_date")
@patch("routes.attendance.validate_notes")
@patch("routes.attendance.validate_checkin_method")
@patch("routes.attendance.validate_approval_status")
@patch("routes.attendance.validate_attendance_status")
@patch("routes.attendance.get_connection")
def test_add_attendance_full_flow_success(
    mock_get_conn,
    mock_val_status,
    mock_val_app_status,
    mock_val_method,
    mock_val_notes,
    mock_val_date,
    mock_val_times,
    mock_create_notification,
    mock_log_activity,
    authenticated_client,
):
    # 1. Mock Database & Cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Giả lập kết quả trả về của DB:
    # - Lần 1: Check EmployeeID tồn tại -> Trả về (1,) (Hợp lệ)
    # - Lần 2: Check Attendance trùng ngày -> Trả về (0,) (Chưa chấm)
    # - Lần 3: Query FullName của Employee -> Trả về ("Nguyen Van A",)
    mock_cursor.fetchone.side_effect = [(1,), (0,), ("Nguyen Van A",)]

    # 2. Mock Validator tính toán WorkingHours & LateMinutes
    # Trả về tuple: (checkin, checkout, working_hours, overtime_hours, late_minutes, early_leave_minutes)
    expected_working_hours = 8.0
    expected_late_minutes = 15
    mock_val_times.return_value = (
        "08:15",
        "17:00",
        expected_working_hours,
        0.0,
        expected_late_minutes,
        0,
    )

    # 3. Dữ liệu POST theo kịch bản Ví dụ
    data = {
        "employee_id": "1",
        "date": "2026-03-25",
        "checkin": "08:15",
        "checkout": "17:00",
        "status": "Di lam",
        "checkin_method": "Tay",
        "approval_status": "Da duyet",
        "notes": "Co mat dung gio",
    }

    # Execute POST Request
    response = authenticated_client.post(
        "/add_attendance", data=data, follow_redirects=True
    )

    # -----------------------------------------------------------------
    # KIỂM TRA CÁC CỘT MỐC THEO YÊU CẦU FLOW & ĐIỀU KIỆN
    # -----------------------------------------------------------------

    # 1. Redirect đúng (chuyển hướng về trang danh sách chấm công)
    assert response.status_code == 200
    assert response.request.path == "/attendance"

    # 2. Kiểm tra Attendance có record & Lệnh INSERT được gọi với WorkingHours + LateMinutes đúng
    assert mock_cursor.execute.called
    assert mock_conn.commit.called

    # Kiểm tra tham số truyền vào câu lệnh INSERT INTO Attendance
    insert_call_args = None
    for call in mock_cursor.execute.call_args_list:
        query = call[0][0]
        if "INSERT INTO Attendance" in query:
            insert_call_args = call[0][1]
            break

    assert insert_call_args is not None, "Không tìm thấy câu lệnh INSERT INTO Attendance"

    # Verify WorkingHours và LateMinutes nằm trong tham số INSERT
    assert expected_working_hours in insert_call_args
    assert expected_late_minutes in insert_call_args

    # 3. Notification tạo (Kiểm tra gọi tạo thông báo)
    mock_create_notification.assert_called_once_with(
        title="Chấm công mới",
        message="Bản ghi chấm công của Nguyen Van A ngày 2026-03-25 đã được thêm.",
        type="Success",
        receiver_role="Admin",
        url="/attendance",
    )

    # 4. Audit log tạo (Kiểm tra ghi log hoạt động)
    mock_log_activity.assert_called_once_with(
        module="Attendance",
        action="Create",
        description="Created attendance record for employee Nguyen Van A on 2026-03-25 (Status: Di lam).",
    )