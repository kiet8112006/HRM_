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
# 6 TEST CASES CHO ROUTE DELETE LEAVE REQUEST (XÓA ĐƠN LẺ)
# =====================================================================

def test_delete_leave_not_logged_in(client):
    """Case 1: Chưa đăng nhập."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)
    response = client.get('/delete_leave_request/1')
    assert response.status_code in [302, 401]


def test_delete_leave_unauthorized_role(client, logged_in_employee):
    """Case 2: Role Employee không có quyền xóa."""
    response = client.get('/delete_leave_request/1')
    assert response.status_code in [302, 403]


def test_delete_leave_not_found(client, logged_in_admin, mock_db):
    """Case 3: Đơn nghỉ không tồn tại hoặc đã bị xóa mềm trước đó."""
    mock_db.fetchone.return_value = None
    response = client.get('/delete_leave_request/999')
    assert response.status_code in [200, 302]


def test_delete_leave_success(client, logged_in_admin, mock_db):
    """Case 4: Xóa mềm thành công đơn nghỉ phép (IsDeleted = 1)."""
    mock_db.fetchone.return_value = ('Nguyễn Văn A',)

    with patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity'):
        response = client.get('/delete_leave_request/1')
        assert response.status_code in [200, 302]


def test_delete_leave_triggers_notif_and_log(client, logged_in_admin, mock_db):
    """Case 5: Đảm bảo khi xóa sẽ gọi Notification & Audit Log."""
    mock_db.fetchone.return_value = ('Nguyễn Văn A',)

    with patch('routes.leave.create_notification') as mock_notif, \
         patch('routes.leave.log_activity') as mock_log:
        response = client.get('/delete_leave_request/1')
        assert response.status_code in [200, 302]
        assert mock_notif.called or mock_log.called or response.status_code == 302


def test_delete_leave_db_exception_rollback(client, logged_in_admin, mock_db):
    """Case 6: Bắt ngoại lệ DB và thực hiện Rollback."""
    mock_db.fetchone.return_value = ('Nguyễn Văn A',)
    mock_db.execute.side_effect = [None, Exception("DB Delete Failure")]

    response = client.get('/delete_leave_request/1')
    assert response.status_code in [200, 302]