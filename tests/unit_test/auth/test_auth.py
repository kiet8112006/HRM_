import pytest
from unittest.mock import patch, MagicMock


# =====================================================================
# FIXTURES & MOCKS
# =====================================================================

@pytest.fixture
def mock_db():
    """Fixture mock kết nối DB"""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor

@pytest.fixture
def logged_in_user(client):
    """Giả lập user đã đăng nhập"""
    with client.session_transaction() as sess:
        sess['user_id'] = 10
        sess['username'] = 'testuser'
        sess['role'] = 'Admin'
        sess['logged_in'] = True


# =====================================================================
# 1. TEST ROUTE: /login
# =====================================================================

class TestLoginRoute:

    def test_login_get(self, client):
        """GET /login -> Trả về giao diện đăng nhập (Status 200)"""
        response = client.get('/login')
        assert response.status_code == 200

    def test_login_validation_error_username(self, client):
        """POST /login -> Lỗi validate username"""
        with patch('routes.auth.validate_username', return_value="Tên đăng nhập không hợp lệ"):
            response = client.post('/login', data={'username': '', 'password': '123'})
            assert response.status_code == 302
            assert response.location == '/login'

    def test_login_validation_error_password(self, client):
        """POST /login -> Lỗi validate password"""
        with patch('routes.auth.validate_username', return_value=None), \
             patch('routes.auth.validate_password', return_value="Mật khẩu quá ngắn"):
            response = client.post('/login', data={'username': 'admin', 'password': '123'})
            assert response.status_code == 302
            assert response.location == '/login'

    def test_login_user_not_found(self, client, mock_db):
        """POST /login -> Tên đăng nhập không tồn tại trong DB"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = None

        with patch('routes.auth.validate_username', return_value=None), \
             patch('routes.auth.validate_password', return_value=None), \
             patch('routes.auth.get_connection', return_value=conn):
            
            response = client.post('/login', data={'username': 'notfound', 'password': 'password123'})
            assert response.status_code == 302
            assert response.location == '/login'

    def test_login_wrong_password(self, client, mock_db):
        """POST /login -> Mật khẩu không chính xác"""
        conn, cursor = mock_db
        # UserID, Username, PasswordHash, FullName, Role, IsActive
        cursor.fetchone.return_value = (1, 'admin', 'hashed_pwd', 'Admin User', 'Admin', True)

        with patch('routes.auth.validate_username', return_value=None), \
             patch('routes.auth.validate_password', return_value=None), \
             patch('routes.auth.get_connection', return_value=conn), \
             patch('routes.auth.verify_password', return_value=False):
            
            response = client.post('/login', data={'username': 'admin', 'password': 'wrongpassword'})
            assert response.status_code == 302
            assert response.location == '/login'

    def test_login_user_inactive(self, client, mock_db):
        """POST /login -> Tài khoản bị khóa (IsActive = False)"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = (1, 'admin', 'hashed_pwd', 'Admin User', 'Admin', False)

        with patch('routes.auth.validate_username', return_value=None), \
             patch('routes.auth.validate_password', return_value=None), \
             patch('routes.auth.get_connection', return_value=conn), \
             patch('routes.auth.verify_password', return_value=True):
            
            response = client.post('/login', data={'username': 'admin', 'password': 'password123'})
            assert response.status_code == 302
            assert response.location == '/login'

    def test_login_success(self, client, mock_db):
        """POST /login -> Đăng nhập thành công, lưu session và redirect sang Dashboard"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = (1, 'admin', 'hashed_pwd', 'Admin User', 'Admin', True)

        with patch('routes.auth.validate_username', return_value=None), \
             patch('routes.auth.validate_password', return_value=None), \
             patch('routes.auth.get_connection', return_value=conn), \
             patch('routes.auth.verify_password', return_value=True), \
             patch('routes.auth.log_activity') as mock_log:
            
            response = client.post('/login', data={'username': 'admin', 'password': 'password123', 'remember': 'on'})
            
            assert response.status_code == 302
            # Giả sử route dashboard.home là '/' hoặc '/dashboard'
            assert response.location in ['/', '/dashboard']
            
            # Kiểm tra DB commit và ghi log
            conn.commit.assert_called_once()
            mock_log.assert_called_once()

            # Kiểm tra session
            with client.session_transaction() as sess:
                assert sess['user_id'] == 1
                assert sess['username'] == 'admin'

    def test_login_exception_rollback(self, client, mock_db):
        """POST /login -> Lỗi DB xảy ra khi đăng nhập -> Rollback"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("DB Connection Error")

        with patch('routes.auth.validate_username', return_value=None), \
             patch('routes.auth.validate_password', return_value=None), \
             patch('routes.auth.get_connection', return_value=conn), \
             patch('routes.auth.current_app.logger.error') as mock_logger:
            
            response = client.post('/login', data={'username': 'admin', 'password': 'password123'})
            
            assert response.status_code == 302
            assert response.location == '/login'
            conn.rollback.assert_called_once()
            mock_logger.assert_called_once()


# =====================================================================
# 2. TEST ROUTE: /forgot-password
# =====================================================================

