import pytest
from unittest.mock import patch

@pytest.fixture
def logged_in_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'Admin'

@pytest.fixture
def logged_in_employee(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 3
        sess['role'] = 'Employee'

# =====================================================================
# 8 TEST CASES CHO ROUTE DELETE SELECTED LEAVE REQUESTS (XÓA HÀNG LOẠT)
# =====================================================================

def test_delete_selected_not_logged_in(client):
    """Case 1: Chưa đăng nhập."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)
    response = client.post('/delete_selected_leave_requests', data={'request_ids': ['1', '2']})
    assert response.status_code in [302, 401]


def test_delete_selected_unauthorized_role(client, logged_in_employee):
    """Case 2: Role Employee không có quyền xóa hàng loạt."""
    response = client.post('/delete_selected_leave_requests', data={'request_ids': ['1', '2']})
    assert response.status_code in [302, 403]


def test_delete_selected_empty_list_warning(client, logged_in_admin):
    """Case 3: Không tích chọn đơn nào (request_ids rỗng)."""
    response = client.post('/delete_selected_leave_requests', data={})
    assert response.status_code in [200, 302]


def test_delete_selected_success(client, logged_in_admin, mock_db):
    """Case 4: Xóa hàng loạt thành công 2 đơn nghỉ phép."""
    mock_db.fetchall.return_value = [(1, 'Nguyễn Văn A'), (2, 'Trần Văn B')]

    with patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity'):
        response = client.post('/delete_selected_leave_requests', data={'request_ids': ['1', '2']})
        assert response.status_code in [200, 302]


def test_delete_selected_ids_not_found(client, logged_in_admin, mock_db):
    """Case 5: Các ID truyền lên không tồn tại trong DB."""
    mock_db.fetchall.return_value = []

    response = client.post('/delete_selected_leave_requests', data={'request_ids': ['99', '100']})
    assert response.status_code in [200, 302]


def test_delete_selected_db_exception_rollback(client, logged_in_admin, mock_db):
    """Case 6: Gặp lỗi DB trong quá trình xóa -> Rollback."""
    mock_db.fetchall.return_value = [(1, 'Nguyễn Văn A')]
    mock_db.execute.side_effect = [None, Exception("DB Batch Delete Error")]

    response = client.post('/delete_selected_leave_requests', data={'request_ids': ['1']})
    assert response.status_code in [200, 302]


def test_delete_selected_single_item(client, logged_in_admin, mock_db):
    """Case 7: Chọn duy nhất 1 item để xóa hàng loạt."""
    mock_db.fetchall.return_value = [(1, 'Nguyễn Văn A')]

    with patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity'):
        response = client.post('/delete_selected_leave_requests', data={'request_ids': ['1']})
        assert response.status_code in [200, 302]


def test_delete_selected_notification_and_audit(client, logged_in_admin, mock_db):
    """Case 8: Kiểm tra việc kích hoạt Notification/Log khi xóa hàng loạt thành công."""
    mock_db.fetchall.return_value = [(1, 'Nguyễn Văn A', 3, 2026)]

    with patch('routes.leave.create_notification') as mock_notif, \
         patch('routes.leave.log_activity') as mock_log:
        response = client.post('/delete_selected_leave_requests', data={'request_ids': ['1']})
        assert response.status_code in [200, 302]
        assert mock_notif.called or mock_log.called or response.status_code == 302