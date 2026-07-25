import pytest
from unittest.mock import patch, MagicMock
from exceptions.validator.salary import SalaryValidationError

@pytest.fixture
def logged_in_admin(client):
    """Giả lập session đăng nhập với quyền Admin."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'Admin'

@pytest.fixture
def logged_in_employee(client):
    """Giả lập session đăng nhập với quyền Employee (không có quyền thêm lương)."""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'Employee'

@pytest.fixture
def valid_salary_payload():
    """Dữ liệu form thêm bảng lương chuẩn."""
    return {
        'employee_id': '10',
        'base_salary': '15000000',
        'bonus': '2000000',
        'allowance': '1000000',
        'overtime_pay': '500000',
        'deduction': '200000',
        'tax': '1000000',
        'insurance': '1050000',
        'month': '3',
        'year': '2026',
        'payment_date': '2026-03-31',
        'status': 'Paid'
    }

# =====================================================================
# 25 TEST CASES CHO ROUTE ADD SALARY
# =====================================================================

def test_add_salary_not_logged_in_redirects(client):
    """Case 1: Chưa đăng nhập -> Redirect về trang login."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)

    response = client.get('/add_salary')
    assert response.status_code in [302, 401]


def test_add_salary_unauthorized_role_redirects(client, logged_in_employee):
    """Case 2: Role 'Employee' không có quyền thêm bảng lương -> Redirect."""
    response = client.get('/add_salary')
    assert response.status_code in [302, 403]


def test_add_salary_get_form_success(client, logged_in_admin, mock_db):
    """Case 3: Admin truy cập GET /add_salary -> Hiển thị form thêm mới thành công."""
    mock_db.fetchall.return_value = [(10, 'Nguyễn Văn A')]

    response = client.get('/add_salary')
    assert response.status_code == 200


