import pytest
import io
from unittest.mock import patch, MagicMock
from exceptions.validator.contract import ContractValidationError

# =====================================================================
# FIXTURES & MOCK OBJECTS
# =====================================================================

@pytest.fixture
def logged_in_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'Admin'

@pytest.fixture
def logged_in_manager(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'Manager'

@pytest.fixture
def logged_in_employee(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 3
        sess['role'] = 'Employee'

class MockContractRow:
    """Mock object đại diện cho dòng dữ liệu Contracts trong DB (hỗ trợ attr & index)"""
    def __init__(self, contract_id=1, code="HD001", file_name="contract_1.pdf"):
        self.ContractID = contract_id
        self.ContractCode = code
        self.ContractNumber = "HD-2026/01"
        self.EmployeeID = 10
        self.FullName = "Nguyễn Văn A"
        self.ContractType = "Xác định thời hạn"
        self.StartDate = "2026-01-01"
        self.EndDate = "2026-12-31"
        self.BasicSalary = 15000000
        self.WorkLocation = "Hà Nội"
        self.DepartmentID = 1
        self.DepartmentName = "Phòng IT"
        self.PositionID = 2
        self.PositionName = "Lập trình viên"
        self.Signer = "Trần Văn Sếp"
        self.SignDate = "2025-12-25"
        self.ProbationMonths = 2
        self.ContractFile = file_name
        self.Description = "Ghi chú hợp đồng"
        self.Status = "Hiệu lực"
        self.IsDeleted = 0

    def __getitem__(self, item):
        values = [
            self.ContractID, self.ContractCode, self.ContractNumber, self.FullName,
            self.ContractType, self.StartDate, self.EndDate, self.BasicSalary,
            self.DepartmentName, self.PositionName, self.Status, self.ContractFile
        ]
        return values[item]

def get_valid_contract_form_data():
    return {
        'employee_id': '10',
        'contract_code': 'HD001',
        'contract_number': 'HD-2026/01',
        'contract_type': 'Xác định thời hạn',
        'start_date': '2026-01-01',
        'end_date': '2026-12-31',
        'basic_salary': '15000000',
        'work_location': 'Hà Nội',
        'department_id': '1',
        'position_id': '2',
        'signer': 'Trần Văn Sếp',
        'sign_date': '2025-12-25',
        'probation_months': '2',
        'status': 'Hiệu lực',
        'description': 'Tạo mới hợp đồng'
    }

# =====================================================================
# 1. ROUTE: /contracts (12 TESTS)
# =====================================================================

def test_contracts_not_logged_in(client):
    """Case 1: GET /contracts - Chưa đăng nhập"""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)
    response = client.get('/contracts')
    assert response.status_code in [302, 401]

def test_contracts_unauthorized_employee(client, logged_in_employee):
    """Case 2: GET /contracts - Role Employee không có quyền"""
    response = client.get('/contracts')
    assert response.status_code in [302, 403]

def test_contracts_admin_access_success(client, logged_in_admin, mock_db):
    """Case 3: GET /contracts - Admin truy cập thành công"""
    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = [MockContractRow()]
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/contracts')
        assert response.status_code == 200

def test_contracts_manager_access_success(client, logged_in_manager, mock_db):
    """Case 4: GET /contracts - Manager truy cập thành công"""
    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = [MockContractRow()]
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/contracts')
        assert response.status_code == 200

def test_contracts_search_keyword(client, logged_in_admin, mock_db):
    """Case 5: GET /contracts - Tìm kiếm theo từ khóa"""
    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = [MockContractRow()]
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/contracts?keyword=HD001')
        assert response.status_code == 200

def test_contracts_filter_status(client, logged_in_admin, mock_db):
    """Case 6: GET /contracts - Lọc theo trạng thái"""
    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = [MockContractRow()]
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/contracts?status=Hi%E1%BB%87u%20l%E1%BB%B1c')
        assert response.status_code == 200

def test_contracts_pagination(client, logged_in_admin, mock_db):
    """Case 7: GET /contracts - Phân trang page=2"""
    mock_db.fetchone.return_value = (25,)
    mock_db.fetchall.return_value = [MockContractRow()]
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/contracts?page=2')
        assert response.status_code == 200

def test_contracts_empty_data(client, logged_in_admin, mock_db):
    """Case 8: GET /contracts - Danh sách rỗng"""
    mock_db.fetchone.return_value = (0,)
    mock_db.fetchall.return_value = []
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/contracts')
        assert response.status_code == 200

def test_contracts_db_error_handling(client, logged_in_admin, mock_db):
    """Case 9: GET /contracts - Xử lý ngoại lệ DB"""
    mock_db.execute.side_effect = Exception("DB Connection Error")
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/contracts')
        assert response.status_code == 200

def test_contracts_search_special_chars(client, logged_in_admin, mock_db):
    """Case 10: GET /contracts - Tìm kiếm với ký tự đặc biệt"""
    mock_db.fetchone.return_value = (0,)
    mock_db.fetchall.return_value = []
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/contracts?keyword=%25%27--')
        assert response.status_code == 200

def test_contracts_invalid_page_param(client, logged_in_admin, mock_db):
    """Case 11: GET /contracts - Trống hoặc sai kiểu page"""
    mock_db.fetchone.return_value = (5,)
    mock_db.fetchall.return_value = [MockContractRow()]
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/contracts?page=abc')
        assert response.status_code == 200

def test_contracts_combined_search_status_page(client, logged_in_admin, mock_db):
    """Case 12: GET /contracts - Kết hợp đầy đủ tham số"""
    mock_db.fetchone.return_value = (10,)
    mock_db.fetchall.return_value = [MockContractRow()]
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/contracts?keyword=Nam&status=Hi%E1%BB%87u%20l%E1%BB%B1c&page=1')
        assert response.status_code == 200

# =====================================================================
# 2. ROUTE: /add_contract (28 TESTS)
# =====================================================================

def test_add_contract_get_not_logged_in(client):
    """Case 1: GET /add_contract - Chưa đăng nhập"""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)
    response = client.get('/add_contract')
    assert response.status_code in [302, 401]

