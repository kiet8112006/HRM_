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
from validators.leave_validator import *
from exceptions.validator.leave import LeaveValidationError
from datetime import datetime
from io import StringIO
import csv
from routes.audit import log_activity 
from utils.notification_service import create_notification

leave_bp = Blueprint("leave", __name__)

# --- HÀM HỖ TRỢ LẤY DANH SÁCH NHÂN VIÊN CÓ CACHE ---
def get_cached_active_employees():
    try:
        from app import cache
        @cache.cached(timeout=60, key_prefix='leave_employees_list')
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
# 1. ROUTE: DANH SÁCH ĐƠN NGHỈ PHÉP (PHÂN TRANG & TÌM KIẾM)
# =====================================================================
@leave_bp.route("/leave_requests")
@login_required
@role_required('Admin', 'Manager')
def leave_requests():
    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "")
    leave_type = request.args.get('leave_type', '')
    page = request.args.get("page", 1, type=int)

    per_page = 10
    offset = (page - 1) * per_page
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # MSSQL: Dùng LIKE, ISNULL và ?
        cursor.execute(""" 
            SELECT COUNT(*) 
            FROM LeaveRequests L 
            INNER JOIN Employees E ON L.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE L.IsDeleted = 0 
              AND E.FullName LIKE ? 
              AND L.Status LIKE ? 
              AND ISNULL(L.LeaveType, '') LIKE ? 
        """, (f"%{keyword}%", f"%{status}%", f'%{leave_type}%'))
        total_records = cursor.fetchone()[0]

        # MSSQL: Dùng DATEDIFF để tính khoảng cách ngày và OFFSET ... ROWS FETCH NEXT ... ROWS ONLY để phân trang
        cursor.execute("""
            SELECT
                L.RequestID, E.FullName, L.LeaveType, L.FromDate, L.ToDate, 
                DATEDIFF(day, L.FromDate, L.ToDate) + 1 AS TotalDays, 
                L.Reason, L.Status, L.ApprovedBy, L.ApprovedDate
            FROM LeaveRequests L
            INNER JOIN Employees E ON L.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE L.IsDeleted = 0 
              AND E.FullName LIKE ?
              AND L.Status LIKE ? 
              AND ISNULL(L.LeaveType, '') LIKE ?
            ORDER BY L.RequestID DESC 
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, (f"%{keyword}%", f"%{status}%", f'%{leave_type}%', offset, per_page))
        requests = cursor.fetchall()
        
        total_pages = max(1, (total_records + per_page - 1) // per_page)

        return render_template(
            "leave/leave_requests.html", 
            requests=requests, 
            page=page, 
            total_pages=total_pages, 
            keyword=keyword, 
            status=status, 
            leave_type=leave_type
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi khi lấy danh sách đơn nghỉ phép: {str(e)}")
        flash("Có lỗi hệ thống xảy ra khi tải dữ liệu đơn nghỉ phép!", "danger")
        return render_template("leave/leave_requests.html", requests=[], page=1, total_pages=1)
    finally:
        conn.close()


# =====================================================================
# 2. ROUTE: THÊM MỚI ĐƠN NGHỈ PHÉP
# =====================================================================
@leave_bp.route("/add_leave_request", methods=["GET", "POST"])
@login_required
@role_required('Admin')
def add_leave_request():
    if request.method == "POST":
        conn = get_connection()
        cursor = conn.cursor()
        try:
            employee_id = request.form.get("employee_id")
            
            cursor.execute('SELECT FullName FROM Employees WHERE EmployeeID = ? AND IsDeleted = 0', (employee_id,))
            emp_row = cursor.fetchone()
            if not emp_row:
                raise LeaveValidationError('Nhân viên không tồn tại hoặc đã bị xóa!')
            emp_name = emp_row[0]

            from_date = datetime.strptime(request.form["from_date"], '%Y-%m-%d').date()
            to_date = datetime.strptime(request.form["to_date"], '%Y-%m-%d').date()
            total_days = validate_leave_dates(from_date, to_date)

            leave_type = request.form.get("leave_type")
            validate_leave_type(leave_type)

            reason = normalize_reason(request.form.get("reason"))
            validate_reason(reason)

            # Kiểm tra trùng lịch nghỉ phép
            cursor.execute("""
                SELECT COUNT(*) FROM LeaveRequests 
                WHERE IsDeleted = 0 AND EmployeeID = ? AND (FromDate <= ? AND ToDate >= ?)
            """, (employee_id, to_date, from_date))
            if cursor.fetchone()[0] > 0:
                raise LeaveValidationError('Nhân viên đã có đơn nghỉ phép trùng trong khoảng thời gian này!')

            # MSSQL: Dùng ISNULL chuẩn
            cursor.execute("SELECT ISNULL(MAX(RequestID), 0) + 1 FROM LeaveRequests")
            next_id = cursor.fetchone()[0]
            leave_code = f"LR{next_id:04d}"

            request_date = datetime.now().date()
            created_by = "Admin"
            approved_by = None
            approved_date = None
            reject_reason = None
            status = "Chờ duyệt"

            cursor.execute("""
                INSERT INTO LeaveRequests
                (LeaveCode, EmployeeID, LeaveType, FromDate, ToDate, TotalDays, Reason, RequestDate, CreatedBy, ApprovedBy, ApprovedDate, RejectReason, Status, IsDeleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (leave_code, employee_id, leave_type, from_date, to_date, total_days, reason, request_date, created_by, approved_by, approved_date, reject_reason, status))

            conn.commit()

            create_notification(
                title='Đơn nghỉ phép mới',
                message=f'Đơn nghỉ phép ({leave_type}) của nhân viên {emp_name} đang chờ duyệt.',
                type='Success',
                receiver_role='Admin',
                url='/leave_requests'
            )

            log_activity(
                module="Leave",
                action="Create",
                description=f"Created leave request for employee {emp_name} from {from_date} to {to_date}."
            )

            flash("Thêm đơn nghỉ phép thành công!", "success")
            return redirect("/leave_requests")

        except LeaveValidationError as e:
            flash(str(e), 'danger')
            return redirect(request.url)
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Lỗi khi thêm đơn nghỉ phép: {str(e)}")
            flash("Đã có lỗi hệ thống xảy ra. Vui lòng thử lại sau!", "danger")
            return redirect(request.url)
        finally:
            conn.close()

    # GET Request
    employees = get_cached_active_employees()
    return render_template("leave/add_leave_request.html", employees=employees)


# =====================================================================
# 3. ROUTE: CHỈNH SỬA / DUYỆT ĐƠN NGHỈ PHÉP
# =====================================================================
@leave_bp.route("/edit_leave_request/<int:id>", methods=["GET", "POST"])
@login_required
@role_required('Admin', 'Manager')
def edit_leave_request(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM LeaveRequests WHERE RequestID = ? AND IsDeleted = 0', (id,))
        request_data = cursor.fetchone()

        if not request_data:
            flash('Đơn nghỉ phép không tồn tại hoặc đã bị xóa trước đó!', 'danger')
            return redirect("/leave_requests")

        if request.method == "POST":
            employee_id = request.form.get("employee_id")
            cursor.execute('SELECT FullName FROM Employees WHERE EmployeeID = ? AND IsDeleted = 0', (employee_id,))
            emp_row = cursor.fetchone()
            if not emp_row:
                raise LeaveValidationError('Nhân viên không tồn tại hoặc đã bị xóa!')
            emp_name = emp_row[0]

            from_date = datetime.strptime(request.form["from_date"], "%Y-%m-%d").date()
            to_date = datetime.strptime(request.form["to_date"], "%Y-%m-%d").date()
            total_days = validate_leave_dates(from_date, to_date)

            leave_type = request.form.get("leave_type")
            validate_leave_type(leave_type)

            reason = normalize_reason(request.form.get("reason"))
            validate_reason(reason)

            status = request.form.get("status")
            validate_leave_status(status)

            reject_reason = normalize_reject_reason(request.form.get("reject_reason"))
            validate_reject_reason(reject_reason, status)

            # Kiểm tra trùng lịch ngoại trừ đơn hiện tại
            cursor.execute("""
                SELECT COUNT(*) FROM LeaveRequests 
                WHERE IsDeleted = 0 AND EmployeeID = ? AND (FromDate <= ? AND ToDate >= ?) AND RequestID <> ?
            """, (employee_id, to_date, from_date, id))
            if cursor.fetchone()[0] > 0:
                raise LeaveValidationError('Đơn nghỉ phép trùng khoảng thời gian với đơn khác!')

            if status == "Đã duyệt":
                approved_by = "Admin"
                approved_date = datetime.now().date()
                reject_reason = None
            elif status == "Từ chối":
                approved_by = None
                approved_date = None
            else:
                approved_by = None
                approved_date = None
                reject_reason = None

            cursor.execute("""
                UPDATE LeaveRequests
                SET EmployeeID = ?, LeaveType = ?, FromDate = ?, ToDate = ?, TotalDays = ?, Reason = ?, 
                    ApprovedBy = ?, ApprovedDate = ?, RejectReason = ?, Status = ?
                WHERE RequestID = ?
            """, (employee_id, leave_type, from_date, to_date, total_days, reason, approved_by, approved_date, reject_reason, status, id))

            conn.commit()

            notification_type = 'Info'
            if status == 'Đã duyệt':
                notification_type = 'Success'
            elif status == 'Từ chối':
                notification_type = 'Warning'

            create_notification(
                title='Cập nhật đơn nghỉ phép',
                message=f'Đơn nghỉ phép của nhân viên {emp_name} đã chuyển sang trạng thái: {status}.',
                type=notification_type,
                receiver_role='Admin',
                url='/leave_requests'
            )

            log_activity(
                module="Leave",
                action="Update",
                record_id=id,
                description=f"Updated leave request for employee {emp_name} (Status: {status})."
            )

            flash("Cập nhật đơn nghỉ phép thành công!", "success")
            return redirect("/leave_requests")

    except LeaveValidationError as e:
        flash(str(e), 'danger')
        return redirect(request.url)
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi khi cập nhật đơn nghỉ phép ID {id}: {str(e)}")
        flash("Đã có lỗi hệ thống xảy ra. Vui lòng thử lại sau!", "danger")
        return redirect(request.url)
    finally:
        conn.close()

    # GET Request
    employees = get_cached_active_employees()
    return render_template("leave/edit_leave_request.html", request_data=request_data, employees=employees)


# =====================================================================
# 4. ROUTE: XÓA ĐƠN LẺ NGHỈ PHÉP (XÓA MỀM)
# =====================================================================
@leave_bp.route("/delete_leave_request/<int:id>")
@login_required
@role_required('Admin')
def delete_leave_request(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT E.FullName FROM LeaveRequests L 
            INNER JOIN Employees E ON L.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE L.RequestID = ? AND L.IsDeleted = 0
        """, (id,))
        emp_row = cursor.fetchone()
        
        if not emp_row:
            flash("Đơn nghỉ phép không tồn tại hoặc đã bị xóa trước đó!", "danger")
            return redirect("/leave_requests")
            
        emp_name = emp_row[0]

        cursor.execute("UPDATE LeaveRequests SET IsDeleted = 1 WHERE RequestID = ?", (id,))
        conn.commit()

        create_notification(
            title='Xóa đơn nghỉ phép',
            message=f'Đơn nghỉ phép của nhân viên {emp_name} đã bị xóa.',
            type='Warning',
            receiver_role='Admin',
            url='/leave_requests'
        )

        log_activity(
            module="Leave",
            action="Delete",
            record_id=id,
            description=f"Soft deleted leave request of employee {emp_name}."
        )

        flash("Xóa đơn nghỉ phép thành công (Xóa mềm)!", "success")
        return redirect("/leave_requests")
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi khi xóa đơn nghỉ phép ID {id}: {str(e)}")
        flash("Có lỗi hệ thống xảy ra khi thực hiện xóa!", "danger")
        return redirect("/leave_requests")
    finally:
        conn.close()


# =====================================================================
# 5. ROUTE: XÓA HÀNG LOẠT ĐƠN NGHỈ PHÉP
# =====================================================================
@leave_bp.route("/delete_selected_leave_requests", methods=["POST"])
@login_required
@role_required('Admin')
def delete_selected_leave_requests():
    request_ids = request.form.getlist("request_ids")
    if not request_ids:
        flash("Vui lòng chọn ít nhất một đơn nghỉ phép!", "warning")
        return redirect("/leave_requests")
        
    conn = get_connection()
    cursor = conn.cursor()
    try:
        placeholders = ', '.join(['?'] * len(request_ids))
        
        query_info = f"""
            SELECT L.RequestID, E.FullName FROM LeaveRequests L
            INNER JOIN Employees E ON L.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE L.RequestID IN ({placeholders}) AND L.IsDeleted = 0
        """
        cursor.execute(query_info, tuple(request_ids))
        records = cursor.fetchall()
        deleted_count = len(records)

        if deleted_count > 0:
            query_delete = f"UPDATE LeaveRequests SET IsDeleted = 1 WHERE RequestID IN ({placeholders})"
            cursor.execute(query_delete, tuple(request_ids))
            
            for row in records:
                req_id = row[0] if isinstance(row, tuple) else row.RequestID
                emp_name = row[1] if isinstance(row, tuple) else row.FullName
                log_activity(
                    module="Leave",
                    action="Delete",
                    record_id=int(req_id),
                    description=f"Soft deleted leave request of employee {emp_name}."
                )
                
            conn.commit()

            create_notification(
                title='Xóa nhiều đơn nghỉ phép',
                message=f'Đã xóa thành công {deleted_count} đơn nghỉ phép được chọn (Xóa mềm).',
                type='Warning',
                receiver_role='Admin',
                url='/leave_requests'
            )
            flash(f"Đã xóa thành công {deleted_count} đơn nghỉ phép được chọn (Xóa mềm)!", "success")
        else:
            flash("Không tìm thấy đơn nghỉ phép hợp lệ nào để tiến hành xóa!", "warning")

    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi khi xóa nhiều đơn nghỉ phép: {str(e)}")
        flash("Có lỗi hệ thống xảy ra khi thực hiện xóa hàng loạt!", "danger")
    finally:
        conn.close()

    return redirect("/leave_requests")


# =====================================================================
# 6. ROUTE: XUẤT FILE CSV DANH SÁCH ĐƠN NGHỈ PHÉP
# =====================================================================
@leave_bp.route("/export_leave_requests_csv")
@login_required
@role_required('Admin', 'Manager')
def export_leave_requests_csv():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                L.RequestID, L.LeaveCode, E.FullName, L.LeaveType, L.FromDate, L.ToDate,
                L.TotalDays, L.Reason, L.Status, L.ApprovedBy, L.ApprovedDate, L.RejectReason
            FROM LeaveRequests L
            INNER JOIN Employees E ON L.EmployeeID = E.EmployeeID AND E.IsDeleted = 0
            WHERE L.IsDeleted = 0
            ORDER BY L.RequestID DESC
        """)
        rows = cursor.fetchall()

        output = StringIO()
        output.write("\ufeff")
        writer = csv.writer(output)

        writer.writerow([
            "RequestID", "RequestCode", "Employee", "LeaveType", "FromDate", "ToDate",
            "TotalDays", "Reason", "Status", "ApprovedBy", "ApprovedDate", "RejectReason"
        ])

        for row in rows:
            if isinstance(row, tuple):
                writer.writerow(list(row))
            else:
                writer.writerow([
                    getattr(row, 'RequestID', row[0]), 
                    getattr(row, 'LeaveCode', row[1]), 
                    getattr(row, 'FullName', row[2]), 
                    getattr(row, 'LeaveType', row[3]), 
                    getattr(row, 'FromDate', row[4]), 
                    getattr(row, 'ToDate', row[5]),
                    getattr(row, 'TotalDays', row[6]), 
                    getattr(row, 'Reason', row[7]), 
                    getattr(row, 'Status', row[8]), 
                    getattr(row, 'ApprovedBy', row[9]), 
                    getattr(row, 'ApprovedDate', row[10]), 
                    getattr(row, 'RejectReason', row[11])
                ])

        log_activity(
            module="Leave",
            action="Export",
            description=f"Exported leave request list ({len(rows)} records)."
        )

        return Response(
            output.getvalue().encode("utf-8-sig"),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=leave_requests.csv"}
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi khi xuất file CSV danh sách nghỉ phép: {str(e)}")
        flash("Không thể xuất file CSV do lỗi hệ thống!", "danger")
        return redirect("/leave_requests")
    finally:
        conn.close()