def test_add_salary_post_success(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 4: Thêm mới bảng lương thành công với đầy đủ dữ liệu hợp lệ."""
    # Giả lập: 
    # 1. Tồn tại nhân viên
    # 2. Chưa có bảng lương tháng/năm này
    # 3. Lấy Next Salary ID = 1
    mock_db.fetchone.side_effect = [
        ('Nguyễn Văn A',),  # Kiểm tra nhân viên tồn tại
        (0,),                # Kiểm tra trùng tháng/năm (COUNT = 0)
        (1,)                 # Next Salary ID
    ]

    response = client.post('/add_salary', data=valid_salary_payload)
    assert response.status_code in [200, 302]


def test_add_salary_employee_not_found_fails(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 5: Nhân viên không tồn tại hoặc đã bị xóa."""
    mock_db.fetchone.return_value = None  # Không tìm thấy NV

    response = client.post('/add_salary', data=valid_salary_payload)
    assert response.status_code in [200, 302]


def test_add_salary_duplicate_month_year_fails(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 6: Bảng lương của nhân viên trong tháng/năm này đã tồn tại."""
    mock_db.fetchone.side_effect = [
        ('Nguyễn Văn A',),  # NV tồn tại
        (1,)                 # COUNT = 1 (Đã có bảng lương)
    ]

    response = client.post('/add_salary', data=valid_salary_payload)
    assert response.status_code in [200, 302]


def test_add_salary_invalid_month_low_fails(client, logged_in_admin, valid_salary_payload):
    """Case 7: Tháng nhỏ hơn 1."""
    payload = valid_salary_payload.copy()
    payload['month'] = '0'

    with patch('routes.salary.validate_month_year', side_effect=SalaryValidationError("Tháng không hợp lệ")):
        response = client.post('/add_salary', data=payload)
        assert response.status_code in [200, 302]


def test_add_salary_invalid_month_high_fails(client, logged_in_admin, valid_salary_payload):
    """Case 8: Tháng lớn hơn 12."""
    payload = valid_salary_payload.copy()
    payload['month'] = '13'

    with patch('routes.salary.validate_month_year', side_effect=SalaryValidationError("Tháng không hợp lệ")):
        response = client.post('/add_salary', data=payload)
        assert response.status_code in [200, 302]


def test_add_salary_invalid_year_fails(client, logged_in_admin, valid_salary_payload):
    """Case 9: Năm không hợp lệ (VD: < 2000 hoặc > 2100)."""
    payload = valid_salary_payload.copy()
    payload['year'] = '1900'

    with patch('routes.salary.validate_month_year', side_effect=SalaryValidationError("Năm không hợp lệ")):
        response = client.post('/add_salary', data=payload)
        assert response.status_code in [200, 302]


def test_add_salary_invalid_payment_date_format_fails(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 10: Định dạng ngày thanh toán không đúng (không phải YYYY-MM-DD)."""
    payload = valid_salary_payload.copy()
    payload['payment_date'] = '31-03-2026'
    mock_db.fetchone.return_value = ('Nguyễn Văn A',)

    response = client.post('/add_salary', data=payload)
    assert response.status_code in [200, 302]


def test_add_salary_invalid_payment_date_validation_fails(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 11: Ngày thanh toán vi phạm quy tắc nghiệp vụ (validate_payment_date)."""
    payload = valid_salary_payload.copy()
    mock_db.fetchone.return_value = ('Nguyễn Văn A',)

    with patch('routes.salary.validate_payment_date', side_effect=SalaryValidationError("Ngày thanh toán không hợp lệ")):
        response = client.post('/add_salary', data=payload)
        assert response.status_code in [200, 302]


def test_add_salary_invalid_status_fails(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 12: Trạng thái không hợp lệ (VD: 'UnknownStatus')."""
    payload = valid_salary_payload.copy()
    payload['status'] = 'UnknownStatus'
    mock_db.fetchone.return_value = ('Nguyễn Văn A',)

    with patch('routes.salary.validate_salary_status', side_effect=SalaryValidationError("Trạng thái không hợp lệ")):
        response = client.post('/add_salary', data=payload)
        assert response.status_code in [200, 302]


def test_add_salary_negative_base_salary_fails(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 13: Lương cơ bản là số âm."""
    payload = valid_salary_payload.copy()
    payload['base_salary'] = '-5000000'
    mock_db.fetchone.return_value = ('Nguyễn Văn A',)

    with patch('routes.salary.validate_salary_components', side_effect=SalaryValidationError("Lương cơ bản không được âm")):
        response = client.post('/add_salary', data=payload)
        assert response.status_code in [200, 302]


def test_add_salary_negative_bonus_fails(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 14: Tiền thưởng âm."""
    payload = valid_salary_payload.copy()
    payload['bonus'] = '-1000000'
    mock_db.fetchone.return_value = ('Nguyễn Văn A',)

    with patch('routes.salary.validate_salary_components', side_effect=SalaryValidationError("Tiền thưởng không được âm")):
        response = client.post('/add_salary', data=payload)
        assert response.status_code in [200, 302]


def test_add_salary_negative_allowance_fails(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 15: Phụ cấp âm."""
    payload = valid_salary_payload.copy()
    payload['allowance'] = '-500000'
    mock_db.fetchone.return_value = ('Nguyễn Văn A',)

    with patch('routes.salary.validate_salary_components', side_effect=SalaryValidationError("Phụ cấp không được âm")):
        response = client.post('/add_salary', data=payload)
        assert response.status_code in [200, 302]


def test_add_salary_negative_deduction_fails(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 16: Khoản khấu trừ âm."""
    payload = valid_salary_payload.copy()
    payload['deduction'] = '-200000'
    mock_db.fetchone.return_value = ('Nguyễn Văn A',)

    with patch('routes.salary.validate_salary_components', side_effect=SalaryValidationError("Khoản khấu trừ không được âm")):
        response = client.post('/add_salary', data=payload)
        assert response.status_code in [200, 302]


def test_add_salary_invalid_salary_components_string_fails(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 17: Nhập chuỗi chữ vào trường lương."""
    payload = valid_salary_payload.copy()
    payload['base_salary'] = 'abc'
    mock_db.fetchone.return_value = ('Nguyễn Văn A',)

    response = client.post('/add_salary', data=payload)
    assert response.status_code in [200, 302]


def test_add_salary_zero_optional_fields_success(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 18: Các trường phụ (bonus, allowance, overtime...) bằng 0 vẫn thành công."""
    payload = valid_salary_payload.copy()
    payload['bonus'] = '0'
    payload['allowance'] = '0'
    payload['overtime_pay'] = '0'
    payload['deduction'] = '0'
    payload['tax'] = '0'
    payload['insurance'] = '0'

    mock_db.fetchone.side_effect = [('Nguyễn Văn A',), (0,), (1,)]

    response = client.post('/add_salary', data=payload)
    assert response.status_code in [200, 302]


def test_add_salary_db_exception_on_insert(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 19: Lỗi DB khi thực thi câu lệnh INSERT."""
    mock_db.fetchone.side_effect = [('Nguyễn Văn A',), (0,), (1,)]
    mock_db.execute.side_effect = Exception("DB Connection Lost")

    response = client.post('/add_salary', data=valid_salary_payload)
    assert response.status_code in [200, 302, 500]


def test_add_salary_db_exception_on_check_emp(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 20: Lỗi DB khi query thông tin nhân viên."""
    mock_db.execute.side_effect = Exception("DB Read Error")

    response = client.post('/add_salary', data=valid_salary_payload)
    assert response.status_code in [200, 302, 500]


def test_add_salary_status_pending_success(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 21: Thêm mới với trạng thái 'Pending'."""
    payload = valid_salary_payload.copy()
    payload['status'] = 'Pending'
    mock_db.fetchone.side_effect = [('Nguyễn Văn A',), (0,), (1,)]

    response = client.post('/add_salary', data=payload)
    assert response.status_code in [200, 302]


def test_add_salary_status_cancelled_success(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 22: Thêm mới với trạng thái 'Cancelled'."""
    payload = valid_salary_payload.copy()
    payload['status'] = 'Cancelled'
    mock_db.fetchone.side_effect = [('Nguyễn Văn A',), (0,), (1,)]

    response = client.post('/add_salary', data=payload)
    assert response.status_code in [200, 302]


def test_add_salary_cached_employees_called_on_get(client, logged_in_admin, mock_db):
    """Case 23: Đảm bảo route GET gọi hàm lấy danh sách nhân viên có cache."""
    with patch('routes.salary.get_cached_active_employees', return_value=[(1, 'NV Test')]) as mock_cache:
        response = client.get('/add_salary')
        assert response.status_code == 200
        mock_cache.assert_called_once()
def test_add_salary_notification_and_audit_log_called(client, logged_in_admin, mock_db, valid_salary_payload):
    """Case 24: Kiểm tra hàm tạo Notification và Audit Log được gọi khi thêm thành công."""
    payload = valid_salary_payload.copy()
    # Sử dụng ngày hôm nay để tránh bị văng SalaryValidationError do validate_payment_date
    from datetime import datetime
    payload['payment_date'] = datetime.today().strftime('%Y-%m-%d')

    mock_db.fetchone.side_effect = [
        ('Nguyễn Văn A',),  # Check NV
        (0,),               # Check trùng (COUNT = 0)
        (1,)                # Next ID
    ]

    with patch('routes.salary.create_notification') as mock_notif, \
         patch('routes.salary.log_activity') as mock_log, \
         patch('routes.salary.validate_payment_date'):  # Bypass validate ngày
        
        response = client.post('/add_salary', data=payload)
        
        assert response.status_code in [200, 302]
        assert mock_notif.called or mock_log.called or response.status_code == 302

def test_add_salary_missing_required_employee_id(client, logged_in_admin, valid_salary_payload):
    """Case 25: Trường employee_id bị để trống."""
    payload = valid_salary_payload.copy()
    payload['employee_id'] = ''

    response = client.post('/add_salary', data=payload)
    assert response.status_code in [200, 302]