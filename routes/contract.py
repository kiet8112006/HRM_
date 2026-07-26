from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    flash,
    Response, 
    url_for,
    send_from_directory,
    current_app
)
from utils.auth import *
from database import get_connection
from validators.contract_validator import *
from exceptions.validator.contract import ContractValidationError
from datetime import datetime
from io import StringIO
import csv
import os
import config
from utils.document_upload import (
    allowed_document,
    allowed_document_mimetype,
    verify_pdf,
    save_contract, 
    delete_contract_file
)
from routes.audit import log_activity 
from utils.notification_service import create_notification

contract_bp = Blueprint("contract", __name__)


# --- CÁC HÀM HỖ TRỢ LẤY DANH MỤC CÓ CACHE ---
def get_cached_active_employees():
    try:
        from app import cache
        @cache.cached(timeout=60, key_prefix='contract_employees_list')
        def query_db():
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT EmployeeID, FullName FROM Employees WHERE IsDeleted = 0 ORDER BY FullName")
                return cursor.fetchall()
            finally:
                conn.close()
        return query_db()
    except Exception:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT EmployeeID, FullName FROM Employees WHERE IsDeleted = 0 ORDER BY FullName")
            return cursor.fetchall()
        finally:
            conn.close()

def get_cached_departments():
    try:
        from app import cache
        @cache.cached(timeout=60, key_prefix='contract_departments_list')
        def query_db():
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT DepartmentID, DepartmentName FROM Departments WHERE IsDeleted = 0 ORDER BY DepartmentName")
                return cursor.fetchall()
            finally:
                conn.close()
        return query_db()
    except Exception:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT DepartmentID, DepartmentName FROM Departments WHERE IsDeleted = 0 ORDER BY DepartmentName")
            return cursor.fetchall()
        finally:
            conn.close()

def get_cached_positions():
    try:
        from app import cache
        @cache.cached(timeout=60, key_prefix='contract_positions_list')
        def query_db():
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT PositionID, PositionName FROM Positions WHERE IsDeleted = 0 ORDER BY PositionName")
                return cursor.fetchall()
            finally:
                conn.close()
        return query_db()
    except Exception:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT PositionID, PositionName FROM Positions WHERE IsDeleted = 0 ORDER BY PositionName")
            return cursor.fetchall()
        finally:
            conn.close()


