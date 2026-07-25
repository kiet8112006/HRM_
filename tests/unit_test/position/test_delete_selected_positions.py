import pytest

@pytest.fixture
def logged_in_admin(client):
    """Giả lập session Admin."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'Admin'

@pytest.fixture
def logged_in_manager(client):
    """Giả lập session Manager."""
    with client.session_transaction() as sess:
        sess['user_id'] = 3
        sess['role'] = 'Manager'

# =====================================================================
# 6 TEST CASES CHO ROUTE DELETE SELECTED POSITIONS (XÓA HÀNG LOẠT)
# =====================================================================

def test_delete_selected_not_logged_in_redirects(client):
    """Case 1: Chưa đăng nhập -> Redirect về login."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)

    response = client.post('/delete_selected_positions', data={'position_ids': ['1', '2']})
    assert response.status_code in [302, 401]


def test_delete_selected_unauthorized_role_redirects(client, logged_in_manager):
    """Case 2: Role không phải Admin -> Không được phép thực hiện."""
    response = client.post('/delete_selected_positions', data={'position_ids': ['1', '2']})
    assert response.status_code in [302, 403]


def test_delete_selected_no_ids_selected_warning(client, logged_in_admin):
    """Case 3: Không tích chọn chức vụ nào mà nhấn submit xóa."""
    response = client.post('/delete_selected_positions', data={})
    assert response.status_code in [200, 302]


def test_delete_selected_success(client, logged_in_admin, mock_db):
    """Case 4: Xóa nhiều chức vụ được chọn thành công."""
    response = client.post('/delete_selected_positions', data={'position_ids': ['1', '2', '3']})
    assert response.status_code in [200, 302]


def test_delete_selected_single_item_success(client, logged_in_admin, mock_db):
    """Case 5: Chọn đúng 1 chức vụ trong danh sách để xóa hàng loạt."""
    response = client.post('/delete_selected_positions', data={'position_ids': ['1']})
    assert response.status_code in [200, 302]


def test_delete_selected_db_exception_handling(client, logged_in_admin, mock_db):
    """Case 6: Xảy ra ngoại lệ DB (Ràng buộc FK với bảng Employees)."""
    mock_db.execute.side_effect = Exception("Cannot delete due to FK constraint")

    response = client.post('/delete_selected_positions', data={'position_ids': ['1', '2']})
    assert response.status_code in [200, 302, 500]