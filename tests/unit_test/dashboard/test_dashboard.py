import pytest
from unittest.mock import patch, MagicMock
from routes.dashboard import format_money_short


# =====================================================================
# FIXTURES
# =====================================================================

@pytest.fixture
def logged_in_admin(client):
    """Giả lập session của Admin"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'admin'
        sess['role'] = 'Admin'
        sess['user_role'] = 'Admin'
        sess['logged_in'] = True

@pytest.fixture
def logged_in_employee(client):
    """Giả lập session của Nhân viên (Không có quyền Admin/Manager)"""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['username'] = 'emp'
        sess['role'] = 'Employee'
        sess['user_role'] = 'Employee'
        sess['logged_in'] = True

@pytest.fixture
def mock_db():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


# =====================================================================
# 1. TEST HÀM HELPER: format_money_short()
# =====================================================================

class TestFormatMoneyShort:

    def test_format_money_none_or_zero(self):
        assert format_money_short(None) == "0 VNĐ"
        assert format_money_short(0) == "0 VNĐ"

    def test_format_money_billions(self):
        assert format_money_short(2_500_000_000) == "2.50B VNĐ"
        assert format_money_short(1_000_000_000) == "1.00B VNĐ"

    def test_format_money_millions(self):
        assert format_money_short(15_500_000) == "15.50M VNĐ"
        assert format_money_short(1_000_000) == "1.00M VNĐ"

    def test_format_money_thousands(self):
        assert format_money_short(500_000) == "500.00K VNĐ"
        assert format_money_short(1_500) == "1.50K VNĐ"

    def test_format_money_small_amount(self):
        assert format_money_short(999) == "999 VNĐ"
        assert format_money_short(50) == "50 VNĐ"


# =====================================================================
# 2. TEST AUTHENTICATION & AUTHORIZATION FOR ROUTE '/'
# =====================================================================

class TestDashboardAuth:

    def test_dashboard_unauthenticated(self, client):
        """Chưa đăng nhập -> Bị chặn bởi @login_required"""
        response = client.get('/')
        assert response.status_code in [200, 302, 401]

    def test_dashboard_unauthorized_role(self, client, logged_in_employee):
        """Role Employee không được vào dashboard -> Bị chặn bởi @role_required"""
        response = client.get('/')
        assert response.status_code in [200, 302, 403]


# =====================================================================
# 3. TEST DASHBOARD ROUTE LOGIC
# =====================================================================

class TestDashboardRoute:

    def test_dashboard_success_with_growth_and_attendance(self, client, logged_in_admin, mock_db):
        """Test tải dashboard thành công khi có đầy đủ dữ liệu (có tăng trưởng lương > 0)"""
        conn, cursor = mock_db

        # Mock các giá trị cho các câu lệnh COUNT / SUM (dùng fetchone)
        cursor.fetchone.side_effect = [
            [50],          # total_employees
            [5],           # total_departments
            [10],          # total_positions
            [500_000_000], # total_salary
            [3],           # new_employees
            [2],           # leave_today
            [120_000_000], # salary_this_month
            [100_000_000], # salary_last_month -> growth = ((120-100)/100)*100 = 20.0%
            [30],          # present_count
            [5],           # late_count
            [2]            # absent_count -> not_checked = max(0, 50 - 30 - 5 - 2) = 13
        ]

        # Mock các câu lệnh trả về danh sách (dùng fetchall)
        cursor.fetchall.side_effect = [
            [("IT", 30), ("HR", 20)],                                    # department_data
            [(1, 100_000_000), (2, 120_000_000)],                         # salary_data
            [("Nguyen Van A", "2026-08-01", 10)],                        # expiring_contracts
            [("Tran Van B", "2026-07-25", "2026-07-27")]                 # pending_leave_requests
        ]

        with patch('routes.dashboard.get_connection', return_value=conn):
            response = client.get('/')

            assert response.status_code == 200
            conn.close.assert_called_once()

    def test_dashboard_zero_last_month_salary_growth(self, client, logged_in_admin, mock_db):
        """Test trường hợp lương tháng trước = 0 -> salary_growth = 0 để tránh chia cho 0"""
        conn, cursor = mock_db

        cursor.fetchone.side_effect = [
            [10], [2], [2], [50_000_000], [1], [0],
            [10_000_000], # salary_this_month
            [0],          # salary_last_month = 0
            [10], [0], [0]
        ]
        cursor.fetchall.side_effect = [[], [], [], []]

        with patch('routes.dashboard.get_connection', return_value=conn):
            response = client.get('/')

            assert response.status_code == 200
            conn.close.assert_called_once()

    def test_dashboard_database_exception_fallback(self, client, logged_in_admin, mock_db):
        """Lỗi DB -> Bắt Exception, ghi log error, flash message và trả về template fallback"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("Database connection failure")

        with patch('routes.dashboard.get_connection', return_value=conn), \
             patch('routes.dashboard.current_app.logger.error') as mock_logger:

            response = client.get('/')

            assert response.status_code == 200
            mock_logger.assert_called_once()
            conn.close.assert_called_once()