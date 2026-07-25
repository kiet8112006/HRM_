import os
import io
import pytest
from PIL import Image
from unittest.mock import patch, MagicMock

# Import các hàm từ module của cậu (chỉnh đường dẫn import nếu cần)
from utils.upload import (
    allowed_mimetype,
    verify_image,
    allowed_file,
    allowed_document,
    resize_image,
    delete_file,
    delete_image,
    delete_contract,
    save_image_file,
    save_document_file,
    save_avatar,
    save_citizen_front,
    save_citizen_back,
    save_contract,
    ALLOWED_IMAGE_MIME
)


# =====================================================================
# FIXTURES & HELPERS
# =====================================================================

def create_dummy_image(format='PNG', mode='RGB', size=(100, 100)):
    """Tạo đối tượng File Stream ảnh thật trong bộ nhớ để test"""
    img_byte_arr = io.BytesIO()
    image = Image.new(mode, size, color='red')
    image.save(img_byte_arr, format=format)
    img_byte_arr.seek(0)
    return img_byte_arr


# =====================================================================
# 1. TEST HÀM VALIDATE CHECKERS & VERIFIERS
# =====================================================================

class TestMediaCheckers:

    # --- Test MIME Type ---
    def test_allowed_mimetype(self):
        mock_file = MagicMock()
        mock_file.mimetype = "image/png"
        assert allowed_mimetype(mock_file) is True

        mock_file.mimetype = "application/pdf"
        assert allowed_mimetype(mock_file) is False
        assert allowed_mimetype(None) is None

    # --- Test Image Verification (Pillow) ---
    def test_verify_image_valid(self):
        """File ảnh hợp lệ -> Trả về True và reset pointer"""
        img_stream = create_dummy_image('PNG')
        mock_file = MagicMock()
        mock_file.read.side_effect = img_stream.read
        mock_file.seek.side_effect = img_stream.seek

        assert verify_image(mock_file) is True
        assert img_stream.tell() == 0

    def test_verify_image_invalid(self):
        """File không phải ảnh -> Logger warning và trả về False"""
        fake_stream = io.BytesIO(b"NOT_AN_IMAGE")
        mock_file = MagicMock()
        mock_file.read.side_effect = fake_stream.read
        mock_file.seek.side_effect = fake_stream.seek

        assert verify_image(mock_file) is False

    # --- Test Extensions ---
    def test_allowed_file(self):
        with patch('config.ALLOWED_EXTENSIONS', {'png', 'jpg'}):
            assert allowed_file("avatar.png") is True
            assert allowed_file("file.txt") is False

    def test_allowed_document(self):
        with patch('config.ALLOWED_DOCUMENT_EXTENSIONS', {'pdf', 'docx'}):
            assert allowed_document("contract.pdf") is True
            assert allowed_document("virus.exe") is False


# =====================================================================
# 2. TEST HÀM RESIZE & CONVERT WEBP
# =====================================================================

class TestResizeImage:

    def test_resize_image_success(self, tmp_path):
        """Convert ảnh JPG/PNG thành WEBP, resize và dọn dẹp file gốc thành công"""
        # Tạo file ảnh gốc tạm thời trên đĩa
        original_filepath = str(tmp_path / "test_image.png")
        image = Image.new('RGBA', (800, 800), color='blue')
        image.save(original_filepath, 'PNG')

        # Chạy hàm resize_image
        webp_path = resize_image(original_filepath, max_size=(400, 400))

        # Asserts
        assert webp_path.endswith(".webp")
        assert os.path.exists(webp_path)
        assert not os.path.exists(original_filepath) # File gốc .png đã bị xóa

        # Kiểm tra kích thước sau khi resize
        with Image.open(webp_path) as resized_img:
            assert resized_img.size[0] <= 400
            assert resized_img.size[1] <= 400

    def test_resize_image_exception_cleans_up(self):
        """Khi convert bị lỗi -> Logger ghi lỗi và dọn dẹp file tạm nếu có"""
        fake_filepath = "/tmp/non_existent_file.jpg"
        expected_new_path = "/tmp/non_existent_file.webp"

        with patch('PIL.Image.open', side_effect=Exception("Corrupt image")), \
             patch('os.path.exists', return_value=True), \
             patch('os.remove') as mock_remove:

            with pytest.raises(Exception, match="Corrupt image"):
                resize_image(fake_filepath)

            # Đảm bảo dọn dẹp file new_path nếu nó lỡ được tạo
            mock_remove.assert_called_once_with(expected_new_path)


# =====================================================================
# 3. TEST HÀM XÓA FILE (delete_file)
# =====================================================================

class TestDeleteFile:

    def test_delete_file_success(self):
        root_path = "/var/www/app"
        relative_path = "avatars/user1.webp"
        expected_full_path = os.path.join(root_path, 'static', relative_path)

        with patch('os.path.exists', return_value=True), \
             patch('os.remove') as mock_remove:

            delete_file(root_path, relative_path)
            mock_remove.assert_called_once_with(expected_full_path)

    def test_delete_file_empty_or_none(self):
        with patch('os.remove') as mock_remove:
            delete_file("/app", "")
            delete_file("/app", None)
            mock_remove.assert_not_called()

    def test_delete_file_exception_handled(self):
        """Gặp lỗi OS khi xóa -> Logger log lỗi, không crash app"""
        with patch('os.path.exists', return_value=True), \
             patch('os.remove', side_effect=PermissionError("Access denied")), \
             patch('utils.media_utils.logger.error') as mock_log:

            delete_file("/app", "avatars/user1.webp")
            mock_log.assert_called_once()

    def test_aliases(self):
        """Kiểm tra 2 Alias delete_image và delete_contract trỏ đúng hàm"""
        assert delete_image == delete_file
        assert delete_contract == delete_file


