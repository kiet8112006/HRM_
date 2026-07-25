from werkzeug.security import generate_password_hash

password = "admin123"

# Tạo chuỗi hash dùng thuật toán pbkdf2:sha256
hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

print("Mật khẩu thô:", password)
print("Chuỗi Hash để chèn vào Database:")
print(hashed_password)