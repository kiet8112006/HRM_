from unittest.mock import MagicMock, patch
from datetime import date
import pytest


# =====================================================================
# INTEGRATION TEST: LUỒNG THÊM ĐƠN NGHỈ PHÉP (LEAVE POST FLOW)
# =====================================================================
@patch("routes.leave.log_activity")
@patch("routes.leave.create_notification")
@patch("routes.leave.validate_reason")
@patch("routes.leave.normalize_reason")
@patch("routes.leave.validate_leave_type")
@patch("routes.leave.validate_leave_dates")
@patch("routes.leave.get_connection")
def test_add_leave_request_full_flow_success(
    mock_get_conn,
    mock_val_dates,
    mock_val_type,
    mock_norm_reason,
    mock_val_reason,
    mock_create_notification,
    mock_log_activity,
    authenticated_client,
):
    # -----------------------------------------------------------------
    # 1. SETUP MOCK DATABASE & CURSOR
    # -----------------------------------------------------------------
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Giả lập kết quả trả về từ DB theo đúng thứ tự các câu lệnh SELECT trong route:
    # 1. SELECT FullName FROM Employees... -> Trả về nhân viên "Nguyễn Văn A"
    # 2. SELECT COUNT(*) FROM LeaveRequests (Check trùng lịch) -> Trả về (0,)
    # 3. SELECT ISNULL(MAX(RequestID), 0) + 1 FROM LeaveRequests -> Trả về (1,)
    mock_cursor.fetchone.side_effect = [
        ("Nguyễn Văn A",),
        (0,),
        (1,),
    ]

    # 2. SETUP MOCK VALIDATORS
    mock_val_dates.return_value = 2  # Tổng số ngày nghỉ: 2 ngày
    mock_norm_reason.side_effect = lambda r: r.strip() if r else ""

    # 3. DỮ LIỆU INPUT POST
    data = {
        "employee_id": "1",
        "from_date": "2026-03-30",
        "to_date": "2026-03-31",
        "leave_type": "Nghỉ phép năm",
        "reason": "Giải quyết việc gia đình",
    }

    # -----------------------------------------------------------------
    # EXECUTE REQUEST
    # -----------------------------------------------------------------
    response = authenticated_client.post(
        "/add_leave_request", data=data, follow_redirects=True
    )

    # -----------------------------------------------------------------
    # KIỂM TRA ĐIỀU KIỆN KẾT QUẢ (VERIFY FLOW & CHECKLIST)
    # -----------------------------------------------------------------

    # 1. Kiểm tra HTTP Status & Redirect
    assert response.status_code == 200
    assert response.request.path == "/leave_requests"

    # 2. Kiểm tra Database Record (INSERT INTO LeaveRequests)
    assert mock_cursor.execute.called
    assert mock_conn.commit.called

    insert_call_args = None
    for call in mock_cursor.execute.call_args_list:
        query = call[0][0]
        if "INSERT INTO LeaveRequests" in query:
            # call[0] chứa tất cả các tham số truyền vào execute(query, arg1, arg2,...)
            insert_call_args = call[0]
            break

    assert insert_call_args is not None, "Không tìm thấy câu lệnh INSERT INTO LeaveRequests"

    # Kiểm tra mã LeaveCode "LR0001", Trạng thái "Chờ duyệt", và Loại nghỉ phép "Nghỉ phép năm"
    assert "LR0001" in insert_call_args
    assert "Chờ duyệt" in insert_call_args
    assert "Nghỉ phép năm" in insert_call_args

    # Chuyển các tham số tuple thành danh sách chuỗi để so sánh chính xác từng giá trị
    args_as_strings = [str(arg) for arg in insert_call_args]

    # Kiểm tra mã LeaveCode "LR0001", Trạng thái "Chờ duyệt", và Loại nghỉ phép "Nghỉ phép năm"
    assert "LR0001" in args_as_strings
    assert "Chờ duyệt" in args_as_strings
    assert "Nghỉ phép năm" in args_as_strings

    # 3. Kiểm tra Notification
    mock_create_notification.assert_called_once_with(
        title="Đơn nghỉ phép mới",
        message="Đơn nghỉ phép (Nghỉ phép năm) của nhân viên Nguyễn Văn A đang chờ duyệt.",
        type="Success",
        receiver_role="Admin",
        url="/leave_requests",
    )

    # 4. Kiểm tra Audit Log
    mock_log_activity.assert_called_once_with(
        module="Leave",
        action="Create",
        description="Created leave request for employee Nguyễn Văn A from 2026-03-30 to 2026-03-31.",
    )