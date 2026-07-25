import os
from dotenv import load_dotenv
load_dotenv()
from validators.employee_validator import *
from validators.department_validator import *
from validators.position_validator import *
from validators.contract_validator import *
from validators.salary_validator import *
from validators.attandance_validator import *
from validators.leave_validator import *
from database import get_connection
from routes.dashboard import dashboard_bp
from routes.employee import employee_bp
from routes.department import department_bp
from routes.position import position_bp
from routes.salary import salary_bp
from routes.contract import contract_bp
from routes.attendance import attendance_bp
from routes.leave import leave_bp
from routes.report import report_bp
from routes.auth import auth_bp
from routes.audit import audit_bp
from routes.notification import notification_bp
import config
from flask import Flask, render_template, request, redirect,flash, Response, url_for 
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta
from flask_caching import Cache
from werkzeug.exceptions import RequestEntityTooLarge
#  from flask import Flask; dùng để tạo một ứng dụng; render_template: dùng để hiện thị file HTMl và route tương ứng với nó sẽ được hoạt động 
# request: dùng để lấy dữ liệu người dùng gửi lên; redirect: dùng để chuyển sang trang khác; flash: dùng để hiện thông báo; dùng để tự tạo HTTP Response
import re, csv #kết nối database; kiểm tra định dạng dữ liệu; Xuất/ nhập file csv
from io import StringIO # tạo file văn bản giả trong RAM
from datetime import datetime
app = Flask(__name__) #Tạo một instance của ứng dụng Flask và gán nó cho biến app. Đây là bước khởi tạo cơ bản để bắt đầu xây dựng ứng dụng web với Flask.
app.secret_key= os.environ.get('FLASK_SECRET_KEY', 'default_fallback_key')# Đặt một khóa bí mật cho ứng dụng Flask, được sử dụng để bảo vệ dữ liệu phiên và các tính năng bảo mật khác.
csrf = CSRFProtect(app)
app.config['WTF_CSRF_ENABLED'] = False
from extensions import limiter
limiter.init_app(app)
cache = Cache(app, config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300  # Thời gian cache mặc định là 5 phút (300 giây)
})
app.config.update({
    "LIMITER_DEFAULT_LIMITS": ["200 per day", "50 per hour"],
    "LIMITER_STORAGE_URI": "memory://"
})
app.permanent_session_lifetime = timedelta(days=30)
app.config['SESSION_COOKIE_HTTPONLY']= True
app.config['SESSION_COOKIE_SAMESITE']= 'Lax'
# app.config['SESSIONN_COOKIE_SECURE'] = True
app.register_blueprint(dashboard_bp)
app.register_blueprint(employee_bp)
app.register_blueprint(department_bp)
app.register_blueprint(position_bp)
app.register_blueprint(salary_bp)
app.register_blueprint(contract_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(leave_bp)
app.register_blueprint(report_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(audit_bp)
app.register_blueprint(notification_bp)
app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
@app.context_processor
def inject_notification_count():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM Notifications
        WHERE IsRead = 0
    """)

    unread_count = cursor.fetchone()[0]

    conn.close()

    return dict(unread_count=unread_count)

# Thêm đoạn này vào cuối file app.py (trước dòng if __name__ == "__main__":)
@app.errorhandler(429)
def ratelimit_handler(e):
    flash("Bạn đã thao tác quá nhanh! Vui lòng đợi một lát rồi thử lại.", "danger")
    return render_template("errors/429.html"), 429
@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(e):
    flash("Dung lượng ảnh không được vượt quá 2MB.", "danger")
    return redirect(request.referrer or "/employees")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)