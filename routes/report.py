from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    current_app
)
from database import get_connection
from utils.auth import login_required, role_required
import json

report_bp = Blueprint("report", __name__)

# --- CÁC HÀM HỖ TRỢ LẤY DANH MỤC CÓ CACHE ---
def get_cached_departments():
    try:
        from app import cache
        @cache.cached(timeout=60, key_prefix='report_departments_cache')
        def query_db():
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT DepartmentName FROM Departments WHERE IsDeleted = 0 ORDER BY DepartmentName")
                return cursor.fetchall()
            finally:
                conn.close()
        return query_db()
    except Exception:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT DepartmentName FROM Departments WHERE IsDeleted = 0 ORDER BY DepartmentName")
            return cursor.fetchall()
        finally:
            conn.close()

def get_cached_positions():
    try:
        from app import cache
        @cache.cached(timeout=60, key_prefix='report_positions_cache')
        def query_db():
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT PositionName FROM Positions WHERE IsDeleted = 0 ORDER BY PositionName")
                return cursor.fetchall()
            finally:
                conn.close()
        return query_db()
    except Exception:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT PositionName FROM Positions WHERE IsDeleted = 0 ORDER BY PositionName")
            return cursor.fetchall()
        finally:
            conn.close()


@report_bp.route("/reports")
@login_required
@role_required('Admin', 'Manager')
def reports():
    from_date = request.args.get("from_date", "")
    to_date = request.args.get("to_date", "")
    department = request.args.get("department", "")
    position = request.args.get("position", "")
    status = request.args.get("status", "")

    departments = get_cached_departments()
    positions = get_cached_positions()

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # ==========================================================
        # Dynamic Filter Construction
        # ==========================================================
        where = ["E.IsDeleted = 0"]
        params = []

        if department:
            where.append("D.DepartmentName = %s")
            params.append(department)

        if position:
            where.append("P.PositionName = %s")
            params.append(position)

        if status:
            where.append("E.Status = %s")
            params.append(status)

        if from_date:
            where.append("E.HireDate >= %s")
            params.append(from_date)

        if to_date:
            where.append("E.HireDate <= %s")
            params.append(to_date)

        condition = " WHERE " + " AND ".join(where)

        # ==========================================================
        # KPI Queries
        # ==========================================================
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM Employees E
            LEFT JOIN Departments D ON E.DepartmentID = D.DepartmentID AND D.IsDeleted = 0
            LEFT JOIN Positions P ON E.PositionID = P.PositionID AND P.IsDeleted = 0
            {condition}
        """, tuple(params))
        total_employees = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Departments WHERE IsDeleted = 0")
        total_departments = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Positions WHERE IsDeleted = 0")
        total_positions = cursor.fetchone()[0]

        # Đã bỏ N'...' ở các chuỗi tiếng Việt
        cursor.execute(f"""
            SELECT COUNT(*) FROM Employees E 
            LEFT JOIN Departments D ON E.DepartmentID = D.DepartmentID AND D.IsDeleted = 0
            LEFT JOIN Positions P ON E.PositionID = P.PositionID AND P.IsDeleted = 0 
            {condition} AND E.Status = 'Đang làm'
        """, tuple(params))
        working_employees = cursor.fetchone()[0]

        cursor.execute(f"""
            SELECT COUNT(*) FROM Employees E 
            LEFT JOIN Departments D ON E.DepartmentID = D.DepartmentID AND D.IsDeleted = 0
            LEFT JOIN Positions P ON E.PositionID = P.PositionID AND P.IsDeleted = 0 
            {condition} AND E.Status = 'Nghỉ việc'
        """, tuple(params))
        quit_employees = cursor.fetchone()[0]

        cursor.execute(f"""
            SELECT COUNT(*) FROM Employees E 
            LEFT JOIN Departments D ON E.DepartmentID = D.DepartmentID AND D.IsDeleted = 0
            LEFT JOIN Positions P ON E.PositionID = P.PositionID AND P.IsDeleted = 0 
            {condition} AND E.Status = 'Thử việc'
        """, tuple(params))
        probation_employees = cursor.fetchone()[0]

        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM LeaveRequests L 
            INNER JOIN Employees E ON L.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            LEFT JOIN Departments D ON E.DepartmentID = D.DepartmentID AND D.IsDeleted = 0
            LEFT JOIN Positions P ON E.PositionID = P.PositionID AND P.IsDeleted = 0 
            {condition} AND L.IsDeleted = 0 AND L.Status = 'Chờ duyệt'
        """, tuple(params))
        pending_leave = cursor.fetchone()[0]

        # Đổi ISNULL -> COALESCE
        cursor.execute(f"""
            SELECT COALESCE(SUM(S.BaseSalary + S.Bonus + S.Allowance), 0) 
            FROM Salaries S 
            INNER JOIN Employees E ON S.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            LEFT JOIN Departments D ON E.DepartmentID = D.DepartmentID AND D.IsDeleted = 0
            LEFT JOIN Positions P ON E.PositionID = P.PositionID AND P.IsDeleted = 0 
            {condition} AND S.IsDeleted = 0
        """, tuple(params))
        total_salary = cursor.fetchone()[0]

        # Đổi GETDATE() + DATEADD -> CURRENT_DATE + INTERVAL '30 days'
        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM Contracts C 
            INNER JOIN Employees E ON C.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            LEFT JOIN Departments D ON E.DepartmentID = D.DepartmentID AND D.IsDeleted = 0
            LEFT JOIN Positions P ON E.PositionID = P.PositionID AND P.IsDeleted = 0 
            {condition} AND C.IsDeleted = 0 AND C.EndDate BETWEEN CURRENT_DATE AND (CURRENT_DATE + INTERVAL '30 days')
        """, tuple(params))
        expiring_contract = cursor.fetchone()[0]

        # Đổi MONTH()/YEAR() -> EXTRACT()
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM Employees E
            LEFT JOIN Departments D ON E.DepartmentID = D.DepartmentID AND D.IsDeleted = 0
            LEFT JOIN Positions P ON E.PositionID = P.PositionID AND P.IsDeleted = 0
            {condition} AND EXTRACT(MONTH FROM E.HireDate) = EXTRACT(MONTH FROM CURRENT_DATE) 
                        AND EXTRACT(YEAR FROM E.HireDate) = EXTRACT(YEAR FROM CURRENT_DATE)
        """, tuple(params))
        new_employee = cursor.fetchone()[0]

        # ==========================================================
        # Chart Data Processing
        # ==========================================================
        # Đổi SELECT TOP 5 -> LIMIT 5
        cursor.execute("""
            SELECT E.FullName, MAX(S.BaseSalary + S.Bonus + S.Allowance) AS TotalSalary
            FROM Employees E
            INNER JOIN Salaries S ON E.EmployeeID = S.EmployeeID AND S.IsDeleted = 0
            WHERE E.IsDeleted = 0
            GROUP BY E.FullName
            ORDER BY TotalSalary DESC
            LIMIT 5
        """)
        top_salaries_raw = cursor.fetchall()
        top_salaries = [{"FullName": row[0], "TotalSalary": float(row[1])} for row in top_salaries_raw]
        salary_names = [item["FullName"] for item in top_salaries]
        salary_values = [item["TotalSalary"] for item in top_salaries]

        cursor.execute("""
            SELECT D.DepartmentName, COUNT(E.EmployeeID) AS EmpCount
            FROM Departments D
            LEFT JOIN Employees E ON D.DepartmentID = E.DepartmentID AND E.IsDeleted = 0
            WHERE D.IsDeleted = 0
            GROUP BY D.DepartmentName
            ORDER BY EmpCount DESC
        """)
        department_report_raw = cursor.fetchall()
        department_report = [{"DepartmentName": row[0], "EmpCount": int(row[1])} for row in department_report_raw]
        department_names = [item["DepartmentName"] for item in department_report]
        department_counts = [item["EmpCount"] for item in department_report]

        cursor.execute("""
            SELECT L.Status, COUNT(*) AS StatusCount
            FROM LeaveRequests L
            WHERE L.IsDeleted = 0
            GROUP BY L.Status
            ORDER BY StatusCount DESC
        """)
        leave_report_raw = cursor.fetchall()
        leave_report = [{"Status": row[0], "StatusCount": int(row[1])} for row in leave_report_raw]
        leave_status = [item["Status"] for item in leave_report]
        leave_counts = [item["StatusCount"] for item in leave_report]

        return render_template(
            "report/reports.html",
            total_employees=total_employees,
            total_departments=total_departments,
            total_positions=total_positions,
            top_salaries=top_salaries,
            department_report=department_report,
            leave_report=leave_report,
            departments=departments,
            positions=positions,
            department=department,
            position=position,
            status=status,
            from_date=from_date,
            to_date=to_date, 
            working_employees=working_employees, 
            quit_employees=quit_employees, 
            probation_employees=probation_employees, 
            pending_leave=pending_leave,
            total_salary=total_salary, 
            expiring_contract=expiring_contract,
            new_employee=new_employee,
            salary_names=json.dumps(salary_names, ensure_ascii=False), 
            salary_values=json.dumps(salary_values),
            department_names=json.dumps(department_names, ensure_ascii=False),
            department_counts=json.dumps(department_counts),
            leave_status=json.dumps(leave_status, ensure_ascii=False),
            leave_counts=json.dumps(leave_counts)
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi hệ thống khi tải trang Báo cáo: {str(e)}")
        flash("Đã có lỗi xảy ra khi tổng hợp dữ liệu báo cáo!", "danger")
        return render_template(
            "report/reports.html",
            departments=departments,
            positions=positions,
            department=department,
            position=position,
            status=status,
            from_date=from_date,
            to_date=to_date,
            total_employees=0, total_departments=0, total_positions=0,
            working_employees=0, quit_employees=0, probation_employees=0,
            pending_leave=0, total_salary=0, expiring_contract=0, new_employee=0,
            top_salaries=[], department_report=[], leave_report=[],
            salary_names=json.dumps([]), salary_values=json.dumps([]),
            department_names=json.dumps([]), department_counts=json.dumps([]),
            leave_status=json.dumps([]), leave_counts=json.dumps([])
        )
    finally:
        conn.close()