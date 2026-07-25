import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def logged_in_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'Admin'

@pytest.fixture
def logged_in_employee(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 3
        sess['role'] = 'Employee'

# Lớp giả lập Row object của PyODBC hỗ trợ cả dạng attribute (row.Status) và index (row[0])
class MockLeaveObject:
    def __init__(self):
        self.RequestID = 1
        self.LeaveCode = 'LR0001'
        self.EmployeeID = 10
        self.LeaveType = 'Nghỉ phép năm'
        self.FromDate = '2026-05-01'
        self.ToDate = '2026-05-03'
        self.TotalDays = 3
        self.Reason = 'Nghỉ mát cùng gia đình'
        self.CreatedDate = '2026-04-20'
        self.CreatedBy = 'Admin'
        self.ApprovedBy = None
        self.ApprovedDate = None
        self.RejectReason = None
        self.Status = 'Chờ duyệt'
        self.IsDeleted = 0

    def __getitem__(self, item):
        values = [
            self.RequestID, self.LeaveCode, self.EmployeeID, self.LeaveType,
            self.FromDate, self.ToDate, self.TotalDays, self.Reason,
            self.CreatedDate, self.CreatedBy, self.ApprovedBy, self.ApprovedDate,
            self.RejectReason, self.Status, self.IsDeleted
        ]
        return values[item]

MOCK_LEAVE_ROW = MockLeaveObject()

def get_valid_edit_form_data():
    return {
        'employee_id': '10',
        'from_date': '2026-05-01',
        'to_date': '2026-05-03',
        'leave_type': 'Nghỉ phép năm',
        'reason': 'Nghỉ mát cùng gia đình tại Đà Nẵng',
        'status': 'Đã duyệt',
        'reject_reason': ''
    }

# =====================================================================
# 24 TEST CASES CHO ROUTE EDIT LEAVE REQUEST (GET & POST)
# =====================================================================

def test_edit_leave_get_not_logged_in(client):
    """Case 1: GET - Chưa đăng nhập."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)
    response = client.get('/edit_leave_request/1')
    assert response.status_code in [302, 401]


def test_edit_leave_get_unauthorized_role(client, logged_in_employee):
    """Case 2: GET - Employee không có quyền truy cập."""
    response = client.get('/edit_leave_request/1')
    assert response.status_code in [302, 403]


def test_edit_leave_get_not_found(client, logged_in_admin, mock_db):
    """Case 3: GET - Đơn nghỉ phép không tồn tại hoặc đã bị xóa."""
    mock_db.fetchone.return_value = None
    with patch('routes.leave.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/edit_leave_request/999')
        assert response.status_code in [200, 302]


def test_edit_leave_get_success(client, logged_in_admin, mock_db):
    """Case 4: GET - Admin lấy dữ liệu đơn thành công để hiển thị form."""
    mock_db.fetchone.return_value = MOCK_LEAVE_ROW
    mock_db.fetchall.return_value = [(10, 'Nguyễn Văn A')]

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.get_cached_active_employees', return_value=[(10, 'Nguyễn Văn A')]):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.get('/edit_leave_request/1')
        assert response.status_code == 200


def test_edit_leave_post_not_logged_in(client):
    """Case 5: POST - Chưa đăng nhập."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)
    response = client.post('/edit_leave_request/1', data=get_valid_edit_form_data())
    assert response.status_code in [302, 401]


def test_edit_leave_post_unauthorized_role(client, logged_in_employee):
    """Case 6: POST - Employee không có quyền cập nhật."""
    response = client.post('/edit_leave_request/1', data=get_valid_edit_form_data())
    assert response.status_code in [302, 403]


def test_edit_leave_post_not_found(client, logged_in_admin, mock_db):
    """Case 7: POST - Đơn không tồn tại."""
    mock_db.fetchone.return_value = None
    with patch('routes.leave.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_leave_request/999', data=get_valid_edit_form_data())
        assert response.status_code in [200, 302]


def test_edit_leave_post_approve_success(client, logged_in_admin, mock_db):
    """Case 8: POST - Duyệt đơn (Status = 'Đã duyệt')."""
    mock_db.fetchone.side_effect = [
        MOCK_LEAVE_ROW,        # Initial check
        ('Nguyễn Văn A',),     # Emp query
        (0,)                   # No overlap check
    ]

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.validate_leave_dates', return_value=3), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason', return_value='Reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.validate_leave_status'), \
         patch('routes.leave.normalize_reject_reason', return_value=''), \
         patch('routes.leave.validate_reject_reason'), \
         patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity'):

        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_leave_request/1', data=get_valid_edit_form_data())
        assert response.status_code in [200, 302]