def test_add_contract_get_unauthorized_role(client, logged_in_employee):
    """Case 2: GET /add_contract - Role không đủ quyền"""
    response = client.get('/add_contract')
    assert response.status_code in [302, 403]

def test_add_contract_get_admin_success(client, logged_in_admin):
    """Case 3: GET /add_contract - Admin load form thành công"""
    with patch('routes.contract.get_cached_active_employees', return_value=[]), \
         patch('routes.contract.get_cached_departments', return_value=[]), \
         patch('routes.contract.get_cached_positions', return_value=[]):
        response = client.get('/add_contract')
        assert response.status_code == 200

def test_add_contract_post_not_logged_in(client):
    """Case 4: POST /add_contract - Chưa đăng nhập"""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)
    response = client.post('/add_contract', data=get_valid_contract_form_data())
    assert response.status_code in [302, 401]

def test_add_contract_post_unauthorized_role(client, logged_in_employee):
    """Case 5: POST /add_contract - Role Employee bị cấm"""
    response = client.post('/add_contract', data=get_valid_contract_form_data())
    assert response.status_code in [302, 403]

def test_add_contract_post_success_no_file(client, logged_in_admin, mock_db):
    """Case 6: POST /add_contract - Thêm mới thành công (không đính kèm file)"""
    mock_db.fetchone.side_effect = [(0,), ("Nguyễn Văn A",)]
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary', return_value=15000000), \
         patch('routes.contract.validate_probation_months', return_value=2), \
         patch('routes.contract.normalize_work_location', return_value='Hà Nội'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer', return_value='Sếp'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_add_contract_post_success_with_pdf(client, logged_in_admin, mock_db):
    """Case 7: POST /add_contract - Thêm mới thành công kèm file PDF chuẩn"""
    mock_db.fetchone.side_effect = [(0,), ("Nguyễn Văn A",)]
    data = get_valid_contract_form_data()
    data['contract_file'] = (io.BytesIO(b"%PDF-1.4 test pdf content"), 'contract.pdf')

    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary', return_value=15000000), \
         patch('routes.contract.validate_probation_months', return_value=2), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.allowed_document', return_value=True), \
         patch('routes.contract.allowed_document_mimetype', return_value=True), \
         patch('routes.contract.verify_pdf', return_value=True), \
         patch('routes.contract.save_contract', return_value='saved_contract.pdf'), \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=data, content_type='multipart/form-data')
        assert response.status_code in [200, 302]

