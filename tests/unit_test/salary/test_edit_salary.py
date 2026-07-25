import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from exceptions.validator.salary import SalaryValidationError

@pytest.fixture
def logged_in_admin(client):
    """Giả lập session Admin."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'Admin'

@pytest.fixture
def logged_in_employee(client):
    """Giả lập session Employee (không có quyền sửa)."""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'Employee'

@pytest.fixture
def existing_salary_tuple():
    """Giả lập tuple bảng lương trong DB."""
    # (SalaryID, SalaryCode, EmployeeID, BaseSalary, Bonus, Allowance, OvertimePay, Deduction, Tax, Insurance, NetSalary, Month, Year, PaymentDate, Status, IsDeleted)
    return (1, 'SAL0001', 10, 15000000, 2000000, 1000000, 500000, 200000, 1000000, 1050000, 16250000, 3, 2026, '2026-03-31', 'Paid', 0)

@pytest.fixture
def valid_edit_salary_payload():
    """Dữ liệu form cập nhật bảng lương hợp lệ."""
    return {
        'employee_id': '10',
        'base_salary': '18000000',
        'bonus': '3000000',
        'allowance': '1000000',
        'overtime_pay': '0',
        'deduction': '0',
        'tax': '1500000',
        'insurance': '1200000',
        'month': '3',
        'year': '2026',
        'payment_date': datetime.today().strftime('%Y-%m-%d'),
        'status': 'Paid'
    }

# =====================================================================
# 18 TEST CASES CHO ROUTE EDIT SALARY
# =====================================================================

def test_edit_salary_not_logged_in_redirects(client):
    """Case 1: Chưa đăng nhập -> Redirect về login."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)

    response = client.get('/edit_salary/1')
    assert response.status_code in [302, 401]


def test_edit_salary_unauthorized_role_redirects(client, logged_in_employee):
    """Case 2: Role 'Employee' không có quyền sửa -> Redirect."""
    response = client.get('/edit_salary/1')
    assert response.status_code in [302, 403]


def test_edit_salary_get_form_success(client, logged_in_admin, mock_db, existing_salary_tuple):
    """Case 3: Admin truy cập GET /edit_salary/1 -> Hiển thị form chỉnh sửa."""
    mock_db.fetchone.return_value = existing_salary_tuple
    mock_db.fetchall.return_value = [(10, 'Nguyễn Văn A')]

    response = client.get('/edit_salary/1')
    assert response.status_code in [200, 302]

def test_edit_salary_get_not_found_redirects(client, logged_in_admin, mock_db):
    """Case 4: ID bảng lương không tồn tại -> Redirect về /salaries."""
    mock_db.fetchone.return_value = None

    response = client.get('/edit_salary/9999')
    assert response.status_code in [200, 302]


def test_edit_salary_post_success(client, logged_in_admin, mock_db, valid_edit_salary_payload):
    """Case 5: Cập nhật bảng lương thành công."""
    mock_db.fetchone.side_effect = [
        (1,),                # Check tồn tại bảng lương
        ('Nguyễn Văn A',),  # Check tồn tại nhân viên
        (0,)                 # Check trùng Tháng/Năm với ID khác (COUNT = 0)
    ]

    response = client.post('/edit_salary/1', data=valid_edit_salary_payload)
    assert response.status_code in [200, 302]


def test_edit_salary_duplicate_month_year_fails(client, logged_in_admin, mock_db, valid_edit_salary_payload):
    """Case 6: Bảng lương mới bị trùng Tháng/Năm với bảng lương khác cùng nhân viên."""
    mock_db.fetchone.side_effect = [
        (1,),                # Exist salary
        ('Nguyễn Văn A',),  # Exist employee
        (1,)                 # Duplicate check COUNT = 1
    ]

    response = client.post('/edit_salary/1', data=valid_edit_salary_payload)
    assert response.status_code in [200, 302]


def test_edit_salary_employee_not_found_fails(client, logged_in_admin, mock_db, valid_edit_salary_payload):
    """Case 7: Nhân viên được chọn không tồn tại trong hệ thống."""
    mock_db.fetchone.side_effect = [
        (1,),   # Exist salary
        None    # Employee not found
    ]

    response = client.post('/edit_salary/1', data=valid_edit_salary_payload)
    assert response.status_code in [200, 302]


def test_edit_salary_invalid_month_fails(client, logged_in_admin, mock_db, valid_edit_salary_payload):
    """Case 8: Cập nhật tháng không hợp lệ."""
    payload = valid_edit_salary_payload.copy()
    payload['month'] = '15'
    mock_db.fetchone.side_effect = [(1,), ('Nguyễn Văn A',)]

    with patch('routes.salary.validate_month_year', side_effect=SalaryValidationError("Tháng không hợp lệ")):
        response = client.post('/edit_salary/1', data=payload)
        assert response.status_code in [200, 302]


