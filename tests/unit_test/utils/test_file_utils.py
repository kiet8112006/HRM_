import os
import io
import pytest
from unittest.mock import patch, MagicMock

# Import các hàm từ module utils (chỉnh lại đường dẫn import nếu cần)
from utils.document_upload import (
    allowed_document,
    allowed_document_mimetype,
    verify_pdf,
    generate_document_filename,
    save_contract,
    delete_contract_file,
    ALLOWED_DOCUMENT_MIME
)


# =====================================================================
# 1. TEST HÀM VALIDATE VÀ VERIFY FILE
# =====================================================================

class TestFileValidation:

    # --- Test Extension ---
    def test_allowed_document_valid(self, app):
        """File có extension nằm trong ALLOWED_DOCUMENT_EXTENSIONS cho phép"""
        with patch('config.ALLOWED_DOCUMENT_EXTENSIONS', {'pdf', 'docx'}):
            assert allowed_document("hop_dong.pdf") is True
            assert allowed_document("contract.DOCX") is True

    def test_allowed_document_invalid(self, app):
        """File không có extension hoặc extension không hợp lệ"""
        with patch('config.ALLOWED_DOCUMENT_EXTENSIONS', {'pdf'}):
            assert allowed_document("script.exe") is False
            assert allowed_document("filename_without_extension") is False
            assert allowed_document("") is False

    # --- Test MIME Type ---
    def test_allowed_document_mimetype_valid(self):
        """MIME type thuộc danh sách ALLOWED_DOCUMENT_MIME"""
        mock_file = MagicMock()
        mock_file.mimetype = "application/pdf"
        assert allowed_document_mimetype(mock_file) is True

    def test_allowed_document_mimetype_invalid(self):
        """MIME type không thuộc danh sách cho phép"""
        mock_file = MagicMock()
        mock_file.mimetype = "image/png"
        assert allowed_document_mimetype(mock_file) is False

    # --- Test Header PDF Verification ---
    def test_verify_pdf_valid_header(self):
        """File stream bắt đầu bằng 5 bytes magic header %PDF-"""
        pdf_stream = io.BytesIO(b"%PDF-1.7\n%...")
        mock_file = MagicMock()
        mock_file.read.side_effect = pdf_stream.read
        mock_file.seek.side_effect = pdf_stream.seek

        assert verify_pdf(mock_file) is True
        # Đảm bảo file pointer được reset về lại vị trí 0 sau khi đọc
        assert pdf_stream.tell() == 0

    def test_verify_pdf_invalid_header(self):
        """File stream chứa dữ liệu rác không phải header PDF"""
        fake_stream = io.BytesIO(b"NOT_A_PDF_FILE")
        mock_file = MagicMock()
        mock_file.read.side_effect = fake_stream.read
        mock_file.seek.side_effect = fake_stream.seek

        assert verify_pdf(mock_file) is False

    def test_verify_pdf_exception_handling(self):
        """Ngoại lệ xảy ra khi đọc file -> Trả về False"""
        mock_file = MagicMock()
        mock_file.read.side_effect = Exception("Read error")

        assert verify_pdf(mock_file) is False


# =====================================================================
# 2. TEST HÀM GENERATE & FILE I/O (SAVE & DELETE)
# =====================================================================

class TestFileOperations:

    # --- Test Filename Generator ---
    def test_generate_document_filename(self):
        """Đổi tên file thành UUID mới và giữ nguyên extension dạng chữ thường"""
        mock_file = MagicMock()
        mock_file.filename = "my_contract_v1.PDF"

        generated_name = generate_document_filename(mock_file)

        # Đảm bảo đuôi file chuyển về chữ thường (.pdf)
        assert generated_name.endswith(".pdf")
        # Đảm bảo có cấu trúc UUID_HEX (32 ký tự hex + 1 dấu . + 3 ký tự ext)
        assert len(generated_name) == 32 + 1 + 3
        assert generated_name != "my_contract_v1.pdf"

    # --- Test Save Contract File ---
    def test_save_contract(self):
        """Lưu file hợp đồng vào thư mục config.CONTRACT_FOLDER"""
        mock_file = MagicMock()
        mock_file.filename = "hop_dong_lao_dong.pdf"

        fake_folder = "/var/uploads/contracts"

        with patch('config.CONTRACT_FOLDER', fake_folder), \
             patch('utils.file_utils.generate_document_filename', return_value="abc123hex.pdf"):

            saved_filename = save_contract(mock_file)

            # Kiểm tra đường dẫn lưu file hợp lệ
            expected_filepath = os.path.join(fake_folder, "abc123hex.pdf")
            mock_file.save.assert_called_once_with(expected_filepath)
            assert saved_filename == "abc123hex.pdf"

    # --- Test Delete Contract File ---
    def test_delete_contract_file_exists(self):
        """Thực hiện xóa file nếu file tồn tại trên đĩa"""
        fake_folder = "/var/uploads/contracts"
        filename = "abc123hex.pdf"
        expected_path = os.path.join(fake_folder, filename)

        with patch('config.CONTRACT_FOLDER', fake_folder), \
             patch('os.path.exists', return_value=True) as mock_exists, \
             patch('os.remove') as mock_remove:

            delete_contract_file(filename)

            mock_exists.assert_called_once_with(expected_path)
            mock_remove.assert_called_once_with(expected_path)

    def test_delete_contract_file_not_exists(self):
        """Không gọi os.remove nếu file không tồn tại"""
        fake_folder = "/var/uploads/contracts"
        filename = "non_existent.pdf"

        with patch('config.CONTRACT_FOLDER', fake_folder), \
             patch('os.path.exists', return_value=False), \
             patch('os.remove') as mock_remove:

            delete_contract_file(filename)

            mock_remove.assert_not_called()

    def test_delete_contract_file_empty_filename(self):
        """Tên file rỗng hoặc None -> Bỏ qua không thực hiện gì"""
        with patch('os.path.exists') as mock_exists, \
             patch('os.remove') as mock_remove:

            delete_contract_file("")
            delete_contract_file(None)

            mock_exists.assert_not_called()
            mock_remove.assert_not_called()