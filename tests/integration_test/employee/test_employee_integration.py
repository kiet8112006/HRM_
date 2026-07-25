import io
from unittest.mock import MagicMock, patch
import pytest


# =====================================================================
# INTEGRATION TEST: LUỒNG THÊM MỚI NHÂN VIÊN ĐẦY ĐỦ (EMPLOYEE ADD FLOW)
# =====================================================================
@patch("routes.employee.log_activity")
@patch("routes.employee.create_notification")
@patch("routes.employee.save_citizen_back")
@patch("routes.employee.save_citizen_front")
@patch("routes.employee.save_avatar")
@patch("routes.employee.verify_image")
@patch("routes.employee.allowed_mimetype")
@patch("routes.employee.allowed_file")
@patch("routes.employee.get_connection")
def test_add_employee_full_flow_success(
    mock_get_conn,
    mock_allowed_file,
    mock_allowed_mimetype,
    mock_verify_image,
    mock_save_avatar,
    mock_save_front,
    mock_save_back,
    mock_create_notification,
    mock_log_activity,
    authenticated_client,
):
    # 1. Mock Database & Cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Giả lập kết quả SELECT check trùng (CitizenID, Email, Phone) -> Trả về 0 (Chưa tồn tại)
    mock_cursor.fetchone.side_effect = [(0,), (0,), (0,)]

    # 2. Mock File Validation & File Upload Helpers
    mock_allowed_file.return_value = True
    mock_allowed_mimetype.return_value = True
    mock_verify_image.return_value = True

    mock_save_avatar.return_value = "avatar_test.jpg"
    mock_save_front.return_value = "citizen_front_test.jpg"
    mock_save_back.return_value = "citizen_back_test.jpg"

    # Giả lập dữ liệu Form POST gửi lên
    dummy_file = (io.BytesIO(b"fake_image_bytes"), "test.jpg")
    data = {
        "fullname": "Nguyen Van A",
        "gender": "Nam",
        "dob": "1995-05-15",
        "hiredate": "2023-01-10",
        "email": "nguyenvana@gmail.com",
        "phone": "0987654321",
        "citizenid": "123456789012",
        "address": "123 Duong ABC, Quan 1, TP.HCM",
        "nationality": "Viet Nam",
        "maritalstatus": "Doc thân",
        "emergencycontact": "Nguyen Van B",
        "emergencyphone": "0912345678",
        "status": "Dang lam viec",
        "department_id": "1",
        "position_id": "2",
        "manager_id": "",
        "photo": dummy_file,
        "citizen_front": dummy_file,
        "citizen_back": dummy_file,
    }

    # Execute POST request
    response = authenticated_client.post(
        "/add_employee",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    # -----------------------------------------------------------------
    # KIỂM TRA CAC CỘT MỐC THEO FLOW TRONG HÌNH
    # -----------------------------------------------------------------

    # 1. Redirect đúng (Redirect về /employees)
    assert response.status_code == 200
    assert response.request.path == "/employees"

    # 2. Employee xuất hiện / Insert DB
    # Verify execute INSERT INTO Employees được gọi đúng thông số
    assert mock_cursor.execute.called
    assert mock_conn.commit.called

    # 3. Avatar / Files đã được xử lý lưu
    assert mock_save_avatar.called
    assert mock_save_front.called
    assert mock_save_back.called

    # 4. Notification tạo
    mock_create_notification.assert_called_once_with(
        title="Nhân viên mới",
        message="Nguyen Van A vừa được thêm vào hệ thống.",
        type="Success",
        receiver_role="Admin",
        url="/employees",
    )

    # 5. Audit Log tạo
    mock_log_activity.assert_called_once_with(
        module="Employee",
        action="Create",
        description="Created employee Nguyen Van A. ",
    )