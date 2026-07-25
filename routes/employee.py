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

def get_cached_departments():
    try:
        from app import cache
        @cache.cached(timeout=60, key_prefix='departments_list')
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
        @cache.cached(timeout=60, key_prefix='positions_list')
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
              AND COALESCE(E.Status, 'Active') ILIKE %s
        """, (f"%{keyword}%", f"%{department}%", f"%{position}%", f"%{status}%"))
        total_records = cursor.fetchone()[0]

        cursor.execute("""
            SELECT E.EmployeeID,
                   'NV' || LPAD(CAST(E.EmployeeID AS TEXT), 4, '0') AS EmployeeCode,
                   E.FullName, 
                   E."Photo",
                   E.Gender,
                   E.Phone,
                   E.Email,
                   COALESCE(E.Status, 'Active') AS Status,
                   D.DepartmentName,
                   P.PositionName
            FROM Employees E
            LEFT JOIN Departments D ON E.DepartmentID = D.DepartmentID AND D.IsDeleted = 0
            LEFT JOIN Positions P ON E.PositionID = P.PositionID AND P.IsDeleted = 0
            WHERE E.IsDeleted = 0
              AND E.FullName ILIKE %s 
              AND COALESCE(D.DepartmentName, '') ILIKE %s
              AND COALESCE(P.PositionName, '') ILIKE %s
              AND COALESCE(E.Status, 'Active') ILIKE %s
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
            
            for file_name, file in [('Ảnh nhân viên', photo), ('CCCD mặt trước', citizen_front), ('CCCD mặt sau', citizen_back)]:
                if file and file.filename != '':
                    if not allowed_file(file.filename) or not allowed_mimetype(file) or not verify_image(file):
                        raise EmployeeValidationError(f'{file_name} không hợp lệ.')

            fullname = normalize_name(request.form["fullname"])
            validate_name(fullname)

            gender = request.form["gender"]
            dob = datetime.strptime(request.form['dob'], '%Y-%m-%d').date()
            hiredate = datetime.strptime(request.form['hiredate'], '%Y-%m-%d').date()
            validate_dob(dob)
            validate_hiredate(dob, hiredate)

            status = request.form.get('status', 'Active')
            email = normalize_email(request.form["email"])
            validate_email(email)

            citizenid = normalize_citizenid(request.form['citizenid'])
            validate_citizenid(citizenid)

            address = normalize_address(request.form['address'])
            nationality = normalize_nationality(request.form['nationality'])
            maritalstatus = request.form['maritalstatus']
            emergencycontact = normalize_name(request.form['emergencycontact'])
            emergencyphone = normalize_phone(request.form['emergencyphone'])

            phone = normalize_phone(request.form["phone"])
            validate_phone(phone)

            photo_filename = save_avatar(photo) if photo and photo.filename != '' else None
            citizen_front_filename = save_citizen_front(citizen_front) if citizen_front and citizen_front.filename != '' else None
            citizen_back_filename = save_citizen_back(citizen_back) if citizen_back and citizen_back.filename != '' else None

            department_id = request.form.get("department_id") or None
            position_id = request.form.get("position_id") or None
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
        return render_template("employee/add_employee.html", departments=departments, positions=positions, managers=managers)
    finally:
        conn.close()

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
            fullname = normalize_name(request.form["fullname"])
            gender = request.form["gender"]
            dob = datetime.strptime(request.form['dob'], '%Y-%m-%d').date()
            hiredate = datetime.strptime(request.form['hiredate'], '%Y-%m-%d').date()
            email = normalize_email(request.form["email"])
            phone = normalize_phone(request.form["phone"])
            citizenid = normalize_citizenid(request.form['citizenid'])
            address = normalize_address(request.form['address'])
            nationality = normalize_nationality(request.form['nationality'])
            maritalstatus = request.form['maritalstatus']
            emergencycontact = normalize_name(request.form['emergencycontact'])
            emergencyphone = normalize_phone(request.form['emergencyphone'])
            department_id = request.form.get("department_id") or None
            position_id = request.form.get("position_id") or None
            manager_id = request.form.get("manager_id") or None
            status = request.form.get("status", "Active")

            cursor.execute("""
                UPDATE Employees
                SET FullName = %s, Gender = %s, DOB = %s, HireDate = %s, Email = %s, Phone = %s, 
                    DepartmentID = %s, PositionID = %s, ManagerID = %s, Status = %s, CitizenID = %s, 
                    Address = %s, Nationality = %s, MaritalStatus = %s, EmergencyContact = %s, 
                    EmergencyPhone = %s
                WHERE EmployeeID = %s 
            """, (fullname, gender, dob, hiredate, email, phone, department_id, position_id, 
                 manager_id, status, citizenid, address, nationality, maritalstatus, 
                 emergencycontact, emergencyphone, id))

            conn.commit()
            flash("Cập nhật nhân viên thành công!", "success")
            return redirect("/employees")

    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi cập nhật nhân viên ID {id}: {str(e)}")
        flash("Đã có lỗi hệ thống xảy ra!", 'danger')
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
        return render_template("employee/edit_employee.html", employee=employee, departments=departments, positions=positions, managers=managers)
    finally:
        conn.close()

@employee_bp.route("/delete_employee/<int:id>")
@login_required
@role_required('Admin')
def delete_employee(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Employees SET IsDeleted = 1 WHERE EmployeeID = %s", (id,))
        conn.commit()
        flash('Xóa nhân viên thành công!', "success")
        return redirect("/employees")
    except Exception as e:
        conn.rollback()
        flash("Có lỗi hệ thống xảy ra khi xóa nhân viên!", "danger")
        return redirect("/employees")
    finally:
        conn.close()

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
            writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]])
        
        return Response(
            output.getvalue().encode('utf-8-sig'), 
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=employees.csv"}
        )
    except Exception:
        flash("Không thể xuất file CSV do lỗi hệ thống!", "danger")
        return redirect("/employees")
    finally:
        conn.close()

@employee_bp.route("employee_detail/<int:id>")
@login_required
@role_required('Admin', 'Manager')
def employee_detail(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(""" 
            SELECT E.EmployeeID, 'NV' || LPAD(CAST(E.EmployeeID AS TEXT), 4, '0') AS EmployeeCode, 
                   E.FullName, E.Gender, E.DOB, E.Phone, E.Email, E.CitizenID, E.Address, 
                   E.Nationality, E.MaritalStatus, E.EmergencyContact, E.EmergencyPhone, E.HireDate, E.Status, 
                   D.DepartmentName, P.PositionName 
            FROM Employees E 
            LEFT JOIN Departments D ON E.DepartmentID = D.DepartmentID AND D.IsDeleted = 0
            LEFT CASCADE Positions P ON E.PositionID = P.PositionID AND P.IsDeleted = 0
            WHERE E.EmployeeID = %s AND E.IsDeleted = 0
        """, (id,))
        # Chú ý phần LEFT JOIN chuẩn ở dưới
        cursor.execute(""" 
            SELECT E.EmployeeID, 'NV' || LPAD(CAST(E.EmployeeID AS TEXT), 4, '0') AS EmployeeCode, 
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
            flash('Nhân viên không tồn tại!', 'danger')
            return redirect("/employees")

        return render_template("employee/employee_detail.html", employee=employee)
    except Exception as e:
        flash("Có lỗi hệ thống xảy ra!", "danger")
        return redirect("/employees")
    finally:
        conn.close()