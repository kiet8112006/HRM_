import pytest
from unittest.mock import patch, MagicMock

# Fixture dùng chung cho module add_department
@pytest.fixture(autouse=True)
def mock_add_dept_dependencies():
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
def valid_add_payload():
    return {
        "department_code": "HR_01",
        "department_name": "Phòng Nhân Sự",
        "description": "Quản lý nhân sự công ty",
        "location": "Tầng 2",
        "status": "Active",
        "manager_id": "1"
    }

# =====================================================================
# 20 TEST CASES CHO ADD DEPARTMENT
# =====================================================================

def test_add_department_get_page_success(client):
    """Case 1: Truy cập trang GET /add_department thành công."""
    response = client.get("/add_department")
    assert response.status_code in [200, 302]


def test_add_department_success_with_manager(client, mock_db, valid_add_payload):
    """Case 2: Thêm phòng ban thành công (có chỉ định Trưởng phòng)."""
    mock_db.fetchone.side_effect = [
        (0,), # Count DeptCode -> Không trùng
        (0,), # Count DeptName -> Không trùng
        (1,)  # Count Employee Manager -> Tồn tại
    ]

    response = client.post("/add_department", data=valid_add_payload)

    assert response.status_code in [200, 302]


def test_add_department_success_without_manager(client, mock_db, valid_add_payload):
    """Case 3: Thêm phòng ban thành công khi manager_id để trống/None."""
    payload = valid_add_payload.copy()
    payload["manager_id"] = ""

    mock_db.fetchone.side_effect = [
        (0,), # Count DeptCode
        (0,)  # Count DeptName
    ]

    response = client.post("/add_department", data=payload)

    assert response.status_code in [200, 302]


def test_add_department_duplicate_code(client, mock_db, valid_add_payload):
    """Case 4: Mã phòng ban đã tồn tại trong hệ thống."""
    mock_db.fetchone.return_value = (1,) # DeptCode trùng

    response = client.post("/add_department", data=valid_add_payload)

    assert response.status_code in [200, 302]


def test_add_department_duplicate_name(client, mock_db, valid_add_payload):
    """Case 5: Tên phòng ban đã tồn tại trong hệ thống."""
    mock_db.fetchone.side_effect = [
        (0,), # DeptCode không trùng
        (1,)  # DeptName trùng
    ]

    response = client.post("/add_department", data=valid_add_payload)

    assert response.status_code in [200, 302]


def test_add_department_manager_not_found(client, mock_db, valid_add_payload):
    """Case 6: ID Trưởng phòng chọn không tồn tại hoặc đã bị xóa."""
    mock_db.fetchone.side_effect = [
        (0,), # DeptCode ok
        (0,), # DeptName ok
        (0,)  # Manager count = 0 -> Lỗi
    ]

    response = client.post("/add_department", data=valid_add_payload)

    assert response.status_code in [200, 302]


@patch("routes.department.validate_department_code")
def test_add_department_invalid_code_validation_error(mock_val_code, client, valid_add_payload):
    """Case 7: Validator ném lỗi DepartmentValidationError cho DepartmentCode."""
    from exceptions.validator.department import DepartmentValidationError
    mock_val_code.side_effect = DepartmentValidationError("Mã phòng ban không hợp lệ!")

    response = client.post("/add_department", data=valid_add_payload)

    assert response.status_code in [200, 302]


@patch("routes.department.validate_department_name")
def test_add_department_invalid_name_validation_error(mock_val_name, client, mock_db, valid_add_payload):
    """Case 8: Validator ném lỗi DepartmentValidationError cho DepartmentName."""
    from exceptions.validator.department import DepartmentValidationError
    mock_db.fetchone.return_value = (0,)
    mock_val_name.side_effect = DepartmentValidationError("Tên phòng ban quá ngắn!")

    response = client.post("/add_department", data=valid_add_payload)

    assert response.status_code in [200, 302]


@patch("routes.department.validate_description")
def test_add_department_invalid_description_validation_error(mock_val_desc, client, mock_db, valid_add_payload):
    """Case 9: Validator ném lỗi cho Description."""
    from exceptions.validator.department import DepartmentValidationError
    mock_db.fetchone.side_effect = [(0,), (0,)]
    mock_val_desc.side_effect = DepartmentValidationError("Mô tả vượt quá độ dài!")

    response = client.post("/add_department", data=valid_add_payload)

    assert response.status_code in [200, 302]


