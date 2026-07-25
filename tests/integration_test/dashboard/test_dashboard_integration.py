from datetime import date, datetime
from unittest.mock import MagicMock, patch
import pytest


# =====================================================================
# INTEGRATION TEST: LUỒNG TẢI DỮ LIỆU TRANG DASHBOARD
# =====================================================================
@patch("routes.dashboard.get_connection")
def test_dashboard_full_flow_success(mock_get_conn, authenticated_client):
    # 1. SETUP MOCK DATABASE & CURSOR
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Fetchone sequence (11 calls)
    mock_cursor.fetchone.side_effect = [
        (50,),           # total_employees
        (8,),            # total_departments
        (10,),           # total_positions
        (500000000.0,),  # total_salary
        (3,),            # new_employees
        (12,),           # leave_today / pending_leave
        (500000000.0,),  # salary_this_month
        (480000000.0,),  # salary_last_month
        (35,),           # present_count
        (5,),            # late_count
        (2,),            # absent_count
    ]

    # Fetchall sequence
    # QUAN TRỌNG: Dùng date object thay vì string để tránh lỗi 'str' object has no attribute 'strftime'
    mock_cursor.fetchall.side_effect = [
        [("IT", 20), ("HR", 10), ("Kế toán", 20)],             # department_data
        [(1, 450000000.0), (2, 500000000.0)],                   # salary_data
        [("Nguyễn Văn A", date(2026, 8, 1), 8)],                # expiring_contracts
        [("Trần Văn B", date(2026, 7, 25), date(2026, 7, 27))], # pending_leave_requests
    ]

    # 2. EXECUTE REQUEST GET /
    response = authenticated_client.get("/")

    # 3. VERIFY
    assert response.status_code == 200

    html_content = response.data.decode("utf-8")

    assert "50" in html_content, "Dashboard phải hiển thị Total Employees = 50"
    assert "8" in html_content, "Dashboard phải hiển thị Total Departments = 8"
    assert "12" in html_content, "Dashboard phải hiển thị Pending Leave = 12"

    assert mock_conn.close.called