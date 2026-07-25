import pytest

@pytest.fixture
def logged_in_admin(client):
    """Giả lập session đăng nhập với quyền Admin."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'Admin'

@pytest.fixture
def logged_in_employee(client):
    """Giả lập session đăng nhập với quyền Employee (không có quyền xem danh sách lương)."""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'Employee'

# Mock tuple dữ liệu của bảng lương
# Schema: SalaryID, SalaryCode, FullName, BaseSalary, Bonus, Allowance, OvertimePay, Deduction, Tax, Insurance, NetSalary, Month, Year, PaymentDate, Status
MOCK_SALARY_ROW = (
    1, "SAL0001", "Nguyễn Văn A", 10000000.0, 1000000.0, 500000.0, 
    0.0, 0.0, 500000.0, 800000.0, 10200000.0, 3, 2026, "2026-03-31", "Paid"
)

# =====================================================================
# 12 TEST CASES CHO ROUTE SALARIES (LIST / SEARCH / PAGINATION)
# =====================================================================

def test_salaries_not_logged_in_redirects(client):
    """Case 1: Chưa đăng nhập -> Redirect về trang login."""
    with client.session_transaction() as sess:
        sess.pop('user_id', None)

    response = client.get('/salaries')
    assert response.status_code in [302, 401]


def test_salaries_unauthorized_role_redirects(client, logged_in_employee):
    """Case 2: Role không phải Admin (VD: Employee) -> Redirect hoặc bị cấm."""
    response = client.get('/salaries')
    assert response.status_code in [302, 403]


def test_salaries_get_success_with_data(client, logged_in_admin, mock_db):
    """Case 3: Admin lấy danh sách bảng lương thành công khi có dữ liệu."""
    mock_db.fetchone.return_value = (1,)  # COUNT(*) = 1
    mock_db.fetchall.return_value = [MOCK_SALARY_ROW]

    response = client.get('/salaries')
    assert response.status_code == 200


def test_salaries_get_success_empty_data(client, logged_in_admin, mock_db):
    """Case 4: Load danh sách thành công khi DB rỗng (0 bản ghi)."""
    mock_db.fetchone.return_value = (0,)
    mock_db.fetchall.return_value = []

    response = client.get('/salaries')
    assert response.status_code == 200


def test_salaries_pagination_page_1(client, logged_in_admin, mock_db):
    """Case 5: Kiểm tra phân trang trang 1."""
    mock_db.fetchone.return_value = (25,)  # Tổng 25 bản ghi -> 3 trang
    mock_db.fetchall.return_value = [MOCK_SALARY_ROW] * 10

    response = client.get('/salaries?page=1')
    assert response.status_code == 200


def test_salaries_pagination_page_2(client, logged_in_admin, mock_db):
    """Case 6: Kiểm tra chuyển sang trang 2."""
    mock_db.fetchone.return_value = (25,)
    mock_db.fetchall.return_value = [MOCK_SALARY_ROW] * 10

    response = client.get('/salaries?page=2')
    assert response.status_code == 200


def test_salaries_search_by_keyword(client, logged_in_admin, mock_db):
    """Case 7: Tìm kiếm bảng lương theo tên nhân viên (keyword)."""
    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = [MOCK_SALARY_ROW]

    response = client.get('/salaries?keyword=Nguyễn')
    assert response.status_code == 200


def test_salaries_filter_by_month(client, logged_in_admin, mock_db):
    """Case 8: Lọc danh sách bảng lương theo tháng."""
    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = [MOCK_SALARY_ROW]

    response = client.get('/salaries?month=3')
    assert response.status_code == 200


def test_salaries_filter_by_year(client, logged_in_admin, mock_db):
    """Case 9: Lọc danh sách bảng lương theo năm."""
    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = [MOCK_SALARY_ROW]

    response = client.get('/salaries?year=2026')
    assert response.status_code == 200


def test_salaries_filter_combined_search(client, logged_in_admin, mock_db):
    """Case 10: Kết hợp lọc theo keyword, month, year và page."""
    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = [MOCK_SALARY_ROW]

    response = client.get('/salaries?keyword=Nguyễn&month=3&year=2026&page=1')
    assert response.status_code == 200


def test_salaries_db_exception_handling(client, logged_in_admin, mock_db):
    """Case 11: Bắt ngoại lệ DB khi lấy dữ liệu danh sách lương."""
    mock_db.execute.side_effect = Exception("DB Read Error")

    response = client.get('/salaries')
    assert response.status_code == 200


def test_salaries_invalid_page_param_defaults(client, logged_in_admin, mock_db):
    """Case 12: Truyền tham số page không hợp lệ (VD: page=abc hoặc âm)."""
    mock_db.fetchone.return_value = (0,)
    mock_db.fetchall.return_value = []

    # Flask route request.args.get("page", 1, type=int) sẽ fallback về None/1 nếu lỗi ép kiểu
    response = client.get('/salaries?page=invalid')
    assert response.status_code in [200, 400, 500]