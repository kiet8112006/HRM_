from flask import (
    Blueprint,
    render_template,
    redirect,
    session,
    flash,
    current_app
)
from database import get_connection
from utils.auth import login_required
from datetime import datetime

notification_bp = Blueprint("notification", __name__)


# =====================================================================
# HÀM HỖ TRỢ: TÍNH THỜI GIAN TƯƠNG ĐỐI (TIME AGO)
# =====================================================================
def time_ago(created_time):
    if not created_time or not isinstance(created_time, datetime):
        return ""

    now = datetime.now()
    diff = now - created_time
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "Vừa xong"
    elif seconds < 3600:
        return f"{seconds // 60} phút trước"
    elif seconds < 86400:
        return f"{seconds // 3600} giờ trước"
    elif seconds < 604800:
        return f"{diff.days} ngày trước"

    return created_time.strftime("%d/%m/%Y")


# =====================================================================
# HÀM HỖ TRỢ: LẤY SỐ LƯỢNG THÔNG BÁO CHƯA ĐỌC (CONTEXT PROCESSOR / UTIL)
# =====================================================================
def get_unread_count():
    role = session.get('role')
    if not role:
        return 0

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # MSSQL: Dùng ? làm tham số
        cursor.execute("""
            SELECT COUNT(*)
            FROM Notifications
            WHERE IsRead = 0 AND (ReceiverRole = ? OR ReceiverRole IS NULL)
        """, (role,))
        count = cursor.fetchone()[0]
        return count
    except Exception as e:
        current_app.logger.error(f"Lỗi khi đếm số thông báo chưa đọc: {str(e)}")
        return 0
    finally:
        conn.close()


# =====================================================================
# 1. ROUTE: DANH SÁCH THÔNG BÁO
# =====================================================================
@notification_bp.route("/notifications")
@login_required
def notifications():
    role = session.get('role')

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # MSSQL: Dùng ? làm tham số
        cursor.execute("""
            SELECT
                NotificationID,
                Title,
                Message,
                Type,
                Url,
                IsRead,
                CreatedAt
            FROM Notifications
            WHERE ReceiverRole = ? OR ReceiverRole IS NULL
            ORDER BY CreatedAt DESC
        """, (role,))
        rows = cursor.fetchall()

        notification_data = []
        for n in rows:
            # Tương thích linh hoạt với cả Tuple lẫn pyodbc Row object
            if isinstance(n, tuple):
                n_id, title, message, n_type, url, is_read, created_at = n[0], n[1], n[2], n[3], n[4], n[5], n[6]
            else:
                n_id = getattr(n, 'NotificationID', n[0])
                title = getattr(n, 'Title', n[1])
                message = getattr(n, 'Message', n[2])
                n_type = getattr(n, 'Type', n[3])
                url = getattr(n, 'Url', n[4])
                is_read = getattr(n, 'IsRead', n[5])
                created_at = getattr(n, 'CreatedAt', n[6])

            notification_data.append({
                'NotificationID': n_id,
                'Title': title,
                'Message': message,
                'Type': n_type,
                'Url': url,
                'Isread': is_read,
                'CreatedAt': created_at,
                'TimeAgo': time_ago(created_at)
            })

        # MSSQL: Lọc unread dùng ?
        cursor.execute("""
            SELECT COUNT(*)
            FROM Notifications
            WHERE IsRead = 0 AND (ReceiverRole = ? OR ReceiverRole IS NULL)
        """, (role,))
        unread_count = cursor.fetchone()[0]

        return render_template(
            "notification/notifications.html",
            notifications=notification_data,
            unread_count=unread_count
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi khi lấy danh sách thông báo: {str(e)}")
        flash("Có lỗi hệ thống xảy ra khi tải danh sách thông báo!", "danger")
        return render_template("notification/notifications.html", notifications=[], unread_count=0)
    finally:
        conn.close()


# =====================================================================
# 2. ROUTE: ĐÁNH DẤU 1 THÔNG BÁO ĐÃ ĐỌC
# =====================================================================
@notification_bp.route("/notification/read/<int:id>")
@login_required
def read_notification(id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # MSSQL: Dùng ? làm tham số
        cursor.execute("""
            UPDATE Notifications
            SET IsRead = 1
            WHERE NotificationID = ?
        """, (id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi khi đánh dấu đã đọc thông báo ID {id}: {str(e)}")
    finally:
        conn.close()

    return redirect("/notifications")


# =====================================================================
# 3. ROUTE: ĐÁNH DẤU TẤT CẢ THÔNG BÁO ĐÃ ĐỌC
# =====================================================================
@notification_bp.route("/notifications/read_all")
@login_required
def read_all_notifications():
    role = session.get('role')

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # MSSQL: Dùng ? làm tham số
        cursor.execute("""
            UPDATE Notifications
            SET IsRead = 1
            WHERE IsRead = 0 AND (ReceiverRole = ? OR ReceiverRole IS NULL)
        """, (role,))
        conn.commit()
        flash("Đã đánh dấu đọc tất cả thông báo!", "success")
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Lỗi khi đánh dấu đọc tất cả thông báo: {str(e)}")
        flash("Có lỗi xảy ra khi cập nhật trạng thái thông báo!", "danger")
    finally:
        conn.close()

    return redirect("/notifications")