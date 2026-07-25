import pytest
from unittest.mock import patch, MagicMock

# Import hàm create_notification (chỉnh lại đường dẫn import nếu cần)
from utils.notification_service import create_notification


# =====================================================================
# FIXTURES
# =====================================================================

@pytest.fixture
def mock_db():
    """Fixture mock kết nối Database"""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


# =====================================================================
# UNIT TESTS FOR create_notification
# =====================================================================

class TestCreateNotification:

    def test_create_notification_default_parameters(self, mock_db):
        """
        Test tạo thông báo với các tham số mặc định:
        - type mặc định là 'Info'
        - receiver_role, receiver_id, url mặc định là None
        """
        conn, cursor = mock_db

        with patch('utils.notification.get_connection', return_value=conn):
            create_notification(
                title="Thông báo mới",
                message="Nội dung thông báo hệ thống"
            )

            # Kiểm tra cursor.execute có được gọi 1 lần
            cursor.execute.assert_called_once()
            
            # Lấy câu lệnh SQL và các tham số truyền vào execute
            args, _ = cursor.execute.call_args
            query = args[0]
            params = args[1:]

            # Kiểm tra câu lệnh INSERT
            assert "INSERT INTO Notifications" in query
            
            # Kiểm tra giá trị các tham số truyền vào tuple SQL
            assert params == (
                "Thông báo mới",                  # Title
                "Nội dung thông báo hệ thống",     # Message
                "Info",                           # Type (default)
                None,                             # ReceiverRole (default)
                None,                             # ReceiverID (default)
                None                              # Url (default)
            )

            # Kiểm tra gọi commit và close kết nối
            conn.commit.assert_called_once()
            conn.close.assert_called_once()

    def test_create_notification_custom_parameters(self, mock_db):
        """
        Test tạo thông báo với đầy đủ tất cả các tham số tùy chỉnh
        """
        conn, cursor = mock_db

        with patch('utils.notification.get_connection', return_value=conn):
            create_notification(
                title="Duyệt đơn nghỉ phép",
                message="Đơn nghỉ phép của bạn đã được duyệt.",
                type="Success",
                receiver_role="Employee",
                receiver_id=105,
                url="/leave/my-requests"
            )

            cursor.execute.assert_called_once()
            args, _ = cursor.execute.call_args
            params = args[1:]

            assert params == (
                "Duyệt đơn nghỉ phép",
                "Đơn nghỉ phép của bạn đã được duyệt.",
                "Success",
                "Employee",
                105,
                "/leave/my-requests"
            )

            conn.commit.assert_called_once()
            conn.close.assert_called_once()