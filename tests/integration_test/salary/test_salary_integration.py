from unittest.mock import MagicMock, patch
from datetime import date
import pytest


# =====================================================================
# INTEGRATION TEST: LUỒNG THÊM BẢNG LƯƠNG (SALARY POST FLOW)
# =====================================================================
@patch("routes.salary.log_activity")
@patch("routes.salary.create_notification")
@patch("routes.salary.validate_salary_status")
@patch("routes.salary.validate_payment_date")
@patch("routes.salary.validate_month_year")
@patch("routes.salary.validate_salary_components")
@patch("routes.salary.get_connection")
def test_add_salary_full_flow_success(
    mock_get_conn,
    mock_val_components,
    mock_val_month_year,
    mock_val_payment_date,
    mock_val_status,
    mock_create_notification,
    mock_log_activity,
    authenticated_client,
):
    # -----------------------------------------------------------------
    # 1. SETUP MOCK DATABASE & CURSOR
    # -----------------------------------------------------------------
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Giả lập kết quả trả về từ DB theo đúng thứ tự các câu lệnh SELECT trong route add_salary:
    # 1. SELECT FullName FROM Employees... -> Trả về ("Trần Thị B",)
    # 2. SELECT COUNT(*) FROM Salaries (Check trùng lương tháng) -> Trả về (0,)
    # 3. SELECT ISNULL(MAX(SalaryID), 0) + 1 FROM Salaries -> Trả về (1,)
    mock_cursor.fetchone.side_effect = [
        ("Trần Thị B",),
        (0,),
        (1,),
    ]

    # 2. SETUP MOCK VALIDATORS
    # Lương thực nhận (NetSalary) = 15,000,000 + 1,000,000 + 500,000 + 0 - 0 - 500,000 - 1,000,000 = 15,000,000
    mock_val_components.return_value = 15000000.0

    # 3. DỮ LIỆU INPUT POST FORM
    data = {
        "employee_id": "1",
        "base_salary": "15000000",
        "bonus": "1000000",
        "allowance": "500000",
        "overtime_pay": "0",
        "deduction": "0",
        "tax": "500000",
        "insurance": "1000000",
        "month": "3",
        "year": "2026",
        "payment_date": "2026-03-31",
        "status": "Đã thanh toán",
    }

    # -----------------------------------------------------------------
    # EXECUTE REQUEST
    # -----------------------------------------------------------------
    response = authenticated_client.post(
        "/add_salary", data=data, follow_redirects=True
    )

    # -----------------------------------------------------------------
    # KIỂM TRA ĐIỀU KIỆN KẾT QUẢ (VERIFY FLOW & CHECKLIST)
    # -----------------------------------------------------------------

    # 1. Kiểm tra HTTP Status & Redirect
    assert response.status_code == 200
    assert response.request.path == "/salaries"

    # 2. Kiểm tra Database Record (INSERT INTO Salaries)
    assert mock_cursor.execute.called
    assert mock_conn.commit.called

    insert_args = None
    for call in mock_cursor.execute.call_args_list:
        query = call[0][0]
        if "INSERT INTO Salaries" in query:
            # call[0] chứa toàn bộ tham số truyền vào execute(query, arg1, arg2,...)
            insert_args = call[0]
            break

    assert insert_args is not None, "Không tìm thấy câu lệnh INSERT INTO Salaries"

    # Verify mã SalaryCode "SAL0001", NetSalary, Month, Year, Status trong câu lệnh INSERT
    assert "SAL0001" in insert_args
    assert 15000000.0 in insert_args
    assert 3 in insert_args
    assert 2026 in insert_args
    assert "Đã thanh toán" in insert_args

    # 3. Kiểm tra Notification
    mock_create_notification.assert_called_once_with(
        title="Bảng lương mới",
        message="Đã khởi tạo bảng lương tháng 3/2026 cho nhân viên Trần Thị B.",
        type="Success",
        receiver_role="Admin",
        url="/salaries",
    )

    # 4. Kiểm tra Audit Log
    mock_log_activity.assert_called_once_with(
        module="Salary",
        action="Create",
        description="Created salary record for employee Trần Thị B (3/2026).",
    )