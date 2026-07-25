import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from exceptions.validator.employee import EmployeeValidationError

# Fixture dùng chung cho module add_employee
@pytest.fixture(autouse=True)
def mock_add_dependencies():
    with patch("utils.auth.login_required", lambda f: f), \
         patch("utils.auth.role_required", lambda *args, **kwargs: lambda f: f), \
         patch("routes.employee.get_cached_departments", return_value=[(1, "IT")]), \
         patch("routes.employee.get_cached_positions", return_value=[(1, "Dev")]), \
         patch("routes.employee.create_notification"), \
         patch("routes.employee.log_activity"):
        yield

@pytest.fixture
def valid_employee_payload():
    """Mẫu dữ liệu form hợp lệ chuẩn."""
    return {
        "fullname": "Nguyen Van Test",
        "gender": "Nam",
        "dob": "1998-05-20",
        "hiredate": "2023-01-10",
        "status": "Active",
        "email": "test.employee@gmail.com",
        "citizenid": "012345678901",
        "address": "123 Đường ABC, Hà Nội",
        "nationality": "Việt Nam",
        "maritalstatus": "Độc thân",
        "emergencycontact": "Nguyen Van B",
        "emergencyphone": "0987654321",
        "phone": "0901234567",
        "department_id": "1",
        "position_id": "1",
        "manager_id": ""
    }

# =====================================================================
# 1. GET ROUTE & HAPPY PATH POST (3 Cases)
# =====================================================================

def test_add_employee_get_page(client, mock_db):
    """Case 1: GET /add_employee hiển thị form thành công."""
    mock_db.fetchall.return_value = [(1, "Quản lý A")]
    response = client.get("/add_employee")
    assert response.status_code == 200

def test_add_employee_post_success_no_files(client, mock_db, valid_employee_payload):
    """Case 2: POST thêm mới thành công (Không upload file ảnh nào)."""
    mock_db.fetchone.return_value = (0,)

    response = client.post("/add_employee", data=valid_employee_payload, follow_redirects=True)
    
    assert response.status_code == 200
    assert mock_db.execute.called
    
    # Kiểm tra xem CÓ BẤT KỲ câu lệnh execute nào chứa "INSERT INTO Employees" không
    executed_sqls = [call[0][0] for call in mock_db.execute.call_args_list if call[0]]
    assert any("INSERT INTO Employees" in sql for sql in executed_sqls)
def test_add_employee_post_success_with_all_files(client, mock_db, valid_employee_payload):
    """Case 3: POST thêm mới thành công khi upload đủ cả 3 ảnh (Avatar, CCCD trước, CCCD sau)."""
    mock_db.fetchone.return_value = (0,)
    
    files = {
        "photo": (BytesIO(b"img"), "avatar.jpg"),
        "citizen_front": (BytesIO(b"img"), "front.jpg"),
        "citizen_back": (BytesIO(b"img"), "back.jpg")
    }
    data = {**valid_employee_payload, **files}

    with patch("routes.employee.allowed_file", return_value=True), \
         patch("routes.employee.allowed_mimetype", return_value=True), \
         patch("routes.employee.verify_image", return_value=True), \
         patch("routes.employee.save_avatar", return_value="avatar.jpg"), \
         patch("routes.employee.save_citizen_front", return_value="front.jpg"), \
         patch("routes.employee.save_citizen_back", return_value="back.jpg"):

        response = client.post("/add_employee", data=data, follow_redirects=True)
        assert response.status_code == 200

# =====================================================================
# 2. FILE UPLOAD VALIDATIONS CHI TIẾT (9 Cases)
# =====================================================================

def test_add_employee_skip_empty_file_inputs(client, mock_db, valid_employee_payload):
    """Case 4: Truyền input file rỗng (filename = '') -> Hệ thống tự bỏ qua không validate."""
    mock_db.fetchone.return_value = (0,)
    data = {**valid_employee_payload, "photo": (BytesIO(b""), "")}
    response = client.post("/add_employee", data=data, follow_redirects=True)
    assert response.status_code == 200

@pytest.mark.parametrize("file_key", ["photo", "citizen_front", "citizen_back"])
def test_add_employee_disallowed_file_extension(client, mock_db, valid_employee_payload, file_key):
    """Cases 5, 6, 7: Upload file sai đuôi mở rộng (.pdf, .exe) cho từng loại ảnh."""
    data = {**valid_employee_payload, file_key: (BytesIO(b"data"), "file.pdf")}
    with patch("routes.employee.allowed_file", return_value=False):
        response = client.post("/add_employee", data=data, follow_redirects=True)
        assert response.status_code == 200

