import os
import uuid
import logging
from PIL import Image
from werkzeug.utils import secure_filename
import config

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_MIME = {
    "image/jpeg",
    "image/png",
    "image/webp"
}

def allowed_mimetype(file):
    return file and file.mimetype in ALLOWED_IMAGE_MIME

def verify_image(file):
    """Kiểm tra file có thực sự là ảnh hợp lệ hay không."""
    try:
        image = Image.open(file)
        image.verify()
        file.seek(0) # Đưa con trỏ file về đầu để đọc lại sau này
        return True
    except Exception as e:
        logger.warning(f"File tải lên không phải là ảnh hợp lệ: {str(e)}")
        return False

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS
    )

def allowed_document(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_DOCUMENT_EXTENSIONS
    )

def resize_image(filepath, max_size=(400, 400)):
    """Resize và chuyển đổi ảnh sang định dạng WEBP."""
    new_path = filepath.rsplit('.', 1)[0] + '.webp'
    try:
        with Image.open(filepath) as img:
            img.thumbnail(max_size)
            # FIX BUG: Sửa 'RGGBA' thành 'RGBA'
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            img.save(new_path, 'WEBP', quality=85, method=6)
        
        # Xóa file gốc sau khi đã convert thành công
        if os.path.exists(filepath) and filepath != new_path:
            os.remove(filepath)
            
        return new_path
    except Exception as e:
        logger.error(f"Lỗi khi xử lý/resize ảnh '{filepath}': {str(e)}", exc_info=True)
        # Nếu convert lỗi, dọn dẹp file tạm nếu có
        if os.path.exists(new_path):
            os.remove(new_path)
        raise e

def delete_file(root_path, relative_path):
    """Hàm dùng chung để xóa file/ảnh an toàn."""
    if not relative_path:
        return
    try:
        filepath = os.path.join(root_path, 'static', relative_path)
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Đã xóa file: {filepath}")
    except Exception as e:
        logger.error(f"Lỗi khi xóa file '{relative_path}': {str(e)}")

# Giữ lại Alias để không làm gãy code cũ đang gọi
delete_image = delete_file
delete_contract = delete_file

def save_image_file(file, upload_folder, relative_folder):
    """Lưu và tối ưu hóa FILE ẢNH (Avatar, CCCD...)."""
    if not verify_image(file):
        raise ValueError("File tải lên không phải là hình ảnh hợp lệ.")

    file_id = uuid.uuid4().hex
    extension = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "jpg"
    temp_filename = f"{file_id}.{extension}"
    temp_filepath = os.path.join(upload_folder, temp_filename)

    try:
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(upload_folder, exist_ok=True)
        
        file.save(temp_filepath)
        new_filepath = resize_image(temp_filepath)
        filename = os.path.basename(new_filepath)
        
        return f"{relative_folder}/{filename}"
    except Exception as e:
        logger.error(f"Thất bại khi lưu ảnh vào '{upload_folder}': {str(e)}", exc_info=True)
        # Dọn dẹp file tạm nếu lưu thất bại
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        raise RuntimeError("Không thể lưu file ảnh vào hệ thống.") from e

def save_document_file(file, upload_folder, relative_folder):
    """Lưu TÀI LIỆU/HỢP ĐỒNG (PDF, DOCX...) - Không convert WebP."""
    if not allowed_document(file.filename):
        raise ValueError("Định dạng tài liệu không được hỗ trợ.")

    file_id = uuid.uuid4().hex
    extension = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{file_id}.{extension}"
    filepath = os.path.join(upload_folder, filename)

    try:
        os.makedirs(upload_folder, exist_ok=True)
        file.save(filepath)
        return f"{relative_folder}/{filename}"
    except Exception as e:
        logger.error(f"Thất bại khi lưu tài liệu vào '{upload_folder}': {str(e)}", exc_info=True)
        if os.path.exists(filepath):
            os.remove(filepath)
        raise RuntimeError("Không thể lưu tài liệu vào hệ thống.") from e

# --- Wrapper functions ---

def save_avatar(file):
    return save_image_file(file, config.AVATAR_UPLOAD_FOLDER, "avatars/employees")

def save_citizen_front(file):
    return save_image_file(file, config.CITIZEN_FRONT_FOLDER, "documents/citizen/front")

def save_citizen_back(file):
    return save_image_file(file, config.CITIZEN_BACK_FOLDER, "documents/citizen/back")

def save_contract(file):
    # FIX BUG: Hợp đồng dùng save_document_file thay vì save_image_file
    return save_document_file(file, config.CONTRACT_FOLDER, "documents/contracts")