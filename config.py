import os

# Thư mục gốc của dự án
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Thư mục lưu ảnh nhân viên
UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "avatars",
    "employees"
)
CONTRACT_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "documents",
    "contracts"
)
# Định dạng ảnh được phép
ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}
ALLOWED_DOCUMENT_EXTENSIONS = {
    "pdf"
}
# Kích thước tối đa: 2MB
MAX_CONTENT_LENGTH = 2 * 1024 * 1024