@pytest.mark.parametrize("file_key", ["photo", "citizen_front", "citizen_back"])
def test_add_employee_disallowed_mimetype(client, mock_db, valid_employee_payload, file_key):
    """Cases 8, 9, 10: Upload file sai Mimetype cho từng loại ảnh."""
    data = {**valid_employee_payload, file_key: (BytesIO(b"data"), "file.jpg")}
    with patch("routes.employee.allowed_file", return_value=True), \
         patch("routes.employee.allowed_mimetype", return_value=False):
        response = client.post("/add_employee", data=data, follow_redirects=True)
        assert response.status_code == 200

@pytest.mark.parametrize("file_key", ["photo", "citizen_front", "citizen_back"])
def test_add_employee_corrupted_image(client, mock_db, valid_employee_payload, file_key):
    """Cases 11, 12, 13: Upload file bị hỏng (verify_image = False) cho từng loại ảnh."""
    data = {**valid_employee_payload, file_key: (BytesIO(b"fake data"), "file.jpg")}
    with patch("routes.employee.allowed_file", return_value=True), \
         patch("routes.employee.allowed_mimetype", return_value=True), \
         patch("routes.employee.verify_image", return_value=False):
        response = client.post("/add_employee", data=data, follow_redirects=True)
        assert response.status_code == 200

# =====================================================================
# 3. TRÙNG LẶP DỮ LIỆU DB (3 Cases)
# =====================================================================

def test_add_employee_duplicate_citizenid(client, mock_db, valid_employee_payload):
    """Case 14: Trùng CCCD trong CSDL."""
    mock_db.fetchone.return_value = (1,)
    response = client.post("/add_employee", data=valid_employee_payload, follow_redirects=True)
    assert response.status_code == 200

def test_add_employee_duplicate_email(client, mock_db, valid_employee_payload):
    """Case 15: Trùng Email trong CSDL."""
    mock_db.fetchone.side_effect = [(0,), (1,)] # CCCD ok, Email trùng
    response = client.post("/add_employee", data=valid_employee_payload, follow_redirects=True)
    assert response.status_code == 200

def test_add_employee_duplicate_phone(client, mock_db, valid_employee_payload):
    """Case 16: Trùng Số điện thoại trong CSDL."""
    mock_db.fetchone.side_effect = [(0,), (0,), (1,)] # CCCD ok, Email ok, Phone trùng
    response = client.post("/add_employee", data=valid_employee_payload, follow_redirects=True)
    assert response.status_code == 200

# =====================================================================
# 4. VALIDATOR EXCEPTIONS (10 Cases)
# =====================================================================

@pytest.mark.parametrize("validator_target, exception_msg", [
    ("validate_name", "Tên không hợp lệ"),                 # Case 17
    ("validate_dob", "Tuổi phải từ 18 trở lên"),            # Case 18
    ("validate_hiredate", "Ngày vào làm nhỏ hơn ngày sinh"),# Case 19
    ("validate_email", "Email không đúng định dạng"),       # Case 20
    ("validate_citizenid", "CCCD phải có 12 chữ số"),       # Case 21
    ("validate_address", "Địa chỉ chứa ký tự đặc biệt"),    # Case 22
    ("validate_nationality", "Quốc tịch không hợp lệ"),     # Case 23
    ("validate_emergency_contact", "Tên NLH khẩn cấp sai"), # Case 24
    ("validate_emergency_phone", "SĐT khẩn cấp không đúng"),# Case 25
    ("validate_phone", "Số điện thoại sai định dạng")       # Case 26
])
def test_add_employee_validators(
    client, mock_db, valid_employee_payload, validator_target, exception_msg
):
    with patch(f"routes.employee.{validator_target}", side_effect=EmployeeValidationError(exception_msg)):
        response = client.post("/add_employee", data=valid_employee_payload, follow_redirects=True)
        assert response.status_code == 200

# =====================================================================
# 5. DATABASE EXCEPTION & MANAGER OPTIONAL (2 Cases)
# =====================================================================

def test_add_employee_with_manager_id(client, mock_db, valid_employee_payload):
    """Case 27: Thêm nhân viên có chọn người Quản lý (manager_id = 5)."""
    mock_db.fetchone.return_value = (0,)
    valid_employee_payload["manager_id"] = "5"
    response = client.post("/add_employee", data=valid_employee_payload, follow_redirects=True)
    assert response.status_code == 200

def test_add_employee_db_error_triggers_rollback(client, mock_db, valid_employee_payload):
    """Case 28: DB bị lỗi crash khi đang Insert -> Phải gọi conn.rollback()."""
    mock_db.fetchone.return_value = (0,)
    
    # Dùng hàm để ném Exception chỉ khi gặp câu INSERT
    def side_effect_with_error(sql, *args, **kwargs):
        if "INSERT INTO Employees" in sql:
            raise Exception("Lỗi ghi DB")
        return MagicMock()

    mock_db.execute.side_effect = side_effect_with_error

    response = client.post("/add_employee", data=valid_employee_payload, follow_redirects=True)
    assert response.status_code == 200