from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app
)
from validators.auth_validator import (
    validate_username,
    validate_password, 
    validate_confirm_password, 
    validate_old_password, 
    validate_new_password
)
from utils.auth import (
    hash_password,
    verify_password, 
    login_required
)
from database import get_connection
from extensions import limiter
from utils.audit import log_activity

auth_bp = Blueprint("auth", __name__)


# =====================================================================
# 1. ROUTE: ĐĂNG NHẬP (CÓ HỖ TRỢ MOCK DEMO CẬP NHẬT)
# =====================================================================
@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit('100 per minute')
def login():
    if request.method == "POST":
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember')

        username_error = validate_username(username)
        if username_error:
            flash(username_error, 'danger')
            return redirect(url_for('auth.login'))

        password_error = validate_password(password)
        if password_error:
            flash(password_error, 'danger')
            return redirect(url_for('auth.login'))

        # -------------------------------------------------------------
        # MOCK LOGIN DEMO CHO CLOUD/CV: TẢI KHOẢN ADMIN DỰ PHÒNG
        # -------------------------------------------------------------
        if username == "admin" and password == "123456":
            session['user_id'] = 1
            session['username'] = "admin"
            session['full_name'] = "Quản trị viên Demo"
            session['role'] = "Admin"
            session.permanent = bool(remember)

            flash('Đăng nhập Demo thành công với quyền Admin.', 'success')
            return redirect(url_for('dashboard.home'))
        # -------------------------------------------------------------

        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # MSSQL: Dùng ? làm tham số
            cursor.execute("SELECT UserID, Username, PasswordHash, FullName, Role, IsActive FROM Users WHERE Username = ?", (username,))
            user = cursor.fetchone()

            if user is None:
                flash('Tên đăng nhập không tồn tại.', 'danger')
                return redirect(url_for('auth.login'))

            if isinstance(user, tuple):
                user_id, db_username, password_hash, full_name, role, is_active = user[0], user[1], user[2], user[3], user[4], user[5]
            else:
                user_id = getattr(user, 'UserID', user[0])
                db_username = getattr(user, 'Username', user[1])
                password_hash = getattr(user, 'PasswordHash', user[2])
                full_name = getattr(user, 'FullName', user[3])
                role = getattr(user, 'Role', user[4])
                is_active = getattr(user, 'IsActive', user[5])

            if not verify_password(password, password_hash):
                flash('Mật khẩu không chính xác.', 'danger')
                return redirect(url_for('auth.login'))

            if not is_active:
                flash('Tài khoản đã bị khóa.', 'danger')
                return redirect(url_for('auth.login'))

            # MSSQL: Dùng GETDATE() và ? làm tham số
            cursor.execute("UPDATE Users SET LastLogin = GETDATE() WHERE UserID = ?", (user_id,))
            conn.commit()

            session['user_id'] = user_id
            session['username'] = db_username
            session['full_name'] = full_name
            session['role'] = role
            session.permanent = bool(remember)

            log_activity(
                module='Authentication', 
                action='Login', 
                description=f"User {db_username} logged in successfully."
            )

            flash('Đăng nhập thành công.', 'success')
            return redirect(url_for('dashboard.home'))

        except Exception as e:
            if conn:
                conn.rollback()
            current_app.logger.error(f"Lỗi hệ thống khi đăng nhập user '{username}': {str(e)}")
            flash("Không thể kết nối đến CSDL. Hãy sử dụng tài khoản Demo (admin / 123456)!", "warning")
            return redirect(url_for('auth.login'))
        finally:
            if conn:
                conn.close()

    return render_template("auth/login.html")


