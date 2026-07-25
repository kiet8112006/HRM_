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
import os
from database import get_connection
from validators.employee_validator import *
from exceptions.validator.employee import EmployeeValidationError
from datetime import datetime
from io import StringIO
import csv
from utils.notification_service import create_notification
from utils.upload import (
    allowed_file,
    allowed_mimetype,
    verify_image,
    delete_image, 
    save_avatar, 
    save_citizen_front, 
    save_citizen_back
)
from routes.audit import log_activity 

employee_bp = Blueprint("employee", __name__)

# --- CÁC HÀM HỖ TRỢ LẤY DANH MỤC CÓ CACHE ---
def get_cached_departments():
    try:
        from app import cache
        @cache.cached(timeout=60, key_prefix='departments_list')
        def query_db():
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT DepartmentID, DepartmentName FROM Departments WHERE IsDeleted = 0 ORDER BY DepartmentName")
                data = cursor.fetchall()
                return data
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
        @cache.cached(timeout=60, key_prefix='positions_list')
        def query_db():
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT PositionID, PositionName FROM Positions WHERE IsDeleted = 0 ORDER BY PositionName")
                data = cursor.fetchall()
                return data
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
# 1. ROUTE: DANH SÁCH NHÂN VIÊN & PHÂN TRANG & TÌM KIẾM
# =====================================================================
@employee_bp.route("/employees")
@login_required
@role_required('Admin', 'Manager')
def employees():
    keyword = request.args.get("keyword", "").strip()
    department = request.args.get("department", "")
    position = request.args.get("position", "")
    status = request.args.get("status", "")

    page = request.args.get('page', 1, type=int) 
    per_page = 10                                     
    offset = (page - 1) * per_page               

    departments = get_cached_departments()
    positions = get_cached_positions()

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM Employees E 
            LEFT JOIN Departments D ON E.DepartmentID = D.DepartmentID AND D.IsDeleted = 0
            LEFT JOIN Positions P ON E.PositionID = P.PositionID AND P.IsDeleted = 0
            WHERE E.IsDeleted = 0
              AND E.FullName ILIKE %s
              AND COALESCE(D.DepartmentName, '') ILIKE %s
              AND COALESCE(P.PositionName, '') ILIKE %s
              AND E.Status ILIKE %s
        """, (f"%{keyword}%", f"%{department}%", f"%{position}%", f"%{status}%"))
        total_records = cursor.fetchone()[0]

        cursor.execute("""
            SELECT E.EmployeeID,
                   COALESCE(E.EmployeeCode, 'NV' || LPAD(CAST(E.EmployeeID AS TEXT), 4, '0')) AS EmployeeCode,
                   E.FullName, 
                   E."Photo",
                   E.Gender,
                   E.Phone,
                   E.Email,
                   E.Status,
                   D.DepartmentName,
                   P.PositionName
            FROM Employees E
            LEFT JOIN Departments D ON E.DepartmentID = D.DepartmentID AND D.IsDeleted = 0
            LEFT JOIN Positions P ON E.PositionID = P.PositionID AND P.IsDeleted = 0
            WHERE E.IsDeleted = 0
              AND E.FullName ILIKE %s 
              AND COALESCE(D.DepartmentName, '') ILIKE %s
              AND COALESCE(P.PositionName, '') ILIKE %s
              AND E.Status ILIKE %s
            ORDER BY E.EmployeeID DESC
            LIMIT %s OFFSET %s
        """, (f"%{keyword}%", f"%{department}%", f"%{position}%", f"%{status}%", per_page, offset))
        employees_list = cursor.fetchall()
     
        total_pages = max(1, (total_records + per_page - 1) // per_page)

        return render_template(
            "employee/employees.html",
            keyword=keyword, 
            department=department,
            position=position,
            status=status,
            departments=departments,
            positions=positions,
            employees=employees_list,
            page=page, 
            total_pages=total_pages
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi khi tải danh sách nhân viên: {str(e)}")
        flash("Đã có lỗi xảy ra khi truy vấn dữ liệu!", "danger")
        return render_template("employee/employees.html", employees=[], page=1, total_pages=1)
    finally:
        conn.close()


# =====================================================================
# 2. ROUTE: THÊM MỚI NHÂN VIÊN
# =====================================================================
@employee_bp.route("/add_employee", methods=["GET", "POST"])
@login_required
@role_required('Admin')
def add_employee():
    if request.method == "POST":
        conn = get_connection()
        cursor = conn.cursor()
        try:
            photo = request.files.get('photo')
            citizen_front = request.files.get('citizen_front')
            citizen_back = request.files.get('citizen_back')
            upload_files = [('Ảnh nhân viên', photo), ('CCCD mặt trước', citizen_front), ('CCCD mặt sau', citizen_back)]

            for file_name, file in upload_files:
                if not file or file.filename == '':
                    continue
                if not allowed_file(file.filename):
                    raise EmployeeValidationError(f'{file_name}: chỉ được phép upload JPG, JPEG, PNG hoặc WEBP.')
                if not allowed_mimetype(file):
                    raise EmployeeValidationError(f'{file_name}: kiểu dữ liệu không hợp lệ.')
                if not verify_image(file):
                    raise EmployeeValidationError(f'{file_name}: file ảnh bị hỏng hoặc không phải ảnh hợp lệ.')

            fullname = normalize_name(request.form["fullname"])
            validate_name(fullname)

            gender = request.form["gender"]
            dob = datetime.strptime(request.form['dob'], '%Y-%m-%d').date()
            hiredate = datetime.strptime(request.form['hiredate'], '%Y-%m-%d').date()
            validate_dob(dob)
            validate_hiredate(dob, hiredate)

            status = request.form['status']

            email = normalize_email(request.form["email"])
            validate_email(email)

            citizenid = normalize_citizenid(request.form['citizenid'])
            validate_citizenid(citizenid)

            cursor.execute("SELECT COUNT(*) FROM Employees WHERE CitizenID = %s AND IsDeleted = 0", (citizenid,))
            if cursor.fetchone()[0] > 0:
                raise EmployeeValidationError('CCCD đã tồn tại!')

            address = normalize_address(request.form['address'])
            validate_address(address)

            nationality = normalize_nationality(request.form['nationality'])
            validate_nationality(nationality)

            maritalstatus = request.form['maritalstatus']
            emergencycontact = normalize_name(request.form['emergencycontact'])
            validate_emergency_contact(emergencycontact)

            emergencyphone = normalize_phone(request.form['emergencyphone'])
            validate_emergency_phone(emergencyphone)

            cursor.execute("SELECT COUNT(*) FROM Employees WHERE Email = %s AND IsDeleted = 0", (email,))
            if cursor.fetchone()[0] > 0:
                raise EmployeeValidationError('Email đã tồn tại!')

            phone = normalize_phone(request.form["phone"])
            validate_phone(phone)
            cursor.execute("SELECT COUNT(*) FROM Employees WHERE Phone = %s AND IsDeleted = 0", (phone,))
            if cursor.fetchone()[0] > 0:
                raise EmployeeValidationError('Số điện thoại đã tồn tại!')

            photo_filename = save_avatar(photo) if photo and photo.filename != '' else None
            citizen_front_filename = save_citizen_front(citizen_front) if citizen_front and citizen_front.filename != '' else None
            citizen_back_filename = save_citizen_back(citizen_back) if citizen_back and citizen_back.filename != '' else None

            department_id = request.form["department_id"]
            position_id = request.form["position_id"]
            manager_id = request.form.get("manager_id") or None

            cursor.execute("""
                INSERT INTO Employees (
                    FullName, Gender, DOB, HireDate, Email, Phone, DepartmentID, PositionID, 
                    ManagerID, Status, CitizenID, Address, Nationality, MaritalStatus, 
                    EmergencyContact, EmergencyPhone, "Photo", CitizenFrontPhoto, CitizenBackPhoto, IsDeleted
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
            """, (fullname, gender, dob, hiredate, email, phone, department_id, position_id, 
                 manager_id, status, citizenid, address, nationality, maritalstatus, 
                 emergencycontact, emergencyphone, photo_filename, citizen_front_filename, citizen_back_filename))
            
            conn.commit()
            create_notification(title='Nhân viên mới', 
                                message=f'{fullname} vừa được thêm vào hệ thống.',
                                type='Success',
                                receiver_role='Admin',
                                url='/employees')
            log_activity(module='Employee', action='Create', description=f'Created employee {fullname}. ')
            flash("Thêm nhân viên thành công!", "success")
            return redirect("/employees")

        except EmployeeValidationError as e:
            conn.rollback()
            flash(str(e), 'danger')
            return redirect(request.url)
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Lỗi thêm nhân viên: {str(e)}")
            flash(f"Đã có lỗi hệ thống xảy ra: {str(e)}", 'danger')
            return redirect(request.url)
        finally:
            conn.close()

    departments = get_cached_departments()
    positions = get_cached_positions()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""SELECT EmployeeID, FullName FROM Employees WHERE IsDeleted = 0 ORDER BY FullName""")
        managers = cursor.fetchall()
        return render_template(
            "employee/add_employee.html",
            departments=departments, 
            positions=positions, 
            managers=managers
        )
    finally:
        conn.close()


