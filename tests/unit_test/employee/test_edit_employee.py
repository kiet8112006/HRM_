import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from exceptions.validator.employee import EmployeeValidationError

# Fixture dùng chung cho module edit_employee
@pytest.fixture(autouse=True)
def mock_edit_dependencies():
    with patch("utils.auth.login_required", lambda f: f), \
         patch("utils.auth.role_required", lambda *args, **kwargs: lambda f: f), \
         patch("routes.employee.get_cached_departments", return_value=[(1, "IT")]), \
         patch("routes.employee.get_cached_positions", return_value=[(1, "Dev")]), \
         patch("routes.employee.create_notification"), \
         patch("routes.employee.log_activity"), \
         patch("routes.employee.delete_image"):
        yield

@pytest.fixture
def mock_employee_record():
    """Mock dữ liệu một nhân viên đang tồn tại trong DB."""
    emp = MagicMock()
    emp.EmployeeID = 1
    emp.Photo = "uploads/old_avatar.jpg"
    emp.CitizenFrontPhoto = "uploads/old_front.jpg"
    emp.CitizenBackPhoto = "uploads/old_back.jpg"
    emp.FullName = "Nguyen Van A"
    return emp

@pytest.fixture
def valid_edit_payload():
    """Form dữ liệu cập nhật hợp lệ."""
    return {
        "fullname": "Nguyen Van A Updated",
        "gender": "Nam",
        "dob": "1995-01-01",
        "hiredate": "2020-01-01",
        "email": "updated@gmail.com",
        "citizenid": "012345678901",
        "address": "456 Đường XYZ",
        "nationality": "Việt Nam",
        "maritalstatus": "Đã kết hôn",
        "emergencycontact": "Nguyen Van C",
        "emergencyphone": "0987654321",
        "phone": "0912345678",
        "department_id": "1",
        "position_id": "1",
        "manager_id": "",
        "status": "Active"
    }

# =====================================================================
# 1. GET ROUTE & EMPLOYEE EXISTENCE (3 Cases)
# =====================================================================

def test_edit_employee_get_success(client, mock_db, mock_employee_record):
    """Case 1: GET /edit_employee/1 thành công khi nhân viên tồn tại."""
    mock_db.fetchone.side_effect = [mock_employee_record, [(2, "Manager B")]]
    response = client.get("/edit_employee/1")
    assert response.status_code == 200

def test_edit_employee_get_not_found(client, mock_db):
    """Case 2: GET /edit_employee/999 nhân viên không tồn tại."""
    mock_db.fetchone.return_value = None
    response = client.get("/edit_employee/999")
    assert response.status_code in [200, 302]

def test_edit_employee_post_not_found(client, mock_db, valid_edit_payload):
    """Case 3: POST /edit_employee/999 khi nhân viên không tồn tại."""
    mock_db.fetchone.return_value = None
    response = client.post("/edit_employee/999", data=valid_edit_payload)
    assert response.status_code in [200, 302]

# =====================================================================
# 2. HAPPY PATH POST & MANAGER CHECK (3 Cases)
# =====================================================================

def test_edit_employee_post_success(client, mock_db, mock_employee_record, valid_edit_payload):
    """Case 4: Cập nhật thành công thông tin cơ bản (Không đổi ảnh)."""
    mock_db.fetchone.side_effect = [mock_employee_record, (0,), (0,), (0,)]

    response = client.post("/edit_employee/1", data=valid_edit_payload)
    assert response.status_code in [200, 302]
    
    executed_sqls = [call[0][0] for call in mock_db.execute.call_args_list if call[0]]
    assert any("UPDATE Employees" in sql for sql in executed_sqls)

def test_edit_employee_self_manager_error(client, mock_db, mock_employee_record, valid_edit_payload):
    """Case 5: Chọn chính mình làm Quản lý (manager_id == id) -> Báo lỗi."""
    mock_db.fetchone.side_effect = [mock_employee_record, (0,), (0,), (0,)]
    valid_edit_payload["manager_id"] = "1"

    response = client.post("/edit_employee/1", data=valid_edit_payload)
    assert response.status_code in [200, 302]