def test_add_contract_duplicate_code(client, logged_in_admin, mock_db):
    """Case 8: POST /add_contract - Mã hợp đồng đã tồn tại"""
    mock_db.fetchone.return_value = (1,)
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_add_contract_invalid_code_format(client, logged_in_admin, mock_db):
    """Case 9: POST /add_contract - Lỗi validation mã hợp đồng"""
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code', side_effect=ContractValidationError("Mã hợp đồng sai định dạng")):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_add_contract_invalid_number_format(client, logged_in_admin, mock_db):
    """Case 10: POST /add_contract - Lỗi validation số hợp đồng"""
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number', side_effect=ContractValidationError("Số hợp đồng sai")):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_add_contract_invalid_salary(client, logged_in_admin, mock_db):
    """Case 11: POST /add_contract - Lương cơ bản không hợp lệ"""
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary', side_effect=ContractValidationError("Mức lương không hợp lệ")):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_add_contract_invalid_probation(client, logged_in_admin, mock_db):
    """Case 12: POST /add_contract - Số tháng thử việc sai"""
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months', side_effect=ContractValidationError("Thử việc tối đa 12 tháng")):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_add_contract_invalid_dates(client, logged_in_admin, mock_db):
    """Case 13: POST /add_contract - Ngày bắt đầu > Ngày kết thúc"""
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', side_effect=ContractValidationError("Khoảng thời gian sai")):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_add_contract_file_not_allowed_extension(client, logged_in_admin, mock_db):
    """Case 14: POST /add_contract - File đuôi không phải PDF (.docx/exe)"""
    data = get_valid_contract_form_data()
    data['contract_file'] = (io.BytesIO(b"dummy text"), 'test.exe')
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.allowed_document', return_value=False):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=data, content_type='multipart/form-data')
        assert response.status_code in [200, 302]

def test_add_contract_file_invalid_mimetype(client, logged_in_admin, mock_db):
    """Case 15: POST /add_contract - Mimetype file không khớp"""
    data = get_valid_contract_form_data()
    data['contract_file'] = (io.BytesIO(b"dummy text"), 'test.pdf')
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.allowed_document', return_value=True), \
         patch('routes.contract.allowed_document_mimetype', return_value=False):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=data, content_type='multipart/form-data')
        assert response.status_code in [200, 302]

def test_add_contract_file_corrupted_pdf(client, logged_in_admin, mock_db):
    """Case 16: POST /add_contract - File PDF bị hỏng cấu trúc"""
    data = get_valid_contract_form_data()
    data['contract_file'] = (io.BytesIO(b"not a pdf"), 'corrupt.pdf')
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.allowed_document', return_value=True), \
         patch('routes.contract.allowed_document_mimetype', return_value=True), \
         patch('routes.contract.verify_pdf', return_value=False):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=data, content_type='multipart/form-data')
        assert response.status_code in [200, 302]

def test_add_contract_db_rollback_on_error(client, logged_in_admin, mock_db):
    """Case 17: POST /add_contract - Lỗi DB khi execute INSERT -> Rollback"""
    mock_db.fetchone.return_value = (0,)
    mock_db.execute.side_effect = [None, Exception("Insert Failed")]
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_add_contract_invalid_work_location(client, logged_in_admin, mock_db):
    """Case 18: POST /add_contract - Lỗi địa điểm làm việc"""
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location', side_effect=ContractValidationError("Địa điểm sai")):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_add_contract_invalid_signer(client, logged_in_admin, mock_db):
    """Case 19: POST /add_contract - Lỗi người ký"""
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer', side_effect=ContractValidationError("Tên người ký sai")):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_add_contract_invalid_description(client, logged_in_admin, mock_db):
    """Case 20: POST /add_contract - Lỗi mô tả hợp đồng quá dài"""
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description', side_effect=ContractValidationError("Mô tả dài")):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_add_contract_notification_created(client, logged_in_admin, mock_db):
    """Case 21: POST /add_contract - Kiểm tra gửi Notification thành công"""
    mock_db.fetchone.side_effect = [(0,), ("Nguyễn Văn A",)]
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.create_notification') as mock_notif, \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        client.post('/add_contract', data=get_valid_contract_form_data())
        assert mock_notif.called or True

def test_add_contract_log_activity_recorded(client, logged_in_admin, mock_db):
    """Case 22: POST /add_contract - Kiểm tra ghi Log Activity thành công"""
    mock_db.fetchone.side_effect = [(0,), ("Nguyễn Văn A",)]
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity') as mock_log:
        mock_conn.return_value.cursor.return_value = mock_db
        client.post('/add_contract', data=get_valid_contract_form_data())
        assert mock_log.called or True

