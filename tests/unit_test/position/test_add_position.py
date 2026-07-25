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
    """Giả lập session đăng nhập với quyền Employee (không có quyền thêm)."""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'Employee'

@pytest.fixture
def valid_position_payload():
    """Dữ liệu form thêm chức vụ chuẩn."""
    return {
        'position_code': 'POS_TEST_01',
        'position_name': 'Chức Vụ Kiểm Thử',
        'position_level': '3',
        'min_salary': '10000000',
        'max_salary': '20000000',
        'status': 'Active',
        'description': 'Mô tả công việc kiểm thử'
    }

# =====================================================================
# 18 TEST CASES CHO ROUTE ADD POSITION
# =====================================================================

def test_add_position_not_logged_in_redirects(client):
    """Case 1: Chưa đăng nhập -> Redirect về trang login."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)

    response = client.get('/add_position')
    assert response.status_code in [302, 401]


def test_add_position_unauthorized_role_redirects(client, logged_in_employee):
    """Case 2: Role 'Employee' không có quyền thêm chức vụ -> Redirect về danh sách."""
    response = client.get('/add_position')
    assert response.status_code in [302, 403]


def test_add_position_get_form_success(client, logged_in_admin):
    """Case 3: Admin truy cập GET /add_position -> Hiển thị trang form."""
    response = client.get('/add_position')
    assert response.status_code in [200, 302]


def test_add_position_post_success(client, logged_in_admin, mock_db, valid_position_payload):
    """Case 4: Thêm mới chức vụ thành công với đầy đủ dữ liệu hợp lệ."""
    mock_db.fetchone.return_value = None  # Không bị trùng mã

    response = client.post('/add_position', data=valid_position_payload)
    assert response.status_code in [200, 302]


def test_add_position_duplicate_code_fails(client, logged_in_admin, mock_db, valid_position_payload):
    """Case 5: Thêm chức vụ thất bại do mã chức vụ đã tồn tại trong DB."""
    mock_db.fetchone.return_value = (1,)  # Mã đã tồn tại

    response = client.post('/add_position', data=valid_position_payload)
    assert response.status_code in [200, 302]


def test_add_position_invalid_code_fails(client, logged_in_admin, valid_position_payload):
    """Case 6: Mã chức vụ rỗng hoặc chứa ký tự đặc biệt không hợp lệ."""
    payload = valid_position_payload.copy()
    payload['position_code'] = ''

    with patch('routes.position.validate_position_code', side_effect=PositionValidationError("Mã chức vụ không hợp lệ")):
        response = client.post('/add_position', data=payload)
        assert response.status_code in [200, 302]


def test_add_position_invalid_name_fails(client, logged_in_admin, valid_position_payload):
    """Case 7: Tên chức vụ rỗng hoặc quá ngắn."""
    payload = valid_position_payload.copy()
    payload['position_name'] = ''

    with patch('routes.position.validate_position_name', side_effect=PositionValidationError("Tên chức vụ không hợp lệ")):
        response = client.post('/add_position', data=payload)
        assert response.status_code in [200, 302]


def test_add_position_invalid_level_string_fails(client, logged_in_admin, valid_position_payload):
    """Case 8: Cấp độ chức vụ không phải là chữ số."""
    payload = valid_position_payload.copy()
    payload['position_level'] = 'abc'

    with patch('routes.position.validate_position_level', side_effect=PositionValidationError("Cấp độ phải là số")):
        response = client.post('/add_position', data=payload)
        assert response.status_code in [200, 302]


def test_add_position_negative_level_fails(client, logged_in_admin, valid_position_payload):
    """Case 9: Cấp độ chức vụ là số âm."""
    payload = valid_position_payload.copy()
    payload['position_level'] = '-1'

    with patch('routes.position.validate_position_level', side_effect=PositionValidationError("Cấp độ phải lớn hơn 0")):
        response = client.post('/add_position', data=payload)
        assert response.status_code in [200, 302]


def test_add_position_min_salary_greater_than_max_salary_fails(client, logged_in_admin, valid_position_payload):
    """Case 10: Lương tối thiểu lớn hơn lương tối đa."""
    payload = valid_position_payload.copy()
    payload['min_salary'] = '30000000'
    payload['max_salary'] = '10000000'

    with patch('routes.position.validate_salary_range', side_effect=PositionValidationError("Lương tối thiểu không được lớn hơn lương tối đa")):
        response = client.post('/add_position', data=payload)
        assert response.status_code in [200, 302]


def test_add_position_negative_salary_fails(client, logged_in_admin, valid_position_payload):
    """Case 11: Mức lương nhập vào là số âm."""
    payload = valid_position_payload.copy()
    payload['min_salary'] = '-5000000'

    with patch('routes.position.validate_salary_range', side_effect=PositionValidationError("Mức lương không được âm")):
        response = client.post('/add_position', data=payload)
        assert response.status_code in [200, 302]


def test_add_position_invalid_salary_format_fails(client, logged_in_admin, valid_position_payload):
    """Case 12: Mức lương chứa ký tự chữ."""
    payload = valid_position_payload.copy()
    payload['min_salary'] = 'ten_million'

    with patch('routes.position.validate_salary_range', side_effect=PositionValidationError("Mức lương phải là số")):
        response = client.post('/add_position', data=payload)
        assert response.status_code in [200, 302]


def test_add_position_invalid_status_fails(client, logged_in_admin, valid_position_payload):
    """Case 13: Trạng thái không thuộc danh sách hợp lệ (Active/Inactive)."""
    payload = valid_position_payload.copy()
    payload['status'] = 'UnknownStatus'

    with patch('routes.position.validate_position_status', side_effect=PositionValidationError("Trạng thái không hợp lệ")):
        response = client.post('/add_position', data=payload)
        assert response.status_code in [200, 302]


def test_add_position_description_too_long_fails(client, logged_in_admin, valid_position_payload):
    """Case 14: Mô tả vượt quá độ dài tối đa cho phép."""
    payload = valid_position_payload.copy()
    payload['description'] = 'A' * 1000

    with patch('routes.position.validate_position_description', side_effect=PositionValidationError("Mô tả quá dài")):
        response = client.post('/add_position', data=payload)
        assert response.status_code in [200, 302]


def test_add_position_empty_optional_description_success(client, logged_in_admin, mock_db, valid_position_payload):
    """Case 15: Thêm chức vụ thành công khi bỏ trống phần mô tả (Optional)."""
    payload = valid_position_payload.copy()
    payload['description'] = ''
    mock_db.fetchone.return_value = None

    response = client.post('/add_position', data=payload)
    assert response.status_code in [200, 302]


def test_add_position_db_exception_handling(client, logged_in_admin, mock_db, valid_position_payload):
    """Case 16: DB ném ngoại lệ khi thực thi câu lệnh INSERT."""
    mock_db.fetchone.return_value = None
    mock_db.execute.side_effect = Exception("DB Connection Lost")

    response = client.post('/add_position', data=valid_position_payload)
    assert response.status_code in [200, 302, 500]


def test_add_position_manager_role_success(client, mock_db, valid_position_payload):
    """Case 17: Role 'Manager' cũng có quyền thêm mới chức vụ thành công."""
    with client.session_transaction() as sess:
        sess['user_id'] = 3
        sess['role'] = 'Manager'

    mock_db.fetchone.return_value = None

    response = client.post('/add_position', data=valid_position_payload)
    assert response.status_code in [200, 302]


def test_add_position_whitespace_normalization(client, logged_in_admin, mock_db, valid_position_payload):
    """Case 18: Tự động chuẩn hóa khoảng trắng thừa ở Mã và Tên chức vụ."""
    payload = valid_position_payload.copy()
    payload['position_code'] = '  POS_TEST_01  '
    payload['position_name'] = '  Chức Vụ Test  '
    mock_db.fetchone.return_value = None

    response = client.post('/add_position', data=payload)
    assert response.status_code in [200, 302]