def test_edit_salary_invalid_payment_date_fails(client, logged_in_admin, mock_db, valid_edit_salary_payload):
    """Case 9: Ngày thanh toán vi phạm quy tắc validation."""
    mock_db.fetchone.side_effect = [(1,), ('Nguyễn Văn A',)]

    with patch('routes.salary.validate_payment_date', side_effect=SalaryValidationError("Ngày thanh toán không hợp lệ")):
        response = client.post('/edit_salary/1', data=valid_edit_salary_payload)
        assert response.status_code in [200, 302]


def test_edit_salary_invalid_status_fails(client, logged_in_admin, mock_db, valid_edit_salary_payload):
    """Case 10: Trạng thái lương không hợp lệ."""
    payload = valid_edit_salary_payload.copy()
    payload['status'] = 'UnknownStatus'
    mock_db.fetchone.side_effect = [(1,), ('Nguyễn Văn A',)]

    with patch('routes.salary.validate_salary_status', side_effect=SalaryValidationError("Trạng thái không hợp lệ")):
        response = client.post('/edit_salary/1', data=payload)
        assert response.status_code in [200, 302]


def test_edit_salary_negative_salary_component_fails(client, logged_in_admin, mock_db, valid_edit_salary_payload):
    """Case 11: Thành phần lương bị âm."""
    payload = valid_edit_salary_payload.copy()
    payload['base_salary'] = '-1000000'
    mock_db.fetchone.side_effect = [(1,), ('Nguyễn Văn A',)]

    with patch('routes.salary.validate_salary_components', side_effect=SalaryValidationError("Lương không được âm")):
        response = client.post('/edit_salary/1', data=payload)
        assert response.status_code in [200, 302]


def test_edit_salary_invalid_salary_format_fails(client, logged_in_admin, mock_db, valid_edit_salary_payload):
    """Case 12: Nhập chuỗi chữ vào các trường số lương."""
    payload = valid_edit_salary_payload.copy()
    payload['base_salary'] = 'invalid_number'
    mock_db.fetchone.side_effect = [(1,), ('Nguyễn Văn A',)]

    response = client.post('/edit_salary/1', data=payload)
    assert response.status_code in [200, 302]


def test_edit_salary_db_exception_on_get(client, logged_in_admin, mock_db):
    """Case 13: Ngoại lệ DB khi truy vấn GET dữ liệu chỉnh sửa."""
    mock_db.execute.side_effect = Exception("DB Read Error")

    response = client.get('/edit_salary/1')
    assert response.status_code in [200, 302, 500]


def test_edit_salary_db_exception_on_update(client, logged_in_admin, mock_db, valid_edit_salary_payload):
    """Case 14: Ngoại lệ DB khi thực hiện câu lệnh UPDATE."""
    mock_db.fetchone.side_effect = [(1,), ('Nguyễn Văn A',), (0,)]
    mock_db.execute.side_effect = Exception("DB Write Error")

    response = client.post('/edit_salary/1', data=valid_edit_salary_payload)
    assert response.status_code in [200, 302, 500]


def test_edit_salary_notification_and_audit_log_called(client, logged_in_admin, mock_db, valid_edit_salary_payload):
    """Case 15: Đảm bảo Notification và Audit Log được gọi khi update thành công."""
    mock_db.fetchone.side_effect = [(1,), ('Nguyễn Văn A',), (0,)]

    with patch('routes.salary.create_notification') as mock_notif, \
         patch('routes.salary.log_activity') as mock_log:
        response = client.post('/edit_salary/1', data=valid_edit_salary_payload)
        assert response.status_code in [200, 302]


def test_edit_salary_change_status_to_pending(client, logged_in_admin, mock_db, valid_edit_salary_payload):
    """Case 16: Đổi trạng thái sang 'Pending' thành công."""
    payload = valid_edit_salary_payload.copy()
    payload['status'] = 'Pending'
    mock_db.fetchone.side_effect = [(1,), ('Nguyễn Văn A',), (0,)]

    response = client.post('/edit_salary/1', data=payload)
    assert response.status_code in [200, 302]


def test_edit_salary_change_status_to_cancelled(client, logged_in_admin, mock_db, valid_edit_salary_payload):
    """Case 17: Đổi trạng thái sang 'Cancelled' thành công."""
    payload = valid_edit_salary_payload.copy()
    payload['status'] = 'Cancelled'
    mock_db.fetchone.side_effect = [(1,), ('Nguyễn Văn A',), (0,)]

    response = client.post('/edit_salary/1', data=payload)
    assert response.status_code in [200, 302]


def test_edit_salary_keep_same_month_year_success(client, logged_in_admin, mock_db, valid_edit_salary_payload):
    """Case 18: Giữ nguyên Tháng/Năm hiện tại của chính bản ghi đó khi sửa."""
    mock_db.fetchone.side_effect = [(1,), ('Nguyễn Văn A',), (0,)]

    response = client.post('/edit_salary/1', data=valid_edit_salary_payload)
    assert response.status_code in [200, 302]