# =====================================================================
# 2. ROUTE: QUÊN MẬT KHẨU
# =====================================================================
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        username_error = validate_username(username)
        if username_error:
            flash(username_error, 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        password_error = validate_password(password)
        if password_error:
            flash(password_error, 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        confirm_error = validate_confirm_password(password, confirm_password)
        if confirm_error:
            flash(confirm_error, 'danger')
            return redirect(url_for('auth.forgot_password'))

        conn = get_connection()
        cursor = conn.cursor()
        try:
            # MSSQL: Dùng ? làm tham số
            cursor.execute("SELECT UserID FROM Users WHERE Username = ?", (username,))
            user = cursor.fetchone()

            if user is None:
                flash('Tên đăng nhập không tồn tại.', 'danger')
                return redirect(url_for('auth.forgot_password'))

            new_password_hash = hash_password(password)
            # MSSQL: Dùng ? làm tham số
            cursor.execute("UPDATE Users SET PasswordHash = ? WHERE Username = ?", (new_password_hash, username))
            conn.commit()

            log_activity(
                module='Authentication', 
                action='ForgotPassword', 
                description=f"User {username} reset password successfully."
            )

            flash('Đổi mật khẩu thành công. Vui lòng đăng nhập lại.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Lỗi hệ thống khi quên mật khẩu user '{username}': {str(e)}")
            flash("Đã có lỗi hệ thống xảy ra khi lấy lại mật khẩu!", "danger")
            return redirect(url_for('auth.forgot_password'))
        finally:
            conn.close()

    return render_template('auth/forgot_password.html')


# =====================================================================
# 3. ROUTE: ĐỔI MẬT KHẨU
# =====================================================================
@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        old_password_error = validate_old_password(old_password)
        if old_password_error:
            flash(old_password_error, 'danger')
            return redirect(url_for('auth.change_password'))
        
        new_password_error = validate_new_password(new_password)
        if new_password_error:
            flash(new_password_error, 'danger')
            return redirect(url_for('auth.change_password'))
        
        confirm_error = validate_confirm_password(new_password, confirm_password)
        if confirm_error:
            flash(confirm_error, 'danger')
            return redirect(url_for('auth.change_password'))

        user_id = session.get('user_id')
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # MSSQL: Dùng ? làm tham số
            cursor.execute("SELECT PasswordHash FROM Users WHERE UserID = ?", (user_id,))
            user = cursor.fetchone()

            db_password_hash = user[0] if isinstance(user, tuple) else getattr(user, 'PasswordHash', user[0])

            if not user or not verify_password(old_password, db_password_hash):
                flash('Mật khẩu hiện tại không đúng.', 'danger')
                return redirect(url_for('auth.change_password'))

            if verify_password(new_password, db_password_hash):
                flash('Mật khẩu mới phải khác với mật khẩu hiện tại.', 'danger')
                return redirect(url_for('auth.change_password'))

            new_password_hash = hash_password(new_password)
            # MSSQL: Dùng ? làm tham số
            cursor.execute("UPDATE Users SET PasswordHash = ? WHERE UserID = ?", (new_password_hash, user_id))
            conn.commit()

            username = session.get('username', 'Unknown')
            log_activity(
                module='Authentication', 
                action='ChangePassword', 
                description=f"User {username} changed password successfully."
            )

            session.clear()
            flash('Đổi mật khẩu thành công. Vui lòng đăng nhập lại.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Lỗi hệ thống khi đổi mật khẩu UserID {user_id}: {str(e)}")
            flash("Đã có lỗi hệ thống xảy ra khi đổi mật khẩu!", "danger")
            return redirect(url_for('auth.change_password'))
        finally:
            conn.close()

    return render_template('auth/change_password.html')


# =====================================================================
# 4. ROUTE: ĐĂNG XUẤT
# =====================================================================
@auth_bp.route("/logout")
def logout():
    try:
        username = session.get('username')
        if username:
            log_activity(
                module='Authentication',
                action='Logout', 
                description=f"User {username} logged out."
            )
    except Exception as e:
        current_app.logger.error(f"Lỗi ghi log khi đăng xuất: {str(e)}")
    finally:
        session.clear()
        flash("Đăng xuất thành công.", "success")
        return redirect(url_for("auth.login"))