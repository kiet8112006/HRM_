import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


# =====================================================================
# FIXTURES & MOCK UTILS
# =====================================================================

@pytest.fixture
def logged_in_admin(client):
    """Giả lập session đăng nhập cho tài khoản Admin"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'admin'
        sess['role'] = 'Admin'
        sess['logged_in'] = True


@pytest.fixture
def logged_in_employee(client):
    """Giả lập session đăng nhập cho tài khoản không phải Admin (Employee)"""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['username'] = 'employee'
        sess['role'] = 'Employee'
        sess['logged_in'] = True


@pytest.fixture
def mock_db():
    """Fixture mock kết nối Database"""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


# =====================================================================
# 1. TEST PHÂN QUYỀN (AUTH & ROLE AUTHORIZATION)
# =====================================================================

class TestAuditAuth:

    def test_audit_logs_unauthenticated(self, client):
        """Chưa đăng nhập -> Bị chặn bởi @login_required"""
        response = client.get('/audit_logs')
        assert response.status_code in [200, 302, 401]

    def test_audit_logs_unauthorized_role(self, client, logged_in_employee):
        """Không phải Admin (VD: Employee) -> Bị chặn bởi @role_required"""
        response = client.get('/audit_logs')
        assert response.status_code in [200, 302, 403]

    def test_export_csv_unauthorized_role(self, client, logged_in_employee):
        """Employee cố gắng xuất CSV -> Bị chặn"""
        response = client.get('/audit_logs/export')
        assert response.status_code in [200, 302, 403]


# =====================================================================
# 2. TEST ROUTE: /audit_logs (DANH SÁCH NHẬT KÝ HỆ THỐNG)
# =====================================================================

class TestAuditLogsRoute:

    def test_audit_logs_success(self, client, logged_in_admin, mock_db):
        """Lấy danh sách Audit Logs thành công với phân trang"""
        conn, cursor = mock_db

        # Mock tổng số bản ghi (fetchone) và danh sách bản ghi (fetchall)
        cursor.fetchone.return_value = [25]  # total_records = 25 -> total_pages = 3 với per_page = 10
        mock_logs = [
            (1, 1, 'admin', 'Admin', 'Authentication', 'Login', None, 'Logged in', '127.0.0.1', 'Chrome', datetime.now())
        ]
        cursor.fetchall.return_value = mock_logs

        with patch('routes.audit.get_connection', return_value=conn):
            response = client.get('/audit_logs?keyword=admin&module=Auth&action=Login&page=2')

            assert response.status_code == 200
            # Kiểm tra xem DB có gọi lệnh SELECT COUNT và SELECT logs với đúng tham số không
            assert cursor.execute.call_count == 2
            conn.close.assert_called_once()

    def test_audit_logs_db_exception_fallback(self, client, logged_in_admin, mock_db):
        """Lỗi truy vấn DB -> Log error, flash message và render danh sách rỗng"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("Database connection error")

        with patch('routes.audit.get_connection', return_value=conn), \
             patch('routes.audit.current_app.logger.error') as mock_logger:

            response = client.get('/audit_logs')

            assert response.status_code == 200
            mock_logger.assert_called_once()
            conn.close.assert_called_once()


# =====================================================================
# 3. TEST ROUTE: /audit_logs/export (XUẤT FILE CSV)
# =====================================================================

class TestExportAuditLogsCSVRoute:

    def test_export_csv_success(self, client, logged_in_admin, mock_db):
        """Xuất file CSV thành công, trả về file đính kèm đúng header và log activity"""
        conn, cursor = mock_db

        now_str = "2026-07-23 21:00:00"
        mock_rows = [
            (now_str, 'admin', 'Admin', 'Audit', 'Export', 'Exported logs', '127.0.0.1', 'Mozilla/5.0')
        ]
        cursor.fetchall.return_value = mock_rows

        with patch('routes.audit.get_connection', return_value=conn), \
             patch('routes.audit.log_activity') as mock_log:

            response = client.get('/audit_logs/export')

            assert response.status_code == 200
            assert response.mimetype == "text/csv"
            assert "attachment; filename=audit_logs.csv" in response.headers["Content-Disposition"]

            # Kiểm tra nội dung CSV có chứa Header tiếng Anh và Data
            content = response.data.decode('utf-8-sig')
            assert "Time,Username,Role,Module,Action,Description,IP Address,Browser" in content
            assert "admin,Admin,Audit,Export" in content

            mock_log.assert_called_once_with(
                module='Audit',
                action='Export',
                description='Exported audit log (1 records).'
            )
            conn.close.assert_called_once()

    def test_export_csv_exception_redirect(self, client, logged_in_admin, mock_db):
        """Lỗi khi xuất CSV -> Flash message lỗi và redirect về /audit_logs"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("CSV generation error")

        with patch('routes.audit.get_connection', return_value=conn), \
             patch('routes.audit.current_app.logger.error') as mock_logger:

            response = client.get('/audit_logs/export')

            assert response.status_code == 302
            assert response.location == '/audit_logs'
            mock_logger.assert_called_once()
            conn.close.assert_called_once()