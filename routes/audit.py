from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    flash,
    Response,
    current_app
)
from database import get_connection
from utils.auth import login_required, role_required
from utils.audit import log_activity
import csv
import io

audit_bp = Blueprint("audit", __name__)


# =====================================================================
# 1. ROUTE: DANH SÁCH NHẬT KÝ HỆ THỐNG (AUDIT LOGS)
# =====================================================================
@audit_bp.route("/audit_logs")
@login_required
@role_required("Admin")
def audit_logs():
    keyword = request.args.get("keyword", "").strip()
    module = request.args.get("module", "").strip()
    action = request.args.get("action", "").strip()

    page = request.args.get("page", 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Sửa logic search: (Username LIKE OR Description LIKE) thay vì AND
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM AuditLogs
            WHERE (Username LIKE ? OR Description LIKE ?)
              AND Module LIKE ?
              AND Action LIKE ?
            """,
            (
                f"%{keyword}%",
                f"%{keyword}%",
                f"%{module}%",
                f"%{action}%"
            )
        )
        total_records = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT
                LogID,
                UserID,
                Username,
                Role,
                Module,
                Action,
                RecordID,
                Description,
                IPAddress,
                UserAgent,
                CreatedAt
            FROM AuditLogs
            WHERE (Username LIKE ? OR Description LIKE ?)
              AND Module LIKE ?
              AND Action LIKE ?
            ORDER BY CreatedAt DESC
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
            """,
            (
                f"%{keyword}%",
                f"%{keyword}%",
                f"%{module}%",
                f"%{action}%",
                offset,
                per_page
            )
        )
        logs = cursor.fetchall()

        total_pages = max(1, (total_records + per_page - 1) // per_page)

        return render_template(
            "audit/audit_logs.html",
            logs=logs,
            keyword=keyword,
            module=module,
            action=action,
            page=page,
            total_pages=total_pages
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi khi tải nhật ký hệ thống (Audit Logs): {str(e)}")
        flash("Đã có lỗi hệ thống xảy ra khi truy vấn nhật ký!", "danger")
        return render_template(
            "audit/audit_logs.html", 
            logs=[], 
            keyword=keyword, 
            module=module, 
            action=action, 
            page=1, 
            total_pages=1
        )
    finally:
        conn.close()


# =====================================================================
# 2. ROUTE: XUẤT FILE CSV NHẬT KÝ HỆ THỐNG
# =====================================================================
@audit_bp.route("/audit_logs/export")
@login_required
@role_required("Admin")
def export_audit_logs_csv():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                CreatedAt,
                Username,
                Role,
                Module,
                Action,
                Description,
                IPAddress,
                UserAgent
            FROM AuditLogs
            ORDER BY CreatedAt DESC
        """)
        rows = cursor.fetchall()

        output = io.StringIO()
        output.write('\ufeff')  # Đảm bảo hiển thị đúng font tiếng Việt trên Excel
        writer = csv.writer(output)

        writer.writerow([
            "Time",
            "Username",
            "Role",
            "Module",
            "Action",
            "Description",
            "IP Address",
            "Browser"
        ])

        for row in rows:
            writer.writerow(row)
        
        log_activity(
            module='Audit', 
            action='Export', 
            description=f'Exported audit log ({len(rows)} records).'
        )

        return Response(
            output.getvalue().encode('utf-8-sig'),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_logs.csv"}
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi khi xuất file CSV Audit Logs: {str(e)}")
        flash("Không thể xuất file CSV do lỗi hệ thống!", "danger")
        return redirect("/audit_logs")
    finally:
        conn.close()