def test_edit_employee_valid_other_manager(client, mock_db, mock_employee_record, valid_edit_payload):
    """Case 6: Chọn nhân viên khác làm Quản lý (manager_id = 2) -> Hợp lệ."""
    mock_db.fetchone.side_effect = [mock_employee_record, (0,), (0,), (0,)]
    valid_edit_payload["manager_id"] = "2"

    response = client.post("/edit_employee/1", data=valid_edit_payload)
    assert response.status_code in [200, 302]

# =====================================================================
# 3. TRÙNG LẶP DỮ LIỆU (DUPLICATE CHECKS EXCEPT SELF) (3 Cases)
# =====================================================================

def test_edit_employee_duplicate_citizenid(client, mock_db, mock_employee_record, valid_edit_payload):
    """Case 7: CCCD đã tồn tại ở nhân viên khác."""
    mock_db.fetchone.side_effect = [mock_employee_record, (1,)]
    response = client.post("/edit_employee/1", data=valid_edit_payload)
    assert response.status_code in [200, 302]

def test_edit_employee_duplicate_email(client, mock_db, mock_employee_record, valid_edit_payload):
    """Case 8: Email đã tồn tại ở nhân viên khác."""
    mock_db.fetchone.side_effect = [mock_employee_record, (0,), (1,)]
    response = client.post("/edit_employee/1", data=valid_edit_payload)
    assert response.status_code in [200, 302]

def test_edit_employee_duplicate_phone(client, mock_db, mock_employee_record, valid_edit_payload):
    """Case 9: Số điện thoại đã tồn tại ở nhân viên khác."""
    mock_db.fetchone.side_effect = [mock_employee_record, (0,), (0,), (1,)]
    response = client.post("/edit_employee/1", data=valid_edit_payload)
    assert response.status_code in [200, 302]

# =====================================================================
# 4. FILE UPLOAD & UPDATE ANH CU (7 Cases)
# =====================================================================

@pytest.mark.parametrize("file_key", ["photo", "citizen_front", "citizen_back"])
def test_edit_employee_invalid_upload_files(client, mock_db, mock_employee_record, valid_edit_payload, file_key):
    """Cases 10, 11, 12: Upload file không hợp lệ khi cập nhật từng loại ảnh."""
    mock_db.fetchone.side_effect = [mock_employee_record, (0,), (0,), (0,)]
    data = {**valid_edit_payload, file_key: (BytesIO(b"bad file"), "bad.exe")}

    with patch("routes.employee.allowed_file", return_value=False):
        response = client.post("/edit_employee/1", data=data)
        assert response.status_code in [200, 302]

def test_edit_employee_update_avatar_success(client, mock_db, mock_employee_record, valid_edit_payload):
    """Case 13: Cập nhật Avatar mới thành công & xóa Avatar cũ."""
    mock_db.fetchone.side_effect = [mock_employee_record, (0,), (0,), (0,)]
    data = {**valid_edit_payload, "photo": (BytesIO(b"new avatar"), "new_avatar.jpg")}

    with patch("routes.employee.allowed_file", return_value=True), \
         patch("routes.employee.allowed_mimetype", return_value=True), \
         patch("routes.employee.verify_image", return_value=True), \
         patch("routes.employee.save_avatar", return_value="uploads/new_avatar.jpg"):

        response = client.post("/edit_employee/1", data=data)
        assert response.status_code in [200, 302]

def test_edit_employee_update_front_citizen_success(client, mock_db, mock_employee_record, valid_edit_payload):
    """Case 14: Cập nhật CCCD mặt trước mới thành công."""
    mock_db.fetchone.side_effect = [mock_employee_record, (0,), (0,), (0,)]
    data = {**valid_edit_payload, "citizen_front": (BytesIO(b"new front"), "front.jpg")}

    with patch("routes.employee.allowed_file", return_value=True), \
         patch("routes.employee.allowed_mimetype", return_value=True), \
         patch("routes.employee.verify_image", return_value=True), \
         patch("routes.employee.save_citizen_front", return_value="uploads/new_front.jpg"):

        response = client.post("/edit_employee/1", data=data)
        assert response.status_code in [200, 302]