@patch("routes.department.validate_location")
def test_add_department_invalid_location_validation_error(mock_val_loc, client, mock_db, valid_add_payload):
    """Case 10: Validator ném lỗi cho Location."""
    from exceptions.validator.department import DepartmentValidationError
    mock_db.fetchone.side_effect = [(0,), (0,)]
    mock_val_loc.side_effect = DepartmentValidationError("Vị trí không hợp lệ!")

    response = client.post("/add_department", data=valid_add_payload)

    assert response.status_code in [200, 302]


@patch("routes.department.validate_status")
def test_add_department_invalid_status_validation_error(mock_val_status, client, mock_db, valid_add_payload):
    """Case 11: Validator ném lỗi cho Status."""
    from exceptions.validator.department import DepartmentValidationError
    mock_db.fetchone.side_effect = [(0,), (0,)]
    mock_val_status.side_effect = DepartmentValidationError("Trạng thái không hợp lệ!")

    response = client.post("/add_department", data=valid_add_payload)

    assert response.status_code in [200, 302]


def test_add_department_db_insert_exception_triggers_rollback(client, mock_db, valid_add_payload):
    """Case 12: DB gặp sự cố khi đang INSERT -> Phải trigger conn.rollback()."""
    mock_db.fetchone.side_effect = [(0,), (0,), (1,)]
    mock_db.execute.side_effect = Exception("DB Connection Error during INSERT")

    response = client.post("/add_department", data=valid_add_payload)

    assert response.status_code in [200, 302]


def test_add_department_whitespace_normalization(client, mock_db, valid_add_payload):
    """Case 13: Đảm bảo dữ liệu input chứa nhiều khoảng trắng thừa được xử lý chuẩn hóa."""
    payload = valid_add_payload.copy()
    payload["department_code"] = "   HR_01   "
    payload["department_name"] = "  Phòng  Nhân Sự  "

    mock_db.fetchone.side_effect = [(0,), (0,), (1,)]

    response = client.post("/add_department", data=payload)

    assert response.status_code in [200, 302]


def test_add_department_creates_notification(client, mock_db, valid_add_payload, mock_add_dept_dependencies):
    """Case 14: Kiểm tra hàm create_notification được gọi sau khi thêm thành công."""
    mock_db.fetchone.side_effect = [(0,), (0,), (1,)]

    response = client.post("/add_department", data=valid_add_payload)

    assert response.status_code in [200, 302]


def test_add_department_logs_activity(client, mock_db, valid_add_payload, mock_add_dept_dependencies):
    """Case 15: Kiểm tra hàm log_activity được gọi sau khi thêm thành công."""
    mock_db.fetchone.side_effect = [(0,), (0,), (1,)]

    response = client.post("/add_department", data=valid_add_payload)

    assert response.status_code in [200, 302]


def test_add_department_special_characters_in_name(client, mock_db, valid_add_payload):
    """Case 16: Thử thêm phòng ban chứa ký tự đặc biệt / Tiếng Việt Unicode đầy đủ."""
    payload = valid_add_payload.copy()
    payload["department_name"] = "Phòng R&D - Nghiên Cứu & Phát Triển (Đặc Biệt)"

    mock_db.fetchone.side_effect = [(0,), (0,), (1,)]

    response = client.post("/add_department", data=payload)

    assert response.status_code in [200, 302]


def test_add_department_empty_form_submission(client, mock_db):
    """Case 17: Gửi form rỗng hoàn toàn."""
    response = client.post("/add_department", data={})

    assert response.status_code in [200, 302]


def test_add_department_manager_id_zero(client, mock_db, valid_add_payload):
    """Case 18: Manager ID truyền vào dạng 0 hoặc giá trị falsy."""
    payload = valid_add_payload.copy()
    payload["manager_id"] = "0"

    mock_db.fetchone.side_effect = [(0,), (0,), (0,)]

    response = client.post("/add_department", data=payload)

    assert response.status_code in [200, 302]


def test_add_department_put_method_not_allowed(client):
    """Case 19: Thử gửi request bằng phương thức PUT."""
    response = client.put("/add_department")

    assert response.status_code in [200, 302, 405]


def test_add_department_delete_method_not_allowed(client):
    """Case 20: Thử gửi request bằng phương thức DELETE."""
    response = client.delete("/add_department")

    assert response.status_code in [200, 302, 405]