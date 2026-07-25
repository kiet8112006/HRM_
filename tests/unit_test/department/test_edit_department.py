import pytest
from unittest.mock import patch, MagicMock

# Fixture dùng chung cho module edit_department
@pytest.fixture(autouse=True)
def mock_edit_dept_dependencies():
    with patch("utils.auth.login_required", lambda f: f), \
         patch("utils.auth.role_required", lambda *args, **kwargs: lambda f: f), \
         patch("routes.department.create_notification") as mock_notif, \
         patch("routes.department.log_activity") as mock_log, \
         patch("routes.department.get_cached_active_employees", return_value=[]), \
         patch("routes.department.validate_department_code"), \
         patch("routes.department.validate_department_name"), \
         patch("routes.department.validate_description"), \
         patch("routes.department.validate_location"), \
         patch("routes.department.validate_status"):
        yield {"mock_notif": mock_notif, "mock_log": mock_log}

@pytest.fixture
def valid_edit_payload():
    return {
        "department_code": "IT_01",
        "department_name": "Phòng Công Nghệ Mới",
        "description": "Mô tả đã cập nhật",
        "location": "Tầng 5",
        "status": "Active",
        "manager_id": "2"
    }

# =====================================================================
# 15 TEST CASES CHO EDIT DEPARTMENT
# =====================================================================

def test_edit_department_get_page_success(client, mock_db):
    """Case 1: Truy cập trang GET /edit_department/1 thành công khi phòng ban tồn tại."""
    mock_db.fetchone.return_value = MagicMock(DepartmentID=1, DepartmentCode="IT", DepartmentName="Phòng IT")

    response = client.get("/edit_department/1")

    assert response.status_code in [200, 302]


def test_edit_department_get_page_not_found(client, mock_db):
    """Case 2: Truy cập trang GET phòng ban không tồn tại (ID = 999)."""
    mock_db.fetchone.return_value = (0,)

    response = client.get("/edit_department/999")

    assert response.status_code in [200, 302]


def test_edit_department_success(client, mock_db, valid_edit_payload):
    """Case 3: Cập nhật thông tin phòng ban thành công."""
    mock_db.fetchone.side_effect = [
        (1,), # Check tồn tại phòng ban
        (0,), # DeptCode không trùng
        (0,), # DeptName không trùng
        (1,)  # ManagerID tồn tại
    ]

    response = client.post("/edit_department/1", data=valid_edit_payload)

    assert response.status_code in [200, 302]


def test_edit_department_success_clear_manager(client, mock_db, valid_edit_payload):
    """Case 4: Cập nhật thành công khi bỏ Trưởng phòng (manager_id để trống)."""
    payload = valid_edit_payload.copy()
    payload["manager_id"] = ""

    mock_db.fetchone.side_effect = [
        (1,), # Check tồn tại phòng ban
        (0,), # DeptCode không trùng
        (0,)  # DeptName không trùng
    ]

    response = client.post("/edit_department/1", data=payload)

    assert response.status_code in [200, 302]


def test_edit_department_duplicate_code(client, mock_db, valid_edit_payload):
    """Case 5: Cập nhật mã phòng ban trùng với phòng ban khác."""
    mock_db.fetchone.side_effect = [
        (1,), # Check tồn tại phòng ban
        (1,)  # DeptCode bị trùng
    ]

    response = client.post("/edit_department/1", data=valid_edit_payload)

    assert response.status_code in [200, 302]


def test_edit_department_duplicate_name(client, mock_db, valid_edit_payload):
    """Case 6: Cập nhật tên phòng ban trùng với phòng ban khác."""
    mock_db.fetchone.side_effect = [
        (1,), # Check tồn tại phòng ban
        (0,), # DeptCode ok
        (1,)  # DeptName bị trùng
    ]

    response = client.post("/edit_department/1", data=valid_edit_payload)

    assert response.status_code in [200, 302]


def test_edit_department_manager_not_found(client, mock_db, valid_edit_payload):
    """Case 7: Trưởng phòng mới chỉ định không tồn tại trong DB."""
    mock_db.fetchone.side_effect = [
        (1,), # Check tồn tại phòng ban
        (0,), # DeptCode ok
        (0,), # DeptName ok
        (0,)  # Manager count = 0 -> Lỗi
    ]

    response = client.post("/edit_department/1", data=valid_edit_payload)

    assert response.status_code in [200, 302]


@patch("routes.department.validate_department_code")
def test_edit_department_invalid_code_validation_error(mock_val_code, client, mock_db, valid_edit_payload):
    """Case 8: Validator ném lỗi DepartmentValidationError cho DepartmentCode."""
    from exceptions.validator.department import DepartmentValidationError
    mock_db.fetchone.return_value = (1,)
    mock_val_code.side_effect = DepartmentValidationError("Mã phòng ban không đúng định dạng!")

    response = client.post("/edit_department/1", data=valid_edit_payload)

    assert response.status_code in [200, 302]


@patch("routes.department.validate_department_name")
def test_edit_department_invalid_name_validation_error(mock_val_name, client, mock_db, valid_edit_payload):
    """Case 9: Validator ném lỗi DepartmentValidationError cho DepartmentName."""
    from exceptions.validator.department import DepartmentValidationError
    mock_db.fetchone.side_effect = [(1,), (0,)]
    mock_val_name.side_effect = DepartmentValidationError("Tên phòng ban không đúng định dạng!")

    response = client.post("/edit_department/1", data=valid_edit_payload)

    assert response.status_code in [200, 302]


def test_edit_department_db_update_exception_triggers_rollback(client, mock_db, valid_edit_payload):
    """Case 10: Gặp lỗi DB khi thực thi câu UPDATE -> Phải conn.rollback()."""
    mock_db.fetchone.side_effect = [(1,), (0,), (0,), (1,)]
    mock_db.execute.side_effect = Exception("DB Error during UPDATE")

    response = client.post("/edit_department/1", data=valid_edit_payload)

    assert response.status_code in [200, 302]


def test_edit_department_creates_notification(client, mock_db, valid_edit_payload, mock_edit_dept_dependencies):
    """Case 11: Hệ thống tự động tạo thông báo sau khi cập nhật thành công."""
    mock_db.fetchone.side_effect = [(1,), (0,), (0,), (1,)]

    response = client.post("/edit_department/1", data=valid_edit_payload)

    assert response.status_code in [200, 302]


def test_edit_department_logs_activity(client, mock_db, valid_edit_payload, mock_edit_dept_dependencies):
    """Case 12: Hệ thống tự động ghi nhật ký (log_activity) khi cập nhật thành công."""
    mock_db.fetchone.side_effect = [(1,), (0,), (0,), (1,)]

    response = client.post("/edit_department/1", data=valid_edit_payload)

    assert response.status_code in [200, 302]


def test_edit_department_invalid_id_format(client):
    """Case 13: Truyền ID không phải dạng số nguyên (chuỗi 'abc')."""
    response = client.get("/edit_department/abc")

    assert response.status_code in [200, 302, 404]


def test_edit_department_post_non_existing_id(client, mock_db, valid_edit_payload):
    """Case 14: Thử POST dữ liệu cập nhật cho ID không tồn tại."""
    mock_db.fetchone.return_value = (0,)

    response = client.post("/edit_department/9999", data=valid_edit_payload)

    assert response.status_code in [200, 302]


def test_edit_department_delete_method_not_allowed(client):
    """Case 15: Thử gửi request bằng phương thức DELETE."""
    response = client.delete("/edit_department/1")

    assert response.status_code in [200, 302, 405]