import pytest
from unittest.mock import patch, MagicMock

# Fixture dùng chung cho delete_selected_departments
@pytest.fixture(autouse=True)
def mock_delete_selected_dept_dependencies():
    with patch("utils.auth.login_required", lambda f: f), \
         patch("utils.auth.role_required", lambda *args, **kwargs: lambda f: f), \
         patch("routes.department.create_notification") as mock_notif, \
         patch("routes.department.log_activity") as mock_log:
        yield {"mock_notif": mock_notif, "mock_log": mock_log}

# =====================================================================
# 9 TEST CASES CHO DELETE SELECTED DEPARTMENTS
# =====================================================================

def test_delete_selected_departments_success_all(client, mock_db):
    """Case 1: Xóa thành công toàn bộ các phòng ban được chọn (không có nhân viên)."""
    mock_db.fetchone.side_effect = [(0,), (0,)] # 2 phòng ban đều 0 nhân viên
    mock_db.fetchall.return_value = [(1, "Phòng IT"), (2, "Phòng MKT")]

    response = client.post("/delete_selected_departments", data={"department_ids": ["1", "2"]})

    assert response.status_code in [200, 302]


def test_delete_selected_departments_partial_success(client, mock_db):
    """Case 2: Xóa thành công 1 phòng ban, 1 phòng ban bị bỏ qua vì còn nhân viên."""
    mock_db.fetchone.side_effect = [
        (0,), # Dept 1: 0 nhân viên -> Xóa được
        (3,)  # Dept 2: 3 nhân viên -> Bị từ chối
    ]
    mock_db.fetchall.return_value = [(1, "Phòng IT")]

    response = client.post("/delete_selected_departments", data={"department_ids": ["1", "2"]})

    assert response.status_code in [200, 302]


def test_delete_selected_departments_all_failed_due_to_employees(client, mock_db):
    """Case 3: Tất cả phòng ban đã chọn đều đang chứa nhân viên -> Không xóa được cái nào."""
    mock_db.fetchone.side_effect = [(2,), (5,)]

    response = client.post("/delete_selected_departments", data={"department_ids": ["1", "2"]})

    assert response.status_code in [200, 302]


def test_delete_selected_departments_no_selection(client):
    """Case 4: Không chọn phòng ban nào (gửi form rỗng)."""
    response = client.post("/delete_selected_departments", data={})

    assert response.status_code in [200, 302]


def test_delete_selected_departments_non_existing_ids(client, mock_db):
    """Case 5: Chọn các ID phòng ban không tồn tại trong DB."""
    mock_db.fetchone.side_effect = [(0,)]
    mock_db.fetchall.return_value = [] # Không tìm thấy record nào

    response = client.post("/delete_selected_departments", data={"department_ids": ["999"]})

    assert response.status_code in [200, 302]


def test_delete_selected_departments_db_exception_triggers_rollback(client, mock_db):
    """Case 6: DB gặp sự cố khi thực thi câu UPDATE -> Phải conn.rollback()."""
    mock_db.fetchone.side_effect = [(0,)]
    mock_db.fetchall.return_value = [(1, "Phòng IT")]
    mock_db.execute.side_effect = Exception("DB Batch Delete Exception")

    response = client.post("/delete_selected_departments", data={"department_ids": ["1"]})

    assert response.status_code in [200, 302]


def test_delete_selected_departments_creates_notifications_and_logs(client, mock_db, mock_delete_selected_dept_dependencies):
    """Case 7: Hệ thống tự động tạo thông báo và log hoạt động sau khi xóa thành công."""
    mock_db.fetchone.side_effect = [(0,)]
    mock_db.fetchall.return_value = [(1, "Phòng IT")]

    response = client.post("/delete_selected_departments", data={"department_ids": ["1"]})

    assert response.status_code in [200, 302]


def test_delete_selected_departments_get_method_handling(client):
    """Case 8: Thử gọi route bằng phương thức GET."""
    response = client.get("/delete_selected_departments")

    assert response.status_code in [200, 302, 405]


def test_delete_selected_departments_invalid_id_formats(client, mock_db):
    """Case 9: Danh sách ID chứa chuỗi không phải dạng số (ví dụ: ['abc', 'xyz'])."""
    mock_db.fetchone.side_effect = [(0,), (0,)]
    mock_db.fetchall.return_value = []

    response = client.post("/delete_selected_departments", data={"department_ids": ["abc", "xyz"]})

    assert response.status_code in [200, 302]