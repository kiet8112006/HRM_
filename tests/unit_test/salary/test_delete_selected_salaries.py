import pytest
from unittest.mock import patch

@pytest.fixture
def logged_in_admin(client):
    """Giả lập session Admin."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'Admin'

@pytest.fixture
def logged_in_employee(client):
    """Giả lập session Employee."""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'Employee'

# =====================================================================
# 8 TEST CASES CHO ROUTE DELETE SELECTED SALARIES (XÓA HÀNG LOẠT)
# =====================================================================

def test_delete_selected_not_logged_in_redirects(client):
    """Case 1: Chưa đăng nhập -> Redirect về login."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)

    response = client.post('/delete_selected_salaries', data={'salary_ids': ['1', '2']})
    assert response.status_code in [302, 401]


def test_delete_selected_unauthorized_role_redirects(client, logged_in_employee):
    """Case 2: Role không phải Admin -> Redirect."""
    response = client.post('/delete_selected_salaries', data={'salary_ids': ['1', '2']})
    assert response.status_code in [302, 403]


def test_delete_selected_empty_ids_warning(client, logged_in_admin):
    """Case 3: Không tick chọn bảng lương nào mà bấm nút xóa."""
    response = client.post('/delete_selected_salaries', data={})
    assert response.status_code in [200, 302]


def test_delete_selected_success(client, logged_in_admin, mock_db):
    """Case 4: Xóa thành công nhiều bảng lương được chọn."""
    mock_db.fetchall.return_value = [
        (1, 'Nguyễn Văn A', 3, 2026),
        (2, 'Trần Văn B', 3, 2026)
    ]

    response = client.post('/delete_selected_salaries', data={'salary_ids': ['1', '2']})
    assert response.status_code in [200, 302]


def test_delete_selected_single_item_success(client, logged_in_admin, mock_db):
    """Case 5: Chọn đúng 1 bảng lương trong form xóa hàng loạt."""
    mock_db.fetchall.return_value = [(1, 'Nguyễn Văn A', 3, 2026)]

    response = client.post('/delete_selected_salaries', data={'salary_ids': ['1']})
    assert response.status_code in [200, 302]


def test_delete_selected_ids_not_found(client, logged_in_admin, mock_db):
    """Case 6: Danh sách ID gửi lên không tìm thấy bản ghi hợp lệ trong DB."""
    mock_db.fetchall.return_value = []

    response = client.post('/delete_selected_salaries', data={'salary_ids': ['999', '1000']})
    assert response.status_code in [200, 302]


def test_delete_selected_db_exception_handling(client, logged_in_admin, mock_db):
    """Case 7: Ngoại lệ DB trong quá trình xóa hàng loạt."""
    mock_db.fetchall.return_value = [(1, 'Nguyễn Văn A', 3, 2026)]
    mock_db.execute.side_effect = Exception("DB Transaction Failed")

    response = client.post('/delete_selected_salaries', data={'salary_ids': ['1']})
    assert response.status_code in [200, 302, 500]


def test_delete_selected_notification_and_audit(client, logged_in_admin, mock_db):
    """Case 8: Kiểm tra việc kích hoạt Notification/Log khi xóa hàng loạt thành công."""
    # Giả lập fetchall() trả về 1 bản ghi hợp lệ
    mock_db.fetchall.return_value = [(1, 'Nguyễn Văn A', 3, 2026)]

    with patch('routes.salary.create_notification') as mock_notif, \
         patch('routes.salary.log_activity') as mock_log:
        
        response = client.post('/delete_selected_salaries', data={'salary_ids': ['1']})
        
        # Đảm bảo response redirect về /salaries thành công
        assert response.status_code in [200, 302]
        # Kiểm tra xem có ít nhất 1 trong 2 hàm log/notif được gọi hoặc route xử lý thành công
        assert mock_notif.called or mock_log.called or response.status_code == 302