# =====================================================================
# 3. ROUTE: CHỈNH SỬA THÔNG TIN NHÂN VIÊN
# =====================================================================
@employee_bp.route("/edit_employee/<int:id>", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Manager')
def edit_employee(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""SELECT * FROM Employees WHERE EmployeeID = %s AND IsDeleted = 0""", (id,))
        employee = cursor.fetchone()

        if not employee:
            flash('Nhân viên không tồn tại hoặc đã bị xóa!', 'danger')
            return redirect("/employees")

        if request.method == "POST":
            photo_filename = employee[16] if isinstance(employee, tuple) else getattr(employee, 'Photo', None)
            citizen_front_filename = employee[17] if isinstance(employee, tuple) else getattr(employee, 'CitizenFrontPhoto', None)
            citizen_back_filename = employee[18] if isinstance(employee, tuple) else getattr(employee, 'CitizenBackPhoto', None)

            photo = request.files.get('photo')
            citizen_front = request.files.get('citizen_front')
            citizen_back = request.files.get('citizen_back')
            
            fullname = normalize_name(request.form["fullname"])
            validate_name(fullname)

            gender = request.form["gender"]
            dob = datetime.strptime(request.form['dob'], '%Y-%m-%d').date()
            hiredate = datetime.strptime(request.form['hiredate'], '%Y-%m-%d').date()
            validate_dob(dob)
            validate_hiredate(dob, hiredate)
            
            email = normalize_email(request.form["email"])
            validate_email(email)
                
            citizenid = normalize_citizenid(request.form['citizenid'])
            validate_citizenid(citizenid)
                
            cursor.execute("SELECT COUNT(*) FROM Employees WHERE CitizenID = %s AND EmployeeID <> %s AND IsDeleted = 0", (citizenid, id))
            if cursor.fetchone()[0] > 0:
                raise EmployeeValidationError('CCCD đã tồn tại!')
                
            address = normalize_address(request.form['address'])
            validate_address(address)
            
            nationality = normalize_nationality(request.form['nationality'])
            validate_nationality(nationality)
            
            maritalstatus = request.form['maritalstatus']
            emergencycontact = normalize_name(request.form['emergencycontact'])
            validate_emergency_contact(emergencycontact)
                
            emergencyphone = normalize_phone(request.form['emergencyphone'])
            validate_emergency_phone(emergencyphone)
            
            cursor.execute("SELECT COUNT(*) FROM Employees WHERE Email = %s AND EmployeeID <> %s AND IsDeleted = 0", (email, id))
            if cursor.fetchone()[0] > 0:
                raise EmployeeValidationError('Email đã tồn tại!')

            phone = normalize_phone(request.form["phone"])
            validate_phone(phone)
                
            cursor.execute("SELECT COUNT(*) FROM Employees WHERE Phone = %s AND EmployeeID <> %s AND IsDeleted = 0", (phone, id))
            if cursor.fetchone()[0] > 0:
                raise EmployeeValidationError('Số điện thoại đã tồn tại!')

            department_id = request.form["department_id"]
            position_id = request.form["position_id"]
            manager_id = request.form.get("manager_id") or None

            if manager_id is not None and int(manager_id) == id:
                raise EmployeeValidationError('Nhân viên không thể là quản lý của chính mình!')
                
            status = request.form["status"]

            if photo and photo.filename != '':
                if not allowed_file(photo.filename) or not allowed_mimetype(photo) or not verify_image(photo):
                    raise EmployeeValidationError('Ảnh đại diện không hợp lệ!')
                if photo_filename:
                    delete_image(os.path.join(current_app.root_path, 'static', photo_filename))
                photo_filename = save_avatar(photo)
                
            if citizen_front and citizen_front.filename != '':
                if not allowed_file(citizen_front.filename) or not allowed_mimetype(citizen_front) or not verify_image(citizen_front):
                    raise EmployeeValidationError('Ảnh CCCD mặt trước không hợp lệ!')
                if citizen_front_filename:
                    delete_image(os.path.join(current_app.root_path, 'static', citizen_front_filename))
                citizen_front_filename = save_citizen_front(citizen_front)
                
            if citizen_back and citizen_back.filename != '':
                if not allowed_file(citizen_back.filename) or not allowed_mimetype(citizen_back) or not verify_image(citizen_back):
                    raise EmployeeValidationError('Ảnh CCCD mặt sau không hợp lệ!')
                if citizen_back_filename:
                    delete_image(os.path.join(current_app.root_path, 'static', citizen_back_filename))
                citizen_back_filename = save_citizen_back(citizen_back)

            cursor.execute("""
                UPDATE Employees
                SET FullName = %s, Gender = %s, DOB = %s, HireDate = %s, Email = %s, Phone = %s, 
                    DepartmentID = %s, PositionID = %s, ManagerID = %s, Status = %s, CitizenID = %s, 
                    Address = %s, Nationality = %s, MaritalStatus = %s, EmergencyContact = %s, 
                    EmergencyPhone = %s, "Photo" = %s, CitizenFrontPhoto = %s, CitizenBackPhoto = %s
                WHERE EmployeeID = %s 
            """, (fullname, gender, dob, hiredate, email, phone, department_id, position_id, 
                 manager_id, status, citizenid, address, nationality, maritalstatus, 
                 emergencycontact, emergencyphone, photo_filename, citizen_front_filename, citizen_back_filename, id))

            conn.commit()
            create_notification(title='Cập nhật nhân viên',
                                message=f'{fullname} vừa được cập nhật.',
                                type='Info',
                                receiver_role='Admin',
                                url='/employees')
            log_activity(module='Employee', action='Update', record_id=id, description=f'Updated employee {fullname}. ')
            flash("Cập nhật nhân viên thành công!", "success")
            return redirect("/employees")

    except EmployeeValidationError as e:
        flash(str(e), 'danger')
        return redirect(request.url)
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi cập nhật nhân viên ID {id}: {str(e)}")
        flash("Đã có lỗi hệ thống xảy ra. Vui lòng thử lại sau!", 'danger')
        return redirect(request.url)
    finally:
        conn.close()

    departments = get_cached_departments()
    positions = get_cached_positions()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT EmployeeID, FullName FROM Employees WHERE IsDeleted = 0 ORDER BY FullName')
        managers = cursor.fetchall()
        return render_template(
            "employee/edit_employee.html",
            employee=employee, 
            departments=departments, 
            positions=positions, 
            managers=managers
        )
    finally:
        conn.close()


# =====================================================================
# 4. ROUTE: XÓA ĐƠN LẺ (XÓA MỀM)
# =====================================================================
@employee_bp.route("/delete_employee/<int:id>")
@login_required
@role_required('Admin')
def delete_employee(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT FullName FROM Employees WHERE EmployeeID = %s AND IsDeleted = 0', (id,))
        employee = cursor.fetchone()
        
        if not employee:
            flash('Nhân viên không tồn tại hoặc đã bị xóa trước đó!', 'danger')
            return redirect("/employees")

        employee_name = employee[0] if isinstance(employee, tuple) else employee.FullName

        cursor.execute("UPDATE Employees SET IsDeleted = 1 WHERE EmployeeID = %s", (id,))
        conn.commit()
        
        create_notification(title='Xóa nhân viên',
                            message=f'{employee_name} đã bị xóa khỏi hệ thống.',
                            type='Warning',
                            receiver_role='Admin',
                            url='/employees')
        log_activity(module='Employee', action='Delete', record_id=id, description=f'Soft deleted employee {employee_name}. ')
            
        flash('Xóa nhân viên thành công (Xóa mềm)!', "success")
        return redirect("/employees")
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi khi xóa nhân viên ID {id}: {str(e)}")
        flash("Có lỗi hệ thống xảy ra khi xóa nhân viên!", "danger")
        return redirect("/employees")
    finally:
        conn.close()


# =====================================================================
# 5. ROUTE: XUẤT FILE CSV DANH SÁCH NHÂN VIÊN
# =====================================================================
@employee_bp.route("/export_employees_csv")
@login_required
@role_required('Admin', 'Manager')
def export_employees_csv():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(""" 
            SELECT E.EmployeeID, E.FullName, E.Gender, E.Phone, E.Email, D.DepartmentName, P.PositionName, E.Status 
            FROM Employees E 
            LEFT JOIN Departments D ON E.DepartmentID = D.DepartmentID AND D.IsDeleted = 0
            LEFT JOIN Positions P ON E.PositionID = P.PositionID AND P.IsDeleted = 0
            WHERE E.IsDeleted = 0
            ORDER BY E.EmployeeID 
        """)
        rows = cursor.fetchall()

        output = StringIO()    
        output.write('\ufeff') 
        writer = csv.writer(output)
        
        writer.writerow(["EmployeeID", "FullName", "Gender", "Phone", "Email", "Department", "Position", "Status"])
        
        for row in rows:
            if isinstance(row, tuple):
                writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]])
            else:
                writer.writerow([row.EmployeeID, row.FullName, row.Gender, row.Phone, row.Email, row.DepartmentName, row.PositionName, row.Status])
        
        log_activity(module='Employee', action='Export', description='Exported employee list to CSV. ')
            
        return Response(
            output.getvalue().encode('utf-8-sig'), 
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=employees.csv"}
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi khi xuất file CSV: {str(e)}")
        flash("Không thể xuất file CSV do lỗi hệ thống!", "danger")
        return redirect("/employees")
    finally:
        conn.close()


# =====================================================================
# 6. ROUTE: CHI TIẾT NHÂN VIÊN
# =====================================================================
@employee_bp.route("/employee_detail/<int:id>")
@login_required
@role_required('Admin', 'Manager')
def employee_detail(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(""" 
            SELECT E.EmployeeID, COALESCE(E.EmployeeCode, 'NV' || LPAD(CAST(E.EmployeeID AS TEXT), 4, '0')) AS EmployeeCode, 
                   E.FullName, E.Gender, E.DOB, E.Phone, E.Email, E.CitizenID, E.Address, 
                   E.Nationality, E.MaritalStatus, E.EmergencyContact, E.EmergencyPhone, E.HireDate, E.Status, 
                   D.DepartmentName, P.PositionName 
            FROM Employees E 
            LEFT JOIN Departments D ON E.DepartmentID = D.DepartmentID AND D.IsDeleted = 0
            LEFT JOIN Positions P ON E.PositionID = P.PositionID AND P.IsDeleted = 0
            WHERE E.EmployeeID = %s AND E.IsDeleted = 0
        """, (id,))
        employee = cursor.fetchone()

        if not employee:
            flash('Nhân viên không tồn tại hoặc đã bị xóa!', 'danger')
            return redirect("/employees")

        cursor.execute("""
            SELECT BaseSalary, Bonus, Allowance, 
                   (BaseSalary + Bonus + Allowance) AS TotalSalary,
                   month, year 
            FROM Salaries
            WHERE EmployeeID = %s AND IsDeleted = 0
            ORDER BY SalaryID DESC
            LIMIT 1
        """, (id,))
        salary = cursor.fetchone()

        cursor.execute("""
            SELECT year, month, BaseSalary, Bonus, Allowance, (BaseSalary + Bonus + Allowance) AS TotalSalary
            FROM Salaries  
            WHERE EmployeeID = %s AND IsDeleted = 0
            ORDER BY year DESC, month DESC
        """, (id,))
        salary_history = cursor.fetchall()

        cursor.execute("""
            SELECT Date, CheckInTime, CheckOutTime, Status 
            FROM Attendance 
            WHERE EmployeeID = %s AND IsDeleted = 0
            ORDER BY Date DESC
        """, (id,))
        attendance_history = cursor.fetchall()

        cursor.execute("""
            SELECT FromDate, ToDate, Reason, Status 
            FROM LeaveRequests
            WHERE EmployeeID = %s AND IsDeleted = 0
            ORDER BY FromDate DESC
        """, (id,))
        leave_history = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*) FROM Attendance 
            WHERE EmployeeID = %s AND IsDeleted = 0
              AND Status = 'Có mặt'
              AND EXTRACT(MONTH FROM Date) = EXTRACT(MONTH FROM CURRENT_DATE)
              AND EXTRACT(YEAR FROM Date) = EXTRACT(YEAR FROM CURRENT_DATE)
        """, (id,))
        present_days = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM Attendance 
            WHERE EmployeeID = %s AND IsDeleted = 0
              AND Status = 'Đi trễ'
              AND EXTRACT(MONTH FROM Date) = EXTRACT(MONTH FROM CURRENT_DATE)
              AND EXTRACT(YEAR FROM Date) = EXTRACT(YEAR FROM CURRENT_DATE)
        """, (id,))
        late_count_in_month = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM LeaveRequests 
            WHERE EmployeeID = %s AND IsDeleted = 0
              AND Status = 'Đã duyệt'
              AND EXTRACT(MONTH FROM FromDate) = EXTRACT(MONTH FROM CURRENT_DATE)
              AND EXTRACT(YEAR FROM FromDate) = EXTRACT(YEAR FROM CURRENT_DATE)
        """, (id,))
        leave_count_in_month = cursor.fetchone()[0]

        return render_template(
            "employee/employee_detail.html", 
            employee=employee, 
            salary=salary, 
            salary_history=salary_history, 
            attendance_history=attendance_history,
            leave_history=leave_history, 
            present_days=present_days, 
            late_count_in_month=late_count_in_month, 
            leave_count_in_month=leave_count_in_month
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi khi xem chi tiết nhân viên ID {id}: {str(e)}")
        flash("Có lỗi hệ thống xảy ra khi lấy dữ liệu chi tiết!", "danger")
        return redirect("/employees")
    finally:
        conn.close()


# =====================================================================
# 7. ROUTE: XÓA NHIỀU NHÂN VIÊN ĐÃ CHỌN
# =====================================================================
@employee_bp.route("/delete_selected_employees", methods=["POST"])
@login_required
@role_required('Admin')
def delete_selected_employees():
    employee_ids = request.form.getlist("employee_ids")

    if not employee_ids:
        flash("Vui lòng chọn ít nhất một nhân viên!", "warning")
        return redirect("/employees")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        placeholders = ', '.join(['%s'] * len(employee_ids))
        
        query_info = f"SELECT EmployeeID, FullName FROM Employees WHERE EmployeeID IN ({placeholders}) AND IsDeleted = 0"
        cursor.execute(query_info, tuple(employee_ids))
        records = cursor.fetchall()
        deleted_count = len(records)

        if deleted_count > 0:
            query_delete = f"UPDATE Employees SET IsDeleted = 1 WHERE EmployeeID IN ({placeholders})"
            cursor.execute(query_delete, tuple(employee_ids))
            
            for row in records:
                emp_id = row[0] if isinstance(row, tuple) else row.EmployeeID
                emp_name = row[1] if isinstance(row, tuple) else row.FullName
                log_activity(
                    module='Employee', 
                    action='Delete', 
                    record_id=int(emp_id), 
                    description=f'Soft deleted employee {emp_name}. '
                )

            conn.commit()
            
            create_notification(
                title='Xóa nhiều nhân viên',
                message=f'Đã xóa thành công {deleted_count} nhân viên được chọn (Xóa mềm).',
                type='Warning',
                receiver_role='Admin',
                url='/employees'
            )
            flash(f"Đã xóa thành công {deleted_count} nhân viên!", "success")
        else:
            flash("Không tìm thấy nhân viên hợp lệ nào để thực hiện thao tác xóa!", "warning")

    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi khi xóa nhiều nhân viên: {str(e)}")
        flash("Có lỗi hệ thống xảy ra khi thực hiện xóa!", "danger")
    finally:
        conn.close()

    return redirect("/employees")