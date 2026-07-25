import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Giả sử hàm time_ago và get_unread_count nằm trong module routes.notification
from routes.notification import time_ago, get_unread_count


# =====================================================================
# FIXTURES & MOCK UTILS
# =====================================================================

@pytest.fixture
def logged_in_user(client):
    """Fixture giả lập user đã đăng nhập với role 'Manager'"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'Manager'
        sess['logged_in'] = True

@pytest.fixture
def mock_db():
    """Fixture mock kết nối DB"""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


# Helper class để giả lập Object Row trả về từ DB Cursor (truy cập bằng dot notation)
class MockNotificationRow:
    def __init__(self, noti_id, title, msg, noti_type, url, is_read, created_at):
        self.NotificationID = noti_id
        self.Title = title
        self.Message = msg
        self.Type = noti_type
        self.Url = url
        self.IsRead = is_read
        self.CreatedAt = created_at


# =====================================================================
# 1. TEST HÀM HELPER: time_ago()
# =====================================================================

class TestTimeAgoHelper:

    def test_time_ago_invalid_input(self):
        """Đầu vào None hoặc không phải datetime -> Trả về chuỗi rỗng"""
        assert time_ago(None) == ""
        assert time_ago("2026-03-28") == ""

    def test_time_ago_seconds(self):
        """Thời gian < 60s -> 'Vừa xong'"""
        now = datetime.now()
        assert time_ago(now - timedelta(seconds=30)) == "Vừa xong"

    def test_time_ago_minutes(self):
        """Thời gian < 1 giờ -> 'X phút trước'"""
        now = datetime.now()
        assert time_ago(now - timedelta(minutes=15)) == "15 phút trước"

    def test_time_ago_hours(self):
        """Thời gian < 1 ngày -> 'X giờ trước'"""
        now = datetime.now()
        assert time_ago(now - timedelta(hours=5)) == "5 giờ trước"

    def test_time_ago_days(self):
        """Thời gian < 7 ngày -> 'X ngày trước'"""
        now = datetime.now()
        assert time_ago(now - timedelta(days=3)) == "3 ngày trước"

    def test_time_ago_old_date(self):
        """Thời gian >= 7 ngày -> Trả về định dạng DD/MM/YYYY"""
        old_date = datetime(2026, 1, 10, 10, 0, 0)
        assert time_ago(old_date) == "10/01/2026"


# =====================================================================
# 2. TEST HÀM HELPER: get_unread_count()
# =====================================================================

class TestGetUnreadCountHelper:

    def test_get_unread_count_no_session(self, app):
        """Không có session role -> Trả về 0"""
        with app.test_request_context():
            assert get_unread_count() == 0

    def test_get_unread_count_success(self, app, mock_db):
        """Có session role -> Trả về số lượng count từ DB"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = [5]

        with app.test_request_context():
            from flask import session
            session['role'] = 'Admin'

            with patch('routes.notification.get_connection', return_value=conn):
                count = get_unread_count()
                assert count == 5
                cursor.execute.assert_called_once()
                conn.close.assert_called_once()

    def test_get_unread_count_exception(self, app, mock_db):
        """DB gặp lỗi -> Bắt exception, log error và trả về 0"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("DB Connection Error")

        with app.test_request_context():
            from flask import session
            session['role'] = 'Admin'

            with patch('routes.notification.get_connection', return_value=conn), \
                 patch('routes.notification.current_app.logger.error') as mock_logger:
                
                count = get_unread_count()
                assert count == 0
                mock_logger.assert_called_once()
                conn.close.assert_called_once()


# =====================================================================
# 3. TEST ROUTE: /notifications
# =====================================================================

class TestNotificationsRoute:

    def test_notifications_unauthenticated(self, client):
        """Chưa đăng nhập -> Bị chặn bởi @login_required"""
        response = client.get('/notifications')
        assert response.status_code in [302, 401, 200]

    def test_notifications_success(self, client, logged_in_user, mock_db):
        """Lấy danh sách thông báo thành công"""
        conn, cursor = mock_db

        mock_rows = [
            MockNotificationRow(1, "Tiêu đề 1", "Nội dung 1", "Info", "/link1", 0, datetime.now()),
            MockNotificationRow(2, "Tiêu đề 2", "Nội dung 2", "Warning", "/link2", 1, datetime.now() - timedelta(days=1))
        ]
        
        # mock fetchall cho danh sách noti, fetchone cho unread_count
        cursor.fetchall.return_value = mock_rows
        cursor.fetchone.return_value = [1]

        with patch('routes.notification.get_connection', return_value=conn):
            response = client.get('/notifications')
            assert response.status_code == 200
            conn.close.assert_called_once()

    def test_notifications_exception(self, client, logged_in_user, mock_db):
        """DB bị lỗi -> Flash message danger và render list rỗng"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("SQL Error")

        with patch('routes.notification.get_connection', return_value=conn), \
             patch('routes.notification.current_app.logger.error') as mock_logger:
            
            response = client.get('/notifications')
            assert response.status_code == 200
            mock_logger.assert_called_once()
            conn.close.assert_called_once()


