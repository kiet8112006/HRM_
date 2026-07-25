from unittest.mock import MagicMock, patch
import pytest


# =====================================================================
# INTEGRATION TEST: LUỒNG THÊM MỚI PHÒNG BAN (DEPARTMENT ADD FLOW)
# =====================================================================
@patch("routes.department.validate_status")
@patch("routes.department.validate_location")
@patch("routes.department.validate_description")
@patch("routes.department.validate_department_name")
@patch("routes.department.validate_department_code")
@patch("routes.department.get_cached_active_employees")
@patch("routes.department.log_activity")
@patch("routes.department.create_notification")
@patch("routes.department.get_connection")
def test_add_department_full_flow_success(
    mock_get_conn,
    mock_create_notification,
    mock_log_activity,
    mock_get_cached_employees,
    mock_val_code,
    mock_val_name,
    mock_val_desc,
    mock_val_loc,
    mock_val_status,
    authenticated_client,
):
    # 1. Mock cache employees trả về danh sách giả trống
    mock_get_cached_employees.return_value = []

    # 2. Mock Database & Cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Giả lập SELECT COUNT(*) trả về (0,) -> Chưa tồn tại mã/tên phòng ban
    mock_cursor.fetchone.return_value = (0,)

    # 3. Dữ liệu POST
    department_code = "HR01"
    department_name = "Phong Nhan Su"

    data = {
        "department_code": department_code,
        "department_name": department_name,
        "description": "Phong quan ly nhan su",
        "location": "Tang 3",
        "status": "Hoat dong",
        "manager_id": "",
    }

    # Execute POST Request
    response = authenticated_client.post(
        "/add_department", data=data, follow_redirects=True
    )

    # -----------------------------------------------------------------
    # KIỂM TRA CÁC CỘT MỐC THEO FLOW
    # -----------------------------------------------------------------

    # 1. Redirect đúng về /departments
    assert response.status_code == 200
    assert response.request.path == "/departments"

    # 2. Kiểm tra câu lệnh INSERT INTO Departments đã được gọi
    assert mock_cursor.execute.called
    assert mock_conn.commit.called

    # 3. Notification tạo
    mock_create_notification.assert_called_once_with(
        title="Phòng ban mới",
        message=f"Phòng ban {department_name} ({department_code}) đã được thêm vào hệ thống.",
        type="Success",
        receiver_role="Admin",
        url="/departments",
    )

    # 4. Audit Log tạo
    mock_log_activity.assert_called_once_with(
        module="Department",
        action="Create",
        description=f"Created department {department_name}.",
    )