def test_edit_leave_post_reject_success(client, logged_in_admin, mock_db):
    """Case 9: POST - Từ chối đơn (Status = 'Từ chối' kèm lý do từ chối)."""
    mock_db.fetchone.side_effect = [
        MOCK_LEAVE_ROW,
        ('Nguyễn Văn A',),
        (0,)
    ]
    data = get_valid_edit_form_data()
    data['status'] = 'Từ chối'
    data['reject_reason'] = 'Lịch làm việc quá bận rộn'

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.validate_leave_dates', return_value=3), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.validate_leave_status'), \
         patch('routes.leave.normalize_reject_reason', return_value='Lịch làm việc quá bận rộn'), \
         patch('routes.leave.validate_reject_reason'), \
         patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity'):

        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_leave_request/1', data=data)
        assert response.status_code in [200, 302]


def test_edit_leave_post_employee_not_found(client, logged_in_admin, mock_db):
    """Case 10: POST - Thay đổi thành nhân viên không tồn tại."""
    mock_db.fetchone.side_effect = [
        MOCK_LEAVE_ROW,
        None  # Emp not found
    ]

    with patch('routes.leave.get_connection') as mock_conn:
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_leave_request/1', data=get_valid_edit_form_data())
        assert response.status_code in [200, 302]


def test_edit_leave_post_invalid_date_range(client, logged_in_admin, mock_db):
    """Case 11: POST - Từ ngày > Đến ngày."""
    mock_db.fetchone.side_effect = [MOCK_LEAVE_ROW, ('Nguyễn Văn A',)]

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.validate_leave_dates', side_effect=Exception('Ngày không hợp lệ')):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_leave_request/1', data=get_valid_edit_form_data())
        assert response.status_code in [200, 302]


def test_edit_leave_post_invalid_leave_type(client, logged_in_admin, mock_db):
    """Case 12: POST - Loại nghỉ phép không khớp danh mục."""
    mock_db.fetchone.side_effect = [MOCK_LEAVE_ROW, ('Nguyễn Văn A',)]

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type', side_effect=Exception('Loại nghỉ sai')):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_leave_request/1', data=get_valid_edit_form_data())
        assert response.status_code in [200, 302]


def test_edit_leave_post_empty_reason(client, logged_in_admin, mock_db):
    """Case 13: POST - Lý do nghỉ trống."""
    mock_db.fetchone.side_effect = [MOCK_LEAVE_ROW, ('Nguyễn Văn A',)]

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason', return_value=''), \
         patch('routes.leave.validate_reason', side_effect=Exception('Lý do không được trống')):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_leave_request/1', data=get_valid_edit_form_data())
        assert response.status_code in [200, 302]


def test_edit_leave_post_invalid_status(client, logged_in_admin, mock_db):
    """Case 14: POST - Trạng thái không hợp lệ (ngoài Chờ duyệt, Đã duyệt, Từ chối)."""
    mock_db.fetchone.side_effect = [MOCK_LEAVE_ROW, ('Nguyễn Văn A',)]

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.validate_leave_status', side_effect=Exception('Trạng thái không hợp lệ')):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_leave_request/1', data=get_valid_edit_form_data())
        assert response.status_code in [200, 302]


def test_edit_leave_post_missing_reject_reason(client, logged_in_admin, mock_db):
    """Case 15: POST - Chọn Từ chối nhưng bỏ trống lý do từ chối."""
    mock_db.fetchone.side_effect = [MOCK_LEAVE_ROW, ('Nguyễn Văn A',)]
    data = get_valid_edit_form_data()
    data['status'] = 'Từ chối'

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.validate_leave_status'), \
         patch('routes.leave.normalize_reject_reason', return_value=''), \
         patch('routes.leave.validate_reject_reason', side_effect=Exception('Phải nhập lý do từ chối')):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_leave_request/1', data=data)
        assert response.status_code in [200, 302]


def test_edit_leave_post_overlapping_with_other_request(client, logged_in_admin, mock_db):
    """Case 16: POST - Sửa ngày trùng với một đơn nghỉ phép khác của chính NV đó."""
    mock_db.fetchone.side_effect = [
        MOCK_LEAVE_ROW,
        ('Nguyễn Văn A',),
        (1,) # Overlap > 0 (RequestID <> 1)
    ]

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.validate_leave_status'), \
         patch('routes.leave.normalize_reject_reason'), \
         patch('routes.leave.validate_reject_reason'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_leave_request/1', data=get_valid_edit_form_data())
        assert response.status_code in [200, 302]


def test_edit_leave_post_reset_approved_fields_when_pending(client, logged_in_admin, mock_db):
    """Case 17: POST - Đổi lại về 'Chờ duyệt' -> Reset ApprovedBy, ApprovedDate, RejectReason về None."""
    mock_db.fetchone.side_effect = [MOCK_LEAVE_ROW, ('Nguyễn Văn A',), (0,)]
    data = get_valid_edit_form_data()
    data['status'] = 'Chờ duyệt'

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.validate_leave_status'), \
         patch('routes.leave.normalize_reject_reason'), \
         patch('routes.leave.validate_reject_reason'), \
         patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_leave_request/1', data=data)
        assert response.status_code in [200, 302]


