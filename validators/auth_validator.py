def validate_username(username):

    username = username.strip()

    if username == "":
        return "Tên đăng nhập không được để trống."

    if len(username) < 4:
        return "Tên đăng nhập phải có ít nhất 4 ký tự."

    return None

def validate_password(password):

    if password == "":
        return "Mật khẩu không được để trống."

    if len(password) < 6:
        return "Mật khẩu phải từ 6 ký tự."

    return None

def validate_confirm_password(
    password,
    confirm_password
):

    if confirm_password == "":

        return "Xác nhận mật khẩu không được để trống."

    if password != confirm_password:

        return "Xác nhận mật khẩu không khớp."

    return None

def validate_old_password(old_password):

    if old_password == "":

        return "Mật khẩu hiện tại không được để trống."

    return None

def validate_new_password(new_password):

    if new_password == "":

        return "Mật khẩu mới không được để trống."

    if len(new_password) < 6:

        return "Mật khẩu mới phải có ít nhất 6 ký tự."

    return None