# =====================================================================
# 4. TEST SAVE IMAGE & DOCUMENT FILES
# =====================================================================

class TestSaveFiles:

    # --- Test save_image_file ---
    def test_save_image_file_success(self):
        mock_file = MagicMock()
        mock_file.filename = "my_photo.PNG"

        with patch('utils.media_utils.verify_image', return_value=True), \
             patch('os.makedirs') as mock_makedirs, \
             patch('utils.media_utils.resize_image', return_value="/uploads/avatars/uuid123.webp"):

            result = save_image_file(mock_file, "/uploads/avatars", "avatars/employees")

            mock_makedirs.assert_called_once_with("/uploads/avatars", exist_ok=True)
            mock_file.save.assert_called_once()
            assert result == "avatars/employees/uuid123.webp"

    def test_save_image_file_invalid_image(self):
        mock_file = MagicMock()
        with patch('utils.media_utils.verify_image', return_value=False):
            with pytest.raises(ValueError, match="File tải lên không phải là hình ảnh hợp lệ."):
                save_image_file(mock_file, "/uploads", "relative")

    def test_save_image_file_exception_cleans_temp(self):
        """Khi lưu bị lỗi -> Raise RuntimeError và dọn dẹp temp_filepath"""
        mock_file = MagicMock()
        mock_file.filename = "photo.jpg"
        mock_file.save.side_effect = Exception("Disk write error")

        with patch('utils.media_utils.verify_image', return_value=True), \
             patch('os.makedirs'), \
             patch('os.path.exists', return_value=True), \
             patch('os.remove') as mock_remove:

            with pytest.raises(RuntimeError, match="Không thể lưu file ảnh vào hệ thống."):
                save_image_file(mock_file, "/uploads", "relative")

            mock_remove.assert_called_once()

    # --- Test save_document_file ---
    def test_save_document_file_success(self):
        mock_file = MagicMock()
        mock_file.filename = "hop_dong.pdf"

        with patch('utils.media_utils.allowed_document', return_value=True), \
             patch('os.makedirs') as mock_makedirs:

            result = save_document_file(mock_file, "/uploads/contracts", "documents/contracts")

            mock_makedirs.assert_called_once_with("/uploads/contracts", exist_ok=True)
            mock_file.save.assert_called_once()
            assert result.startswith("documents/contracts/")
            assert result.endswith(".pdf")

    def test_save_document_file_unsupported_type(self):
        mock_file = MagicMock()
        mock_file.filename = "script.sh"

        with patch('utils.media_utils.allowed_document', return_value=False):
            with pytest.raises(ValueError, match="Định dạng tài liệu không được hỗ trợ."):
                save_document_file(mock_file, "/uploads", "relative")


# =====================================================================
# 5. TEST WRAPPER FUNCTIONS
# =====================================================================

class TestWrappers:

    def test_save_avatar_wrapper(self):
        mock_file = MagicMock()
        with patch('config.AVATAR_UPLOAD_FOLDER', '/path/avatars'), \
             patch('utils.media_utils.save_image_file', return_value='avatars/employees/1.webp') as mock_save:

            res = save_avatar(mock_file)
            mock_save.assert_called_once_with(mock_file, '/path/avatars', 'avatars/employees')
            assert res == 'avatars/employees/1.webp'

    def test_save_citizen_front_wrapper(self):
        mock_file = MagicMock()
        with patch('config.CITIZEN_FRONT_FOLDER', '/path/front'), \
             patch('utils.media_utils.save_image_file', return_value='documents/citizen/front/1.webp') as mock_save:

            res = save_citizen_front(mock_file)
            mock_save.assert_called_once_with(mock_file, '/path/front', 'documents/citizen/front')
            assert res == 'documents/citizen/front/1.webp'

    def test_save_citizen_back_wrapper(self):
        mock_file = MagicMock()
        with patch('config.CITIZEN_BACK_FOLDER', '/path/back'), \
             patch('utils.media_utils.save_image_file', return_value='documents/citizen/back/1.webp') as mock_save:

            res = save_citizen_back(mock_file)
            mock_save.assert_called_once_with(mock_file, '/path/back', 'documents/citizen/back')
            assert res == 'documents/citizen/back/1.webp'

    def test_save_contract_wrapper(self):
        mock_file = MagicMock()
        with patch('config.CONTRACT_FOLDER', '/path/contracts'), \
             patch('utils.media_utils.save_document_file', return_value='documents/contracts/1.pdf') as mock_save:

            res = save_contract(mock_file)
            mock_save.assert_called_once_with(mock_file, '/path/contracts', 'documents/contracts')
            assert res == 'documents/contracts/1.pdf'