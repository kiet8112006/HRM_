import pytest
from unittest.mock import patch, MagicMock

# Import hàm log_activity từ utils/audit.py (chỉnh đường dẫn import nếu cần)
from utils.audit import log_activity


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
# UNIT TESTS FOR log_activity
# =====================================================================

class TestLogActivity:

    def test_log_activity_success_with_session_and_request(self, app, mock_db):
        """
        Test ghi log thành công:
        - Lấy đúng UserID, Username, Role từ Session
        - Lấy đúng IPAddress, UserAgent từ Request
        - Gọi execute, commit và close kết nối DB
        """
        conn, cursor = mock_db

        with patch('utils.audit.get_connection', return_value=conn):
            # Tạo Request Context với session và headers giả lập
            with app.test_request_context('/some-route', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
                with app.test_client() as client:
                    with client.session_transaction() as sess:
                        sess['user_id'] = 10
                        sess['username'] = 'admin_user'
                        sess['role'] = 'Admin'

                    # Chạy hàm log_activity trong Request Context
                    log_activity(
                        module='Employee',
                        action='Create',
                        description='Tạo mới nhân viên Nguyễn Văn A',
                        record_id=101
                    )

                    # Kiểm tra DB Cursor có gọi lệnh INSERT với đúng tham số không
                    cursor.execute.assert_called_once()
                    args, _ = cursor.execute.call_args
                    query, params = args

                    assert "INSERT INTO AuditLogs" in query
                    assert params[0] == 10                 # user_id
                    assert params[1] == 'admin_user'       # username
                    assert params[2] == 'Admin'            # role
                    assert params[3] == 'Employee'         # module
                    assert params[4] == 'Create'           # action
                    assert params[5] == 101                # record_id
                    assert params[6] == 'Tạo mới nhân viên Nguyễn Văn A' # description
                    assert params[7] == '192.168.1.1'      # ip_address

                    # Kiểm tra commit và close DB
                    conn.commit.assert_called_once()
                    conn.close.assert_called_once()

    def test_log_activity_null_session_and_user_agent(self, app, mock_db):
        """
        Test trường hợp người dùng chưa đăng nhập (Session rỗng) và Request thiếu UserAgent
        """
        conn, cursor = mock_db

        with patch('utils.audit.get_connection', return_value=conn):
            with app.test_request_context('/guest-route'):
                log_activity(
                    module='Auth',
                    action='Failed Login',
                    description='Đăng nhập thất bại'
                )

                cursor.execute.assert_called_once()
                args, _ = cursor.execute.call_args
                _, params = args

                assert params[0] is None  # user_id
                assert params[1] is None  # username
                assert params[2] is None  # role
                assert params[5] is None  # record_id mặc định là None

                conn.commit.assert_called_once()
                conn.close.assert_called_once()

    def test_log_activity_database_exception_triggers_rollback(self, app, mock_db):
        """
        Test khi xảy ra lỗi DB:
        - Phải bắt được ngoại lệ
        - Gọi logger.error
        - Gọi conn.rollback()
        - Vẫn luôn đóng DB (conn.close())
        """
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("Database disk full")

        with patch('utils.audit.get_connection', return_value=conn), \
             patch('utils.audit.logger.error') as mock_logger:

            with app.test_request_context('/error-route'):
                # Gọi hàm, bảo đảm không bị văng Crash App do đã có try-except
                log_activity(
                    module='System',
                    action='ErrorTest',
                    description='Test exception handling'
                )

                # Kiểm tra logger.error có được ghi nhận
                mock_logger.assert_called_once()
                assert "Lỗi khi ghi AuditLog: Database disk full" in mock_logger.call_args[0][0]

                # Kiểm tra rollback và close được gọi trong exception/finally
                conn.rollback.assert_called_once()
                conn.close.assert_called_once()