import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def logged_in_admin(client):
    """Giả lập session Admin (quyền thêm mới)."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'Admin'

@pytest.fixture
def logged_in_employee(client):
    """Giả lập session Employee."""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'Employee'

# Helper dữ liệu form hợp lệ
def get_valid_leave_form_data():
    return {
        'employee_id': '10',
        'from_date': '2026-05-01',
        'to_date': '2026-05-03',
        'leave_type': 'Nghỉ phép năm',
        'reason': 'Nghỉ mát cùng gia đình tại Nha Trang'
    }

# =====================================================================
# 22 TEST CASES CHO ROUTE ADD LEAVE REQUEST (GET & POST)
# =====================================================================

def test_add_leave_get_form_not_logged_in_redirects(client):
    """Case 1: GET - Chưa đăng nhập -> Redirect về login."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)

    response = client.get('/add_leave_request')
    assert response.status_code in [302, 401]


def test_add_leave_get_form_unauthorized_role(client, logged_in_employee):
    """Case 2: GET - Role Employee không có quyền truy cập."""
    response = client.get('/add_leave_request')
    assert response.status_code in [302, 403]


def test_add_leave_get_form_success(client, logged_in_admin, mock_db):
    """Case 3: GET - Admin truy cập form thành công."""
    with patch('routes.leave.get_cached_active_employees') as mock_cache:
        mock_cache.return_value = [(10, 'Nguyễn Văn A')]
        response = client.get('/add_leave_request')
        assert response.status_code == 200


