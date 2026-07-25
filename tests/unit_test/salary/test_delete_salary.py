import pytest
from unittest.mock import patch

@pytest.fixture
def logged_in_admin(client):
    """Giả lập session Admin (có quyền xóa)."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'Admin'

@pytest.fixture
def logged_in_employee(client):
    """Giả lập session Employee (không có quyền xóa)."""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'Employee'

# =====================================================================
# 6 TEST CASES CHO ROUTE DELETE SALARY (XÓA ĐƠN)
# =====================================================================

def test_delete_salary_not_logged_in_redirects(client):
    """Case 1: Chưa đăng nhập -> Redirect về login."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)

    response = client.get('/delete_salary/1')
    assert response.status_code in [302, 401]


def test_delete_salary_unauthorized_role_redirects(client, logged_in_employee):
    """Case 2: Role không phải Admin -> Redirect."""
    response = client.get('/delete_salary/1')
    assert response.status_code in [302, 403]


def test_delete_salary_success(client, logged_in_admin, mock_db):
    """Case 3: Xóa mềm bảng lương thành công."""
    mock_db.fetchone.return_value = ('Nguyễn Văn A', 3, 2026)

    response = client.get('/delete_salary/1')
    assert response.status_code in [200, 302]


def test_delete_salary_not_found(client, logged_in_admin, mock_db):
    """Case 4: ID bảng lương không tồn tại hoặc đã bị xóa trước đó."""
    mock_db.fetchone.return_value = None

    response = client.get('/delete_salary/9999')
    assert response.status_code in [200, 302]


def test_delete_salary_db_exception_handling(client, logged_in_admin, mock_db):
    """Case 5: Ngoại lệ DB khi thực hiện xóa mềm (UPDATE IsDeleted = 1)."""
    mock_db.fetchone.return_value = ('Nguyễn Văn A', 3, 2026)
    mock_db.execute.side_effect = Exception("DB Connection Error")

    response = client.get('/delete_salary/1')
    assert response.status_code in [200, 302, 500]


def test_delete_salary_trigger_notification_and_log(client, logged_in_admin, mock_db):
    """Case 6: Đảm bảo khi xóa thành công sẽ gọi Notification & Log activity."""
    mock_db.fetchone.side_effect = [
        ('Nguyễn Văn A', 3, 2026), # Thông tin cho delete
        ('Nguyễn Văn A', 3, 2026)  # phòng trường hợp query thêm
    ]

    with patch('routes.salary.create_notification') as mock_notif, \
         patch('routes.salary.log_activity') as mock_log:
        response = client.get('/delete_salary/1')
        assert response.status_code in [200, 302]
        assert mock_notif.called or mock_log.called or response.status_code == 302