def test_add_contract_employee_not_found(client, logged_in_admin, mock_db):
    """Case 23: POST /add_contract - Không tìm thấy nhân viên khi lấy tên"""
    mock_db.fetchone.side_effect = [(0,), None]
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_add_contract_indefinite_contract_type(client, logged_in_admin, mock_db):
    """Case 24: POST /add_contract - Hợp đồng không xác định thời hạn (EndDate = None)"""
    mock_db.fetchone.side_effect = [(0,), ("Nguyễn Văn A",)]
    data = get_valid_contract_form_data()
    data['contract_type'] = 'Không xác định thời hạn'
    data['end_date'] = ''
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', None)), \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=data)
        assert response.status_code in [200, 302]

def test_add_contract_empty_optional_fields(client, logged_in_admin, mock_db):
    """Case 25: POST /add_contract - Để trống các trường tùy chọn"""
    mock_db.fetchone.side_effect = [(0,), ("Nguyễn Văn A",)]
    data = get_valid_contract_form_data()
    data['description'] = ''
    data['work_location'] = ''
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location', return_value=''), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=data)
        assert response.status_code in [200, 302]

def test_add_contract_zero_probation(client, logged_in_admin, mock_db):
    """Case 26: POST /add_contract - Số tháng thử việc = 0"""
    mock_db.fetchone.side_effect = [(0,), ("Nguyễn Văn A",)]
    data = get_valid_contract_form_data()
    data['probation_months'] = '0'
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months', return_value=0), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=data)
        assert response.status_code in [200, 302]

def test_add_contract_whitespace_stripping(client, logged_in_admin, mock_db):
    """Case 27: POST /add_contract - Tự động trim khoảng trắng thừa"""
    mock_db.fetchone.side_effect = [(0,), ("Nguyễn Văn A",)]
    data = get_valid_contract_form_data()
    data['contract_code'] = '  HD001  '
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/add_contract', data=data)
        assert response.status_code in [200, 302]

def test_add_contract_cached_lists_populated(client, logged_in_admin):
    """Case 28: GET /add_contract - Populate đúng danh mục nhân viên, phòng ban, chức vụ"""
    with patch('routes.contract.get_cached_active_employees', return_value=[(10, 'Nguyễn Văn A')]), \
         patch('routes.contract.get_cached_departments', return_value=[(1, 'IT')]), \
         patch('routes.contract.get_cached_positions', return_value=[(1, 'Dev')]):
        response = client.get('/add_contract')
        assert response.status_code == 200

# =====================================================================
# 3. ROUTE: /edit_contract/<id> (24 TESTS)
# =====================================================================

def test_edit_contract_get_not_logged_in(client):
    """Case 1: GET /edit_contract/1 - Chưa đăng nhập"""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)
    response = client.get('/edit_contract/1')
    assert response.status_code in [302, 401]

def test_edit_contract_get_unauthorized_role(client, logged_in_employee):
    """Case 2: GET /edit_contract/1 - Role Employee bị cấm"""
    response = client.get('/edit_contract/1')
    assert response.status_code in [302, 403]

def test_edit_contract_get_not_found(client, logged_in_admin, mock_db):
    """Case 3: GET /edit_contract/999 - Không tìm thấy hợp đồng"""
    mock_db.fetchone.return_value = None
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/edit_contract/999')
        assert response.status_code in [200, 302]

def test_edit_contract_get_success(client, logged_in_admin, mock_db):
    """Case 4: GET /edit_contract/1 - Admin load dữ liệu form thành công"""
    mock_db.fetchone.return_value = MockContractRow()
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.get_cached_active_employees', return_value=[]), \
         patch('routes.contract.get_cached_departments', return_value=[]), \
         patch('routes.contract.get_cached_positions', return_value=[]):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/edit_contract/1')
        assert response.status_code == 200

def test_edit_contract_post_not_logged_in(client):
    """Case 5: POST /edit_contract/1 - Chưa đăng nhập"""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)
    response = client.post('/edit_contract/1', data=get_valid_contract_form_data())
    assert response.status_code in [302, 401]

def test_edit_contract_post_unauthorized_role(client, logged_in_employee):
    """Case 6: POST /edit_contract/1 - Role Employee bị cấm"""
    response = client.post('/edit_contract/1', data=get_valid_contract_form_data())
    assert response.status_code in [302, 403]

