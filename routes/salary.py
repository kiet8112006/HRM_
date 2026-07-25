from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    flash,
    Response,
    current_app
)
from utils.auth import *
from database import get_connection
from validators.salary_validator import *
from exceptions.validator.salary import SalaryValidationError
from datetime import datetime
from io import StringIO
import csv
from routes.audit import log_activity 
from utils.notification_service import create_notification

salary_bp = Blueprint("salary", __name__)

# --- HÀM HỖ TRỢ LẤY DANH SÁCH NHÂN VIÊN CÓ CACHE ---
def get_cached_active_employees():
    from app import cache
    @cache.cached(timeout=60, key_prefix='salary_employees_list_cache')
    def query_db():
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT EmployeeID, FullName FROM Employees WHERE IsDeleted = 0 ORDER BY FullName")
            data = cursor.fetchall()
            return data
        finally:
            conn.close()
    return query_db()


# =====================================================================
# 1. ROUTE: DANH SÁCH BẢNG LƯƠNG (PHÂN TRANG & TÌM KIẾM)
# =====================================================================
@salary_bp.route("/salaries")
@login_required
@role_required('Admin')
def salaries():
    page = request.args.get("page", 1, type=int) 
    keyword = request.args.get("keyword", "").strip() 
    month = request.args.get("month", "") 
    year = request.args.get("year", "") 

    per_page = 10 
    offset = (page - 1) * per_page 

    conn = get_connection() 
    cursor = conn.cursor() 
    try:
        cursor.execute(""" 
            SELECT COUNT(*) 
            FROM Salaries S 
            INNER JOIN Employees E ON S.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE S.IsDeleted = 0 
              AND E.FullName LIKE ? 
              AND CAST(S.Month AS VARCHAR) LIKE ? 
              AND CAST(S.Year AS VARCHAR) LIKE ?
        """, (f"%{keyword}%", f"%{month}%", f"%{year}%"))
        total_records = cursor.fetchone()[0]

        total_pages = max(1, (total_records + per_page - 1) // per_page)

        cursor.execute("""
            SELECT S.SalaryID, S.SalaryCode, E.FullName as Fullname, S.BaseSalary, S.Bonus, S.Allowance, 
                   S.OvertimePay, S.Deduction, S.Tax, S.Insurance, S.NetSalary,
                   S.Month, S.Year, S.PaymentDate, S.Status
            FROM Salaries S 
            INNER JOIN Employees E ON S.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE S.IsDeleted = 0 
              AND E.FullName LIKE ? 
              AND CAST(S.Month AS VARCHAR) LIKE ? 
              AND CAST(S.Year AS VARCHAR) LIKE ?
            ORDER BY S.Year DESC, S.Month DESC, S.SalaryID DESC 
            OFFSET ? ROWS 
            FETCH NEXT ? ROWS ONLY 
        """, (f"%{keyword}%", f"%{month}%", f"%{year}%", offset, per_page))
        salaries_list = cursor.fetchall() 

        return render_template(
            "salary/salaries.html",
            salaries=salaries_list,
            page=page, 
            total_pages=total_pages, 
            keyword=keyword, 
            month=month, 
            year=year
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi khi lấy danh sách bảng lương: {str(e)}")
        flash("Có lỗi hệ thống xảy ra khi tải danh sách bảng lương!", "danger")
        return render_template("salary/salaries.html", salaries=[], page=1, total_pages=1)
    finally:
        conn.close()


# =====================================================================
# 2. ROUTE: THÊM MỚI BẢNG LƯƠNG
# =====================================================================
@salary_bp.route("/add_salary", methods=["GET", "POST"])
@login_required
@role_required('Admin')
def add_salary():
    if request.method == "POST":
        conn = get_connection() 
        cursor = conn.cursor() 
        try:
            employee_id = request.form.get("employee_id")
            
            cursor.execute("SELECT FullName FROM Employees WHERE EmployeeID = ? AND IsDeleted = 0", employee_id)
            emp_row = cursor.fetchone()
            if not emp_row:
                raise SalaryValidationError('Nhân viên không tồn tại hoặc đã bị xóa!')
            emp_name = emp_row[0]

            base_salary = float(request.form.get("base_salary", 0))
            bonus = float(request.form.get("bonus", 0))
            allowance = float(request.form.get("allowance", 0))
            overtime_pay = float(request.form.get('overtime_pay', 0))
            deduction = float(request.form.get('deduction', 0))
            tax = float(request.form.get('tax', 0))
            insurance = float(request.form.get('insurance', 0))

            net_salary = validate_salary_components(base_salary, bonus, allowance, overtime_pay, deduction, tax, insurance)

            month = int(request.form.get("month", 0))
            year = int(request.form.get("year", 0))
            validate_month_year(month, year)

            payment_date = datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d').date()
            validate_payment_date(payment_date)

            status = request.form.get('status')
            validate_salary_status(status)

            cursor.execute("""
                SELECT COUNT(*) FROM Salaries 
                WHERE EmployeeID = ? AND Month = ? AND Year = ? AND IsDeleted = 0
            """, employee_id, month, year)
            if cursor.fetchone()[0] > 0:
                raise SalaryValidationError('Nhân viên đã có bảng lương trong tháng này!')

            cursor.execute("SELECT ISNULL(MAX(SalaryID), 0) + 1 FROM Salaries")
            next_id = cursor.fetchone()[0]
            salary_code = f"SAL{next_id:04d}"

            cursor.execute("""
                INSERT INTO Salaries
                (SalaryCode, EmployeeID, BaseSalary, Bonus, Allowance, OvertimePay, Deduction, Tax, Insurance, NetSalary, Month, Year, PaymentDate, Status, IsDeleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, salary_code, employee_id, base_salary, bonus, allowance, overtime_pay, deduction, tax, insurance, net_salary, month, year, payment_date, status)

            conn.commit() 

            create_notification(
                title='Bảng lương mới',
                message=f'Đã khởi tạo bảng lương tháng {month}/{year} cho nhân viên {emp_name}.',
                type='Success',
                receiver_role='Admin',
                url='/salaries'
            )

            log_activity(
                module="Salary",
                action="Create",
                description=f"Created salary record for employee {emp_name} ({month}/{year})."
            )

            flash("Thêm bảng lương thành công!", "success")
            return redirect("/salaries")

        except SalaryValidationError as e:
            flash(str(e), 'danger')
            return redirect(request.url)
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Lỗi khi thêm bảng lương: {str(e)}")
            flash("Đã có lỗi hệ thống xảy ra. Vui lòng thử lại sau!", "danger")
            return redirect(request.url)
        finally:
            conn.close()

    # GET Request
    employees = get_cached_active_employees()
    return render_template("salary/add_salary.html", employees=employees, today=datetime.today().strftime('%Y-%m-%d'))


# =====================================================================
# 3. ROUTE: CHỈNH SỬA BẢNG LƯƠNG
# =====================================================================
@salary_bp.route("/edit_salary/<int:id>", methods=["GET", "POST"])
@login_required
@role_required('Admin')
def edit_salary(id):
    conn = get_connection() 
    cursor = conn.cursor() 
    try:
        cursor.execute("SELECT * FROM Salaries WHERE SalaryID = ? AND IsDeleted = 0", id)
        salary = cursor.fetchone()

        if not salary:
            flash('Bảng lương không tồn tại hoặc đã bị xóa trước đó!', 'danger')
            return redirect("/salaries")

        if request.method == "POST":
            employee_id = request.form.get("employee_id")
            cursor.execute("SELECT FullName FROM Employees WHERE EmployeeID = ? AND IsDeleted = 0", employee_id)
            emp_row = cursor.fetchone()
            if not emp_row:
                raise SalaryValidationError('Nhân viên không tồn tại hoặc đã bị xóa!')
            emp_name = emp_row[0]

            base_salary = float(request.form.get("base_salary", 0))
            bonus = float(request.form.get("bonus", 0))
            allowance = float(request.form.get("allowance", 0))
            overtime_pay = float(request.form.get('overtime_pay', 0))
            deduction = float(request.form.get('deduction', 0))
            tax = float(request.form.get('tax', 0))
            insurance = float(request.form.get('insurance', 0))

            net_salary = validate_salary_components(base_salary, bonus, allowance, overtime_pay, deduction, tax, insurance)

            month = int(request.form.get("month", 0))
            year = int(request.form.get("year", 0))
            validate_month_year(month, year)

            payment_date = datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d').date()
            validate_payment_date(payment_date)

            status = request.form.get('status')
            validate_salary_status(status)

            cursor.execute("""
                SELECT COUNT(*) FROM Salaries 
                WHERE EmployeeID = ? AND Month = ? AND Year = ? AND SalaryID <> ? AND IsDeleted = 0
            """, employee_id, month, year, id)
            if cursor.fetchone()[0] > 0:
                raise SalaryValidationError('Nhân viên đã có bảng lương trong tháng này!')

            cursor.execute("""
                UPDATE Salaries
                SET EmployeeID = ?, BaseSalary = ?, Bonus = ?, Allowance = ?, OvertimePay = ?, Deduction = ?, Tax = ?, Insurance = ?, NetSalary = ?, 
                    Month = ?, Year = ?, PaymentDate = ?, Status = ?
                WHERE SalaryID = ?
            """, employee_id, base_salary, bonus, allowance, overtime_pay, deduction, tax, insurance, net_salary, month, year, payment_date, status, id)

            conn.commit() 

            create_notification(
                title='Cập nhật bảng lương',
                message=f'Bảng lương tháng {month}/{year} của nhân viên {emp_name} đã được cập nhật.',
                type='Info',
                receiver_role='Admin',
                url='/salaries'
            )

            log_activity(
                module="Salary",
                action="Update",
                record_id=id,
                description=f"Updated salary record for employee {emp_name} ({month}/{year})."
            )

            flash("Cập nhật bảng lương thành công!", "success")
            return redirect("/salaries")

    except SalaryValidationError as e:
        flash(str(e), 'danger')
        return redirect(request.url)
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi khi cập nhật bảng lương ID {id}: {str(e)}")
        flash("Đã có lỗi hệ thống xảy ra. Vui lòng thử lại sau!", "danger")
        return redirect(request.url)
    finally:
        conn.close()

    # GET Request
    employees = get_cached_active_employees()
    return render_template("salary/edit_salary.html", salary=salary, employees=employees)


# =====================================================================
# 4. ROUTE: XÓA ĐƠN LẺ BẢNG LƯƠNG (XÓA MỀM)
# =====================================================================
@salary_bp.route("/delete_salary/<int:id>")
@login_required
@role_required('Admin')
def delete_salary(id):
    conn = get_connection() 
    cursor = conn.cursor() 
    try:
        cursor.execute("""
            SELECT E.FullName, S.Month, S.Year 
            FROM Salaries S 
            INNER JOIN Employees E ON S.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE S.SalaryID = ? AND S.IsDeleted = 0
        """, id)
        salary_row = cursor.fetchone()
        
        if not salary_row:
            flash("Bảng lương không tồn tại hoặc đã bị xóa trước đó!", "danger")
            return redirect("/salaries")

        info_str = f"của nhân viên {salary_row[0]} ({salary_row[1]}/{salary_row[2]})"
        log_info_str = f"of employee {salary_row[0]} ({salary_row[1]}/{salary_row[2]})"

        cursor.execute("UPDATE Salaries SET IsDeleted = 1 WHERE SalaryID = ?", id)
        conn.commit()

        create_notification(
            title='Xóa bảng lương',
            message=f'Bảng lương {info_str} đã bị xóa khỏi hệ thống.',
            type='Warning',
            receiver_role='Admin',
            url='/salaries'
        )

        log_activity(
            module="Salary",
            action="Delete",
            record_id=id,
            description=f"Soft deleted salary record {log_info_str}."
        )

        flash("Xóa bảng lương thành công (Xóa mềm)!", "success")
        return redirect("/salaries")
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi khi xóa bảng lương ID {id}: {str(e)}")
        flash("Có lỗi hệ thống xảy ra khi xóa bảng lương!", "danger")
        return redirect("/salaries")
    finally:
        conn.close()


# =====================================================================
# 5. ROUTE: XÓA HÀNG LOẠT BẢNG LƯƠNG
# =====================================================================
@salary_bp.route("/delete_selected_salaries", methods=["POST"])
@login_required
@role_required('Admin')
def delete_selected_salaries():
    salary_ids = request.form.getlist("salary_ids")

    if not salary_ids:
        flash("Vui lòng chọn ít nhất một bảng lương!", "warning")
        return redirect("/salaries")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        placeholders = ', '.join(['?'] * len(salary_ids))
        
        query_info = f"""
            SELECT S.SalaryID, E.FullName, S.Month, S.Year 
            FROM Salaries S 
            INNER JOIN Employees E ON S.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE S.SalaryID IN ({placeholders}) AND S.IsDeleted = 0
        """
        cursor.execute(query_info, tuple(salary_ids))
        records = cursor.fetchall()
        deleted_count = len(records)

        if deleted_count > 0:
            query_delete = f"UPDATE Salaries SET IsDeleted = 1 WHERE SalaryID IN ({placeholders})"
            cursor.execute(query_delete, tuple(salary_ids))
            
            for row in records:
                log_activity(
                    module="Salary",
                    action="Delete",
                    record_id=int(row[0]),
                    description=f"Soft deleted salary record of employee {row[1]} ({row[2]}/{row[3]})."
                )

            conn.commit()

            create_notification(
                title='Xóa nhiều bảng lương',
                message=f'Đã xóa thành công {deleted_count} bảng lương được chọn (Xóa mềm).',
                type='Warning',
                receiver_role='Admin',
                url='/salaries'
            )
            flash(f"Đã xóa thành công {deleted_count} bảng lương được chọn (Xóa mềm)!", "success")
        else:
            flash("Không tìm thấy bảng lương hợp lệ nào để tiến hành xóa!", "warning")

    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi khi xóa nhiều bảng lương: {str(e)}")
        flash("Có lỗi hệ thống xảy ra khi xóa hàng loạt!", "danger")
    finally:
        conn.close()

    return redirect("/salaries")


# =====================================================================
# 6. ROUTE: XUẤT FILE CSV DANH SÁCH BẢNG LƯƠNG
# =====================================================================
@salary_bp.route("/export_salaries_csv")
@login_required
@role_required('Admin')
def export_salaries_csv():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                S.SalaryID, S.SalaryCode, E.FullName, S.BaseSalary, S.Bonus, S.Allowance, S.OvertimePay, S.Deduction, S.Tax, S.Insurance,
                (S.BaseSalary + S.Bonus + S.Allowance + S.OvertimePay - S.Deduction - S.Tax - S.Insurance) AS NetSalary,
                S.Month, S.Year, S.PaymentDate, S.Status
            FROM Salaries S
            INNER JOIN Employees E ON S.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE S.IsDeleted = 0
            ORDER BY S.Year DESC, S.Month DESC, S.SalaryID DESC
        """)
        rows = cursor.fetchall()

        output = StringIO()
        output.write("\ufeff")
        writer = csv.writer(output)

        writer.writerow([
            "SalaryID", "SalaryCode", "Employee", "BaseSalary", "Bonus", "Allowance",
            "OvertimePay", "Deduction", "Tax", "Insurance", "NetSalary", "Month", "Year", "PaymentDate", "Status"
        ])

        for row in rows:
            writer.writerow([
                row.SalaryID, row.SalaryCode, row.FullName, row.BaseSalary, row.Bonus, row.Allowance,
                row.OvertimePay, row.Deduction, row.Tax, row.Insurance, row.NetSalary, row.Month, row.Year, row.PaymentDate, row.Status
            ])

        log_activity(
            module="Salary",
            action="Export",
            description=f"Exported salary list ({len(rows)} records)."
        )

        return Response(
            output.getvalue().encode("utf-8-sig"),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=salaries.csv"}
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi khi xuất file CSV bảng lương: {str(e)}")
        flash("Không thể xuất file CSV do lỗi hệ thống!", "danger")
        return redirect("/salaries")
    finally:
        conn.close()