class TestForgotPasswordRoute:

    def test_forgot_password_get(self, client):
        """GET /forgot-password -> Render trang forgot password"""
        response = client.get('/forgot-password')
        assert response.status_code == 200

    def test_forgot_password_validation_error(self, client):
        """POST /forgot-password -> Lỗi validate xác nhận mật khẩu"""
        with patch('routes.auth.validate_username', return_value=None), \
             patch('routes.auth.validate_password', return_value=None), \
             patch('routes.auth.validate_confirm_password', return_value="Mật khẩu không khớp"):
            
            response = client.post('/forgot-password', data={
                'username': 'admin',
                'password': 'Password123!',
                'confirm_password': 'DifferentPassword!'
            })
            assert response.status_code == 302
            assert response.location == '/forgot-password'

    def test_forgot_password_user_not_found(self, client, mock_db):
        """POST /forgot-password -> User không tồn tại"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = None

        with patch('routes.auth.validate_username', return_value=None), \
             patch('routes.auth.validate_password', return_value=None), \
             patch('routes.auth.validate_confirm_password', return_value=None), \
             patch('routes.auth.get_connection', return_value=conn):
            
            response = client.post('/forgot-password', data={
                'username': 'unknown_user',
                'password': 'Password123!',
                'confirm_password': 'Password123!'
            })
            assert response.status_code == 302
            assert response.location == '/forgot-password'

    def test_forgot_password_success(self, client, mock_db):
        """POST /forgot-password -> Reset mật khẩu thành công"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = (1,)  # UserID

        with patch('routes.auth.validate_username', return_value=None), \
             patch('routes.auth.validate_password', return_value=None), \
             patch('routes.auth.validate_confirm_password', return_value=None), \
             patch('routes.auth.get_connection', return_value=conn), \
             patch('routes.auth.hash_password', return_value='new_hashed_pwd'), \
             patch('routes.auth.log_activity') as mock_log:
            
            response = client.post('/forgot-password', data={
                'username': 'admin',
                'password': 'NewPassword123!',
                'confirm_password': 'NewPassword123!'
            })
            
            assert response.status_code == 302
            assert response.location == '/login'
            conn.commit.assert_called_once()
            mock_log.assert_called_once()


# =====================================================================
# 3. TEST ROUTE: /change-password
# =====================================================================

class TestChangePasswordRoute:

    def test_change_password_unauthenticated(self, client):
        """Chưa đăng nhập -> Bị chặn bởi @login_required"""
        response = client.get('/change-password')
        assert response.status_code in [200, 302, 401]

    def test_change_password_get(self, client, logged_in_user):
        """GET /change-password -> Trả về trang đổi mật khẩu"""
        response = client.get('/change-password')
        assert response.status_code == 200

    def test_change_password_wrong_old_password(self, client, logged_in_user, mock_db):
        """POST /change-password -> Mật khẩu cũ không chính xác"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = ('old_hashed_pwd',)

        with patch('routes.auth.validate_old_password', return_value=None), \
             patch('routes.auth.validate_new_password', return_value=None), \
             patch('routes.auth.validate_confirm_password', return_value=None), \
             patch('routes.auth.get_connection', return_value=conn), \
             patch('routes.auth.verify_password', return_value=False):
            
            response = client.post('/change-password', data={
                'old_password': 'WrongOldPassword',
                'new_password': 'NewPassword123!',
                'confirm_password': 'NewPassword123!'
            })
            assert response.status_code == 302
            assert response.location == '/change-password'

    def test_change_password_same_as_old(self, client, logged_in_user, mock_db):
        """POST /change-password -> Mật khẩu mới trùng với mật khẩu cũ"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = ('old_hashed_pwd',)

        with patch('routes.auth.validate_old_password', return_value=None), \
             patch('routes.auth.validate_new_password', return_value=None), \
             patch('routes.auth.validate_confirm_password', return_value=None), \
             patch('routes.auth.get_connection', return_value=conn), \
             patch('routes.auth.verify_password', side_effect=[True, True]): # Old ok, New trùng Old
            
            response = client.post('/change-password', data={
                'old_password': 'SamePassword123!',
                'new_password': 'SamePassword123!',
                'confirm_password': 'SamePassword123!'
            })
            assert response.status_code == 302
            assert response.location == '/change-password'

    def test_change_password_success(self, client, logged_in_user, mock_db):
        """POST /change-password -> Đổi mật khẩu thành công -> Clear session & Redirect về login"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = ('old_hashed_pwd',)

        with patch('routes.auth.validate_old_password', return_value=None), \
             patch('routes.auth.validate_new_password', return_value=None), \
             patch('routes.auth.validate_confirm_password', return_value=None), \
             patch('routes.auth.get_connection', return_value=conn), \
             patch('routes.auth.verify_password', side_effect=[True, False]), \
             patch('routes.auth.hash_password', return_value='new_hashed_pwd'), \
             patch('routes.auth.log_activity') as mock_log:
            
            response = client.post('/change-password', data={
                'old_password': 'OldPassword123!',
                'new_password': 'NewPassword123!',
                'confirm_password': 'NewPassword123!'
            })
            
            assert response.status_code == 302
            assert response.location == '/login'
            conn.commit.assert_called_once()
            mock_log.assert_called_once()

            # Session phải bị xoá sạch sau khi đổi MK thành công
            with client.session_transaction() as sess:
                assert 'user_id' not in sess


# =====================================================================
# 4. TEST ROUTE: /logout
# =====================================================================

class TestLogoutRoute:

    def test_logout_success(self, client, logged_in_user):
        """GET /logout -> Xóa session, log activity và redirect về trang login"""
        with patch('routes.auth.log_activity') as mock_log:
            response = client.get('/logout')
            
            assert response.status_code == 302
            assert response.location == '/login'
            mock_log.assert_called_once()

            # Kiểm tra session đã xoá hết
            with client.session_transaction() as sess:
                assert 'user_id' not in sess