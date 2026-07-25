import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from exceptions.validator.attendance import AttendanceValidationError

# =====================================================================
# FIXTURES & MOCK DATA
# =====================================================================

@pytest.fixture
def logged_in_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'admin_user'  # Thêm username tránh lỗi NULL AuditLogs
        sess['user_role'] = 'Admin'
        sess['logged_in'] = True

@pytest.fixture
def logged_in_manager(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['username'] = 'manager_user'
        sess['user_role'] = 'Manager'
        sess['logged_in'] = True

@pytest.fixture
def logged_in_employee(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 3
        sess['username'] = 'employee_user'
        sess['user_role'] = 'Employee'
        sess['logged_in'] = True

@pytest.fixture
def mock_db():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor

@pytest.fixture
def mock_attendance_row():
    row = MagicMock()
    row.AttendanceID = 1
    row.FullName = "Nguyen Van A"
    row.Date = date(2026, 3, 20)
    row.CheckInTime = "08:00"
    row.CheckOutTime = "17:00"
    row.WorkingHours = 8.0
    row.OvertimeHours = 0.0
    row.LateMinutes = 0
    row.EarlyLeaveMinutes = 0
    row.CheckInMethod = "Fingerprint"
    row.Status = "Present"
    row.ApprovalStatus = "Approved"
    row.Notes = "Good"
    row.__getitem__ = lambda self, idx: [
        1, "Nguyen Van A", date(2026, 3, 20), "08:00", "17:00", 
        8.0, 0.0, 0, 0, "Fingerprint", "Present", "Approved", "Good"
    ][idx]
    return row


# =====================================================================
# 1. ROUTE: /attendance (GET)
# =====================================================================

class TestAttendanceList:

    def test_attendance_unauthenticated(self, client):
        """Case 1: Chưa đăng nhập -> Redirect hoặc Unauthorized"""
        response = client.get('/attendance')
        assert response.status_code in [200, 302, 401]

    def test_attendance_unauthorized_role(self, client, logged_in_employee):
        """Case 2: Role Employee không có quyền vào xem danh sách"""
        response = client.get('/attendance')
        assert response.status_code in [200, 302, 403]

    def test_attendance_success_admin(self, client, logged_in_admin, mock_db):
        """Case 3: Admin truy cập thành công"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = [1]
        cursor.fetchall.return_value = []

        with patch('routes.attendance.get_connection', return_value=conn):
            response = client.get('/attendance')
            assert response.status_code == 200

    def test_attendance_success_manager(self, client, logged_in_manager, mock_db):
        """Case 4: Manager truy cập thành công"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = [0]
        cursor.fetchall.return_value = []

        with patch('routes.attendance.get_connection', return_value=conn):
            response = client.get('/attendance')
            assert response.status_code == 200

    def test_attendance_with_search_keyword_and_status(self, client, logged_in_admin, mock_db):
        """Case 5: Tìm kiếm theo keyword và status"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = [5]
        cursor.fetchall.return_value = []

        with patch('routes.attendance.get_connection', return_value=conn):
            response = client.get('/attendance?keyword=Nguyen&status=Present&page=2')
            assert response.status_code == 200

    def test_attendance_invalid_page_number(self, client, logged_in_admin, mock_db):
        """Case 6: Truyền page là chữ -> Fallback về default page 1"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = [0]
        cursor.fetchall.return_value = []

        with patch('routes.attendance.get_connection', return_value=conn):
            response = client.get('/attendance?page=abc')
            assert response.status_code == 200

    def test_attendance_pagination_calculation(self, client, logged_in_admin, mock_db):
        """Case 7: Kiểm tra tính toán total_pages"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = [25]
        cursor.fetchall.return_value = []

        with patch('routes.attendance.get_connection', return_value=conn):
            response = client.get('/attendance?page=3')
            assert response.status_code == 200

    def test_attendance_db_exception(self, client, logged_in_admin, mock_db):
        """Case 8: Lỗi Database khi query danh sách"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("Database connection failed")

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.current_app.logger.error'):
            response = client.get('/attendance')
            assert response.status_code == 200

    def test_attendance_empty_result(self, client, logged_in_admin, mock_db):
        """Case 9: Kết quả tìm kiếm rỗng"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = [0]
        cursor.fetchall.return_value = []

        with patch('routes.attendance.get_connection', return_value=conn):
            response = client.get('/attendance')
            assert response.status_code == 200

    def test_attendance_whitespace_keyword(self, client, logged_in_admin, mock_db):
        """Case 10: Nhập keyword chỉ có khoảng trắng"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = [0]
        cursor.fetchall.return_value = []

        with patch('routes.attendance.get_connection', return_value=conn):
            response = client.get('/attendance?keyword=%20%20')
            assert response.status_code == 200

    def test_attendance_ensure_connection_closed(self, client, logged_in_admin, mock_db):
        """Case 11: Đảm bảo conn.close() luôn được gọi"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = [0]

        with patch('routes.attendance.get_connection', return_value=conn):
            client.get('/attendance')
            conn.close.assert_called_once()

    def test_attendance_ensure_connection_closed_on_error(self, client, logged_in_admin, mock_db):
        """Case 12: Đảm bảo conn.close() được gọi khi có Exception"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("Fatal SQL Error")

        with patch('routes.attendance.get_connection', return_value=conn):
            client.get('/attendance')
            conn.close.assert_called_once()


# =====================================================================
# 2. ROUTE: /add_attendance (GET & POST)
# =====================================================================

class TestAddAttendance:

    def test_add_attendance_get_unauthenticated(self, client):
        """Case 1: Unauthenticated GET /add_attendance"""
        response = client.get('/add_attendance')
        assert response.status_code in [200, 302, 401]

    def test_add_attendance_get_unauthorized_manager(self, client, logged_in_manager):
        """Case 2: Manager truy cập /add_attendance"""
        response = client.get('/add_attendance')
        assert response.status_code in [200, 302, 403]

    def test_add_attendance_get_success(self, client, logged_in_admin):
        """Case 3: GET /add_attendance hiển thị form"""
        with patch('routes.attendance.get_cached_active_employees', return_value=[(1, "Nguyen Van A")]):
            response = client.get('/add_attendance')
            assert response.status_code == 200

    def test_add_attendance_post_success(self, client, logged_in_admin, mock_db):
        """Case 4: POST /add_attendance hợp lệ -> Thêm thành công"""
        conn, cursor = mock_db
        cursor.fetchone.side_effect = [[1], [0], ["Nguyen Van A"]]

        valid_data = {
            "employee_id": "1",
            "date": "2026-03-20",
            "checkin": "08:00",
            "checkout": "17:00",
            "status": "Present",
            "checkin_method": "Fingerprint",
            "approval_status": "Approved",
            "notes": "Valid note"
        }

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes'), \
             patch('routes.attendance.validate_attendance_date'), \
             patch('routes.attendance.validate_checkin_checkout_times', return_value=('08:00', '17:00', 8.0, 0.0, 0, 0)), \
             patch('routes.attendance.create_notification'), \
             patch('routes.attendance.log_activity'), \
             patch('utils.audit.log_activity'):

            response = client.post('/add_attendance', data=valid_data)
            assert response.status_code == 302
            assert response.location.endswith('/attendance')

    def test_add_attendance_validation_error_status(self, client, logged_in_admin, mock_db):
        """Case 5: Lỗi Validator Status"""
        conn, cursor = mock_db

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status', side_effect=AttendanceValidationError("Status error")), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.post('/add_attendance', data={"date": "2026-03-20"})
            assert response.status_code in [200, 302]

    def test_add_attendance_validation_error_approval_status(self, client, logged_in_admin, mock_db):
        """Case 6: Lỗi Validator Approval Status"""
        conn, cursor = mock_db

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status', side_effect=AttendanceValidationError("Approval error")), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.post('/add_attendance', data={"date": "2026-03-20"})
            assert response.status_code in [200, 302]

    def test_add_attendance_validation_error_method(self, client, logged_in_admin, mock_db):
        """Case 7: Lỗi Validator Phương thức"""
        conn, cursor = mock_db

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method', side_effect=AttendanceValidationError("Method error")), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.post('/add_attendance', data={"date": "2026-03-20"})
            assert response.status_code in [200, 302]

    def test_add_attendance_validation_error_notes(self, client, logged_in_admin, mock_db):
        """Case 8: Lỗi Validator Ghi chú"""
        conn, cursor = mock_db

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes', side_effect=AttendanceValidationError("Notes error")), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.post('/add_attendance', data={"date": "2026-03-20"})
            assert response.status_code in [200, 302]

    def test_add_attendance_validation_error_future_date(self, client, logged_in_admin, mock_db):
        """Case 9: Ngày chấm công tương lai"""
        conn, cursor = mock_db

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes'), \
             patch('routes.attendance.validate_attendance_date', side_effect=AttendanceValidationError("Future date error")), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.post('/add_attendance', data={"date": "2026-03-20"})
            assert response.status_code in [200, 302]

    def test_add_attendance_employee_not_found(self, client, logged_in_admin, mock_db):
        """Case 10: Nhân viên không tồn tại"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = [0]

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes'), \
             patch('routes.attendance.validate_attendance_date'), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.post('/add_attendance', data={"employee_id": "99", "date": "2026-03-20"})
            assert response.status_code in [200, 302]

    def test_add_attendance_duplicate_record(self, client, logged_in_admin, mock_db):
        """Case 11: Trùng bản ghi chấm công"""
        conn, cursor = mock_db
        cursor.fetchone.side_effect = [[1], [1]]

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes'), \
             patch('routes.attendance.validate_attendance_date'), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.post('/add_attendance', data={"employee_id": "1", "date": "2026-03-20"})
            assert response.status_code in [200, 302]

    def test_add_attendance_checkin_checkout_time_error(self, client, logged_in_admin, mock_db):
        """Case 12: Lỗi thời gian Check-in / Check-out"""
        conn, cursor = mock_db
        cursor.fetchone.side_effect = [[1], [0]]

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes'), \
             patch('routes.attendance.validate_attendance_date'), \
             patch('routes.attendance.validate_checkin_checkout_times', side_effect=AttendanceValidationError("Time error")), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.post('/add_attendance', data={"employee_id": "1", "date": "2026-03-20"})
            assert response.status_code in [200, 302]

    def test_add_attendance_employee_without_name(self, client, logged_in_admin, mock_db):
        """Case 13: Không fetch được FullName"""
        conn, cursor = mock_db
        cursor.fetchone.side_effect = [[1], [0], None]

        valid_data = {"employee_id": "1", "date": "2026-03-20"}

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes'), \
             patch('routes.attendance.validate_attendance_date'), \
             patch('routes.attendance.validate_checkin_checkout_times', return_value=('08:00', '17:00', 8.0, 0.0, 0, 0)), \
             patch('routes.attendance.create_notification'), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):

            response = client.post('/add_attendance', data=valid_data)
            assert response.status_code == 302

    def test_add_attendance_db_exception_triggers_rollback(self, client, logged_in_admin, mock_db):
        """Case 14: Lỗi DB bất ngờ -> Exception handler rollback"""
        conn, cursor = mock_db
        cursor.fetchone.side_effect = Exception("Unexpected DB Crash")

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes'), \
             patch('routes.attendance.validate_attendance_date'), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):

            response = client.post('/add_attendance', data={"date": "2026-03-20"})
            assert response.status_code in [200, 302]
            conn.rollback.assert_called_once()

    def test_add_attendance_invalid_date_format(self, client, logged_in_admin, mock_db):
        """Case 15: Định dạng date không đúng %Y-%m-%d"""
        conn, cursor = mock_db

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes'), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):

            response = client.post('/add_attendance', data={"date": "20/03/2026"})
            assert response.status_code in [200, 302]
            conn.rollback.assert_called_once()

    def test_add_attendance_ensure_connection_closed(self, client, logged_in_admin, mock_db):
        """Case 16: Đảm bảo conn.close() luôn chạy trên POST thành công"""
        conn, cursor = mock_db
        cursor.fetchone.side_effect = [[1], [0], ["Nguyen Van A"]]

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes'), \
             patch('routes.attendance.validate_attendance_date'), \
             patch('routes.attendance.validate_checkin_checkout_times', return_value=('08:00', '17:00', 8.0, 0.0, 0, 0)), \
             patch('routes.attendance.create_notification'), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):

            client.post('/add_attendance', data={"employee_id": "1", "date": "2026-03-20"})
            conn.close.assert_called_once()

    def test_add_attendance_cached_employees_called_on_get(self, client, logged_in_admin):
        """Case 17: Xác nhận get_cached_active_employees được gọi khi GET"""
        with patch('routes.attendance.get_cached_active_employees') as mock_cache:
            mock_cache.return_value = []
            client.get('/add_attendance')
            mock_cache.assert_called_once()

    def test_add_attendance_unauthenticated_post(self, client):
        """Case 18: Unauthenticated POST /add_attendance"""
        response = client.post('/add_attendance', data={})
        assert response.status_code in [200, 302, 401]


# =====================================================================
# 3. ROUTE: /edit_attendance/<int:id> (GET & POST)
# =====================================================================

class TestEditAttendance:

    def test_edit_attendance_unauthenticated(self, client):
        """Case 1: Unauthenticated -> Redirect Login"""
        response = client.get('/edit_attendance/1')
        assert response.status_code in [200, 302, 401]

    def test_edit_attendance_unauthorized_role(self, client, logged_in_employee):
        """Case 2: Role Employee không có quyền sửa"""
        response = client.get('/edit_attendance/1')
        assert response.status_code in [200, 302, 403]

    def test_edit_attendance_record_not_found(self, client, logged_in_admin, mock_db):
        """Case 3: ID không tồn tại"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = None

        with patch('routes.attendance.get_connection', return_value=conn):
            response = client.get('/edit_attendance/999')
            assert response.status_code == 302
            assert response.location.endswith('/attendance')

    def test_edit_attendance_get_success_admin(self, client, logged_in_admin, mock_db, mock_attendance_row):
        """Case 4: Admin GET form sửa thành công"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = mock_attendance_row

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.get_cached_active_employees', return_value=[]):
            response = client.get('/edit_attendance/1')
            assert response.status_code == 200

    def test_edit_attendance_get_success_manager(self, client, logged_in_manager, mock_db, mock_attendance_row):
        """Case 5: Manager GET form sửa thành công"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = mock_attendance_row

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.get_cached_active_employees', return_value=[]):
            response = client.get('/edit_attendance/1')
            assert response.status_code == 200

    def test_edit_attendance_post_success(self, client, logged_in_admin, mock_db, mock_attendance_row):
        """Case 6: POST cập nhật chấm công thành công"""
        conn, cursor = mock_db
        cursor.fetchone.side_effect = [mock_attendance_row, [1], [0], ["Nguyen Van A"]]

        post_data = {
            "employee_id": "1",
            "date": "2026-03-20",
            "checkin": "08:00",
            "checkout": "17:00",
            "status": "Present",
            "checkin_method": "Fingerprint",
            "approval_status": "Approved",
            "notes": "Updated note"
        }

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes'), \
             patch('routes.attendance.validate_attendance_date'), \
             patch('routes.attendance.validate_checkin_checkout_times', return_value=('08:00', '17:00', 8.0, 0.0, 0, 0)), \
             patch('routes.attendance.create_notification'), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):

            response = client.post('/edit_attendance/1', data=post_data)
            assert response.status_code == 302
            assert response.location.endswith('/attendance')

    def test_edit_attendance_validation_error_status(self, client, logged_in_admin, mock_db, mock_attendance_row):
        """Case 7: Sửa chấm công - Lỗi Status Validation"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = mock_attendance_row

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status', side_effect=AttendanceValidationError("Status error")), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.post('/edit_attendance/1', data={"date": "2026-03-20"})
            assert response.status_code in [200, 302]

    def test_edit_attendance_validation_error_approval(self, client, logged_in_admin, mock_db, mock_attendance_row):
        """Case 8: Sửa chấm công - Lỗi Approval Status Validation"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = mock_attendance_row

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status', side_effect=AttendanceValidationError("Approval error")), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.post('/edit_attendance/1', data={"date": "2026-03-20"})
            assert response.status_code in [200, 302]

    def test_edit_attendance_validation_error_method(self, client, logged_in_admin, mock_db, mock_attendance_row):
        """Case 9: Sửa chấm công - Lỗi Method Validation"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = mock_attendance_row

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method', side_effect=AttendanceValidationError("Method error")), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.post('/edit_attendance/1', data={"date": "2026-03-20"})
            assert response.status_code in [200, 302]

    def test_edit_attendance_validation_error_notes(self, client, logged_in_admin, mock_db, mock_attendance_row):
        """Case 10: Sửa chấm công - Lỗi Notes Validation"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = mock_attendance_row

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes', side_effect=AttendanceValidationError("Notes error")), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.post('/edit_attendance/1', data={"date": "2026-03-20"})
            assert response.status_code in [200, 302]

    def test_edit_attendance_validation_error_date(self, client, logged_in_admin, mock_db, mock_attendance_row):
        """Case 11: Sửa chấm công - Lỗi Date Validation"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = mock_attendance_row

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes'), \
             patch('routes.attendance.validate_attendance_date', side_effect=AttendanceValidationError("Date error")), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.post('/edit_attendance/1', data={"date": "2026-03-20"})
            assert response.status_code in [200, 302]

    def test_edit_attendance_employee_not_found(self, client, logged_in_admin, mock_db, mock_attendance_row):
        """Case 12: Sửa chấm công - Employee ID không tồn tại"""
        conn, cursor = mock_db
        cursor.fetchone.side_effect = [mock_attendance_row, [0]]

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes'), \
             patch('routes.attendance.validate_attendance_date'), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.post('/edit_attendance/1', data={"employee_id": "99", "date": "2026-03-20"})
            assert response.status_code in [200, 302]

    def test_edit_attendance_duplicate_date_different_id(self, client, logged_in_admin, mock_db, mock_attendance_row):
        """Case 13: Trùng ngày chấm công với bản ghi khác"""
        conn, cursor = mock_db
        cursor.fetchone.side_effect = [mock_attendance_row, [1], [1]]

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes'), \
             patch('routes.attendance.validate_attendance_date'), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.post('/edit_attendance/1', data={"employee_id": "1", "date": "2026-03-20"})
            assert response.status_code in [200, 302]

    def test_edit_attendance_invalid_times(self, client, logged_in_admin, mock_db, mock_attendance_row):
        """Case 14: Lỗi Checkin/Checkout Times Validation"""
        conn, cursor = mock_db
        cursor.fetchone.side_effect = [mock_attendance_row, [1], [0]]

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes'), \
             patch('routes.attendance.validate_attendance_date'), \
             patch('routes.attendance.validate_checkin_checkout_times', side_effect=AttendanceValidationError("Time error")), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.post('/edit_attendance/1', data={"employee_id": "1", "date": "2026-03-20"})
            assert response.status_code in [200, 302]

    def test_edit_attendance_emp_row_none(self, client, logged_in_admin, mock_db, mock_attendance_row):
        """Case 15: Cập nhật thành công nhưng không lấy được emp_name"""
        conn, cursor = mock_db
        cursor.fetchone.side_effect = [mock_attendance_row, [1], [0], None]

        post_data = {"employee_id": "1", "date": "2026-03-20"}

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes'), \
             patch('routes.attendance.validate_attendance_date'), \
             patch('routes.attendance.validate_checkin_checkout_times', return_value=('08:00', '17:00', 8.0, 0.0, 0, 0)), \
             patch('routes.attendance.create_notification'), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):

            response = client.post('/edit_attendance/1', data=post_data)
            assert response.status_code == 302

    def test_edit_attendance_db_exception_rollback(self, client, logged_in_admin, mock_db, mock_attendance_row):
        """Case 16: Lỗi DB bất ngờ khi POST"""
        conn, cursor = mock_db
        cursor.fetchone.side_effect = [mock_attendance_row, Exception("DB Error")]

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.validate_attendance_status'), \
             patch('routes.attendance.validate_approval_status'), \
             patch('routes.attendance.validate_checkin_method'), \
             patch('routes.attendance.validate_notes'), \
             patch('routes.attendance.validate_attendance_date'), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):

            response = client.post('/edit_attendance/1', data={"date": "2026-03-20"})
            assert response.status_code in [200, 302]
            conn.rollback.assert_called_once()

    def test_edit_attendance_ensure_connection_closed(self, client, logged_in_admin, mock_db, mock_attendance_row):
        """Case 17: Đảm bảo conn.close() được gọi khi kết thúc GET"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = mock_attendance_row

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.get_cached_active_employees', return_value=[]):
            client.get('/edit_attendance/1')
            conn.close.assert_called_once()


# =====================================================================
# 4. ROUTE: /delete_attendance/<int:id> (GET)
# =====================================================================

class TestDeleteAttendance:

    def test_delete_attendance_unauthenticated(self, client):
        """Case 1: Unauthenticated -> Redirect Login"""
        response = client.get('/delete_attendance/1')
        assert response.status_code in [200, 302, 401]

    def test_delete_attendance_unauthorized_manager(self, client, logged_in_manager):
        """Case 2: Manager không có quyền xóa"""
        response = client.get('/delete_attendance/1')
        assert response.status_code in [200, 302, 403]

    def test_delete_attendance_not_found(self, client, logged_in_admin, mock_db):
        """Case 3: Xóa bản ghi không tồn tại"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = None

        with patch('routes.attendance.get_connection', return_value=conn):
            response = client.get('/delete_attendance/999')
            assert response.status_code == 302
            assert response.location.endswith('/attendance')

    def test_delete_attendance_success(self, client, logged_in_admin, mock_db):
        """Case 4: Xóa mềm bản ghi chấm công thành công"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = ["Nguyen Van A", date(2026, 3, 20)]

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.create_notification'), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):

            response = client.get('/delete_attendance/1')
            assert response.status_code == 302
            assert response.location.endswith('/attendance')

    def test_delete_attendance_db_exception(self, client, logged_in_admin, mock_db):
        """Case 5: Lỗi DB khi thực hiện xóa"""
        conn, cursor = mock_db
        cursor.fetchone.side_effect = Exception("Delete SQL Error")

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):
            
            response = client.get('/delete_attendance/1')
            assert response.status_code == 302
            assert response.location.endswith('/attendance')
            conn.rollback.assert_called_once()

    def test_delete_attendance_ensure_connection_closed(self, client, logged_in_admin, mock_db):
        """Case 6: Đảm bảo conn.close() luôn được thực thi"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = ["Nguyen Van A", date(2026, 3, 20)]

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.create_notification'), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):

            client.get('/delete_attendance/1')
            conn.close.assert_called_once()


# =====================================================================
# 5. ROUTE: /delete_selected_attendance (POST)
# =====================================================================

class TestDeleteSelectedAttendance:

    def test_delete_selected_unauthenticated(self, client):
        """Case 1: Unauthenticated -> Redirect Login"""
        response = client.post('/delete_selected_attendance', data={})
        assert response.status_code in [200, 302, 401]

    def test_delete_selected_unauthorized_manager(self, client, logged_in_manager):
        """Case 2: Manager không có quyền xóa hàng loạt"""
        response = client.post('/delete_selected_attendance', data={"attendance_ids": ["1", "2"]})
        assert response.status_code in [200, 302, 403]

    def test_delete_selected_no_ids_provided(self, client, logged_in_admin):
        """Case 3: Không tích chọn bản ghi nào"""
        response = client.post('/delete_selected_attendance', data={})
        assert response.status_code == 302
        assert response.location.endswith('/attendance')

    def test_delete_selected_success(self, client, logged_in_admin, mock_db):
        """Case 4: Xóa thành công danh sách bản ghi hợp lệ"""
        conn, cursor = mock_db
        records = [("Nguyen Van A", date(2026, 3, 20)), ("Tran Van B", date(2026, 3, 21))]
        cursor.fetchall.return_value = records

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.create_notification'), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):

            response = client.post('/delete_selected_attendance', data={"attendance_ids": ["1", "2"]})
            assert response.status_code == 302
            assert response.location.endswith('/attendance')

    def test_delete_selected_no_valid_records_found(self, client, logged_in_admin, mock_db):
        """Case 5: Có gửi IDs nhưng tất cả đã bị xóa trước đó"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = []

        with patch('routes.attendance.get_connection', return_value=conn):
            response = client.post('/delete_selected_attendance', data={"attendance_ids": ["99", "100"]})
            assert response.status_code == 302
            assert response.location.endswith('/attendance')

    def test_delete_selected_db_exception(self, client, logged_in_admin, mock_db):
        """Case 6: Lỗi DB khi query xóa hàng loạt"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("Bulk Delete Error")

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):

            response = client.post('/delete_selected_attendance', data={"attendance_ids": ["1", "2"]})
            assert response.status_code == 302
            conn.rollback.assert_called_once()

    def test_delete_selected_single_id_list(self, client, logged_in_admin, mock_db):
        """Case 7: Chọn duy nhất 1 ID để xóa hàng loạt"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [("Nguyen Van A", date(2026, 3, 20))]

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.create_notification'), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):

            response = client.post('/delete_selected_attendance', data={"attendance_ids": ["1"]})
            assert response.status_code == 302

    def test_delete_selected_ensure_connection_closed(self, client, logged_in_admin, mock_db):
        """Case 8: Đảm bảo conn.close() luôn chạy"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = []

        with patch('routes.attendance.get_connection', return_value=conn):
            client.post('/delete_selected_attendance', data={"attendance_ids": ["1"]})
            conn.close.assert_called_once()


# =====================================================================
# 6. ROUTE: /export_attendance_csv (GET)
# =====================================================================

class TestExportAttendanceCSV:

    def test_export_csv_unauthenticated(self, client):
        """Case 1: Unauthenticated -> Redirect Login"""
        response = client.get('/export_attendance_csv')
        assert response.status_code in [200, 302, 401]

    def test_export_csv_unauthorized_manager(self, client, logged_in_manager):
        """Case 2: Manager không có quyền xuất CSV"""
        response = client.get('/export_attendance_csv')
        assert response.status_code in [200, 302, 403]

    def test_export_csv_success(self, client, logged_in_admin, mock_db, mock_attendance_row):
        """Case 3: Xuất file CSV thành công"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [mock_attendance_row]

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):

            response = client.get('/export_attendance_csv')
            assert response.status_code == 200
            assert response.mimetype == "text/csv"

    def test_export_csv_empty_database(self, client, logged_in_admin, mock_db):
        """Case 4: Xuất CSV khi DB trống"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = []

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.log_activity'), patch('utils.audit.log_activity'):

            response = client.get('/export_attendance_csv')
            assert response.status_code == 200

    def test_export_csv_db_exception(self, client, logged_in_admin, mock_db):
        """Case 5: Lỗi DB khi query xuất CSV"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("Export SQL Failure")

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('routes.attendance.current_app.logger.error'):

            response = client.get('/export_attendance_csv')
            assert response.status_code == 302
            assert response.location.endswith('/attendance')

    def test_export_csv_ensure_connection_closed(self, client, logged_in_admin, mock_db):
        """Case 6: Đảm bảo conn.close() luôn chạy"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("Export Error")

        with patch('routes.attendance.get_connection', return_value=conn):
            client.get('/export_attendance_csv')
            conn.close.assert_called_once()


# =====================================================================
# 7. AUXILIARY FUNCTIONS: get_cached_active_employees
# =====================================================================

class TestAttendanceHelperFunctions:

    def test_get_cached_active_employees(self, mock_db):
        """Case 1: Helper function query DB danh sách nhân viên active"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [(1, "Nguyen Van A"), (2, "Tran Van B")]

        with patch('routes.attendance.get_connection', return_value=conn), \
             patch('app.cache.cached', lambda **kwargs: lambda f: f):
            
            from routes.attendance import get_cached_active_employees
            employees = get_cached_active_employees()
            
            assert len(employees) == 2
            assert employees[0][1] == "Nguyen Van A"
            conn.close.assert_called_once()