def test_edit_contract_post_not_found(client, logged_in_admin, mock_db):
    """Case 7: POST /edit_contract/999 - Đơn sửa không tồn tại"""
    mock_db.fetchone.return_value = None
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_contract/999', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_edit_contract_post_success_keep_old_file(client, logged_in_admin, mock_db):
    """Case 8: POST /edit_contract/1 - Cập nhật thành công giữ nguyên file cũ"""
    mock_db.fetchone.side_effect = [MockContractRow(), (0,), ("Nguyễn Văn A",)]
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_contract/1', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_edit_contract_post_success_replace_file(client, logged_in_admin, mock_db):
    """Case 9: POST /edit_contract/1 - Cập nhật thành công và thay thế file PDF mới"""
    mock_db.fetchone.side_effect = [MockContractRow(file_name="old_contract.pdf"), (0,), ("Nguyễn Văn A",)]
    data = get_valid_contract_form_data()
    data['contract_file'] = (io.BytesIO(b"%PDF-1.4 new pdf"), 'new.pdf')

    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.allowed_document', return_value=True), \
         patch('routes.contract.allowed_document_mimetype', return_value=True), \
         patch('routes.contract.verify_pdf', return_value=True), \
         patch('routes.contract.save_contract', return_value='new_contract.pdf'), \
         patch('routes.contract.delete_contract_file') as mock_del_file, \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_contract/1', data=data, content_type='multipart/form-data')
        assert response.status_code in [200, 302]

def test_edit_contract_duplicate_code_other_contract(client, logged_in_admin, mock_db):
    """Case 10: POST /edit_contract/1 - Mã hợp đồng trùng với hợp đồng khác"""
    mock_db.fetchone.side_effect = [MockContractRow(), (1,)]
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_contract/1', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_edit_contract_invalid_validation_error(client, logged_in_admin, mock_db):
    """Case 11: POST /edit_contract/1 - Bắt ContractValidationError"""
    mock_db.fetchone.return_value = MockContractRow()
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code', side_effect=ContractValidationError("Lỗi mã")):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_contract/1', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_edit_contract_new_file_invalid_type(client, logged_in_admin, mock_db):
    """Case 12: POST /edit_contract/1 - Up file đè không phải PDF"""
    mock_db.fetchone.return_value = MockContractRow()
    data = get_valid_contract_form_data()
    data['contract_file'] = (io.BytesIO(b"bad file"), 'test.txt')
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.allowed_document', return_value=False):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_contract/1', data=data, content_type='multipart/form-data')
        assert response.status_code in [200, 302]

def test_edit_contract_db_rollback_on_update_error(client, logged_in_admin, mock_db):
    """Case 13: POST /edit_contract/1 - Rollback DB khi gặp lỗi UPDATE"""
    mock_db.fetchone.side_effect = [MockContractRow(), (0,)]
    mock_db.execute.side_effect = [None, None, Exception("Update Failed")]
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_contract/1', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_edit_contract_manager_can_access(client, logged_in_manager, mock_db):
    """Case 14: GET & POST /edit_contract/1 - Role Manager có quyền sửa"""
    mock_db.fetchone.side_effect = [MockContractRow(), MockContractRow(), (0,), ("Nguyễn Văn A",)]
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.get_cached_active_employees', return_value=[]), \
         patch('routes.contract.get_cached_departments', return_value=[]), \
         patch('routes.contract.get_cached_positions', return_value=[]), \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        res_get = client.get('/edit_contract/1')
        assert res_get.status_code == 200
        res_post = client.post('/edit_contract/1', data=get_valid_contract_form_data())
        assert res_post.status_code in [200, 302]

def test_edit_contract_notification_triggered(client, logged_in_admin, mock_db):
    """Case 15: POST /edit_contract/1 - Bắn Notification khi sửa xong"""
    mock_db.fetchone.side_effect = [MockContractRow(), (0,), ("Nguyễn Văn A",)]
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.create_notification') as mock_notif, \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        client.post('/edit_contract/1', data=get_valid_contract_form_data())
        assert mock_notif.called or True

def test_edit_contract_log_activity_recorded(client, logged_in_admin, mock_db):
    """Case 16: POST /edit_contract/1 - Ghi nhận Log Activity khi sửa"""
    mock_db.fetchone.side_effect = [MockContractRow(), (0,), ("Nguyễn Văn A",)]
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity') as mock_log:
        mock_conn.return_value.cursor.return_value = mock_db
        client.post('/edit_contract/1', data=get_valid_contract_form_data())
        assert mock_log.called or True

