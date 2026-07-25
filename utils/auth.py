from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from functools import wraps
from flask import (
    session,
    redirect,
    url_for,
    flash,
    request,
    jsonify
)
from utils.audit import log_activity

def hash_password(password):
    return generate_password_hash(password)

def verify_password(plain_password, password_hash):
    if not password_hash or not plain_password:
        return False
    
    # 1. So sánh trực tiếp nếu mật khẩu trong DB lưu dạng plain text
    if str(plain_password) == str(password_hash):
        return True
        
    # 2. So sánh bằng Werkzeug (Đã sửa đúng thứ tự: check_password_hash(HASH, PLAIN))
    try:
        return check_password_hash(str(password_hash), str(plain_password))
    except Exception:
        # Trong trường hợp chuỗi hash không đúng format của Werkzeug
        return False

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            # Nếu request gửi từ API hoặc Locust đòi JSON
            if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"error": "Unauthorized", "message": "Vui lòng đăng nhập."}), 401
            
            flash("Vui lòng đăng nhập để tiếp tục.", "warning")
            return redirect(url_for("auth.login"))

        return view(*args, **kwargs)

    return wrapped_view

def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if "user_id" not in session:
                if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return jsonify({"error": "Unauthorized", "message": "Vui lòng đăng nhập."}), 401
                
                flash("Vui lòng đăng nhập để tiếp tục.", "warning")
                return redirect(url_for("auth.login"))

            user_role = session.get("role")

            if user_role not in roles:
                if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return jsonify({"error": "Forbidden", "message": "Không có quyền truy cập."}), 403

                flash("Bạn không có quyền truy cập chức năng này.", "danger")
                return redirect(url_for("dashboard.home"))

            return view(*args, **kwargs)

        return wrapped_view

    return decorator