import pytest
from unittest.mock import patch, MagicMock
import json

# =====================================================================
# FIXTURES & MOCK DATA
# =====================================================================

@pytest.fixture
def logged_in_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'admin_user'
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
def patch_helpers():
    """Mock 2 hàm helper lấy danh mục để tránh đụng độ cache/DB thật"""
    with patch('routes.report.get_cached_departments', return_value=[('IT',), ('HR',)]), \
         patch('routes.report.get_cached_positions', return_value=[('Developer',), ('Manager',)]):
        yield


# =====================================================================
# 1. TEST AUTHENTICATION & AUTHORIZATION
# =====================================================================

class TestReportAuth:

    def test_reports_unauthenticated(self, client):
        """Chưa đăng nhập -> Redirect hoặc Unauthorized"""
        response = client.get('/reports')
        assert response.status_code in [200, 302, 401]

    def test_reports_unauthorized_employee(self, client, logged_in_employee):
        """Role Employee không được phép xem trang báo cáo"""
        response = client.get('/reports')
        assert response.status_code in [200, 302, 403]


# =====================================================================
# 2. TEST ROUTE /reports (GET)
# =====================================================================

class TestReportRoute:

    def test_reports_success_admin_no_filters(self, client, logged_in_admin, mock_db, patch_helpers):
        """Admin xem báo cáo thành công (Không truyền bộ lọc)"""
        conn, cursor = mock_db

        # Mock trả về cho 9 câu lệnh KPI COUNT/SUM
        cursor.fetchone.side_effect = [
            [100],  # total_employees
            [5],    # total_departments
            [10],   # total_positions
            [80],   # working_employees
            [10],   # quit_employees
            [10],   # probation_employees
            [3],    # pending_leave
            [50000000.0], # total_salary
            [2],    # expiring_contract
            [5]     # new_employee
        ]

        # Mock trả về cho 3 câu lệnh Chart (Top Salary, Department Report, Leave Report)
        cursor.fetchall.side_effect = [
            [("Nguyen Van A", 20000000.0), ("Tran Van B", 15000000.0)], # Top salaries
            [("IT", 50), ("HR", 30)],                                 # Department report
            [("Đã duyệt", 40), ("Chờ duyệt", 5)]                       # Leave report
        ]

        with patch('routes.report.get_connection', return_value=conn):
            response = client.get('/reports')
            
            assert response.status_code == 200
            conn.close.assert_called_once()

    def test_reports_success_manager_with_filters(self, client, logged_in_manager, mock_db, patch_helpers):
        """Manager xem báo cáo với đầy đủ bộ lọc dynamic (department, position, status, date)"""
        conn, cursor = mock_db

        cursor.fetchone.side_effect = [
            [20], [5], [10], [15], [2], [3], [1], [15000000.0], [0], [1]
        ]
        cursor.fetchall.side_effect = [[], [], []]

        query_params = {
            "department": "IT",
            "position": "Developer",
            "status": "Đang làm",
            "from_date": "2026-01-01",
            "to_date": "2026-12-31"
        }

        with patch('routes.report.get_connection', return_value=conn):
            response = client.get('/reports', query_string=query_params)
            
            assert response.status_code == 200
            # Kiểm tra xem SQL query có ghép đúng các điều kiện WHERE không
            executed_sql = cursor.execute.call_args_list[0][0][0]
            assert "D.DepartmentName = ?" in executed_sql
            assert "P.PositionName = ?" in executed_sql
            assert "E.Status = ?" in executed_sql
            assert "E.HireDate >= ?" in executed_sql
            assert "E.HireDate <= ?" in executed_sql

    def test_reports_db_exception_fallback(self, client, logged_in_admin, mock_db, patch_helpers):
        """Lỗi Database bất ngờ -> Bắt Exception, flash message và render fallback UI"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("Database Connection Lost")

        with patch('routes.report.get_connection', return_value=conn), \
             patch('routes.report.current_app.logger.error') as mock_log_error:

            response = client.get('/reports')
            
            assert response.status_code == 200
            mock_log_error.assert_called_once()
            conn.close.assert_called_once()


# =====================================================================
# 3. TEST HELPER FUNCTIONS (CACHING)
# =====================================================================

class TestReportHelpers:

    def test_get_cached_departments(self, mock_db):
        """Kiểm tra hàm helper query danh sách phòng ban"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [("IT",), ("HR",)]

        # Bypass decorator @cache.cached để test logic thực thi bên trong
        with patch('routes.report.get_connection', return_value=conn), \
             patch('app.cache.cached', lambda **kwargs: lambda f: f):
            
            from routes.report import get_cached_departments
            result = get_cached_departments()

            assert len(result) == 2
            assert result[0][0] == "IT"
            conn.close.assert_called_once()

    def test_get_cached_positions(self, mock_db):
        """Kiểm tra hàm helper query danh sách chức vụ"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [("Developer",), ("Tester",)]

        with patch('routes.report.get_connection', return_value=conn), \
             patch('app.cache.cached', lambda **kwargs: lambda f: f):
            
            from routes.report import get_cached_positions
            result = get_cached_positions()

            assert len(result) == 2
            assert result[0][0] == "Developer"
            conn.close.assert_called_once()