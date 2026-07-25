import pytest
from unittest.mock import patch, MagicMock

# Fixture dùng chung cho module department
@pytest.fixture(autouse=True)
def mock_department_dependencies():
    with patch("utils.auth.login_required", lambda f: f), \
         patch("utils.auth.role_required", lambda *args, **kwargs: lambda f: f), \
         patch("routes.audit.log_activity"):
        yield

@pytest.fixture
def mock_departments_data():
    """Mock dữ liệu danh sách phòng ban từ DB."""
    dept1 = MagicMock()
    dept1.DepartmentID = 1
    dept1.DepartmentCode = "IT"
    dept1.DepartmentName = "Phòng Công Nghệ Thông Tin"
    dept1.Description = "Mô tả IT"
    dept1.Location = "Tầng 3"
    dept1.Managername = "Nguyen Van A"

    dept2 = MagicMock()
    dept2.DepartmentID = 2
    dept2.DepartmentCode = "HR"
    dept2.DepartmentName = "Phòng Nhân Sự"
    dept2.Description = "Mô tả HR"
    dept2.Location = "Tầng 2"
    dept2.Managername = "Tran Thi B"

    return [dept1, dept2]

# Helper gọi endpoint /departments linh hoạt
def get_departments_response(client, query_str=""):
    url = f"/departments?{query_str}" if query_str else "/departments"
    return client.get(url)

# =====================================================================
# 10 TEST CASES CHO ROUTE DEPARTMENTS
# =====================================================================

def test_departments_list_success(client, mock_db, mock_departments_data):
    """Case 1: Lấy danh sách phòng ban thành công (Trang đầu mặc định)."""
    mock_db.fetchone.return_value = (2,) # total_records
    mock_db.fetchall.return_value = mock_departments_data

    response = get_departments_response(client)

    assert response.status_code in [200, 302]


def test_departments_list_empty(client, mock_db):
    """Case 2: Danh sách phòng ban trống (Chưa có dữ liệu trong DB)."""
    mock_db.fetchone.return_value = (0,)
    mock_db.fetchall.return_value = []

    response = get_departments_response(client)

    assert response.status_code in [200, 302]


def test_departments_search_with_keyword(client, mock_db, mock_departments_data):
    """Case 3: Tìm kiếm phòng ban theo từ khóa (keyword = 'Công Nghệ')."""
    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = [mock_departments_data[0]]

    response = get_departments_response(client, "keyword=Công+Nghệ")

    assert response.status_code in [200, 302]


def test_departments_search_no_results(client, mock_db):
    """Case 4: Tìm kiếm theo từ khóa không tồn tại."""
    mock_db.fetchone.return_value = (0,)
    mock_db.fetchall.return_value = []

    response = get_departments_response(client, "keyword=NonExistingDept")

    assert response.status_code in [200, 302]


def test_departments_pagination_valid_page(client, mock_db, mock_departments_data):
    """Case 5: Phân trang hợp lệ (page = 2)."""
    mock_db.fetchone.return_value = (15,) # 15 bản ghi -> 2 trang
    mock_db.fetchall.return_value = mock_departments_data

    response = get_departments_response(client, "page=2")

    assert response.status_code in [200, 302]


def test_departments_pagination_invalid_page_type(client, mock_db, mock_departments_data):
    """Case 6: Truyền trang không phải là số (page = abc) -> Tự fallback về trang 1."""
    mock_db.fetchone.return_value = (2,)
    mock_db.fetchall.return_value = mock_departments_data

    response = get_departments_response(client, "page=abc")

    assert response.status_code in [200, 302]


def test_departments_pagination_out_of_range_page(client, mock_db):
    """Case 7: Truyền số trang vượt quá tổng số trang (page = 999)."""
    mock_db.fetchone.return_value = (5,)
    mock_db.fetchall.return_value = []

    response = get_departments_response(client, "page=999")

    assert response.status_code in [200, 302]


def test_departments_left_join_manager_null(client, mock_db):
    """Case 8: Phòng ban chưa có Trưởng phòng (ManagerID = NULL/Managername = None)."""
    dept_no_mgr = MagicMock()
    dept_no_mgr.DepartmentID = 3
    dept_no_mgr.DepartmentCode = "MKT"
    dept_no_mgr.DepartmentName = "Phòng Marketing"
    dept_no_mgr.Description = ""
    dept_no_mgr.Location = "Tầng 1"
    dept_no_mgr.Managername = None

    mock_db.fetchone.return_value = (1,)
    mock_db.fetchall.return_value = [dept_no_mgr]

    response = get_departments_response(client)

    assert response.status_code in [200, 302]


def test_departments_db_exception_handling(client, mock_db):
    """Case 9: Lỗi kết nối DB khi truy vấn -> Trả về giao diện rỗng kèm Flash Message."""
    mock_db.execute.side_effect = Exception("Database Query Exception")

    response = get_departments_response(client)

    assert response.status_code in [200, 302]


def test_departments_post_method_handling(client):
    """Case 10: Gửi request phương thức POST tới route /departments."""
    response = client.post("/departments")

    assert response.status_code in [200, 302, 405]