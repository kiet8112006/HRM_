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
from validators.department_validator import *
from exceptions.validator.department import DepartmentValidationError
from io import StringIO
import csv
from routes.audit import log_activity 
from utils.notification_service import create_notification

department_bp = Blueprint("department", __name__)


# --- HÀM HỖ TRỢ LẤY DANH SÁCH NHÂN VIÊN CÓ CACHE ---
def get_cached_active_employees():
    try:
        from app import cache
        @cache.cached(timeout=60, key_prefix='department_employees_list')
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
    except Exception:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT EmployeeID, FullName FROM Employees WHERE IsDeleted = 0 ORDER BY FullName")
            return cursor.fetchall()
        finally:
            conn.close()


# =====================================================================
# 1. ROUTE: DANH SÁCH PHÒNG BAN & PHÂN TRANG & TÌM KIẾM
# =====================================================================
@department_bp.route("/departments")
@login_required
@role_required('Admin')
def departments():
    keyword = request.args.get("keyword", "").strip() 
    page = request.args.get("page", 1, type=int)     
    per_page = 10                                    
    offset = (page - 1) * per_page 
    
    conn = get_connection() 
    cursor = conn.cursor()   
    try:
        # Cú pháp tìm kiếm không phân biệt hoa thường (ILIKE) & Placeholder %s
        cursor.execute(""" SELECT COUNT(*) FROM Departments WHERE IsDeleted = 0 AND DepartmentName ILIKE %s """, (f"%{keyword}%",))
        total_records = cursor.fetchone()[0]

        # Cú pháp phân trang PostgreSQL: LIMIT %s OFFSET %s
        cursor.execute("""
            SELECT D.DepartmentID,
                   D.DepartmentCode, 
                   D.DepartmentName,
                   D.Description, 
                   D.Location, 
                   E.FullName as Managername 
            FROM Departments D 
            LEFT JOIN Employees E ON D.ManagerID = E.EmployeeID AND E.IsDeleted = 0
            WHERE D.IsDeleted = 0 AND D.DepartmentName ILIKE %s 
            ORDER BY D.DepartmentID 
            LIMIT %s OFFSET %s
        """, (f"%{keyword}%", per_page, offset))
        departments_list = cursor.fetchall()

        total_pages = (total_records + per_page - 1) // per_page

        return render_template(
            "department/departments.html",
            departments=departments_list, 
            page=page, 
            total_pages=total_pages, 
            keyword=keyword
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi tải danh sách phòng ban: {str(e)}")
        flash("Đã có lỗi xảy ra khi lấy danh sách phòng ban!", "danger")
        return render_template("department/departments.html", departments=[], page=1, total_pages=1, keyword=keyword)
    finally:
        conn.close()


# =====================================================================
# 2. ROUTE: THÊM MỚI PHÒNG BAN
# =====================================================================
@department_bp.route("/add_department", methods=["GET", "POST"])
@login_required
@role_required('Admin')
def add_department():
    if request.method == "POST":
        conn = get_connection() 
        cursor = conn.cursor() 
        try:
            # 1. Chuẩn hóa & Validate dữ liệu
            department_code = normalize_department_code(request.form.get('department_code'))
            validate_department_code(department_code)

            cursor.execute("SELECT COUNT(*) FROM Departments WHERE DepartmentCode = %s AND IsDeleted = 0", (department_code,))
            if cursor.fetchone()[0] > 0:
                raise DepartmentValidationError('Mã phòng ban đã tồn tại!')
                
            department_name = normalize_department_name(request.form.get("department_name"))
            validate_department_name(department_name)
                
            cursor.execute("SELECT COUNT(*) FROM Departments WHERE DepartmentName = %s AND IsDeleted = 0", (department_name,))
            if cursor.fetchone()[0] > 0:
                raise DepartmentValidationError('Tên phòng ban đã tồn tại!')

            description = request.form.get('description', '').strip()
            validate_description(description)
                
            location = request.form.get('location', '').strip()
            validate_location(location)
                
            status = request.form.get('status')
            validate_status(status)
                
            manager_id = request.form.get("manager_id") or None
                
            if manager_id is not None:
                cursor.execute('SELECT COUNT(*) FROM Employees WHERE EmployeeID = %s AND IsDeleted = 0', (manager_id,))
                if cursor.fetchone()[0] == 0:
                    raise DepartmentValidationError('Trưởng phòng không tồn tại hoặc đã bị xóa!')
                    
            # 2. Chèn vào Database (Sửa ? thành %s)
            cursor.execute("""
                INSERT INTO Departments (DepartmentCode, DepartmentName, Description, Location, ManagerID, Status, IsDeleted)
                VALUES (%s, %s, %s, %s, %s, %s, 0)
            """, (department_code, department_name, description, location, manager_id, status))
            
            conn.commit() 

            create_notification(
                title='Phòng ban mới',
                message=f'Phòng ban {department_name} ({department_code}) đã được thêm vào hệ thống.',
                type='Success',
                receiver_role='Admin',
                url='/departments'
            )

            log_activity(
                module="Department",
                action="Create",
                description=f"Created department {department_name}."
            )

            flash("Thêm phòng ban thành công!", "success")
            return redirect("/departments")

        except DepartmentValidationError as e:
            flash(str(e), 'danger')
            return redirect(request.url)
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Lỗi thêm phòng ban: {str(e)}")
            flash("Đã có lỗi hệ thống xảy ra. Vui lòng thử lại sau!", 'danger')
            return redirect(request.url)
        finally:
            conn.close()  

    employees = get_cached_active_employees()
    return render_template("department/add_department.html", employees=employees)


# =====================================================================
# 3. ROUTE: CHỈNH SỬA THÔNG TIN PHÒNG BAN
# =====================================================================
@department_bp.route("/edit_department/<int:id>", methods=["GET", "POST"])
@login_required
@role_required('Admin')
def edit_department(id):
    conn = get_connection() 
    cursor = conn.cursor() 

    try:
        cursor.execute("SELECT COUNT(*) FROM Departments WHERE DepartmentID = %s AND IsDeleted = 0", (id,))
        if cursor.fetchone()[0] == 0:
            flash('Phòng ban không tồn tại hoặc đã bị xóa!', 'danger')
            return redirect("/departments")

        if request.method == "POST":
            department_code = normalize_department_code(request.form.get('department_code'))
            validate_department_code(department_code)
                
            cursor.execute("""
                SELECT COUNT(*) FROM Departments WHERE DepartmentCode = %s AND DepartmentID <> %s AND IsDeleted = 0
            """, (department_code, id))
            if cursor.fetchone()[0] > 0:
                raise DepartmentValidationError('Mã phòng ban đã tồn tại!')
                
            department_name = normalize_department_name(request.form.get("department_name"))
            validate_department_name(department_name)
                
            cursor.execute(""" SELECT COUNT(*) FROM Departments WHERE DepartmentName = %s AND DepartmentID <> %s AND IsDeleted = 0 """, (department_name, id))
            if cursor.fetchone()[0] > 0:
                raise DepartmentValidationError('Tên phòng ban đã tồn tại!')

            description = request.form.get('description', '').strip()
            validate_description(description)
                
            location = request.form.get('location', '').strip()
            validate_location(location)
                
            status = request.form.get('status')
            validate_status(status)
                
            manager_id = request.form.get("manager_id") or None
                
            if manager_id is not None:
                cursor.execute('SELECT COUNT(*) FROM Employees WHERE EmployeeID = %s AND IsDeleted = 0', (manager_id,))
                if cursor.fetchone()[0] == 0:
                    raise DepartmentValidationError('Trưởng phòng không tồn tại hoặc đã bị xóa!')

            cursor.execute("""
                UPDATE Departments
                SET DepartmentCode = %s, DepartmentName = %s, Description = %s, Location = %s, ManagerID = %s, Status = %s
                WHERE DepartmentID = %s 
            """, (department_code, department_name, description, location, manager_id, status, id))
            
            conn.commit()

            create_notification(
                title='Cập nhật phòng ban',
                message=f'Phòng ban {department_name} đã được cập nhật thông tin.',
                type='Info',
                receiver_role='Admin',
                url='/departments'
            )

            log_activity(
                module="Department",
                action="Update",
                record_id=id,
                description=f"Updated department {department_name}."
            )

            flash("Cập nhật phòng ban thành công!", "success")
            return redirect("/departments")

    except DepartmentValidationError as e:
        flash(str(e), 'danger')
        return redirect(request.url)
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi cập nhật phòng ban ID {id}: {str(e)}")
        flash("Đã có lỗi hệ thống xảy ra. Vui lòng thử lại sau!", 'danger')
        return redirect(request.url)
    finally:
        conn.close()

    # GET Request
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(""" SELECT * FROM Departments WHERE DepartmentID = %s AND IsDeleted = 0 """, (id,))
        department = cursor.fetchone()
        employees = get_cached_active_employees()
        return render_template("department/edit_department.html", department=department, employees=employees)
    finally:
        conn.close()


# =====================================================================
# 4. ROUTE: XÓA ĐƠN LẺ PHÒNG BAN (XÓA MỀM)
# =====================================================================
@department_bp.route("/delete_department/<int:id>")
@login_required
@role_required('Admin')
def delete_department(id):
    conn = get_connection() 
    cursor = conn.cursor() 
    try:
        cursor.execute(""" SELECT DepartmentName FROM Departments WHERE DepartmentID = %s AND IsDeleted = 0 """, (id,))
        department_row = cursor.fetchone()
        if not department_row:
            flash("Phòng ban không tồn tại hoặc đã bị xóa trước đó!", "danger")
            return redirect("/departments")
            
        department_name = department_row[0]

        cursor.execute(""" SELECT COUNT(*) FROM Employees WHERE DepartmentID = %s AND IsDeleted = 0 """, (id,))
        if cursor.fetchone()[0] > 0:
            flash("Không thể xóa phòng ban vì vẫn còn nhân viên đang làm việc thuộc phòng ban này!", "danger")
            return redirect("/departments")
            
        cursor.execute(""" UPDATE Departments SET IsDeleted = 1 WHERE DepartmentID = %s """, (id,))
        conn.commit()

        create_notification(
            title='Xóa phòng ban',
            message=f'Phòng ban {department_name} đã bị xóa khỏi hệ thống.',
            type='Warning',
            receiver_role='Admin',
            url='/departments'
        )

        log_activity(
            module="Department",
            action="Delete",
            record_id=id,
            description=f"Soft deleted department {department_name}."
        )

        flash("Xóa phòng ban thành công (Xóa mềm)!", "success")
        return redirect("/departments")
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi xóa phòng ban ID {id}: {str(e)}")
        flash("Có lỗi hệ thống xảy ra khi xóa phòng ban!", "danger")
        return redirect("/departments")
    finally:
        conn.close()


# =====================================================================
# 5. ROUTE: XÓA HÀNG LOẠT PHÒNG BAN
# =====================================================================
@department_bp.route("/delete_selected_departments", methods=["POST"])
@login_required
@role_required('Admin')
def delete_selected_departments():
    department_ids = request.form.getlist("department_ids")

    if not department_ids:
        flash("Vui lòng chọn ít nhất một phòng ban!", "warning")
        return redirect("/departments")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        valid_delete_ids = []
        failed_count = 0

        for department_id in department_ids:
            cursor.execute('SELECT COUNT(*) FROM Employees WHERE DepartmentID = %s AND IsDeleted = 0', (department_id,))
            if cursor.fetchone()[0] > 0:
                failed_count += 1
            else:
                valid_delete_ids.append(department_id)

        if len(valid_delete_ids) > 0:
            placeholders = ', '.join(['%s'] * len(valid_delete_ids))
            
            query_info = f"SELECT DepartmentID, DepartmentName FROM Departments WHERE DepartmentID IN ({placeholders}) AND IsDeleted = 0"
            cursor.execute(query_info, tuple(valid_delete_ids))
            records = cursor.fetchall()
            deleted_count = len(records)

            if deleted_count > 0:
                query_delete = f"UPDATE Departments SET IsDeleted = 1 WHERE DepartmentID IN ({placeholders})"
                cursor.execute(query_delete, tuple(valid_delete_ids))

                for row in records:
                    dept_id = row[0] if isinstance(row, tuple) else row.DepartmentID
                    dept_name = row[1] if isinstance(row, tuple) else row.DepartmentName
                    log_activity(
                        module="Department",
                        action="Delete",
                        record_id=int(dept_id),
                        description=f"Soft deleted department {dept_name}."
                    )

                conn.commit()

                create_notification(
                    title='Xóa nhiều phòng ban',
                    message=f'Đã xóa thành công {deleted_count} phòng ban được chọn (Xóa mềm).',
                    type='Warning',
                    receiver_role='Admin',
                    url='/departments'
                )
                
                if failed_count > 0:
                    flash(f'Đã xóa thành công {deleted_count} phòng ban. Không thể xóa {failed_count} phòng ban do còn nhân viên!', 'warning')
                else:
                    flash(f'Đã xóa thành công {deleted_count} phòng ban được chọn!', 'success')
            else:
                flash("Không tìm thấy phòng ban hợp lệ nào để xóa!", "warning")
        else:
            flash(f"Không thể xóa do toàn bộ {failed_count} phòng ban đã chọn đều đang chứa nhân viên!", "danger")

    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi xóa nhiều phòng ban: {str(e)}")
        flash("Có lỗi hệ thống xảy ra khi thực hiện xóa!", "danger")
    finally:
        conn.close()

    return redirect('/departments')


# =====================================================================
# 6. ROUTE: XUẤT FILE CSV DANH SÁCH PHÒNG BAN
# =====================================================================
@department_bp.route("/export_departments_csv")
@login_required
@role_required('Admin')
def export_departments_csv():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Thay ISNULL(...) bằng COALESCE(..., '') chuẩn PostgreSQL
        cursor.execute("""
            SELECT D.DepartmentID,
                   D.DepartmentCode,
                   D.DepartmentName,
                   D.Description,
                   D.Location,
                   COALESCE(E.FullName, '') AS Manager,
                   D.Status
            FROM Departments D
            LEFT JOIN Employees E ON D.ManagerID = E.EmployeeID AND E.IsDeleted = 0
            WHERE D.IsDeleted = 0
            ORDER BY D.DepartmentID
        """)
        rows = cursor.fetchall()

        output = StringIO()    
        output.write('\ufeff') 
        writer = csv.writer(output)

        writer.writerow([
            "DepartmentID", "DepartmentCode", "DepartmentName", "Description", "Location", "Manager", "Status"
        ])

        for row in rows:
            if isinstance(row, tuple):
                writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], row[6]])
            else:
                writer.writerow([
                    row.DepartmentID, row.DepartmentCode, row.DepartmentName, row.Description, row.Location, row.Manager, row.Status
                ])

        log_activity(
            module="Department",
            action="Export",
            description=f"Exported department list ({len(rows)} records)."
        )

        return Response(
            output.getvalue().encode("utf-8-sig"),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=departments.csv"}
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi xuất file CSV phòng ban: {str(e)}")
        flash("Không thể xuất file CSV do lỗi hệ thống!", "danger")
        return redirect("/departments")
    finally:
        conn.close()