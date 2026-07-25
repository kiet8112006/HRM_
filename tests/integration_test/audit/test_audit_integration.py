from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest


# =====================================================================
# INTEGRATION TEST: AUDIT LOG FLOW (CREATE EMPLOYEE -> AUDIT PAGE)
# =====================================================================
@patch("routes.audit.get_connection")
def test_audit_log_flow_after_creating_employee(mock_get_conn, authenticated_client):
    # -----------------------------------------------------------------
    # 1. SETUP MOCK DATABASE & CURSOR
    # Giả lập database chứa record nhật ký hệ thống vừa ghi nhận
    # sau khi Admin thực hiện hành động Create Employee
    # -----------------------------------------------------------------
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    created_at = datetime(2026, 7, 24, 13, 15, 0)

    # Giả lập record AuditLog ghi nhận hành động tạo nhân viên mới
    mock_audit_row = MagicMock()
    mock_audit_row.LogID = 1
    mock_audit_row.UserID = 10
    mock_audit_row.Username = "admin_user"
    mock_audit_row.Role = "Admin"
    mock_audit_row.Module = "Employee"
    mock_audit_row.Action = "Create"
    mock_audit_row.RecordID = 50
    mock_audit_row.Description = "Thêm mới nhân viên Nguyễn Văn A thành công"
    mock_audit_row.IPAddress = "127.0.0.1"
    mock_audit_row.UserAgent = "Mozilla/5.0"
    mock_audit_row.CreatedAt = created_at

    # Mock kết quả cho 2 câu SQL trong route /audit_logs:
    # 1. COUNT(*) -> Trả về tổng số record = 1
    # 2. SELECT danh sách -> Trả về danh sách chứa mock_audit_row
    mock_cursor.fetchone.return_value = (1,)
    mock_cursor.fetchall.return_value = [mock_audit_row]

    # Giả lập Session người dùng đăng nhập là 'Admin'
    with authenticated_client.session_transaction() as sess:
        sess['role'] = 'Admin'
        sess['username'] = 'admin_user'

    # -----------------------------------------------------------------
    # 2. EXECUTE REQUEST GET /audit_logs
    # -----------------------------------------------------------------
    response = authenticated_client.get("/audit_logs")

    # -----------------------------------------------------------------
    # 3. VERIFY AUDIT PAGE RESPONSE & RECORD DETAILS
    # -----------------------------------------------------------------

    # Check HTTP Status Code 200 OK
    assert response.status_code == 200

    html_content = response.data.decode("utf-8")

    # Kiểm tra các thông tin Audit Record bắt buộc phải hiển thị trên màn hình:
    # - Module: Employee
    # - Action: Create
    # - Description: Thêm mới nhân viên...
    # - Username: admin_user
    assert "Employee" in html_content, "Audit Page phải hiển thị Module = Employee"
    assert "Create" in html_content, "Audit Page phải hiển thị Action = Create"
    assert "Thêm mới nhân viên Nguyễn Văn A" in html_content, "Audit Page phải hiển thị Description"
    assert "admin_user" in html_content, "Audit Page phải hiển thị Username"

    # Kiểm tra xem câu lệnh SQL pagination/filter có thực thi thành công không
    assert mock_cursor.execute.called

    # Kiểm tra DB connection được đóng sau khi render
    assert mock_conn.close.called