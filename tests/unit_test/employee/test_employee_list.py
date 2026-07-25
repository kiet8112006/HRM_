import pytest
from unittest.mock import patch, MagicMock

# =====================================================================
# FIXTURE MOCK CHO DANH MỤC CACHE & DỮ LIỆU CƠ BẢN
# =====================================================================
@pytest.fixture(autouse=True)
def mock_employee_dependencies():
    """Tự động mock các hàm cache và decorator phân quyền cho tất cả test cases."""
    with patch("utils.auth.login_required", lambda f: f), \
         patch("utils.auth.role_required", lambda *args, **kwargs: lambda f: f), \
         patch("routes.employee.get_cached_departments", return_value=[(1, "IT"), (2, "HR")]), \
         patch("routes.employee.get_cached_positions", return_value=[(1, "Dev"), (2, "Tester")]):
        yield


# =====================================================================
# 1. HAPPY PATH & PHÂN TRANG CƠ BẢN
# =====================================================================

def test_get_employees_happy_path(client, mock_db):
    """Case 1: Lấy danh sách nhân viên bình thường (Trang 1)."""
    mock_db.fetchone.return_value = (25,) # Tổng 25 bản ghi
    mock_db.fetchall.return_value = [
        (1, "EMP001", "Nguyễn Văn A", None, "Nam", "0901234567", "a@test.com", "Active", "IT", "Dev")
    ]

    response = client.get("/employees")

    assert response.status_code == 200
    assert mock_db.execute.call_count == 2 
    # OFFSET trang 1 phải là 0
    assert mock_db.execute.call_args_list[1][0][1][-2] == 0 


def test_get_employees_pagination_offset(client, mock_db):
    """Case 7: Kiểm tra tính toán OFFSET khi ở Trang 2 (page=2, per_page=10 -> offset=10)."""
    mock_db.fetchone.return_value = (25,)
    mock_db.fetchall.return_value = []

    response = client.get("/employees?page=2")

    assert response.status_code == 200
    select_args = mock_db.execute.call_args_list[1][0][1]
    assert select_args[-2] == 10  # offset = (2-1)*10 = 10
    assert select_args[-1] == 10  # fetch next = 10


# =====================================================================
# 2. BỘ LỌC (SEARCH & FILTERS)
# =====================================================================

@pytest.mark.parametrize("query_str, expected_params", [
    ("keyword=An", ("%An%", "%%", "%%", "%%")),               # Case 2: Tìm theo tên
    ("department=IT", ("%%", "%IT%", "%%", "%%")),             # Case 3: Lọc phòng ban
    ("position=Dev", ("%%", "%%", "%Dev%", "%%")),             # Case 4: Lọc chức danh
    ("status=Active", ("%%", "%%", "%%", "%Active%")),         # Case 5: Lọc trạng thái
    ("keyword=An&department=IT&position=Dev&status=Active",   # Case 6: Combo 4 lọc
     ("%An%", "%IT%", "%Dev%", "%Active%")),
])
def test_get_employees_filters(client, mock_db, query_str, expected_params):
    mock_db.fetchone.return_value = (5,)
    mock_db.fetchall.return_value = []

    response = client.get(f"/employees?{query_str}")

    assert response.status_code == 200
    actual_count_params = mock_db.execute.call_args_list[0][0][1]
    assert actual_count_params == expected_params


# =====================================================================
# 3. EDGE CASES & EXCEPTION HANDLING
# =====================================================================

def test_get_employees_invalid_page_type(client, mock_db):
    """Case 8: Trang không hợp lệ (page=abc) -> Flask tự fallback về page=1."""
    mock_db.fetchone.return_value = (10,)
    mock_db.fetchall.return_value = []

    response = client.get("/employees?page=abc")

    assert response.status_code == 200
    select_args = mock_db.execute.call_args_list[1][0][1]
    assert select_args[-2] == 0


def test_get_employees_empty_result(client, mock_db):
    """Case 9: Không tìm thấy kết quả nào (total_records = 0)."""
    mock_db.fetchone.return_value = (0,)
    mock_db.fetchall.return_value = []

    response = client.get("/employees?keyword=NotFoundName")

    assert response.status_code == 200


def test_get_employees_database_error(client, mock_db):
    """Case 10: Xử lý ngoại lệ khi Database bị ngắt kết nối/lỗi Query."""
    mock_db.execute.side_effect = Exception("Database connection lost")

    response = client.get("/employees")

    assert response.status_code == 200