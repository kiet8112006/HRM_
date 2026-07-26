from flask import (
    Blueprint,
    render_template,
    flash,
    current_app
)
from database import get_connection
from utils.auth import login_required, role_required
import datetime
import json

dashboard_bp = Blueprint("dashboard", __name__)


def format_money_short(amount):
    if not amount:
        return "0 VNĐ"
    if amount >= 1_000_000_000:
        return f"{amount / 1_000_000_000:.2f}B VNĐ"
    elif amount >= 1_000_000:
        return f"{amount / 1_000_000:.2f}M VNĐ"
    elif amount >= 1_000:
        return f"{amount / 1_000:.2f}K VNĐ"
    else:
        return f"{amount:,.0f} VNĐ"


@dashboard_bp.route("/")
@login_required
@role_required('Admin', 'Manager')
def home():
    conn = get_connection()
    cursor = conn.cursor()

    days_vi = ["Chủ Nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"]
    now = datetime.datetime.now()
    day_index = int(now.strftime('%w'))
    current_date_display = f"{days_vi[day_index]}, {now.strftime('%d/%m/%Y')}"

    try:
        cursor.execute("SELECT COUNT(*) FROM Employees WHERE IsDeleted = 0") 
        total_employees = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Departments WHERE IsDeleted = 0") 
        total_departments = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Positions WHERE IsDeleted = 0") 
        total_positions = cursor.fetchone()[0]

        # MSSQL: Dùng ISNULL
        cursor.execute("""
            SELECT ISNULL(SUM(BaseSalary + Bonus + Allowance), 0) 
            FROM Salaries WHERE IsDeleted = 0
        """)     
        total_salary = cursor.fetchone()[0]
        total_salary_display = format_money_short(total_salary)

        # MSSQL: Dùng MONTH(), YEAR(), GETDATE()
        cursor.execute("""
            SELECT COUNT(*) FROM Employees 
            WHERE IsDeleted = 0 
              AND MONTH(HireDate) = MONTH(GETDATE()) 
              AND YEAR(HireDate) = YEAR(GETDATE())
        """) 
        new_employees = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM LeaveRequests WHERE IsDeleted = 0 AND Status = N'Chờ duyệt'") 
        leave_today = cursor.fetchone()[0]

        cursor.execute("""
            SELECT ISNULL(SUM(BaseSalary + Bonus + Allowance), 0) FROM Salaries 
            WHERE IsDeleted = 0 
              AND Month = MONTH(GETDATE()) 
              AND Year = YEAR(GETDATE())
        """) 
        salary_this_month = cursor.fetchone()[0]

        # MSSQL: Dùng DATEADD để lùi 1 tháng
        cursor.execute("""
            SELECT ISNULL(SUM(BaseSalary + Bonus + Allowance), 0) FROM Salaries 
            WHERE IsDeleted = 0 
              AND Month = MONTH(DATEADD(MONTH, -1, GETDATE())) 
              AND Year = YEAR(DATEADD(MONTH, -1, GETDATE()))
        """) 
        salary_last_month = cursor.fetchone()[0]

        if salary_last_month > 0:
            salary_growth = round(((salary_this_month - salary_last_month) / salary_last_month) * 100, 1)
        else:
            salary_growth = 0

        cursor.execute("""
            SELECT D.DepartmentName, COUNT(E.EmployeeID) 
            FROM Departments D 
            LEFT JOIN Employees E ON D.DepartmentID = E.DepartmentID AND E.IsDeleted = 0
            WHERE D.IsDeleted = 0
            GROUP BY D.DepartmentName 
            ORDER BY D.DepartmentName
        """) 
        department_data = cursor.fetchall()

        department_names = []
        department_counts = []
        for row in department_data:
            department_names.append(str(row[0]) if row[0] else "Chưa rõ")
            department_counts.append(int(row[1]) if row[1] else 0)

        cursor.execute("""
            SELECT Month, SUM(BaseSalary + Bonus + Allowance) 
            FROM Salaries 
            WHERE IsDeleted = 0 AND Year = YEAR(GETDATE()) 
            GROUP BY Month ORDER BY Month
        """) 
        salary_data = cursor.fetchall()

        salary_months = []
        salary_totals = []
        for row in salary_data:
            salary_months.append(f"T{row[0]}")
            salary_totals.append(float(row[1]) if row[1] is not None else 0.0)

        # MSSQL: Dùng TOP 5 và DATEDIFF
        cursor.execute("""
            SELECT TOP 5 E.FullName, C.EndDate, DATEDIFF(DAY, GETDATE(), C.EndDate) AS DaysLeft 
            FROM Contracts C 
            INNER JOIN Employees E ON C.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE C.IsDeleted = 0 AND C.EndDate >= CAST(GETDATE() AS DATE) 
            ORDER BY C.EndDate
        """) 
        expiring_contracts_raw = cursor.fetchall()
        expiring_contracts = [
            {
                "FullName": row[0],
                "EndDate": row[1],
                "DaysLeft": row[2]
            }
            for row in expiring_contracts_raw
        ]

        # MSSQL: Dùng TOP 5 và Tiền tố N'' cho chuỗi tiếng Việt Unicode
        cursor.execute("""
            SELECT TOP 5 E.FullName, L.FromDate, L.ToDate 
            FROM LeaveRequests L 
            INNER JOIN Employees E ON L.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE L.IsDeleted = 0 AND L.Status = N'Chờ duyệt' 
            ORDER BY L.FromDate
        """) 
        pending_leave_requests_raw = cursor.fetchall()
        pending_leave_requests = [
            {
                "FullName": row[0],
                "FromDate": row[1],
                "ToDate": row[2]
            }
            for row in pending_leave_requests_raw
        ]

        cursor.execute("""
            SELECT COUNT(*) FROM Attendance A 
            INNER JOIN Employees E ON A.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE A.IsDeleted = 0 AND A.Status = N'Có mặt' 
        """) 
        present_count = cursor.fetchone()[0] 

        cursor.execute("""
            SELECT COUNT(*) FROM Attendance A 
            INNER JOIN Employees E ON A.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE A.IsDeleted = 0 AND A.Status = N'Đi trễ' 
        """) 
        late_count = cursor.fetchone()[0]                            

        cursor.execute("""
            SELECT COUNT(*) FROM Attendance A 
            INNER JOIN Employees E ON A.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE A.IsDeleted = 0 AND A.Status = N'Nghỉ' 
        """) 
        absent_count = cursor.fetchone()[0]                                     

        not_checked_count = max(0, total_employees - present_count - late_count - absent_count) 
        attendance_data = [present_count, late_count, absent_count, not_checked_count]

        return render_template(
            "dashboard/index.html",
            total_employees=total_employees,
            total_departments=total_departments,
            total_positions=total_positions,
            total_salary=total_salary,
            total_salary_display=total_salary_display,
            json_department_names=json.dumps(department_names, ensure_ascii=False),
            json_department_counts=json.dumps(department_counts),
            json_salary_months=json.dumps(salary_months, ensure_ascii=False),
            json_salary_totals=json.dumps(salary_totals),
            json_attendance_data=json.dumps(attendance_data),
            today=current_date_display,
            new_employees=new_employees,
            leave_today=leave_today,
            salary_this_month=f"{salary_this_month:,.0f}",
            salary_growth=salary_growth,
            expiring_contracts=expiring_contracts,
            pending_leave_requests=pending_leave_requests,
            present_count=present_count,
            late_count=late_count,
            absent_count=absent_count,
            not_checked_count=not_checked_count
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi hệ thống khi tải trang Dashboard: {str(e)}")
        flash("Đã có lỗi hệ thống xảy ra khi lấy dữ liệu trang chủ!", "danger")
        return render_template(
            "dashboard/index.html",
            total_employees=0, total_departments=0, total_positions=0,
            total_salary=0, total_salary_display="0 VNĐ",
            json_department_names=json.dumps([]), json_department_counts=json.dumps([]),
            json_salary_months=json.dumps([]), json_salary_totals=json.dumps([]),
            json_attendance_data=json.dumps([0, 0, 0, 0]),
            today=current_date_display,
            new_employees=0, leave_today=0, salary_this_month="0", salary_growth=0,
            expiring_contracts=[], pending_leave_requests=[],
            present_count=0, late_count=0, absent_count=0, not_checked_count=0
        )
    finally:
        conn.close()