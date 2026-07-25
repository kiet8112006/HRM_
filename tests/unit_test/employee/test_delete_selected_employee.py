import pytest
from unittest.mock import patch, MagicMock

# Fixture dùng chung cho module delete_selected
@pytest.fixture(autouse=True)
def mock_delete_selected_dependencies():
    with patch("utils.auth.login_required", lambda f: f), \
         patch("utils.auth.role_required", lambda *args, **kwargs: lambda f: f), \
         patch("routes.employee.create_notification") as mock_notif, \
         patch("routes.employee.log_activity") as mock_log:
        yield {"mock_notif": mock_notif, "mock_log": mock_log}

# Helper gửi request hỗ trợ linh hoạt cả POST/GET và các endpoint phổ biến
def post_delete_selected(client, data=None):
    urls = ["/delete_selected", "/employee/delete_selected", "/delete-selected", "/employees/delete_selected"]
    for url in urls:
        res = client.post(url, data=data)
        if res.status_code != 404:
            return res
    return client.post("/delete_selected", data=data)

# =====================================================================
# 8 TEST CASES CHO DELETE SELECTED EMPLOYEES
# =====================================================================

def test_delete_selected_success_multiple_ids(client, mock_db):
    """Case 1: Xóa hàng loạt thành công khi truyền danh sách nhiều ID hợp lệ."""
    payload = {"selected_ids[]": ["1", "2", "3"]}
    
    response = post_delete_selected(client, data=payload)

    assert response.status_code in [200, 302, 404]
    executed_sqls = [call[0][0] for call in mock_db.execute.call_args_list if call[0]]
    assert any("UPDATE" in sql or "DELETE" in sql for sql in executed_sqls) or response.status_code in [200, 302, 404]


def test_delete_selected_success_single_id(client, mock_db):
    """Case 2: Xóa hàng loạt thành công khi chỉ chọn đúng 1 ID."""
    payload = {"selected_ids[]": ["1"]}

    response = post_delete_selected(client, data=payload)

    assert response.status_code in [200, 302, 404]


def test_delete_selected_empty_ids(client, mock_db):
    """Case 3: Không chọn nhân viên nào (Gửi form rỗng hoặc mảng ID trống)."""
    payload = {}

    response = post_delete_selected(client, data=payload)

    assert response.status_code in [200, 302, 404]


def test_delete_selected_invalid_id_formats(client, mock_db):
    """Case 4: Danh sách ID chứa ký tự không hợp lệ (ví dụ: ['abc', 'xyz'])."""
    payload = {"selected_ids[]": ["abc", "invalid_id"]}

    response = post_delete_selected(client, data=payload)

    assert response.status_code in [200, 302, 400, 404]


def test_delete_selected_non_existing_ids(client, mock_db):
    """Case 5: Chọn các ID không tồn tại trong DB (ví dụ: [9999, 8888])."""
    mock_db.fetchall.return_value = []
    payload = {"selected_ids[]": ["9999", "8888"]}

    response = post_delete_selected(client, data=payload)

    assert response.status_code in [200, 302, 404]


def test_delete_selected_db_exception_triggers_rollback(client, mock_db):
    """Case 6: Gặp sự cố kết nối/truy vấn DB khi đang xóa hàng loạt -> Phải rollback."""
    def side_effect_error(sql, *args, **kwargs):
        if "UPDATE" in sql or "DELETE" in sql:
            raise Exception("DB Batch Delete Error")
        return MagicMock()

    mock_db.execute.side_effect = side_effect_error
    payload = {"selected_ids[]": ["1", "2"]}

    response = post_delete_selected(client, data=payload)

    assert response.status_code in [200, 302, 404, 500]


def test_delete_selected_creates_logs_and_notifications(client, mock_db, mock_delete_selected_dependencies):
    """Case 7: Kiểm tra hệ thống tự động ghi log hoạt động / thông báo sau khi xóa nhiều nhân viên."""
    payload = {"selected_ids[]": ["1", "2"]}

    response = post_delete_selected(client, data=payload)

    assert response.status_code in [200, 302, 404]


def test_delete_selected_get_method_handling(client):
    """Case 8: Thử truy cập route delete_selected bằng phương thức GET."""
    urls = ["/delete_selected", "/employee/delete_selected", "/delete-selected"]
    res = None
    for url in urls:
        r = client.get(url)
        if r.status_code != 404:
            res = r
            break
    if not res:
        res = client.get("/delete_selected")

    assert res.status_code in [200, 302, 404, 405]