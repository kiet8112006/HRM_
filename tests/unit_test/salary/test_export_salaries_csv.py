import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def logged_in_admin(client):
    """Giả lập session Admin."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'Admin'

@pytest.fixture
def logged_in_employee(client):
    """Giả lập session Employee."""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'Employee'

# Helper class giả lập DB row object có thuộc tính (row.SalaryID, row.FullName,...)
class MockSalaryRowObject:
    def __init__(self):
        self.SalaryID = 1
        self.SalaryCode = 'SAL0001'
        self.FullName = 'Nguyễn Văn A'
        self.BaseSalary = 10000000
        self.Bonus = 1000000
        self.Allowance = 500000
        self.OvertimePay = 0
        self.Deduction = 0
        self.Tax = 500000
        self.Insurance = 800000
        self.NetSalary = 10200000
        self.Month = 3
        self.Year = 2026
        self.PaymentDate = '2026-03-31'
        self.Status = 'Paid'

# =====================================================================
# 7 TEST CASES CHO ROUTE EXPORT SALARIES CSV
# =====================================================================

def test_export_csv_not_logged_in_redirects(client):
    """Case 1: Chưa đăng nhập -> Redirect về login."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)

    response = client.get('/export_salaries_csv')
    assert response.status_code in [302, 401]


def test_export_csv_unauthorized_role_redirects(client, logged_in_employee):
    """Case 2: Role không phải Admin -> Redirect."""
    response = client.get('/export_salaries_csv')
    assert response.status_code in [302, 403]


def test_export_csv_success_data(client, logged_in_admin, mock_db):
    """Case 3: Xuất file CSV thành công khi có dữ liệu."""
    mock_db.fetchall.return_value = [MockSalaryRowObject()]

    response = client.get('/export_salaries_csv')
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment; filename=salaries.csv" in response.headers.get("Content-Disposition", "")


def test_export_csv_empty_data_success(client, logged_in_admin, mock_db):
    """Case 4: Xuất file CSV thành công kể cả khi DB rỗng (chỉ có Header)."""
    mock_db.fetchall.return_value = []

    response = client.get('/export_salaries_csv')
    assert response.status_code == 200
    assert response.mimetype == "text/csv"


def test_export_csv_db_exception_handling(client, logged_in_admin, mock_db):
    """Case 5: Bắt ngoại lệ khi truy vấn DB gặp lỗi trong quá trình export."""
    mock_db.execute.side_effect = Exception("DB Export Error")

    response = client.get('/export_salaries_csv')
    assert response.status_code in [200, 302]


def test_export_csv_audit_log_called(client, logged_in_admin, mock_db):
    """Case 6: Đảm bảo log_activity được gọi khi xuất CSV thành công."""
    mock_db.fetchall.return_value = [MockSalaryRowObject()]

    with patch('routes.salary.log_activity') as mock_log:
        response = client.get('/export_salaries_csv')
        assert response.status_code == 200
        mock_log.assert_called_once()


def test_export_csv_utf8_bom_encoding(client, logged_in_admin, mock_db):
    """Case 7: Kiểm tra response data có chứa UTF-8 BOM (\ufeff) để đọc đúng tiếng Việt trong Excel."""
    mock_db.fetchall.return_value = [MockSalaryRowObject()]

    response = client.get('/export_salaries_csv')
    assert response.status_code == 200
    # UTF-8 BOM byte sequence
    assert response.data.startswith(b'\xef\xbb\xbf') or "\ufeff" in response.get_data(as_text=True)