from unittest.mock import MagicMock, patch
import json
import pytest


# =====================================================================
# INTEGRATION TEST: REPORT DASHBOARD & FILTER FLOW
# =====================================================================
@patch("routes.report.get_cached_positions")
@patch("routes.report.get_cached_departments")
@patch("routes.report.get_connection")
def test_report_dashboard_filter_flow_success(
    mock_get_conn,
    mock_get_cached_depts,
    mock_get_cached_pos,
    authenticated_client,
):
    # -----------------------------------------------------------------
    # 1. SETUP MOCK CACHE & DATABASE
    # -----------------------------------------------------------------
    mock_get_cached_depts.return_value = [("IT",), ("HR",), ("Marketing",)]
    mock_get_cached_pos.return_value = [("Developer",), ("Manager",)]

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Giả lập trả về cho chuỗi 12 câu lệnh `cursor.execute` trong route /reports:
    # 1. total_employees (15)
    # 2. total_departments (3)
    # 3. total_positions (5)
    # 4. working_employees (15)
    # 5. quit_employees (0)
    # 6. probation_employees (0)
    # 7. pending_leave (2)
    # 8. total_salary (300,000,000.0)
    # 9. expiring_contract (1)
    # 10. new_employee (3)
    # 11. top_salaries_raw
    # 12. department_report_raw
    # 13. leave_report_raw
    mock_cursor.fetchone.side_effect = [
        (15,),            # total_employees
        (3,),             # total_departments
        (5,),             # total_positions
        (15,),            # working_employees
        (0,),             # quit_employees
        (0,),             # probation_employees
        (2,),             # pending_leave
        (300000000.0,),   # total_salary
        (1,),             # expiring_contract
        (3,),             # new_employee
    ]

    mock_cursor.fetchall.side_effect = [
        [("Nguyễn Văn A", 25000000.0), ("Trần Văn B", 20000000.0)],  # top_salaries
        [("IT", 15)],                                                # department_report
        [("Đã duyệt", 5), ("Chờ duyệt", 2)],                         # leave_report
    ]

    # -----------------------------------------------------------------
    # 2. EXECUTE GET REQUEST VỚI QUERY PARAMS (FILTER)
    # Ví dụ từ ảnh: Department = IT, Status = Đang làm
    # -----------------------------------------------------------------
    query_string = {
        "department": "IT",
        "status": "Đang làm",
        "from_date": "2026-01-01",
        "to_date": "2026-12-31",
    }

    response = authenticated_client.get("/reports", query_string=query_string)

    # -----------------------------------------------------------------
    # 3. VERIFY RESULT & ASSERTIONS
    # -----------------------------------------------------------------

    # Check 1: Request thành công
    assert response.status_code == 200

    # Check 2: Dynamic WHERE Clause & Params được tạo đúng và truyền vào DB Query
    executed_queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
    
    # Ít nhất 1 câu SQL có chứa lọc theo Department Name và Status
    has_dept_filter = any("D.DepartmentName = ?" in q for q in executed_queries)
    has_status_filter = any("E.Status = ?" in q for q in executed_queries)
    
    assert has_dept_filter, "Không tìm thấy điều kiện lọc D.DepartmentName = ? trong SQL"
    assert has_status_filter, "Không tìm thấy điều kiện lọc E.Status = ? trong SQL"

    # Kiểm tra tham số bộ lọc đã được truyền vào execute
    sample_execute_args = mock_cursor.execute.call_args_list[0][0][1]
    assert "IT" in sample_execute_args
    assert "Đang làm" in sample_execute_args

    # Check 3: Render Dashboard (Kiểm tra dữ liệu/KPI xuất hiện trong HTML render)
    html_content = response.data.decode("utf-8")
    
    # Kiểm tra KPI values xuất hiện trên UI
    assert "15" in html_content  # Total / Working IT employees
    assert "IT" in html_content  # Tên phòng ban đã chọn
    
    # Check 4: Đảm bảo DB Connection được đóng sau khi render
    assert mock_conn.close.called