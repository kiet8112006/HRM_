"""
FILE CẤU HÌNH DỮ LIỆU SEED (SEEDER CONFIGURATION)
Quản lý tập trung quy mô sinh dữ liệu cho toàn bộ các script trong thư mục scripts/
"""

# =====================================================================
# 1. CẤU HÌNH SỐ LƯỢNG BẢN GHI (KÍCH THƯỚC DỮ LIỆU SEED)
# =====================================================================

# Số lượng Nhân viên cần tạo
NUM_EMPLOYEES = 100

# Số lượng Hợp đồng lao động cần tạo
NUM_CONTRACTS = 100

# Số lượng Bảng lương cần tạo
NUM_SALARIES = 300

# Số lượng Đơn nghỉ phép cần tạo
NUM_LEAVE_REQUESTS = 150

# Số lượng Bản ghi Chấm công cần tạo
NUM_ATTENDANCES = 500


# =====================================================================
# 2. CẤU HÌNH THỜI GIAN & HỆ THỐNG
# =====================================================================

# Định dạng ngày tháng chuẩn CSDL
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Cấu hình BATCH_SIZE cho executemany() khi cần insert số lượng cực lớn
BATCH_SIZE = 1000