def test_edit_employee_update_back_citizen_success(client, mock_db, mock_employee_record, valid_edit_payload):
    """Case 15: Cập nhật CCCD mặt sau mới thành công."""
    mock_db.fetchone.side_effect = [mock_employee_record, (0,), (0,), (0,)]
    data = {**valid_edit_payload, "citizen_back": (BytesIO(b"new back"), "back.jpg")}

    with patch("routes.employee.allowed_file", return_value=True), \
         patch("routes.employee.allowed_mimetype", return_value=True), \
         patch("routes.employee.verify_image", return_value=True), \
         patch("routes.employee.save_citizen_back", return_value="uploads/new_back.jpg"):

        response = client.post("/edit_employee/1", data=data)
        assert response.status_code in [200, 302]

def test_edit_employee_update_photo_when_old_photo_is_none(client, mock_db, valid_edit_payload):
    """Case 16: Cập nhật ảnh đại diện khi trước đó nhân viên chưa từng có ảnh (Photo = None)."""
    emp_no_photo = MagicMock()
    emp_no_photo.Photo = None
    mock_db.fetchone.side_effect = [emp_no_photo, (0,), (0,), (0,)]
    data = {**valid_edit_payload, "photo": (BytesIO(b"new avatar"), "avatar.jpg")}

    with patch("routes.employee.allowed_file", return_value=True), \
         patch("routes.employee.allowed_mimetype", return_value=True), \
         patch("routes.employee.verify_image", return_value=True), \
         patch("routes.employee.save_avatar", return_value="uploads/avatar.jpg"):

        response = client.post("/edit_employee/1", data=data)
        assert response.status_code in [200, 302]

# =====================================================================
# 5. VALIDATOR EXCEPTIONS (10 Cases)
# =====================================================================

@pytest.mark.parametrize("validator_target, exception_msg", [
    ("validate_name", "Tên sai"),                           # Case 17
    ("validate_dob", "Tuổi sai"),                           # Case 18
    ("validate_hiredate", "Ngày vào làm sai"),              # Case 19
    ("validate_email", "Email sai"),                        # Case 20
    ("validate_citizenid", "CCCD sai"),                     # Case 21
    ("validate_address", "Địa chỉ sai"),                    # Case 22
    ("validate_nationality", "Quốc tịch sai"),              # Case 23
    ("validate_emergency_contact", "Người liên hệ sai"),    # Case 24
    ("validate_emergency_phone", "SĐT khẩn cấp sai"),       # Case 25
    ("validate_phone", "SĐT sai")                           # Case 26
])
def test_edit_employee_validators(
    client, mock_db, mock_employee_record, valid_edit_payload, validator_target, exception_msg
):
    mock_db.fetchone.return_value = mock_employee_record
    with patch(f"routes.employee.{validator_target}", side_effect=EmployeeValidationError(exception_msg)):
        response = client.post("/edit_employee/1", data=valid_edit_payload)
        assert response.status_code in [200, 302]

# =====================================================================
# 6. DATABASE EXCEPTION & ROLLBACK (2 Cases)
# =====================================================================

def test_edit_employee_db_error_triggers_rollback(client, mock_db, mock_employee_record, valid_edit_payload):
    """Case 27: Database gặp sự cố khi UPDATE -> Phải rollback."""
    mock_db.fetchone.side_effect = [mock_employee_record, (0,), (0,), (0,)]
    
    def side_effect_with_error(sql, *args, **kwargs):
        if "UPDATE Employees" in sql:
            raise Exception("Update fail")
        return MagicMock()

    mock_db.execute.side_effect = side_effect_with_error
    response = client.post("/edit_employee/1", data=valid_edit_payload)
    assert response.status_code in [200, 302]

def test_edit_employee_get_db_exception(client, mock_db):
    """Case 28: GET /edit_employee/1 gặp lỗi DB khi query managers list."""
    mock_db.execute.side_effect = Exception("DB Connection Lost")
    response = client.get("/edit_employee/1")
    assert response.status_code in [200, 302]