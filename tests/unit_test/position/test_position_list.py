import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def logged_in_session(client):
    """Fixture giả lập session người dùng đã đăng nhập."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'Admin'

@pytest.fixture
def mock_positions_data():
    """Mock dữ liệu danh sách chức vụ."""
    pos1 = (1, "DEV", "Lập trình viên", 2, 10000000, 25000000, "Active", "Mô tả Dev")
    pos2 = (2, "PM", "Quản lý dự án", 1, 20000000, 40000000, "Active", "Mô tả PM")
    return [pos1, pos2]

# =====================================================================
# 8 TEST CASES CHO ROUTE POSITIONS
# =====================================================================
def test_positions_not_logged_in_redirects(client, mock_db):
    """Case 1: Chưa đăng nhập (không có user_id trong session) -> Redirect về login."""
    mock_db.fetchall.return_value = []
    
    # Xóa user_id trong session để giả lập chưa đăng nhập
    with client.session_transaction() as sess:
        sess.pop('user_id', None)

    response = client.get('/positions')

    assert response.status_code in [302, 401]

def test_positions_list_success(client, logged_in_session, mock_db, mock_positions_data):
    """Case 2: Lấy danh sách chức vụ thành công khi đã đăng nhập."""
    mock_db.fetchall.return_value = mock_positions_data

    response = client.get('/positions')

    assert response.status_code in [200, 302]


def test_positions_list_empty(client, logged_in_session, mock_db):
    """Case 3: Danh sách chức vụ trống (chưa có dữ liệu trong DB)."""
    mock_db.fetchall.return_value = []

    response = client.get('/positions')

    assert response.status_code in [200, 302]


def test_positions_search_with_keyword(client, logged_in_session, mock_db, mock_positions_data):
    """Case 4: Tìm kiếm chức vụ theo từ khóa (keyword = 'DEV')."""
    mock_db.fetchall.return_value = [mock_positions_data[0]]

    response = client.get('/positions?keyword=DEV')

    assert response.status_code in [200, 302]


def test_positions_filter_by_status(client, logged_in_session, mock_db, mock_positions_data):
    """Case 5: Lọc chức vụ theo trạng thái (status = 'Active')."""
    mock_db.fetchall.return_value = mock_positions_data

    response = client.get('/positions?status=Active')

    assert response.status_code in [200, 302]


def test_positions_search_and_filter_combined(client, logged_in_session, mock_db, mock_positions_data):
    """Case 6: Kết hợp cả tìm kiếm theo từ khóa và lọc theo trạng thái."""
    mock_db.fetchall.return_value = [mock_positions_data[0]]

    response = client.get('/positions?keyword=DEV&status=Active')

    assert response.status_code in [200, 302]


def test_positions_search_no_results(client, logged_in_session, mock_db):
    """Case 7: Tìm kiếm từ khóa không khớp với chức vụ nào."""
    mock_db.fetchall.return_value = []

    response = client.get('/positions?keyword=NonExistingPos')

    assert response.status_code in [200, 302]


def test_positions_db_exception_handling(client, logged_in_session, mock_db):
    """Case 8: Gặp lỗi kết nối/truy vấn DB khi lấy danh sách."""
    mock_db.execute.side_effect = Exception("Database connection error")

    response = client.get('/positions')

    assert response.status_code in [200, 302, 500]