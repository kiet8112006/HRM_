import pytest
from unittest.mock import patch, MagicMock

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

# Dummy row cho pyodbc Row object
class DummyRow:
    def __init__(self, req_id, code, emp, leave_type):
        self.RequestID = req_id
        self.LeaveCode = code
        self.FullName = emp
        self.LeaveType = leave_type
        self.FromDate = '2026-05-01'
        self.ToDate = '2026-05-02'
        self.TotalDays = 2
        self.Reason = 'Ốm'
        self.Status = 'Đã duyệt'
        self.ApprovedBy = 'Admin'
        self.ApprovedDate = '2026-04-28'
        self.RejectReason = ''

# =====================================================================
# 7 TEST CASES CHO ROUTE EXPORT LEAVE REQUESTS CSV
# =====================================================================

def test_export_leave_csv_not_logged_in(client):
    """Case 1: Chưa đăng nhập -> Redirect login."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)
    response = client.get('/export_leave_requests_csv')
    assert response.status_code in [302, 401]


def test_export_leave_csv_unauthorized_role(client, logged_in_employee):
    """Case 2: Role Employee không có quyền xuất CSV."""
    response = client.get('/export_leave_requests_csv')
    assert response.status_code in [302, 403]


def test_export_leave_csv_admin_success(client, logged_in_admin, mock_db):
    """Case 3: Admin xuất CSV thành công."""
    mock_db.fetchall.return_value = [DummyRow(1, 'LR0001', 'Nguyễn Văn A', 'Nghỉ phép năm')]

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/export_leave_requests_csv')
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'


def test_export_leave_csv_manager_success(client, logged_in_manager, mock_db):
    """Case 4: Manager xuất CSV thành công."""
    mock_db.fetchall.return_value = [DummyRow(1, 'LR0001', 'Trần Văn B', 'Nghỉ bệnh')]

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/export_leave_requests_csv')
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'


def test_export_leave_csv_empty_data(client, logged_in_admin, mock_db):
    """Case 5: Xuất CSV khi không có dữ liệu đơn nghỉ phép nào trong DB."""
    mock_db.fetchall.return_value = []

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/export_leave_requests_csv')
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'


def test_export_leave_csv_contains_utf8_bom(client, logged_in_admin, mock_db):
    """Case 6: Đảm bảo file CSV xuất ra chứa UTF-8 BOM hiển thị đúng tiếng Việt Excel."""
    mock_db.fetchall.return_value = [DummyRow(1, 'LR0001', 'Nguyễn Văn A', 'Nghỉ thai sản')]

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/export_leave_requests_csv')
        assert response.status_code == 200
        assert response.data.startswith(b'\xef\xbb\xbf')


def test_export_leave_csv_db_exception(client, logged_in_admin, mock_db):
    """Case 7: Ngoại lệ DB khi truy vấn xuất CSV -> Flash thông báo lỗi và redirect."""
    mock_db.execute.side_effect = Exception("CSV Export Query Error")

    with patch('routes.leave.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/export_leave_requests_csv')
        assert response.status_code in [200, 302]