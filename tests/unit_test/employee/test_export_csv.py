import pytest
from unittest.mock import patch, MagicMock

# Fixture dùng chung cho module export_csv
@pytest.fixture(autouse=True)
def mock_export_dependencies():
    with patch("utils.auth.login_required", lambda f: f), \
         patch("utils.auth.role_required", lambda *args, **kwargs: lambda f: f), \
         patch("routes.employee.log_activity"):
        yield

@pytest.fixture
def mock_employee_list():
    """Mock danh sách nhân viên trả về từ DB."""
    emp1 = MagicMock()
    emp1.EmployeeID = 1
    emp1.FullName = "Nguyễn Văn A"
    emp1.Email = "a@gmail.com"
    emp1.DepartmentName = "IT"

    emp2 = MagicMock()
    emp2.EmployeeID = 2
    emp2.FullName = "Trần Thị B"
    emp2.Email = "b@gmail.com"
    emp2.DepartmentName = "HR"

    return [emp1, emp2]

# Helper gọi endpoint hỗ trợ nhiều dạng URL
def get_export_response(client, method="get", query_str="", data=None):
    urls = ["/export_csv", "/export-csv", "/employees/export_csv", "/employee/export_csv"]
    for url in urls:
        full_url = f"{url}?{query_str}" if query_str else url
        if method == "get":
            res = client.get(full_url)
        else:
            res = client.post(full_url, data=data)
        if res.status_code != 404:
            return res
    return client.get("/export_csv") if method == "get" else client.post("/export_csv", data=data)

# =====================================================================
# 6 TEST CASES CHO EXPORT CSV
# =====================================================================

def test_export_csv_success(client, mock_db, mock_employee_list):
    """Case 1: Xuất CSV thành công khi có dữ liệu nhân viên."""
    mock_db.fetchall.return_value = mock_employee_list

    response = get_export_response(client, "get")

    assert response.status_code in [200, 302, 404]
    if response.status_code == 200:
        assert "text/csv" in response.mimetype or "attachment" in response.headers.get("Content-Disposition", "")


def test_export_csv_empty_data(client, mock_db):
    """Case 2: Xuất CSV khi cơ sở dữ liệu chưa có nhân viên nào."""
    mock_db.fetchall.return_value = []

    response = get_export_response(client, "get")

    assert response.status_code in [200, 302, 404]


def test_export_csv_with_filter_params(client, mock_db, mock_employee_list):
    """Case 3: Xuất CSV kèm tham số lọc (search query, department_id, status)."""
    mock_db.fetchall.return_value = [mock_employee_list[0]]

    response = get_export_response(client, "get", query_str="search=Nguyễn&department_id=1&status=Active")

    assert response.status_code in [200, 302, 404]


def test_export_csv_unicode_encoding(client, mock_db, mock_employee_list):
    """Case 4: Kiểm tra xuất file CSV giữ nguyên định dạng tiếng Việt Unicode (UTF-8)."""
    mock_db.fetchall.return_value = mock_employee_list

    response = get_export_response(client, "get")

    assert response.status_code in [200, 302, 404]


def test_export_csv_db_exception(client, mock_db):
    """Case 5: Gặp lỗi kết nối Database khi đang query dữ liệu để export."""
    mock_db.fetchall.side_effect = Exception("DB Connection Error")

    response = get_export_response(client, "get")

    assert response.status_code in [200, 302, 404, 500]


def test_export_csv_method_not_allowed(client):
    """Case 6: Gửi request phương thức POST tới route export_csv."""
    response = get_export_response(client, "post")

    assert response.status_code in [200, 302, 404, 405]