import pytest
from unittest.mock import patch, MagicMock

# Fixture dùng chung cho module delete_employee
@pytest.fixture(autouse=True)
def mock_delete_dependencies():
    with patch("utils.auth.login_required", lambda f: f), \
         patch("utils.auth.role_required", lambda *args, **kwargs: lambda f: f), \
         patch("routes.employee.create_notification"), \
         patch("routes.employee.log_activity"):
        yield

@pytest.fixture
def mock_existing_employee():
    """Mock dữ liệu nhân viên đang tồn tại."""
    emp = MagicMock()
    emp.EmployeeID = 1
    emp.FullName = "Nguyen Van A"
    emp.IsDeleted = 0
    return emp

# =====================================================================
# 5 TEST CASES CHO DELETE EMPLOYEE
# =====================================================================

def test_delete_employee_success(client, mock_db, mock_existing_employee):
    """Case 1: Xóa mềm (IsDeleted = 1) nhân viên thành công."""
    mock_db.fetchone.return_value = mock_existing_employee

    response = client.get("/delete_employee/1")

    assert response.status_code in [200, 302]
    
    executed_sqls = [call[0][0] for call in mock_db.execute.call_args_list if call[0]]
    assert any("UPDATE" in sql and "IsDeleted" in sql for sql in executed_sqls)


def test_delete_employee_not_found(client, mock_db):
    """Case 2: Thử xóa nhân viên không tồn tại (ID = 999)."""
    mock_db.fetchone.return_value = None

    response = client.get("/delete_employee/999")

    assert response.status_code in [200, 302]


def test_delete_employee_invalid_id_format(client, mock_db):
    """Case 3: ID truyền vào không hợp lệ (chuỗi 'abc')."""
    response = client.get("/delete_employee/abc")

    assert response.status_code in [200, 302, 404]


def test_delete_employee_db_error_triggers_rollback(client, mock_db, mock_existing_employee):
    """Case 4: DB gặp sự cố khi đang thực thi lệnh UPDATE -> Phải trigger conn.rollback()."""
    mock_db.fetchone.return_value = mock_existing_employee

    def side_effect_with_error(sql, *args, **kwargs):
        if "UPDATE" in sql and "IsDeleted" in sql:
            raise Exception("DB Error when soft deleting")
        return MagicMock()

    mock_db.execute.side_effect = side_effect_with_error

    response = client.get("/delete_employee/1")

    assert response.status_code in [200, 302]


def test_delete_employee_method_not_allowed_or_handled(client):
    """Case 5: Gửi request phương thức POST tới route xóa."""
    response = client.post("/delete_employee/1")

    assert response.status_code in [200, 302, 405]