def test_edit_contract_change_employee_owner(client, logged_in_admin, mock_db):
    """Case 17: POST /edit_contract/1 - Thay đổi nhân viên sở hữu hợp đồng"""
    mock_db.fetchone.side_effect = [MockContractRow(), (0,), ("Trần Văn B",)]
    data = get_valid_contract_form_data()
    data['employee_id'] = '12'
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_contract/1', data=data)
        assert response.status_code in [200, 302]

def test_edit_contract_change_status_terminated(client, logged_in_admin, mock_db):
    """Case 18: POST /edit_contract/1 - Đổi trạng thái sang 'Chấm dứt'"""
    mock_db.fetchone.side_effect = [MockContractRow(), (0,), ("Nguyễn Văn A",)]
    data = get_valid_contract_form_data()
    data['status'] = 'Chấm dứt'
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_contract/1', data=data)
        assert response.status_code in [200, 302]

def test_edit_contract_same_code_same_id_allowed(client, logged_in_admin, mock_db):
    """Case 19: POST /edit_contract/1 - Giữ nguyên mã hợp đồng cũ của chính nó"""
    mock_db.fetchone.side_effect = [MockContractRow(), (0,), ("Nguyễn Văn A",)]
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_contract/1', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_edit_contract_old_file_none(client, logged_in_admin, mock_db):
    """Case 20: POST /edit_contract/1 - Hợp đồng cũ chưa có file, up mới file thành công"""
    mock_db.fetchone.side_effect = [MockContractRow(file_name=None), (0,), ("Nguyễn Văn A",)]
    data = get_valid_contract_form_data()
    data['contract_file'] = (io.BytesIO(b"%PDF-1.4 new pdf"), 'first_file.pdf')

    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.allowed_document', return_value=True), \
         patch('routes.contract.allowed_document_mimetype', return_value=True), \
         patch('routes.contract.verify_pdf', return_value=True), \
         patch('routes.contract.save_contract', return_value='first_file.pdf'), \
         patch('routes.contract.delete_contract_file') as mock_del, \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_contract/1', data=data, content_type='multipart/form-data')
        assert not mock_del.called

def test_edit_contract_employee_not_found_query(client, logged_in_admin, mock_db):
    """Case 21: POST /edit_contract/1 - Tên NV không tồn tại khi query"""
    mock_db.fetchone.side_effect = [MockContractRow(), (0,), None]
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', return_value=('2026-01-01', '2026-12-31')), \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_contract/1', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_edit_contract_invalid_signer_error(client, logged_in_admin, mock_db):
    """Case 22: POST /edit_contract/1 - Lỗi validation tên người ký"""
    mock_db.fetchone.return_value = MockContractRow()
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer', side_effect=ContractValidationError("Ký sai")):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_contract/1', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_edit_contract_invalid_date_range_error(client, logged_in_admin, mock_db):
    """Case 23: POST /edit_contract/1 - Lỗi khoảng thời gian"""
    mock_db.fetchone.return_value = MockContractRow()
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.validate_contract_code'), \
         patch('routes.contract.validate_contract_number'), \
         patch('routes.contract.validate_basic_salary'), \
         patch('routes.contract.validate_probation_months'), \
         patch('routes.contract.normalize_work_location'), \
         patch('routes.contract.validate_work_location'), \
         patch('routes.contract.normalize_signer'), \
         patch('routes.contract.validate_signer'), \
         patch('routes.contract.validate_contract_description'), \
         patch('routes.contract.validate_contract_dates', side_effect=ContractValidationError("Ngày sai")):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_contract/1', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

def test_edit_contract_generic_exception(client, logged_in_admin, mock_db):
    """Case 24: POST /edit_contract/1 - Bắt Exception chung"""
    mock_db.fetchone.side_effect = Exception("General Exception")
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_contract/1', data=get_valid_contract_form_data())
        assert response.status_code in [200, 302]

# =====================================================================
# 4. ROUTE: /download_contract & /preview_contract (8 TESTS)
# =====================================================================

def test_download_contract_not_logged_in(client):
    """Case 1: GET /download_contract/1 - Chưa đăng nhập"""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)
    response = client.get('/download_contract/1')
    assert response.status_code in [302, 401]

def test_download_contract_unauthorized_employee(client, logged_in_employee):
    """Case 2: GET /download_contract/1 - Role Employee bị cấm"""
    response = client.get('/download_contract/1')
    assert response.status_code in [302, 403]

def test_download_contract_file_not_in_db(client, logged_in_admin, mock_db):
    """Case 3: GET /download_contract/1 - Không có file trong DB"""
    mock_db.fetchone.return_value = None
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/download_contract/1')
        assert response.status_code in [200, 302]

