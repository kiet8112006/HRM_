import os
import uuid

from werkzeug.utils import secure_filename

import config
def allowed_document(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower()
        in config.ALLOWED_DOCUMENT_EXTENSIONS
    )
ALLOWED_DOCUMENT_MIME = {
    "application/pdf"
}
def allowed_document_mimetype(file):
    return file.mimetype in ALLOWED_DOCUMENT_MIME
def verify_pdf(file):
    try:
        header = file.read(5)

        file.seek(0)

        return header == b"%PDF-"

    except Exception:
        return False
    
def generate_document_filename(file):
    extension = file.filename.rsplit(".", 1)[1].lower()

    return f"{uuid.uuid4().hex}.{extension}"

def save_contract(file):
    filename = generate_document_filename(file)

    filepath = os.path.join(
        config.CONTRACT_FOLDER,
        filename
    )

    file.save(filepath)

    return filename

def delete_contract_file(filename):
    if not filename:
        return

    filepath = os.path.join(
        config.CONTRACT_FOLDER,
        filename
    )

    if os.path.exists(filepath):
        os.remove(filepath)