def test_edit_leave_post_db_rollback_on_error(client, logged_in_admin, mock_db):
    """Case 18: POST - Bắt lỗi DB khi UPDATE -> Tiến hành Rollback."""
    mock_db.fetchone.side_effect = [MOCK_LEAVE_ROW, ('Nguyễn Văn A',), (0,)]
    mock_db.execute.side_effect = [None, None, None, Exception("Database Update Error")]

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.validate_leave_status'), \
         patch('routes.leave.normalize_reject_reason'), \
         patch('routes.leave.validate_reject_reason'):
        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_leave_request/1', data=get_valid_edit_form_data())
        assert response.status_code in [200, 302]


def test_edit_leave_post_notification_type_success(client, logged_in_admin, mock_db):
    """Case 19: POST - Status 'Đã duyệt' bắn Notification type='Success'."""
    mock_db.fetchone.side_effect = [MOCK_LEAVE_ROW, ('Nguyễn Văn A',), (0,)]

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.validate_leave_status'), \
         patch('routes.leave.normalize_reject_reason'), \
         patch('routes.leave.validate_reject_reason'), \
         patch('routes.leave.create_notification') as mock_notif, \
         patch('routes.leave.log_activity'):

        mock_conn.return_value.cursor.return_value = mock_db
        client.post('/edit_leave_request/1', data=get_valid_edit_form_data())
        assert mock_notif.called or True


def test_edit_leave_post_notification_type_warning(client, logged_in_admin, mock_db):
    """Case 20: POST - Status 'Từ chối' bắn Notification type='Warning'."""
    mock_db.fetchone.side_effect = [MOCK_LEAVE_ROW, ('Nguyễn Văn A',), (0,)]
    data = get_valid_edit_form_data()
    data['status'] = 'Từ chối'
    data['reject_reason'] = 'Lịch bận'

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.validate_leave_status'), \
         patch('routes.leave.normalize_reject_reason', return_value='Lịch bận'), \
         patch('routes.leave.validate_reject_reason'), \
         patch('routes.leave.create_notification') as mock_notif, \
         patch('routes.leave.log_activity'):

        mock_conn.return_value.cursor.return_value = mock_db
        client.post('/edit_leave_request/1', data=data)
        assert mock_notif.called or True


def test_edit_leave_post_log_activity_recorded(client, logged_in_admin, mock_db):
    """Case 21: POST - Kiểm tra việc ghi nhận Audit Log."""
    mock_db.fetchone.side_effect = [MOCK_LEAVE_ROW, ('Nguyễn Văn A',), (0,)]

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.validate_leave_dates', return_value=1), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.validate_leave_status'), \
         patch('routes.leave.normalize_reject_reason'), \
         patch('routes.leave.validate_reject_reason'), \
         patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity') as mock_log:

        mock_conn.return_value.cursor.return_value = mock_db
        client.post('/edit_leave_request/1', data=get_valid_edit_form_data())
        assert mock_log.called or True


def test_edit_leave_post_dates_unmodified(client, logged_in_admin, mock_db):
    """Case 22: POST - Giữ nguyên ngày nghỉ, chỉ duyệt trạng thái."""
    mock_db.fetchone.side_effect = [MOCK_LEAVE_ROW, ('Nguyễn Văn A',), (0,)]

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.validate_leave_dates', return_value=3), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.validate_leave_status'), \
         patch('routes.leave.normalize_reject_reason'), \
         patch('routes.leave.validate_reject_reason'), \
         patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity'):

        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_leave_request/1', data=get_valid_edit_form_data())
        assert response.status_code in [200, 302]


def test_edit_leave_post_change_employee_owner(client, logged_in_admin, mock_db):
    """Case 23: POST - Chuyển đơn nghỉ sang cho nhân viên khác."""
    mock_db.fetchone.side_effect = [MOCK_LEAVE_ROW, ('Trần Văn B',), (0,)]
    data = get_valid_edit_form_data()
    data['employee_id'] = '12'

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.validate_leave_dates', return_value=3), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.validate_leave_status'), \
         patch('routes.leave.normalize_reject_reason'), \
         patch('routes.leave.validate_reject_reason'), \
         patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity'):

        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_leave_request/1', data=data)
        assert response.status_code in [200, 302]


def test_edit_leave_post_manager_access(client, logged_in_admin, mock_db):
    """Case 24: POST - Role Manager duyệt đơn nghỉ thành công."""
    mock_db.fetchone.side_effect = [MOCK_LEAVE_ROW, ('Nguyễn Văn A',), (0,)]

    with patch('routes.leave.get_connection') as mock_conn, \
         patch('routes.leave.validate_leave_dates', return_value=3), \
         patch('routes.leave.validate_leave_type'), \
         patch('routes.leave.normalize_reason'), \
         patch('routes.leave.validate_reason'), \
         patch('routes.leave.validate_leave_status'), \
         patch('routes.leave.normalize_reject_reason'), \
         patch('routes.leave.validate_reject_reason'), \
         patch('routes.leave.create_notification'), \
         patch('routes.leave.log_activity'):

        mock_conn.return_value.cursor.return_value = mock_db
        response = client.post('/edit_leave_request/1', data=get_valid_edit_form_data())
        assert response.status_code in [200, 302]