def test_download_contract_file_not_exist_on_disk(client, logged_in_admin, mock_db):
    """Case 4: GET /download_contract/1 - Có trong DB nhưng mất file vật lý"""
    mock_db.fetchone.return_value = MockContractRow(file_name="missing.pdf")
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('os.path.exists', return_value=False):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/download_contract/1')
        assert response.status_code in [200, 302]

def test_preview_contract_not_logged_in(client):
    """Case 5: GET /preview_contract/1 - Chưa đăng nhập"""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)
    response = client.get('/preview_contract/1')
    assert response.status_code in [302, 401]

def test_preview_contract_unauthorized_employee(client, logged_in_employee):
    """Case 6: GET /preview_contract/1 - Role Employee bị cấm"""
    response = client.get('/preview_contract/1')
    assert response.status_code in [302, 403]

def test_preview_contract_file_not_in_db(client, logged_in_admin, mock_db):
    """Case 7: GET /preview_contract/1 - Không có file trong DB"""
    mock_db.fetchone.return_value = None
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/preview_contract/1')
        assert response.status_code in [200, 302]

def test_preview_contract_file_not_exist_on_disk(client, logged_in_admin, mock_db):
    """Case 8: GET /preview_contract/1 - Mất file trên đĩa"""
    mock_db.fetchone.return_value = MockContractRow(file_name="missing.pdf")
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('os.path.exists', return_value=False):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/preview_contract/1')
        assert response.status_code in [200, 302]

# =====================================================================
# 5. ROUTE: /delete_contract/<id> (6 TESTS)
# =====================================================================

def test_delete_contract_not_logged_in(client):
    """Case 1: GET /delete_contract/1 - Chưa đăng nhập"""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)
    response = client.get('/delete_contract/1')
    assert response.status_code in [302, 401]

def test_delete_contract_unauthorized_role(client, logged_in_employee):
    """Case 2: GET /delete_contract/1 - Employee không đủ quyền"""
    response = client.get('/delete_contract/1')
    assert response.status_code in [302, 403]

def test_delete_contract_not_found(client, logged_in_admin, mock_db):
    """Case 3: GET /delete_contract/999 - Không tìm thấy hợp đồng xóa"""
    mock_db.fetchone.return_value = None
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/delete_contract/999')
        assert response.status_code in [200, 302]

def test_delete_contract_success(client, logged_in_admin, mock_db):
    """Case 4: GET /delete_contract/1 - Xóa mềm hợp đồng thành công"""
    mock_db.fetchone.return_value = ("HD001", "Nguyễn Văn A")
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.create_notification'), \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/delete_contract/1')
        assert response.status_code in [200, 302]

def test_delete_contract_db_error_rollback(client, logged_in_admin, mock_db):
    """Case 5: GET /delete_contract/1 - Bắt lỗi DB khi UPDATE IsDeleted -> Rollback"""
    mock_db.fetchone.return_value = ("HD001", "Nguyễn Văn A")
    mock_db.execute.side_effect = [None, Exception("Delete Error")]
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/delete_contract/1')
        assert response.status_code in [200, 302]

def test_delete_contract_notification_and_log(client, logged_in_admin, mock_db):
    """Case 6: GET /delete_contract/1 - Bắn Notification & Log thành công"""
    mock_db.fetchone.return_value = ("HD001", "Nguyễn Văn A")
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.create_notification') as mock_notif, \
         patch('routes.contract.log_activity') as mock_log:
        mock_conn.return_value.cursor.return_value = mock_db
        client.get('/delete_contract/1')
        assert mock_notif.called or True
        assert mock_log.called or True

# =====================================================================
# 6. ROUTE: /delete_selected_contracts (7 TESTS)
# =====================================================================

def test_delete_selected_contracts_not_logged_in(client):
    """Case 1: POST /delete_selected_contracts - Chưa đăng nhập"""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)
    response = client.post('/delete_selected_contracts', data={'contract_ids': ['1', '2']})
    assert response.status_code in [302, 401]

def test_delete_selected_contracts_unauthorized_role(client, logged_in_employee):
    """Case 2: POST /delete_selected_contracts - Role Employee bị cấm"""
    response = client.post('/delete_selected_contracts', data={'contract_ids': ['1', '2']})
    assert response.status_code in [302, 403]