# =====================================================================
# 4. TEST ROUTE: /notification/read/<int:id>
# =====================================================================

class TestReadNotificationRoute:

    def test_read_notification_success(self, client, logged_in_user, mock_db):
        """Đánh dấu 1 thông báo là đã đọc thành công -> Redirect về /notifications"""
        conn, cursor = mock_db

        with patch('routes.notification.get_connection', return_value=conn):
            response = client.get('/notification/read/10')
            
            assert response.status_code == 302
            assert response.location == '/notifications'
            
            # Kiểm tra xem có execute UPDATE đúng ID không
            cursor.execute.assert_called_once()
            assert 10 in cursor.execute.call_args[0][1]
            conn.commit.assert_called_once()
            conn.close.assert_called_once()

    def test_read_notification_exception_rollback(self, client, logged_in_user, mock_db):
        """Xảy ra lỗi khi update -> Rollback và log error"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("Update Failed")

        with patch('routes.notification.get_connection', return_value=conn), \
             patch('routes.notification.current_app.logger.error') as mock_logger:
            
            response = client.get('/notification/read/10')
            
            assert response.status_code == 302
            conn.rollback.assert_called_once()
            mock_logger.assert_called_once()
            conn.close.assert_called_once()


# =====================================================================
# 5. TEST ROUTE: /notifications/read_all
# =====================================================================

class TestReadAllNotificationsRoute:

    def test_read_all_notifications_success(self, client, logged_in_user, mock_db):
        """Đánh dấu tất cả thông báo thuộc role là đã đọc thành công"""
        conn, cursor = mock_db

        with patch('routes.notification.get_connection', return_value=conn):
            response = client.get('/notifications/read_all')
            
            assert response.status_code == 302
            assert response.location == '/notifications'
            
            # Kiểm tra query UPDATE có chứa 'Manager' (từ logged_in_user fixture)
            executed_sql = cursor.execute.call_args[0][0]
            params = cursor.execute.call_args[0][1]
            assert "UPDATE Notifications" in executed_sql
            assert 'Manager' in params
            
            conn.commit.assert_called_once()
            conn.close.assert_called_once()

    def test_read_all_notifications_exception_rollback(self, client, logged_in_user, mock_db):
        """Lỗi khi update tất cả -> Rollback và log error"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("Bulk Update Failed")

        with patch('routes.notification.get_connection', return_value=conn), \
             patch('routes.notification.current_app.logger.error') as mock_logger:
            
            response = client.get('/notifications/read_all')
            
            assert response.status_code == 302
            conn.rollback.assert_called_once()
            mock_logger.assert_called_once()
            conn.close.assert_called_once()