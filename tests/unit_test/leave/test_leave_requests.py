import pytest
from unittest.mock import patch, MagicMock

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
        sess['user_id'] = 2
        sess['role'] = 'Manager'

@pytest.fixture
def logged_in_employee(client):
    """Giả lập session Employee."""
    with client.session_transaction() as sess:
        sess['user_id'] = 3
        sess['role'] = 'Employee'

# =====================================================================
# 12 TEST CASES CHO ROUTE LEAVE REQUESTS (DANH SÁCH & LỌC)
# =====================================================================

def test_leave_requests_not_logged_in_redirects(client):
    """Case 1: Chưa đăng nhập -> Redirect về trang login."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)

    response = client.get('/leave_requests')
    assert response.status_code in [302, 401]


def test_leave_requests_employee_role_unauthorized(client, logged_in_employee):
    """Case 2: Role Employee không có quyền -> 403 hoặc Redirect."""
    response = client.get('/leave_requests')
    assert response.status_code in [302, 403]


def test_leave_requests_admin_access_success(client, logged_in_admin, mock_db):
    """Case 3: Admin truy cập thành công."""
    mock_db.fetchone.return_value = (10,)
    mock_db.fetchall.return_value = [
        (1, 'Nguyễn Văn A', 'Nghỉ phép năm', '2026-04-01', '2026-04-02', 2, 'Việc gia đình', 'Chờ duyệt', None, None)
    ]

    response = client.get('/leave_requests')
    assert response.status_code == 200


def test_leave_requests_manager_access_success(client, logged_in_manager, mock_db):
    """Case 4: Manager truy cập thành công."""
    mock_db.fetchone.return_value = (5,)
    mock_db.fetchall.return_value = []

    response = client.get('/leave_requests')
    assert response.status_code == 200


def test_leave_requests_filter_by_keyword(client, logged_in_admin, mock_db):
    """Case 5: Tìm kiếm theo tên nhân viên (keyword)."""
    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = [
        (1, 'Nguyễn Văn A', 'Nghỉ phép năm', '2026-04-01', '2026-04-02', 2, 'Ốm', 'Đã duyệt', 'Admin', '2026-03-31')
    ]

    response = client.get('/leave_requests?keyword=Nguyễn')
    assert response.status_code == 200


def test_leave_requests_filter_by_status(client, logged_in_admin, mock_db):
    """Case 6: Lọc danh sách theo trạng thái (Status)."""
    mock_db.fetchone.return_value = (2,)
    mock_db.fetchall.return_value = []

    response = client.get('/leave_requests?status=Chờ duyệt')
    assert response.status_code == 200


def test_leave_requests_filter_by_leave_type(client, logged_in_admin, mock_db):
    """Case 7: Lọc danh sách theo loại nghỉ phép (leave_type)."""
    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = []

    response = client.get('/leave_requests?leave_type=Nghỉ bệnh')
    assert response.status_code == 200


def test_leave_requests_pagination_valid_page(client, logged_in_admin, mock_db):
    """Case 8: Phân trang hợp lệ (page=2)."""
    mock_db.fetchone.return_value = (25,) # Tổng 25 bản ghi -> 3 trang
    mock_db.fetchall.return_value = []

    response = client.get('/leave_requests?page=2')
    assert response.status_code == 200


def test_leave_requests_pagination_invalid_page(client, logged_in_admin, mock_db):
    """Case 9: Trang âm hoặc không phải số -> Flask tự ép kiểu mặc định về 1."""
    mock_db.fetchone.return_value = (5,)
    mock_db.fetchall.return_value = []

    response = client.get('/leave_requests?page=-1')
    assert response.status_code in [200, 400]


def test_leave_requests_empty_result(client, logged_in_admin, mock_db):
    """Case 10: DB không có đơn nghỉ phép nào."""
    mock_db.fetchone.return_value = (0,)
    mock_db.fetchall.return_value = []

    response = client.get('/leave_requests')
    assert response.status_code == 200


def test_leave_requests_db_exception_handling(client, logged_in_admin, mock_db):
    """Case 11: Ngoại lệ DB trong quá trình query -> Bắt exception và báo flash."""
    mock_db.execute.side_effect = Exception("Database Timeout Error")

    response = client.get('/leave_requests')
    assert response.status_code == 200


def test_leave_requests_combined_filters(client, logged_in_admin, mock_db):
    """Case 12: Kết hợp đồng thời Keyword + Status + LeaveType + Page."""
    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = []

    response = client.get('/leave_requests?keyword=Trần&status=Đã duyệt&leave_type=Nghỉ phép năm&page=1')
    assert response.status_code == 200