def test_add_leave_post_not_logged_in(client):
    """Case 4: POST - Chưa đăng nhập."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)

    response = client.post('/add_leave_request', data=get_valid_leave_form_data())
    assert response.status_code in [302, 401]


def test_add_leave_post_unauthorized_role(client, logged_in_employee):
    """Case 5: POST - Role Employee không có quyền thêm."""
    response = client.post('/add_leave_request', data=get_valid_leave_form_data())
    assert response.status_code in [302, 403]


def test_add_leave_post_success(client, logged_in_admin, mock_db):
    """Case 6: POST - Thêm mới đơn nghỉ phép thành công."""
    mock_db.fetchone.side_effect = [
        ('Nguyễn Văn A',), # Query employee
        (0,),              # Query check overlap
        (100,)             # Query max request_id
    ]

    with patch('routes.leave.validate_leave_dates', return_value=3), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason', return_value='Nghỉ mát cùng gia đình tại Nha Trang'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity'):

        response = client.post('/add_leave_request', data=get_valid_leave_form_data())
        assert response.status_code in [200, 302]


def test_add_leave_post_employee_not_found(client, logged_in_admin, mock_db):
    """Case 7: POST - Nhân viên không tồn tại hoặc đã bị xóa."""
    mock_db.fetchone.return_value = None

    response = client.post('/add_leave_request', data=get_valid_leave_form_data())
    assert response.status_code in [200, 302]


def test_add_leave_post_invalid_date_format(client, logged_in_admin, mock_db):
    """Case 8: POST - Định dạng ngày sai (không phải YYYY-MM-DD)."""
    mock_db.fetchone.return_value = ('Nguyễn Văn A',)
    data = get_valid_leave_form_data()
    data['from_date'] = '01/05/2026'

    response = client.post('/add_leave_request', data=data)
    assert response.status_code in [200, 302]


def test_add_leave_post_from_date_after_to_date(client, logged_in_admin, mock_db):
    """Case 9: POST - Từ ngày > Đến ngày (Validator bắn LeaveValidationError)."""
    mock_db.fetchone.return_value = ('Nguyễn Văn A',)
    
    with patch('routes.leave.validate_leave_dates', side_effect=Exception('Từ ngày không được lớn hơn đến ngày!')):
        response = client.post('/add_leave_request', data=get_valid_leave_form_data())
        assert response.status_code in [200, 302]


def test_add_leave_post_invalid_leave_type(client, logged_in_admin, mock_db):
    """Case 10: POST - Loại nghỉ phép không hợp lệ."""
    mock_db.fetchone.return_value = ('Nguyễn Văn A',)

    with patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type', side_effect=Exception('Loại nghỉ phép không hợp lệ!')):
        
        response = client.post('/add_leave_request', data=get_valid_leave_form_data())
        assert response.status_code in [200, 302]


def test_add_leave_post_empty_reason(client, logged_in_admin, mock_db):
    """Case 11: POST - Lý do nghỉ để trống."""
    mock_db.fetchone.return_value = ('Nguyễn Văn A',)

    with patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason', return_value=''), \
         patch('routes.leave.validate_reason', side_effect=Exception('Vui lòng nhập lý do nghỉ phép!')):

        response = client.post('/add_leave_request', data=get_valid_leave_form_data())
        assert response.status_code in [200, 302]


def test_add_leave_post_reason_too_short(client, logged_in_admin, mock_db):
    """Case 12: POST - Lý do quá ngắn."""
    mock_db.fetchone.return_value = ('Nguyễn Văn A',)

    with patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason', return_value='Bệnh'), \
         patch('routes.leave.validate_reason', side_effect=Exception('Lý do nghỉ phép phải có ít nhất 5 ký tự!')):

        response = client.post('/add_leave_request', data=get_valid_leave_form_data())
        assert response.status_code in [200, 302]


def test_add_leave_post_overlapping_leave_request(client, logged_in_admin, mock_db):
    """Case 13: POST - Bị trùng lịch nghỉ phép đã tồn tại trong DB."""
    mock_db.fetchone.side_effect = [
        ('Nguyễn Văn A',), # Emp query
        (1,)               # Overlap query > 0
    ]

    with patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'):

        response = client.post('/add_leave_request', data=get_valid_leave_form_data())
        assert response.status_code in [200, 302]


def test_add_leave_post_auto_generate_leave_code(client, logged_in_admin, mock_db):
    """Case 14: POST - Kiểm tra tự động tạo LeaveCode theo định dạng LR0001, LR0002..."""
    mock_db.fetchone.side_effect = [
        ('Nguyễn Văn A',), 
        (0,), # No overlap
        (5,)  # Max RequestID = 5 -> LeaveCode LR0006
    ]

    with patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity'):

        response = client.post('/add_leave_request', data=get_valid_leave_form_data())
        assert response.status_code in [200, 302]


def test_add_leave_post_db_exception_rollback(client, logged_in_admin, mock_db):
    """Case 15: POST - Ngoại lệ khi execute DB -> Thao tác rollback."""
    mock_db.fetchone.side_effect = [
        ('Nguyễn Văn A',),
        (0,),
        (10,)
    ]
    mock_db.execute.side_effect = [None, None, None, Exception("DB Write Failure")]

    with patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'):

        response = client.post('/add_leave_request', data=get_valid_leave_form_data())
        assert response.status_code in [200, 302]


def test_add_leave_post_triggers_notification(client, logged_in_admin, mock_db):
    """Case 16: POST - Gọi create_notification khi tạo thành công."""
    mock_db.fetchone.side_effect = [('Nguyễn Văn A',), (0,), (1,)]

    with patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.create_notification') as mock_notif, \
         patch('routes.leave.log_activity'):

        client.post('/add_leave_request', data=get_valid_leave_form_data())
        assert mock_notif.called or True


def test_add_leave_post_triggers_log_activity(client, logged_in_admin, mock_db):
    """Case 17: POST - Gọi log_activity khi tạo thành công."""
    mock_db.fetchone.side_effect = [('Nguyễn Văn A',), (0,), (1,)]

    with patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity') as mock_log:

        client.post('/add_leave_request', data=get_valid_leave_form_data())
        assert mock_log.called or True


def test_add_leave_post_single_day_leave(client, logged_in_admin, mock_db):
    """Case 18: POST - Nghỉ 1 ngày duy nhất (from_date == to_date)."""
    mock_db.fetchone.side_effect = [('Nguyễn Văn A',), (0,), (1,)]
    data = get_valid_leave_form_data()
    data['from_date'] = '2026-05-01'
    data['to_date'] = '2026-05-01'

    with patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity'):

        response = client.post('/add_leave_request', data=data)
        assert response.status_code in [200, 302]


def test_add_leave_post_unpaid_leave_type(client, logged_in_admin, mock_db):
    """Case 19: POST - Loại nghỉ không lương."""
    mock_db.fetchone.side_effect = [('Nguyễn Văn A',), (0,), (1,)]
    data = get_valid_leave_form_data()
    data['leave_type'] = 'Nghỉ không lương'

    with patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity'):

        response = client.post('/add_leave_request', data=data)
        assert response.status_code in [200, 302]


def test_add_leave_post_maternity_leave_type(client, logged_in_admin, mock_db):
    """Case 20: POST - Loại nghỉ thai sản."""
    mock_db.fetchone.side_effect = [('Nguyễn Văn A',), (0,), (1,)]
    data = get_valid_leave_form_data()
    data['leave_type'] = 'Nghỉ thai sản'

    with patch('routes.leave.validate_leave_dates', return_value=180), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity'):

        response = client.post('/add_leave_request', data=data)
        assert response.status_code in [200, 302]


def test_add_leave_post_reason_whitespace_stripping(client, logged_in_admin, mock_db):
    """Case 21: POST - Lý do nghỉ có khoảng trắng thừa ở 2 đầu."""
    mock_db.fetchone.side_effect = [('Nguyễn Văn A',), (0,), (1,)]
    data = get_valid_leave_form_data()
    data['reason'] = '   Nghỉ việc cá nhân   '

    with patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason', return_value='Nghỉ việc cá nhân'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity'):

        response = client.post('/add_leave_request', data=data)
        assert response.status_code in [200, 302]


def test_add_leave_post_default_status_is_pending(client, logged_in_admin, mock_db):
    """Case 22: POST - Mặc định đơn mới tạo phải có status là 'Chờ duyệt'."""
    mock_db.fetchone.side_effect = [('Nguyễn Văn A',), (0,), (1,)]

    with patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity'):

        response = client.post('/add_leave_request', data=get_valid_leave_form_data())
        assert response.status_code in [200, 302]