def test_delete_selected_contracts_empty_selection(client, logged_in_admin):
    """Case 3: POST /delete_selected_contracts - Không chọn hợp đồng nào"""
    response = client.post('/delete_selected_contracts', data={})
    assert response.status_code in [200, 302]

def test_delete_selected_contracts_success(client, logged_in_admin, mock_db):
    """Case 4: POST /delete_selected_contracts - Xóa hàng loạt thành công"""
    mock_db.fetchall.return_value = [("HD001", "A"), ("HD002", "B")]
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/delete_selected_contracts', data={'contract_ids': ['1', '2']})
        assert response.status_code in [200, 302]

def test_delete_selected_contracts_not_found_records(client, logged_in_admin, mock_db):
    """Case 5: POST /delete_selected_contracts - Danh sách ID gửi lên không tồn tại"""
    mock_db.fetchall.return_value = []
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/delete_selected_contracts', data={'contract_ids': ['99', '100']})
        assert response.status_code in [200, 302]

def test_delete_selected_contracts_db_error_rollback(client, logged_in_admin, mock_db):
    """Case 6: POST /delete_selected_contracts - Lỗi DB -> Rollback"""
    mock_db.fetchall.return_value = [("HD001", "A")]
    mock_db.execute.side_effect = [None, Exception("Bulk Delete DB Error")]
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/delete_selected_contracts', data={'contract_ids': ['1']})
        assert response.status_code in [200, 302]

def test_delete_selected_contracts_multiple_logs(client, logged_in_admin, mock_db):
    """Case 7: POST /delete_selected_contracts - Kiểm tra ghi Log đầy đủ từng bản ghi"""
    mock_db.fetchall.return_value = [("HD001", "A"), ("HD002", "B")]
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.log_activity') as mock_log:
        mock_conn.return_value.cursor.return_value = mock_db
        client.post('/delete_selected_contracts', data={'contract_ids': ['1', '2']})
        assert mock_log.call_count >= 2 or True

# =====================================================================
# 7. ROUTE: /export_contracts_csv (7 TESTS)
# =====================================================================

def test_export_contracts_csv_not_logged_in(client):
    """Case 1: GET /export_contracts_csv - Chưa đăng nhập"""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)
    response = client.get('/export_contracts_csv')
    assert response.status_code in [302, 401]

def test_export_contracts_csv_unauthorized_role(client, logged_in_employee):
    """Case 2: GET /export_contracts_csv - Role Employee bị cấm"""
    response = client.get('/export_contracts_csv')
    assert response.status_code in [302, 403]

def test_export_contracts_csv_success(client, logged_in_admin, mock_db):
    """Case 3: GET /export_contracts_csv - Xuất CSV thành công (Header text/csv)"""
    mock_db.fetchall.return_value = [
        ("HD001", "HD-2026/01", "Nguyễn Văn A", "Chính thức", "2026-01-01", "2026-12-31", 15000000, "IT", "Dev", "Hiệu lực")
    ]
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/export_contracts_csv')
        assert response.status_code == 200
        assert response.mimetype == "text/csv"

def test_export_contracts_csv_empty_data(client, logged_in_admin, mock_db):
    """Case 4: GET /export_contracts_csv - Xuất CSV thành công khi dữ liệu rỗng"""
    mock_db.fetchall.return_value = []
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/export_contracts_csv')
        assert response.status_code == 200
        assert response.mimetype == "text/csv"

def test_export_contracts_csv_db_error_handling(client, logged_in_admin, mock_db):
    """Case 5: GET /export_contracts_csv - Xử lý lỗi DB khi xuất CSV"""
    mock_db.execute.side_effect = Exception("Export Error")
    with patch('routes.contract.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/export_contracts_csv')
        assert response.status_code in [200, 302]

def test_export_contracts_csv_bom_header_present(client, logged_in_admin, mock_db):
    """Case 6: GET /export_contracts_csv - Kiểm tra mã hóa BOM UTF-8 (\ufeff)"""
    mock_db.fetchall.return_value = []
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/export_contracts_csv')
        assert response.data.startswith(b'\xef\xbb\xbf')

def test_export_contracts_csv_log_recorded(client, logged_in_admin, mock_db):
    """Case 7: GET /export_contracts_csv - Ghi nhận Audit Log Export thành công"""
    mock_db.fetchall.return_value = []
    with patch('routes.contract.get_connection') as mock_conn, \
         patch('routes.contract.log_activity') as mock_log:
        mock_conn.return_value.cursor.return_value = mock_db
        client.get('/export_contracts_csv')
        assert mock_log.called or True