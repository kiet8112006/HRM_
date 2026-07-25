from unittest.mock import MagicMock, patch
from io import BytesIO
import pytest


# =====================================================================
# INTEGRATION TEST: LUỒNG THÊM HỢP ĐỒNG (CONTRACT POST FLOW)
# =====================================================================
@patch("routes.contract.log_activity")
@patch("routes.contract.create_notification")
@patch("routes.contract.save_contract")
@patch("routes.contract.verify_pdf")
@patch("routes.contract.allowed_document_mimetype")
@patch("routes.contract.allowed_document")
@patch("routes.contract.validate_contract_dates")
@patch("routes.contract.validate_contract_description")
@patch("routes.contract.validate_signer")
@patch("routes.contract.validate_work_location")
@patch("routes.contract.validate_probation_months")
@patch("routes.contract.validate_basic_salary")
@patch("routes.contract.validate_contract_number")
@patch("routes.contract.validate_contract_code")
@patch("routes.contract.get_connection")
def test_add_contract_full_flow_success(
    mock_get_conn,
    mock_val_code,
    mock_val_num,
    mock_val_salary,
    mock_val_probation,
    mock_val_location,
    mock_val_signer,
    mock_val_desc,
    mock_val_dates,
    mock_allowed_doc,
    mock_allowed_mime,
    mock_verify_pdf,
    mock_save_contract,
    mock_create_notification,
    mock_log_activity,
    authenticated_client,
):
    # 1. SETUP MOCK DATABASE & CURSOR
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Giả lập kết quả trả về từ DB:
    # 1. Check trùng mã -> (0,)
    # 2. Get Employee Name -> ("Nguyễn Văn A",)
    mock_cursor.fetchone.side_effect = [
        (0,),
        ("Nguyễn Văn A",),
    ]

    # 2. SETUP MOCK VALIDATORS & FILE UPLOAD
    mock_val_salary.return_value = 15000000.0
    mock_val_probation.return_value = 2
    mock_val_dates.return_value = ("2026-04-01", "2027-04-01")

    mock_allowed_doc.return_value = True
    mock_allowed_mime.return_value = True
    mock_verify_pdf.return_value = True
    mock_save_contract.return_value = "contract_HD0001_2026.pdf"

    # 3. DỮ LIỆU INPUT POST FORM
    pdf_file = (BytesIO(b"%PDF-1.4 Fake PDF Content"), "hop_dong_lao_dong.pdf")

    data = {
        "employee_id": "1",
        "contract_code": "HD0001",
        "contract_number": "01/2026/HĐLĐ",
        "contract_type": "Xác định thời hạn",
        "start_date": "2026-04-01",
        "end_date": "2027-04-01",
        "basic_salary": "15000000",
        "work_location": "Hà Nội",
        "department_id": "1",
        "position_id": "1",
        "signer": "Giám đốc Nguyễn Văn B",
        "sign_date": "2026-03-30",
        "probation_months": "2",
        "status": "Còn hiệu lực",
        "description": "Hợp đồng thử việc 2 tháng",
        "contract_file": pdf_file,
    }

    # EXECUTE REQUEST
    response = authenticated_client.post(
        "/add_contract",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    # -----------------------------------------------------------------
    # KIỂM TRA ĐIỀU KIỆN KẾT QUẢ
    # -----------------------------------------------------------------

    # 1. HTTP Status & Redirect
    assert response.status_code == 200
    assert response.request.path == "/contracts"

    # 2. Check File PDF & Database Record
    assert mock_save_contract.called
    assert mock_cursor.execute.called
    assert mock_conn.commit.called

    insert_args = None
    for call in mock_cursor.execute.call_args_list:
        query = call[0][0]
        if "INSERT INTO Contracts" in query:
            # call[0][1] chứa tuple các tham số truyền vào
            insert_args = call[0][1]
            break

    assert insert_args is not None, "Không tìm thấy câu lệnh INSERT INTO Contracts"

    # Check các giá trị trong tuple tham số
    assert "HD0001" in insert_args
    assert "contract_HD0001_2026.pdf" in insert_args
    assert "Còn hiệu lực" in insert_args

    # 3. Notification
    mock_create_notification.assert_called_once_with(
        title="Hợp đồng mới",
        message="Hợp đồng HD0001 của nhân viên Nguyễn Văn A đã được khởi tạo.",
        type="Success",
        receiver_role="Admin",
        url="/contracts",
    )

    # 4. Audit Log
    mock_log_activity.assert_called_once_with(
        module="Contract",
        action="Create",
        description="Created contract HD0001 for employee Nguyễn Văn A.",
    )