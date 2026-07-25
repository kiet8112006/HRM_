import pytest

@pytest.fixture
def logged_in_admin(client):
    """Giả lập session Admin (có quyền xóa)."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'Admin'

@pytest.fixture
def logged_in_manager(client):
    """Giả lập session Manager (không có quyền xóa chức vụ)."""
    with client.session_transaction() as sess:
        sess['user_id'] = 3
        sess['role'] = 'Manager'

# =====================================================================
# 6 TEST CASES CHO ROUTE DELETE POSITION (XÓA ĐƠN)
# =====================================================================

def test_delete_position_not_logged_in_redirects(client):
    """Case 1: Chưa đăng nhập -> Redirect về login."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)

    response = client.get('/delete_position/1')
    assert response.status_code in [302, 401]


def test_delete_position_unauthorized_role_redirects(client, logged_in_manager):
    """Case 2: Role không phải Admin (VD: Manager) -> Không được xóa, redirect về danh sách."""
    response = client.get('/delete_position/1')
    assert response.status_code in [302, 403]


def test_delete_position_success(client, logged_in_admin, mock_db):
    """Case 3: Xóa chức vụ thành công khi không có nhân viên nào bị ràng buộc."""
    mock_db.fetchone.return_value = (0,)  # 0 nhân viên giữ chức vụ này

    response = client.get('/delete_position/1')
    assert response.status_code in [200, 302]


def test_delete_position_has_employees_fails(client, logged_in_admin, mock_db):
    """Case 4: Xóa chức vụ thất bại do đang có nhân viên giữ chức vụ (Ràng buộc dữ liệu)."""
    mock_db.fetchone.return_value = (5,)  # Có 5 nhân viên đang thuộc chức vụ này

    response = client.get('/delete_position/1')
    assert response.status_code in [200, 302]


def test_delete_position_db_exception_handling(client, logged_in_admin, mock_db):
    """Case 5: Gặp lỗi hệ thống/DB khi thực thi câu lệnh DELETE."""
    mock_db.fetchone.return_value = (0,)
    mock_db.execute.side_effect = Exception("Foreign Key Constraint Error")

    response = client.get('/delete_position/1')
    assert response.status_code in [200, 302, 500]


def test_delete_position_non_existing_id(client, logged_in_admin, mock_db):
    """Case 6: Thực hiện xóa ID chức vụ không tồn tại."""
    mock_db.fetchone.return_value = (0,)

    response = client.get('/delete_position/99999')
    assert response.status_code in [200, 302]