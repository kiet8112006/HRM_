from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest


# =====================================================================
# INTEGRATION TEST: NOTIFICATION FLOW (CREATE & RENDER)
# =====================================================================
@patch("routes.notification.get_connection")
def test_notification_flow_after_adding_employee(mock_get_conn, authenticated_client):
    # -----------------------------------------------------------------
    # 1. SETUP MOCK DATABASE & CURSOR
    # Mô phỏng database có 1 Notification vừa được tạo sau khi thêm Employee
    # -----------------------------------------------------------------
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    created_at = datetime(2026, 7, 24, 13, 0, 0)

    # Giả lập dòng Notification trả về từ Database
    mock_notification_row = MagicMock()
    mock_notification_row.NotificationID = 101
    mock_notification_row.Title = "Nhân viên mới"
    mock_notification_row.Message = "Đã thêm thành công nhân viên Nguyễn Văn A vào hệ thống"
    mock_notification_row.Type = "Employee"
    mock_notification_row.Url = "/employees"
    mock_notification_row.IsRead = 0
    mock_notification_row.CreatedAt = created_at

    # Mock kết quả truy vấn cho route /notifications:
    # 1. fetchall() -> Danh sách thông báo
    # 2. fetchone()  -> unread_count
    mock_cursor.fetchall.return_value = [mock_notification_row]
    mock_cursor.fetchone.return_value = (1,)  # unread_count = 1

    # Giả lập Session role là 'Admin'
    with authenticated_client.session_transaction() as sess:
        sess['role'] = 'Admin'

    # -----------------------------------------------------------------
    # 2. EXECUTE REQUEST GET /notifications
    # -----------------------------------------------------------------
    response = authenticated_client.get("/notifications")

    # -----------------------------------------------------------------
    # 3. VERIFY NOTIFICATION PAGE RESPONSE
    # -----------------------------------------------------------------

    # Check 1: Response HTTP status code 200
    assert response.status_code == 200

    html_content = response.data.decode("utf-8")

    # Check 2: Notification vừa được tạo phải xuất hiện trên trang Notification Page
    assert "Nhân viên mới" in html_content
    assert "Đã thêm thành công nhân viên Nguyễn Văn A" in html_content

    # Check 3: Kiểm tra truy vấn SQL lọc đúng theo ReceiverRole ('Admin')
    executed_queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
    has_role_filter = any("ReceiverRole = ?" in q for q in executed_queries)
    assert has_role_filter, "Câu lệnh SQL phải lọc thông báo theo ReceiverRole"

    # Check 4: Đảm bảo DB Connection đã được đóng
    assert mock_conn.close.called