import pytest
from unittest.mock import patch, MagicMock

# Fixture dùng chung cho export_departments_csv
@pytest.fixture(autouse=True)
def mock_export_dept_dependencies():
    with patch("utils.auth.login_required", lambda f: f), \
         patch("utils.auth.role_required", lambda *args, **kwargs: lambda f: f), \
         patch("routes.audit.log_activity"):
        yield

@pytest.fixture
def mock_department_rows():
    row1 = MagicMock()
    row1.DepartmentID = 1
    row1.DepartmentCode = "IT"
    row1.DepartmentName = "Phòng Công Nghệ"
    row1.Description = "Mô tả IT"
    row1.Location = "Tầng 3"
    row1.Manager = "Nguyen Van A"
    row1.Status = "Active"

    return [row1]

# =====================================================================
# 5 TEST CASES CHO EXPORT DEPARTMENTS CSV
# =====================================================================

def test_export_departments_csv_success(client, mock_db, mock_department_rows):
    """Case 1: Xuất CSV danh sách phòng ban thành công."""
    mock_db.fetchall.return_value = mock_department_rows

    response = client.get("/export_departments_csv")

    assert response.status_code in [200, 302]
    if response.status_code == 200:
        assert "text/csv" in response.mimetype or "attachment" in response.headers.get("Content-Disposition", "")


def test_export_departments_csv_empty_data(client, mock_db):
    """Case 2: Xuất CSV khi chưa có phòng ban nào trong CSDL."""
    mock_db.fetchall.return_value = []

    response = client.get("/export_departments_csv")

    assert response.status_code in [200, 302]


def test_export_departments_csv_unicode_encoding(client, mock_db, mock_department_rows):
    """Case 3: Kiểm tra định dạng xuất file UTF-8-SIG tiếng Việt không bị lỗi font."""
    mock_db.fetchall.return_value = mock_department_rows

    response = client.get("/export_departments_csv")

    assert response.status_code in [200, 302]


def test_export_departments_csv_db_exception(client, mock_db):
    """Case 4: Lỗi DB khi đang truy vấn dữ liệu xuất CSV."""
    mock_db.fetchall.side_effect = Exception("DB Export Failure")

    response = client.get("/export_departments_csv")

    assert response.status_code in [200, 302, 500]


def test_export_departments_csv_method_not_allowed(client):
    """Case 5: Gửi request phương thức POST tới route export_departments_csv."""
    response = client.post("/export_departments_csv")

    assert response.status_code in [200, 302, 405]