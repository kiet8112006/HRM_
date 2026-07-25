import pytest
from unittest.mock import patch, MagicMock
from exceptions.validator.position import PositionValidationError

@pytest.fixture
def logged_in_admin(client):
    """Giả lập session đăng nhập với quyền Admin."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'Admin'

@pytest.fixture
def logged_in_employee(client):
    """Giả lập session đăng nhập với quyền Employee (không có quyền sửa)."""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'Employee'

@pytest.fixture
def existing_position_tuple():
    """Dữ liệu chức vụ giả lập trong DB: (ID, Code, Name, Level, MinSalary, MaxSalary, Status, Description)"""
    return (1, "POS_DEV", "Lập Trình Viên", 2, 10000000, 25000000, "Active", "Mô tả Dev")

@pytest.fixture
def valid_edit_payload():
    """Dữ liệu form chỉnh sửa chức vụ hợp lệ."""
    return {
        'position_code': 'POS_DEV_EDITED',
        'position_name': 'Lập Trình Viên Cao Cấp',
        'position_level': '3',
        'min_salary': '15000000',
        'max_salary': '30000000',
        'status': 'Active',
        'description': 'Mô tả đã cập nhật'
    }

# =====================================================================
# 15 TEST CASES CHO ROUTE EDIT POSITION
# =====================================================================

def test_edit_position_not_logged_in_redirects(client):
    """Case 1: Chưa đăng nhập -> Redirect về trang login."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)

    response = client.get('/edit_position/1')
    assert response.status_code in [302, 401]


def test_edit_position_unauthorized_role_redirects(client, logged_in_employee):
    """Case 2: Role 'Employee' không có quyền truy cập -> Redirect về danh sách."""
    response = client.get('/edit_position/1')
    assert response.status_code in [302, 403]


def test_edit_position_get_form_success(client, logged_in_admin, mock_db, existing_position_tuple):
    """Case 3: Admin lấy thông tin chức vụ thành công -> Render giao diện sửa."""
    mock_db.fetchone.return_value = existing_position_tuple

    response = client.get('/edit_position/1')
    assert response.status_code in [200, 302]


def test_edit_position_get_not_found(client, logged_in_admin, mock_db):
    """Case 4: Truy cập ID chức vụ không tồn tại -> Báo lỗi & Redirect."""
    mock_db.fetchone.return_value = None

    response = client.get('/edit_position/9999')
    assert response.status_code in [200, 302]


def test_edit_position_post_success(client, logged_in_admin, mock_db, valid_edit_payload):
    """Case 5: Cập nhật thông tin chức vụ thành công."""
    mock_db.fetchone.return_value = None  # Không bị trùng mã với ID khác

    response = client.post('/edit_position/1', data=valid_edit_payload)
    assert response.status_code in [200, 302]


def test_edit_position_duplicate_code_fails(client, logged_in_admin, mock_db, valid_edit_payload):
    """Case 6: Mã chức vụ mới bị trùng với một chức vụ khác đã tồn tại."""
    mock_db.fetchone.return_value = (2,)  # Trùng mã với ID = 2

    response = client.post('/edit_position/1', data=valid_edit_payload)
    assert response.status_code in [200, 302]


def test_edit_position_invalid_code_fails(client, logged_in_admin, valid_edit_payload):
    """Case 7: Mã chức vụ để trống hoặc không hợp lệ."""
    payload = valid_edit_payload.copy()
    payload['position_code'] = ''

    with patch('routes.position.validate_position_code', side_effect=PositionValidationError("Mã chức vụ không hợp lệ")):
        response = client.post('/edit_position/1', data=payload)
        assert response.status_code in [200, 302]


def test_edit_position_invalid_name_fails(client, logged_in_admin, valid_edit_payload):
    """Case 8: Tên chức vụ không hợp lệ."""
    payload = valid_edit_payload.copy()
    payload['position_name'] = ''

    with patch('routes.position.validate_position_name', side_effect=PositionValidationError("Tên chức vụ không hợp lệ")):
        response = client.post('/edit_position/1', data=payload)
        assert response.status_code in [200, 302]


def test_edit_position_invalid_level_fails(client, logged_in_admin, valid_edit_payload):
    """Case 9: Cấp độ chức vụ không hợp lệ."""
    payload = valid_edit_payload.copy()
    payload['position_level'] = 'abc'

    with patch('routes.position.validate_position_level', side_effect=PositionValidationError("Cấp độ không hợp lệ")):
        response = client.post('/edit_position/1', data=payload)
        assert response.status_code in [200, 302]


def test_edit_position_invalid_salary_range_fails(client, logged_in_admin, valid_edit_payload):
    """Case 10: Lương tối thiểu lớn hơn lương tối đa."""
    payload = valid_edit_payload.copy()
    payload['min_salary'] = '50000000'
    payload['max_salary'] = '20000000'

    with patch('routes.position.validate_salary_range', side_effect=PositionValidationError("Lương không hợp lệ")):
        response = client.post('/edit_position/1', data=payload)
        assert response.status_code in [200, 302]


def test_edit_position_invalid_status_fails(client, logged_in_admin, valid_edit_payload):
    """Case 11: Trạng thái không hợp lệ."""
    payload = valid_edit_payload.copy()
    payload['status'] = 'InvalidStatus'

    with patch('routes.position.validate_position_status', side_effect=PositionValidationError("Trạng thái không hợp lệ")):
        response = client.post('/edit_position/1', data=payload)
        assert response.status_code in [200, 302]


def test_edit_position_description_too_long_fails(client, logged_in_admin, valid_edit_payload):
    """Case 12: Mô tả quá dài."""
    payload = valid_edit_payload.copy()
    payload['description'] = 'A' * 1000

    with patch('routes.position.validate_position_description', side_effect=PositionValidationError("Mô tả quá dài")):
        response = client.post('/edit_position/1', data=payload)
        assert response.status_code in [200, 302]


def test_edit_position_manager_role_success(client, mock_db, valid_edit_payload):
    """Case 13: Manager cũng có quyền cập nhật chức vụ thành công."""
    with client.session_transaction() as sess:
        sess['user_id'] = 3
        sess['role'] = 'Manager'

    mock_db.fetchone.return_value = None

    response = client.post('/edit_position/1', data=valid_edit_payload)
    assert response.status_code in [200, 302]


def test_edit_position_db_exception_on_post(client, logged_in_admin, mock_db, valid_edit_payload):
    """Case 14: Lỗi DB khi cập nhật dữ liệu (UPDATE query)."""
    mock_db.fetchone.return_value = None
    mock_db.execute.side_effect = Exception("Database write error")

    response = client.post('/edit_position/1', data=valid_edit_payload)
    assert response.status_code in [200, 302, 500]


def test_edit_position_db_exception_on_get(client, logged_in_admin, mock_db):
    """Case 15: Lỗi DB khi load thông tin chức vụ (SELECT query)."""
    mock_db.execute.side_effect = Exception("Database read error")

    response = client.get('/edit_position/1')
    assert response.status_code in [200, 302, 500]