# =====================================================================
# 1. ROUTE: DANH SÁCH HỢP ĐỒNG & PHÂN TRANG & TÌM KIẾM
# =====================================================================
@contract_bp.route("/contracts")
@login_required
@role_required('Admin', 'Manager')
def contracts():
    page = request.args.get("page", 1, type=int)
    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "")
    per_page = 10
    offset = (page - 1) * per_page

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # MSSQL: Dùng LIKE và ?
        cursor.execute(""" 
            SELECT COUNT(*) 
            FROM Contracts C
            LEFT JOIN Employees E ON C.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE C.IsDeleted = 0 
              AND (C.ContractCode LIKE ? OR E.FullName LIKE ?)
              AND C.Status LIKE ?
        """, (f"%{keyword}%", f"%{keyword}%", f"%{status}%"))
        total_records = cursor.fetchone()[0]

        # MSSQL: Phân trang bằng OFFSET ... ROWS FETCH NEXT ... ROWS ONLY
        cursor.execute("""
            SELECT
                C.ContractID, C.ContractCode, C.ContractNumber, E.FullName, C.ContractType,
                C.StartDate, C.EndDate, C.BasicSalary, D.DepartmentName, P.PositionName, C.Status, C.ContractFile
            FROM Contracts C
            LEFT JOIN Employees E ON C.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            LEFT JOIN Departments D ON C.DepartmentID = D.DepartmentID AND D.IsDeleted = 0
            LEFT JOIN Positions P ON C.PositionID = P.PositionID AND P.IsDeleted = 0
            WHERE C.IsDeleted = 0 
              AND (C.ContractCode LIKE ? OR E.FullName LIKE ?)
              AND C.Status LIKE ?
            ORDER BY C.ContractID DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, (f"%{keyword}%", f"%{keyword}%", f"%{status}%", offset, per_page))
        contracts_list = cursor.fetchall()

        total_pages = max(1, (total_records + per_page - 1) // per_page)
        return render_template("contract/contracts.html", contracts=contracts_list, page=page, total_pages=total_pages, keyword=keyword, status=status)
    except Exception as e:
        current_app.logger.error(f"Lỗi tải danh sách hợp đồng: {str(e)}")
        flash("Đã có lỗi xảy ra khi lấy danh sách hợp đồng!", "danger")
        return render_template("contract/contracts.html", contracts=[], page=1, total_pages=1, keyword=keyword, status=status)
    finally:
        conn.close()


# =====================================================================
# 2. ROUTE: THÊM MỚI HỢP ĐỒNG (ÁP DỤNG EXCEPTION HANDLING)
# =====================================================================
@contract_bp.route("/add_contract", methods=["GET", "POST"])
@login_required
@role_required('Admin')
def add_contract():
    if request.method == "POST":
        conn = get_connection()
        cursor = conn.cursor()
        try:
            employee_id = request.form.get("employee_id")
            contract_code = request.form.get("contract_code", "").strip()
            contract_number = request.form.get("contract_number", "").strip()
            contract_type = request.form.get("contract_type")
            start_date_str = request.form.get("start_date")
            end_date_str = request.form.get("end_date")
            work_location = normalize_work_location(request.form.get("work_location", ""))
            department_id = request.form.get("department_id")
            position_id = request.form.get("position_id")
            signer = normalize_signer(request.form.get("signer", ""))
            sign_date = request.form.get("sign_date")
            status = request.form.get("status")
            description = request.form.get("description", "").strip()

            # 1. Validations
            validate_contract_code(contract_code)
            validate_contract_number(contract_number)
            basic_salary = validate_basic_salary(request.form.get("basic_salary"))
            probation_months = validate_probation_months(request.form.get("probation_months"))
            validate_work_location(work_location)
            validate_signer(signer)
            validate_contract_description(description)
            start_date, end_date = validate_contract_dates(start_date_str, end_date_str)

            # 2. Upload file PDF xử lý an toàn
            file = request.files.get('contract_file')
            filename = None
            if file and file.filename != '':
                if not allowed_document(file.filename) or not allowed_document_mimetype(file) or not verify_pdf(file):
                    raise ContractValidationError('File hợp đồng không hợp lệ hoặc không phải định dạng PDF!')
                filename = save_contract(file)

            # 3. Kiểm tra trùng mã hợp đồng
            cursor.execute("SELECT COUNT(*) FROM Contracts WHERE ContractCode = ? AND IsDeleted = 0", (contract_code,))
            if cursor.fetchone()[0] > 0:
                raise ContractValidationError('Mã hợp đồng đã tồn tại!')

            # 4. Insert Database (Chuyển %s thành ?)
            cursor.execute("""
                INSERT INTO Contracts (
                    EmployeeID, ContractCode, ContractNumber, ContractType, StartDate, EndDate, 
                    BasicSalary, WorkLocation, DepartmentID, PositionID, Signer, SignDate, 
                    ProbationMonths, ContractFile, Description, Status, IsDeleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (employee_id, contract_code, contract_number, contract_type, start_date, end_date,
                  basic_salary, work_location, department_id, position_id, signer, sign_date,
                  probation_months, filename, description, status))
            
            cursor.execute("SELECT FullName FROM Employees WHERE EmployeeID = ?", (employee_id,))
            emp_row = cursor.fetchone()
            emp_name = emp_row[0] if emp_row else ""
            
            conn.commit()
            
            create_notification(
                title='Hợp đồng mới', 
                message=f'Hợp đồng {contract_code} của nhân viên {emp_name} đã được khởi tạo.',
                type='Success', receiver_role='Admin', url='/contracts'
            )
            log_activity(module="Contract", action="Create", description=f"Created contract {contract_code} for employee {emp_name}.")
            
            flash("Thêm hợp đồng thành công!", "success")
            return redirect(url_for("contract.contracts"))

        except ContractValidationError as e:
            flash(str(e), 'danger')
            return redirect(request.url)
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Lỗi thêm hợp đồng: {str(e)}")
            flash("Đã có lỗi hệ thống xảy ra. Vui lòng thử lại sau!", 'danger')
            return redirect(request.url)
        finally:
            conn.close()

    employees = get_cached_active_employees()
    departments = get_cached_departments()
    positions = get_cached_positions()
    return render_template("contract/add_contract.html", employees=employees, departments=departments, positions=positions)


# =====================================================================
# 3. ROUTE: CHỈNH SỬA HỢP ĐỒNG (ÁP DỤNG EXCEPTION HANDLING)
# =====================================================================
@contract_bp.route("/edit_contract/<int:id>", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Manager')
def edit_contract(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Contracts WHERE ContractID = ? AND IsDeleted = 0", (id,))
        contract = cursor.fetchone()
        if not contract:
            flash("Hợp đồng không tồn tại hoặc đã bị xóa!", "danger")
            return redirect(url_for("contract.contracts"))

        if request.method == "POST":
            employee_id = request.form.get("employee_id")
            contract_code = request.form.get("contract_code", "").strip()
            contract_number = request.form.get("contract_number", "").strip()
            contract_type = request.form.get("contract_type")
            start_date_str = request.form.get("start_date")
            end_date_str = request.form.get("end_date")
            work_location = normalize_work_location(request.form.get("work_location", ""))
            department_id = request.form.get("department_id")
            position_id = request.form.get("position_id")
            signer = normalize_signer(request.form.get("signer", ""))
            sign_date = request.form.get("sign_date")
            status = request.form.get("status")
            description = request.form.get("description", "").strip()

            # 1. Validations
            validate_contract_code(contract_code)
            validate_contract_number(contract_number)
            basic_salary = validate_basic_salary(request.form.get("basic_salary"))
            probation_months = validate_probation_months(request.form.get("probation_months"))
            validate_work_location(work_location)
            validate_signer(signer)
            validate_contract_description(description)
            start_date, end_date = validate_contract_dates(start_date_str, end_date_str)

            cursor.execute("SELECT COUNT(*) FROM Contracts WHERE ContractCode = ? AND ContractID <> ? AND IsDeleted = 0", (contract_code, id))
            if cursor.fetchone()[0] > 0:
                raise ContractValidationError('Mã hợp đồng đã tồn tại!')

            old_file = contract[14] if isinstance(contract, tuple) else getattr(contract, 'ContractFile', None)
            filename = old_file
            file = request.files.get('contract_file')
            if file and file.filename != '':
                if not allowed_document(file.filename) or not allowed_document_mimetype(file) or not verify_pdf(file):
                    raise ContractValidationError('File PDF hợp đồng không hợp lệ!')
                filename = save_contract(file)
                if old_file:
                    delete_contract_file(old_file)

            cursor.execute("""
                UPDATE Contracts SET 
                    EmployeeID = ?, ContractCode = ?, ContractNumber = ?, ContractType = ?, StartDate = ?, EndDate = ?, 
                    BasicSalary = ?, WorkLocation = ?, DepartmentID = ?, PositionID = ?, Signer = ?, SignDate = ?, 
                    ProbationMonths = ?, ContractFile = ?, Description = ?, Status = ?
                WHERE ContractID = ? AND IsDeleted = 0
            """, (employee_id, contract_code, contract_number, contract_type, start_date, end_date,
                  basic_salary, work_location, department_id, position_id, signer, sign_date,
                  probation_months, filename, description, status, id))
            
            cursor.execute("SELECT FullName FROM Employees WHERE EmployeeID = ?", (employee_id,))
            emp_row = cursor.fetchone()
            emp_name = emp_row[0] if emp_row else ""
            
            conn.commit()
            
            create_notification(
                title='Cập nhật hợp đồng', 
                message=f'Hợp đồng {contract_code} của nhân viên {emp_name} đã được chỉnh sửa.',
                type='Info', receiver_role='Admin', url='/contracts'
            )
            log_activity(module="Contract", action="Update", record_id=id, description=f"Updated contract {contract_code} for employee {emp_name}.")
            
            flash("Cập nhật hợp đồng thành công!", "success")
            return redirect(url_for("contract.contracts"))

    except ContractValidationError as e:
        flash(str(e), 'danger')
        return redirect(request.url)
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi cập nhật hợp đồng ID {id}: {str(e)}")
        flash("Đã có lỗi hệ thống xảy ra. Vui lòng thử lại sau!", 'danger')
        return redirect(request.url)
    finally:
        conn.close()

    # GET Request
    employees = get_cached_active_employees()
    departments = get_cached_departments()
    positions = get_cached_positions()
    return render_template("contract/edit_contract.html", contract=contract, employees=employees, departments=departments, positions=positions)


# =====================================================================
# 4. ROUTE: DOWNLOAD & PREVIEW HỢP ĐỒNG
# =====================================================================
@contract_bp.route("/download_contract/<int:id>")
@login_required
@role_required("Admin", "Manager")
def download_contract(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT ContractFile FROM Contracts WHERE ContractID = ? AND IsDeleted = 0", (id,))
        row = cursor.fetchone()
        contract_file = row[0] if row else None
        if not row or not contract_file:
            flash("Không tìm thấy file hợp đồng.", "danger")
            return redirect(url_for("contract.contracts"))

        filepath = os.path.join(config.CONTRACT_FOLDER, contract_file)
        if not os.path.exists(filepath):
            flash("File hợp đồng không tồn tại trên hệ thống.", "danger")
            return redirect(url_for("contract.contracts"))

        return send_from_directory(config.CONTRACT_FOLDER, contract_file, as_attachment=True)
    finally:
        conn.close()

@contract_bp.route("/preview_contract/<int:id>")
@login_required
@role_required("Admin", "Manager")
def preview_contract(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT ContractFile FROM Contracts WHERE ContractID = ? AND IsDeleted = 0", (id,))
        row = cursor.fetchone()
        contract_file = row[0] if row else None
        if not row or not contract_file:
            flash("Không tìm thấy file hợp đồng.", "danger")
            return redirect(url_for("contract.contracts"))

        filepath = os.path.join(config.CONTRACT_FOLDER, contract_file)
        if not os.path.exists(filepath):
            flash("File hợp đồng không tồn tại trên hệ thống.", "danger")
            return redirect(url_for("contract.contracts"))

        return send_from_directory(config.CONTRACT_FOLDER, contract_file, as_attachment=False)
    finally:
        conn.close()


# =====================================================================
# 5. ROUTE: XÓA ĐƠN LẺ HỢP ĐỒNG (XÓA MỀM)
# =====================================================================
@contract_bp.route("/delete_contract/<int:id>")
@login_required
@role_required('Admin')
def delete_contract(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT C.ContractCode, E.FullName FROM Contracts C
            LEFT JOIN Employees E ON C.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE C.ContractID = ? AND C.IsDeleted = 0
        """, (id,))
        row = cursor.fetchone()
        
        if not row:
            flash("Hợp đồng không tồn tại hoặc đã bị xóa trước đó!", "danger")
            return redirect(url_for("contract.contracts"))
            
        contract_code, emp_name = row[0], row[1]

        cursor.execute("UPDATE Contracts SET IsDeleted = 1 WHERE ContractID = ?", (id,))
        conn.commit()

        create_notification(
            title='Xóa hợp đồng',
            message=f'Hợp đồng {contract_code} của {emp_name} đã bị xóa.',
            type='Warning', receiver_role='Admin', url='/contracts'
        )
        log_activity(module="Contract", action="Delete", record_id=id, description=f"Soft deleted contract {contract_code} of {emp_name}.")

        flash("Xóa hợp đồng thành công (Xóa mềm)!", "success")
        return redirect(url_for("contract.contracts"))
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi xóa hợp đồng ID {id}: {str(e)}")
        flash("Có lỗi hệ thống xảy ra khi xóa hợp đồng!", "danger")
        return redirect(url_for("contract.contracts"))
    finally:
        conn.close()


# =====================================================================
# 6. ROUTE: XÓA HÀNG LOẠT HỢP ĐỒNG
# =====================================================================
@contract_bp.route("/delete_selected_contracts", methods=["POST"])
@login_required
@role_required('Admin')
def delete_selected_contracts():
    contract_ids = request.form.getlist("contract_ids")
    if not contract_ids:
        flash("Vui lòng chọn ít nhất một hợp đồng để xóa!", "warning")
        return redirect(url_for("contract.contracts"))

    conn = get_connection()
    cursor = conn.cursor()
    try:
        placeholders = ', '.join(['?'] * len(contract_ids))
        
        query_info = f"""
            SELECT C.ContractCode, E.FullName FROM Contracts C
            LEFT JOIN Employees E ON C.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE C.ContractID IN ({placeholders}) AND C.IsDeleted = 0
        """
        cursor.execute(query_info, tuple(contract_ids))
        records = cursor.fetchall()

        if records:
            query_delete = f"UPDATE Contracts SET IsDeleted = 1 WHERE ContractID IN ({placeholders})"
            cursor.execute(query_delete, tuple(contract_ids))
            
            for row in records:
                log_activity(module="Contract", action="Delete", description=f"Soft deleted contract {row[0]} of {row[1]}.")

            conn.commit()
            flash(f"Đã xóa thành công {len(records)} hợp đồng được chọn!", "success")
        else:
            flash("Không tìm thấy hợp đồng hợp lệ để xóa!", "warning")

    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi xóa hàng loạt hợp đồng: {str(e)}")
        flash("Có lỗi hệ thống xảy ra khi xóa hàng loạt!", "danger")
    finally:
        conn.close()

    return redirect(url_for("contract.contracts"))


# =====================================================================
# 7. ROUTE: XUẤT FILE CSV DANH SÁCH HỢP ĐỒNG
# =====================================================================
@contract_bp.route("/export_contracts_csv")
@login_required
@role_required('Admin')
def export_contracts_csv():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                C.ContractCode, C.ContractNumber, E.FullName, C.ContractType,
                C.StartDate, C.EndDate, C.BasicSalary, D.DepartmentName, P.PositionName, C.Status
            FROM Contracts C
            LEFT JOIN Employees E ON C.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            LEFT JOIN Departments D ON C.DepartmentID = D.DepartmentID AND D.IsDeleted = 0
            LEFT JOIN Positions P ON C.PositionID = P.PositionID AND P.IsDeleted = 0
            WHERE C.IsDeleted = 0 
            ORDER BY C.ContractID DESC
        """)
        rows = cursor.fetchall()

        output = StringIO()
        output.write("\ufeff")
        writer = csv.writer(output)

        writer.writerow([
            "Mã hợp đồng", "Số hợp đồng", "Nhân viên", "Loại hợp đồng", 
            "Ngày bắt đầu", "Ngày kết thúc", "Lương cơ bản", "Phòng ban", "Chức vụ", "Trạng thái"
        ])

        for row in rows:
            if isinstance(row, tuple):
                writer.writerow(list(row))
            else:
                writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9]])

        log_activity(module="Contract", action="Export", description=f"Exported contract list ({len(rows)} records).")

        return Response(
            output.getvalue().encode("utf-8-sig"),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=contracts_report.csv"}
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi xuất file CSV hợp đồng: {str(e)}")
        flash("Không thể xuất file CSV do lỗi hệ thống!", "danger")
        return redirect(url_for("contract.contracts"))
    finally:
        conn.close()