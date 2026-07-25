from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    flash,
    Response,
    url_for,
    current_app
)
from utils.auth import *
from database import get_connection
from validators.attandance_validator import *
from exceptions.validator.attendance import AttendanceValidationError
from datetime import datetime
from io import StringIO
import csv
from routes.audit import log_activity 
from utils.notification_service import create_notification

attendance_bp = Blueprint("attendance", __name__)

# --- HÀM HỖ TRỢ LẤY DANH SÁCH NHÂN VIÊN CÓ CACHE ---
def get_cached_active_employees():
    try:
        from app import cache
        @cache.cached(timeout=60, key_prefix='active_employees_list')
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
# 1. ROUTE: DANH SÁCH CHẤM CÔNG & PHÂN TRANG & TÌM KIẾM
# =====================================================================
@attendance_bp.route("/attendance")
@login_required
@role_required('Admin', 'Manager')
def attendance():
    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "")
    page = request.args.get("page", 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(""" 
            SELECT COUNT(*) 
            FROM Attendance A 
            INNER JOIN Employees E ON A.EmployeeID = E.EmployeeID 
            WHERE A.IsDeleted = 0 
              AND E.IsDeleted = 0 
              AND E.FullName ILIKE %s 
              AND A.Status ILIKE %s 
        """, (f"%{keyword}%", f"%{status}%"))
        total_records = cursor.fetchone()[0]

        cursor.execute("""
            SELECT
                A.AttendanceID, E.Fullname, A.Date, A.CheckInTime, A.CheckOutTime, A.WorkingHours, A.OvertimeHours, A.LateMinutes, A.EarlyLeaveMinutes,
                A.CheckInMethod, A.Status, A.ApprovalStatus, A.Notes
            FROM Attendance A
            INNER JOIN Employees E ON A.EmployeeID = E.EmployeeID
            WHERE A.IsDeleted = 0 
              AND E.IsDeleted = 0 
              AND E.FullName ILIKE %s AND A.Status ILIKE %s
            ORDER BY A.Date DESC, A.AttendanceID DESC
            LIMIT %s OFFSET %s
        """, (f"%{keyword}%", f"%{status}%", per_page, offset))
        attendances = cursor.fetchall()

        total_pages = max(1, (total_records + per_page - 1) // per_page)

        return render_template(
            "attendance/attendance.html", 
            attendances=attendances, 
            page=page, 
            total_pages=total_pages,  
            keyword=keyword, 
            status=status 
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi tải danh sách chấm công: {str(e)}")
        flash("Đã có lỗi xảy ra khi lấy dữ liệu chấm công!", "danger")
        return render_template("attendance/attendance.html", attendances=[], page=1, total_pages=1, keyword=keyword, status=status)
    finally:
        conn.close()


# =====================================================================
# 2. ROUTE: THÊM MỚI BẢN GHI CHẤM CÔNG (ÁP DỤNG EXCEPTION HANDLING)
# =====================================================================
@attendance_bp.route("/add_attendance", methods=["GET", "POST"])
@login_required
@role_required('Admin')
def add_attendance():
    if request.method == "POST":
        conn = get_connection()
        cursor = conn.cursor()
        try:
            employee_id = request.form.get("employee_id")
            attendance_date = datetime.strptime(request.form.get("date"), "%Y-%m-%d").date()
            checkin = request.form.get("checkin")
            checkout = request.form.get("checkout")
            status = request.form.get("status")
            checkin_method = request.form.get("checkin_method")
            approval_status = request.form.get("approval_status")
            notes = request.form.get("notes", "").strip()

            # 1. Validations
            validate_attendance_status(status)
            validate_approval_status(approval_status)
            validate_checkin_method(checkin_method)
            validate_notes(notes)

            today = datetime.today().date()
            validate_attendance_date(attendance_date, today)

            cursor.execute("SELECT COUNT(*) FROM Employees WHERE EmployeeID = %s AND IsDeleted = 0", (employee_id,))
            if cursor.fetchone()[0] == 0:
                raise AttendanceValidationError('Nhân viên không tồn tại hoặc đã bị xóa!')

            cursor.execute("SELECT COUNT(*) FROM Attendance WHERE EmployeeID = %s AND Date = %s AND IsDeleted = 0", (employee_id, attendance_date))
            if cursor.fetchone()[0] > 0:
                raise AttendanceValidationError('Nhân viên đã được chấm công trong ngày này!')

            checkin, checkout, working_hours, overtime_hours, late_minutes, early_leave_minutes = validate_checkin_checkout_times(checkin, checkout, status)

            # 2. Insert DB
            cursor.execute("""
                INSERT INTO Attendance
                (EmployeeID, Date, CheckInTime, CheckOutTime, WorkingHours, OvertimeHours, Status, LateMinutes, EarlyLeaveMinutes, CheckInMethod, ApprovalStatus, Notes, IsDeleted)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
            """, (employee_id, attendance_date, checkin, checkout, working_hours, overtime_hours, status, late_minutes, early_leave_minutes, checkin_method, approval_status, notes))

            cursor.execute("SELECT FullName FROM Employees WHERE EmployeeID = %s", (employee_id,))
            emp_row = cursor.fetchone()
            emp_name = emp_row[0] if emp_row else ""

            conn.commit()

            create_notification(
                title='Chấm công mới', 
                message=f'Bản ghi chấm công của {emp_name} ngày {attendance_date} đã được thêm.',
                type='Success',
                receiver_role='Admin',
                url='/attendance'
            )

            log_activity(
                module="Attendance",
                action="Create",
                description=f"Created attendance record for employee {emp_name} on {attendance_date} (Status: {status})."
            )

            flash("Thêm chấm công thành công!", "success")
            return redirect(url_for("attendance.attendance"))

        except AttendanceValidationError as e:
            flash(str(e), 'danger')
            return redirect(request.url)
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Lỗi thêm bản ghi chấm công: {str(e)}")
            flash("Đã có lỗi hệ thống xảy ra. Vui lòng thử lại sau!", 'danger')
            return redirect(request.url)
        finally:
            conn.close()

    employees = get_cached_active_employees()
    return render_template("attendance/add_attendance.html", employees=employees, today=datetime.today().date().isoformat())


# =====================================================================
# 3. ROUTE: CHỈNH SỬA BẢN GHI CHẤM CÔNG (ÁP DỤNG EXCEPTION HANDLING)
# =====================================================================
@attendance_bp.route("/edit_attendance/<int:id>", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Manager')
def edit_attendance(id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM Attendance WHERE AttendanceID = %s AND IsDeleted = 0", (id,))
        attendance_record = cursor.fetchone()

        if not attendance_record:
            flash("Bản ghi chấm công không tồn tại hoặc đã bị xóa!", "danger")
            return redirect("/attendance")

        if request.method == "POST":
            employee_id = request.form.get("employee_id")
            attendance_date = datetime.strptime(request.form.get("date"), "%Y-%m-%d").date()
            checkin = request.form.get("checkin")
            checkout = request.form.get("checkout")
            status = request.form.get("status")
            checkin_method = request.form.get("checkin_method")
            approval_status = request.form.get("approval_status")
            notes = request.form.get("notes", "").strip()

            # 1. Validations
            validate_attendance_status(status)
            validate_approval_status(approval_status)
            validate_checkin_method(checkin_method)
            validate_notes(notes)

            today = datetime.today().date()
            validate_attendance_date(attendance_date, today)

            cursor.execute("SELECT COUNT(*) FROM Employees WHERE EmployeeID = %s AND IsDeleted = 0", (employee_id,))
            if cursor.fetchone()[0] == 0:
                raise AttendanceValidationError('Nhân viên không tồn tại!')

            cursor.execute("SELECT COUNT(*) FROM Attendance WHERE EmployeeID = %s AND Date = %s AND AttendanceID <> %s AND IsDeleted = 0", (employee_id, attendance_date, id))
            if cursor.fetchone()[0] > 0:
                raise AttendanceValidationError('Nhân viên đã được chấm công trong ngày này!')

            checkin, checkout, working_hours, overtime_hours, late_minutes, early_leave_minutes = validate_checkin_checkout_times(checkin, checkout, status)

            # 2. Update DB
            cursor.execute("""
                UPDATE Attendance
                SET EmployeeID = %s, Date = %s, CheckInTime = %s, CheckOutTime = %s, WorkingHours = %s, OvertimeHours = %s,
                    Status = %s, LateMinutes = %s, EarlyLeaveMinutes = %s, CheckInMethod = %s, ApprovalStatus = %s, Notes = %s
                WHERE AttendanceID = %s
            """, (employee_id, attendance_date, checkin, checkout, working_hours, overtime_hours, status, late_minutes, early_leave_minutes, checkin_method, approval_status, notes, id))

            cursor.execute("SELECT FullName FROM Employees WHERE EmployeeID = %s", (employee_id,))
            emp_row = cursor.fetchone()
            emp_name = emp_row[0] if emp_row else ""

            conn.commit()
            
            create_notification(
                title='Cập nhật chấm công',
                message=f'Bản ghi chấm công của {emp_name} ngày {attendance_date} đã được cập nhật.',
                type='Info',
                receiver_role='Admin',
                url='/attendance'
            )
            
            log_activity(
                module="Attendance",
                action="Update",
                record_id=id,
                description=f"Updated attendance record for employee {emp_name} on {attendance_date}."
            )

            flash("Cập nhật chấm công thành công!", "success")
            return redirect("/attendance")

    except AttendanceValidationError as e:
        flash(str(e), 'danger')
        return redirect(request.url)
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi cập nhật bản ghi chấm công ID {id}: {str(e)}")
        flash("Đã có lỗi hệ thống xảy ra. Vui lòng thử lại sau!", 'danger')
        return redirect(request.url)
    finally:
        conn.close()

    # GET Request
    employees = get_cached_active_employees()
    return render_template("attendance/edit_attendance.html", attendance=attendance_record, employees=employees, today=datetime.today().date().isoformat())


# =====================================================================
# 4. ROUTE: XÓA ĐƠN LẺ BẢNG GHI CHẤM CÔNG (XÓA MỀM)
# =====================================================================
@attendance_bp.route("/delete_attendance/<int:id>")
@login_required
@role_required('Admin')
def delete_attendance(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT E.FullName, A.Date FROM Attendance A 
            INNER JOIN Employees E ON A.EmployeeID = E.EmployeeID 
            WHERE A.AttendanceID = %s AND A.IsDeleted = 0
        """, (id,))
        info_row = cursor.fetchone()
        
        if not info_row:
            flash("Bản ghi chấm công không tồn tại hoặc đã bị xóa trước đó!", "danger")
            return redirect("/attendance")
            
        emp_name = info_row[0]
        att_date = info_row[1]
        info_str = f"of employee {emp_name} on {att_date}"

        cursor.execute(""" UPDATE Attendance SET IsDeleted = 1 WHERE AttendanceID = %s """, (id,))
        conn.commit()

        create_notification(
            title='Xóa chấm công',
            message=f'Bản ghi chấm công của {emp_name} ngày {att_date} đã bị xóa.',
            type='Warning',
            receiver_role='Admin',
            url='/attendance'
        )

        log_activity(
            module="Attendance",
            action="Delete",
            record_id=id,
            description=f"Soft deleted attendance record {info_str}."
        )

        flash("Xóa chấm công thành công (Xóa mềm)!", "success")
        return redirect("/attendance")
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi xóa bản ghi chấm công ID {id}: {str(e)}")
        flash("Có lỗi hệ thống xảy ra khi thực hiện xóa!", "danger")
        return redirect("/attendance")
    finally:
        conn.close()


# =====================================================================
# 5. ROUTE: XÓA HÀNG LOẠT BẢNG GHI CHẤM CÔNG
# =====================================================================
@attendance_bp.route("/delete_selected_attendance", methods=["POST"])
@login_required
@role_required('Admin')
def delete_selected_attendance():
    attendance_ids = request.form.getlist("attendance_ids")
    if not attendance_ids:
        flash("Vui lòng chọn ít nhất một bản ghi chấm công!", "warning")
        return redirect("/attendance")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        placeholders = ', '.join(['%s'] * len(attendance_ids))
        
        query_info = f"""
            SELECT E.FullName, A.Date FROM Attendance A
            INNER JOIN Employees E ON A.EmployeeID = E.EmployeeID
            WHERE A.AttendanceID IN ({placeholders}) AND A.IsDeleted = 0
        """
        cursor.execute(query_info, tuple(attendance_ids))
        records = cursor.fetchall()
        deleted_count = len(records)

        if deleted_count > 0:
            query_delete = f"UPDATE Attendance SET IsDeleted = 1 WHERE AttendanceID IN ({placeholders})"
            cursor.execute(query_delete, tuple(attendance_ids))
            
            for row in records:
                info_str = f"of employee {row[0]} on {row[1]}"
                log_activity(
                    module="Attendance",
                    action="Delete",
                    description=f"Soft deleted attendance record {info_str}."
                )

            conn.commit()
            
            create_notification(
                title='Xóa nhiều bản ghi chấm công',
                message=f'Đã xóa thành công {deleted_count} bản ghi chấm công (Xóa mềm).',
                type='Warning',
                receiver_role='Admin',
                url='/attendance'
            )
            flash(f"Đã xóa thành công {deleted_count} bản ghi chấm công được chọn!", "success")
        else:
            flash("Không tìm thấy bản ghi hợp lệ nào để xóa!", "warning")

    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi xóa nhiều bản ghi chấm công: {str(e)}")
        flash("Có lỗi hệ thống xảy ra khi thực hiện xóa!", "danger")
    finally:
        conn.close()

    return redirect("/attendance")


# =====================================================================
# 6. ROUTE: XUẤT FILE CSV DANH SÁCH CHẤM CÔNG
# =====================================================================
@attendance_bp.route("/export_attendance_csv")
@login_required
@role_required('Admin')
def export_attendance_csv():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                A.AttendanceID, E.FullName, A.Date, A.CheckInTime, A.CheckOutTime, A.WorkingHours,
                A.OvertimeHours, A.LateMinutes, A.EarlyLeaveMinutes, A.CheckInMethod, A.Status, A.ApprovalStatus, A.Notes
            FROM Attendance A
            INNER JOIN Employees E ON A.EmployeeID = E.EmployeeID
            WHERE A.IsDeleted = 0 
              AND E.IsDeleted = 0 
            ORDER BY A.Date DESC, A.AttendanceID DESC
        """)
        rows = cursor.fetchall()

        output = StringIO()
        output.write("\ufeff")
        writer = csv.writer(output)

        writer.writerow([
            "AttendanceID", "Employee", "Date", "CheckIn", "CheckOut", "WorkingHours",
            "OvertimeHours", "LateMinutes", "EarlyLeaveMinutes", "CheckInMethod", "Status", "ApprovalStatus", "Notes"
        ])

        for row in rows:
            if isinstance(row, tuple):
                writer.writerow(list(row))
            else:
                writer.writerow([
                    getattr(row, 'AttendanceID', row[0]), 
                    getattr(row, 'FullName', row[1]), 
                    getattr(row, 'Date', row[2]), 
                    getattr(row, 'CheckInTime', row[3]), 
                    getattr(row, 'CheckOutTime', row[4]), 
                    getattr(row, 'WorkingHours', row[5]),
                    getattr(row, 'OvertimeHours', row[6]), 
                    getattr(row, 'LateMinutes', row[7]), 
                    getattr(row, 'EarlyLeaveMinutes', row[8]), 
                    getattr(row, 'CheckInMethod', row[9]), 
                    getattr(row, 'Status', row[10]), 
                    getattr(row, 'ApprovalStatus', row[11]), 
                    getattr(row, 'Notes', row[12])
                ])

        log_activity(
            module="Attendance",
            action="Export",
            description=f"Exported attendance list ({len(rows)} records)."
        )

        return Response(
            output.getvalue().encode("utf-8-sig"),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=attendance.csv"}
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi xuất file CSV chấm công: {str(e)}")
        flash("Không thể xuất file CSV do lỗi hệ thống!", "danger")
        return redirect("/attendance")
    finally:
        conn.close()