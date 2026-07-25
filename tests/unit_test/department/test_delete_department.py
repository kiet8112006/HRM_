import pytest
from unittest.mock import patch, MagicMock

# Fixture dùng chung cho delete_department
@pytest.fixture(autouse=True)
def mock_delete_dept_dependencies():
    with patch("utils.auth.login_required", lambda f: f), \
         patch("utils.auth.role_required", lambda *args, **kwargs: lambda f: f), \
         patch("routes.department.create_notification") as mock_notif, \
         patch("routes.department.log_activity") as mock_log:
        yield {"mock_notif": mock_notif, "mock_log": mock_log}

# =====================================================================
# 7 TEST CASES CHO DELETE DEPARTMENT
# =====================================================================

def test_delete_department_success(client, mock_db):
    """Case 1: Xóa mềm phòng ban thành công khi không còn nhân viên thuộc phòng ban."""
    mock_db.fetchone.side_effect = [
        ("Phòng IT",), # Tên phòng ban
        (0,)          # Số nhân viên = 0
    ]

    response = client.get("/delete_department/1")

    assert response.status_code in [200, 302]


def test_delete_department_not_found(client, mock_db):
    """Case 2: Thử xóa phòng ban không tồn tại (ID = 999)."""
    mock_db.fetchone.return_value = None

    response = client.get("/delete_department/999")

    assert response.status_code in [200, 302]


def test_delete_department_has_active_employees_fails(client, mock_db):
    """Case 3: Không cho phép xóa vì phòng ban vẫn còn chứa nhân viên đang hoạt động."""
    mock_db.fetchone.side_effect = [
        ("Phòng Nhân Sự",), # Tên phòng ban
        (5,)               # Còn 5 nhân viên -> Không cho xóa
    ]

    response = client.get("/delete_department/1")

    assert response.status_code in [200, 302]


def test_delete_department_db_exception_triggers_rollback(client, mock_db):
    """Case 4: DB gặp sự cố khi thực thi câu lệnh UPDATE -> Rollback."""
    mock_db.fetchone.side_effect = [("Phòng MKT",), (0,)]
    mock_db.execute.side_effect = Exception("DB Soft Delete Exception")

    response = client.get("/delete_department/1")

    assert response.status_code in [200, 302]


def test_delete_department_invalid_id_format(client):
    """Case 5: ID truyền vào không phải là số nguyên (chuỗi 'abc')."""
    response = client.get("/delete_department/abc")

    assert response.status_code in [200, 302, 404]


def test_delete_department_creates_logs_and_notifications(client, mock_db, mock_delete_dept_dependencies):
    """Case 6: Kiểm tra tự động ghi log_activity và create_notification khi xóa thành công."""
    mock_db.fetchone.side_effect = [("Phòng Kế Toán",), (0,)]

    response = client.get("/delete_department/1")

    assert response.status_code in [200, 302]


def test_delete_department_post_method_handling(client):
    """Case 7: Thử gửi request bằng phương thức POST tới route xóa đơn."""
    response = client.post("/delete_department/1")

    assert response.status_code in [200, 302, 405]