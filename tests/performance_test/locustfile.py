import re
import random
from locust import HttpUser, task, between

class HRMPerformanceUser(HttpUser):
    # Thời gian nghỉ giữa các thao tác: 1 - 3 giây
    wait_time = between(1, 3)

    def on_start(self):
        """
        Khởi tạo user: Tải trang /login lấy CSRF token -> Thực hiện POST đăng nhập
        """
        # 1. Truy cập GET /login lấy cookie session & HTML
        res_get = self.client.get("/login")
        
        # 2. Tìm csrf_token từ Form HTML
        csrf_token = ""
        match = re.search(r'name="csrf_token"\s+type="hidden"\s+value="([^"]+)"', res_get.text)
        if match:
            csrf_token = match.group(1)
        else:
            # Tìm trường hợp đảo vị trí thuộc tính HTML
            match_alt = re.search(r'value="([^"]+)"\s+name="csrf_token"', res_get.text)
            if match_alt:
                csrf_token = match_alt.group(1)

        # 3. Gửi request POST login đầy đủ tham số
        self.client.post("/login", data={
            "username": "admin",
            "password": "123456",  # Đảm bảo mật khẩu đúng với tài khoản admin trong DB
            "csrf_token": csrf_token,
            "remember": "y"
        })

    @task(3)
    def test_dashboard(self):
        self.client.get("/", name="[GET] / Dashboard")

    @task(2)
    def test_employees(self):
        page = random.randint(1, 5)
        self.client.get(f"/employees?page={page}", name="[GET] /employees")

    @task(2)
    def test_notifications(self):
        self.client.get("/notifications", name="[GET] /notifications")

    @task(1)
    def test_audit_logs(self):
        self.client.get("/audit_logs", name="[GET] /audit_logs")