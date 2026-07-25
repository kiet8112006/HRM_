from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response
import csv
import io
import math
from database import get_connection
from validators.position_validator import (
    validate_position_code,
    validate_position_name,
    validate_position_level,
    validate_salary_range,
    validate_position_status,
    validate_position_description,
    normalize_position_code,
    normalize_position_name
)
from exceptions.validator.position import PositionValidationError

# Khai báo Blueprint
position_bp = Blueprint('position', __name__)

# ---------------------------------------------------------------------
# 1. TRANG DANH SÁCH CHỨC VỤ (CÓ TÌM KIẾM, LỌC & PHÂN TRANG)
# ---------------------------------------------------------------------
@position_bp.route('/positions')
def positions():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    keyword = request.args.get('keyword', '').strip()
    status = request.args.get('status', '').strip()
    
    # Xử lý tham số phân trang
    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    per_page = 10  # Số lượng bản ghi trên 1 trang

    conn = get_connection()
    cursor = conn.cursor()

    # Base query (Thêm lọc IsDeleted nếu có hoặc giữ nguyên WHERE 1=1)
    sql_base = "FROM Positions WHERE 1=1"
    params = []

    if keyword:
        # PostgreSQL dùng ILIKE để tìm kiếm không phân biệt hoa thường
        sql_base += " AND (PositionCode ILIKE %s OR PositionName ILIKE %s)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    if status:
        sql_base += " AND Status = %s"
        params.append(status)

    # Đếm tổng số bản ghi
    count_sql = f"SELECT COUNT(*) {sql_base}"
    cursor.execute(count_sql, tuple(params))
    total_items = cursor.fetchone()[0]

    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1
    if page > total_pages:
        page = total_pages

    # Lấy dữ liệu theo trang chuẩn PostgreSQL (LIMIT %s OFFSET %s)
    offset = (page - 1) * per_page
    data_sql = f"""
        SELECT PositionID, PositionCode, PositionName, PositionLevel, MinSalary, MaxSalary, Status, Description 
        {sql_base} 
        ORDER BY PositionLevel ASC, PositionID DESC 
        LIMIT %s OFFSET %s
    """
    params_data = params + [per_page, offset]

    try:
        cursor.execute(data_sql, tuple(params_data))
        position_list = cursor.fetchall()
    except Exception:
        # Fallback nếu câu truy vấn gặp sự cố
        fallback_sql = f"SELECT PositionID, PositionCode, PositionName, PositionLevel, MinSalary, MaxSalary, Status, Description {sql_base} ORDER BY PositionLevel ASC, PositionID DESC"
        cursor.execute(fallback_sql, tuple(params))
        position_list = cursor.fetchall()

    conn.close()

    return render_template(
        'position/positions.html',
        positions=position_list,
        keyword=keyword,
        status=status,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_items=total_items
    )

# ---------------------------------------------------------------------
# 2. THÊM CHỨC VỤ MỚI
# ---------------------------------------------------------------------
@position_bp.route('/add_position', methods=['GET', 'POST'])
def add_position():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    if session.get('role') not in ['Admin', 'Manager']:
        flash('Bạn không có quyền thực hiện chức năng này!', 'danger')
        return redirect(url_for('position.positions'))

    if request.method == 'POST':
        code = normalize_position_code(request.form.get('position_code'))
        name = normalize_position_name(request.form.get('position_name'))
        level_str = request.form.get('position_level')
        min_salary_str = request.form.get('min_salary')
        max_salary_str = request.form.get('max_salary')
        status = request.form.get('status')
        description = request.form.get('description', '').strip()

        try:
            # Validator
            validate_position_code(code)
            validate_position_name(name)
            level = validate_position_level(level_str)
            min_salary, max_salary = validate_salary_range(min_salary_str, max_salary_str)
            validate_position_status(status)
            validate_position_description(description)

            conn = get_connection()
            cursor = conn.cursor()

            # Kiểm tra trùng mã chức vụ (đổi ? thành %s)
            cursor.execute("SELECT PositionID FROM Positions WHERE PositionCode = %s", (code,))
            if cursor.fetchone():
                conn.close()
                raise PositionValidationError('Mã chức vụ này đã tồn tại trong hệ thống!')

            # Insert DB (đổi ? thành %s)
            insert_sql = """
                INSERT INTO Positions (PositionCode, PositionName, PositionLevel, MinSalary, MaxSalary, Status, Description)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (code, name, level, min_salary, max_salary, status, description))
            conn.commit()
            conn.close()

            flash('Thêm chức vụ thành công!', 'success')
            return redirect(url_for('position.positions'))

        except PositionValidationError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f'Lỗi hệ thống: {str(e)}', 'danger')

    return render_template('position/add_position.html')

# ---------------------------------------------------------------------
# 3. SỬA CHỨC VỤ
# ---------------------------------------------------------------------
@position_bp.route('/edit_position/<int:id>', methods=['GET', 'POST'])
def edit_position(id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    if session.get('role') not in ['Admin', 'Manager']:
        flash('Bạn không có quyền thực hiện chức năng này!', 'danger')
        return redirect(url_for('position.positions'))

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        code = normalize_position_code(request.form.get('position_code'))
        name = normalize_position_name(request.form.get('position_name'))
        level_str = request.form.get('position_level')
        min_salary_str = request.form.get('min_salary')
        max_salary_str = request.form.get('max_salary')
        status = request.form.get('status')
        description = request.form.get('description', '').strip()

        try:
            validate_position_code(code)
            validate_position_name(name)
            level = validate_position_level(level_str)
            min_salary, max_salary = validate_salary_range(min_salary_str, max_salary_str)
            validate_position_status(status)
            validate_position_description(description)

            # Kiểm tra trùng mã (đổi ? thành %s)
            cursor.execute("SELECT PositionID FROM Positions WHERE PositionCode = %s AND PositionID != %s", (code, id))
            if cursor.fetchone():
                conn.close()
                raise PositionValidationError('Mã chức vụ này đã bị trùng với chức vụ khác!')

            update_sql = """
                UPDATE Positions
                SET PositionCode = %s, PositionName = %s, PositionLevel = %s, MinSalary = %s, MaxSalary = %s, Status = %s, Description = %s
                WHERE PositionID = %s
            """
            cursor.execute(update_sql, (code, name, level, min_salary, max_salary, status, description, id))
            conn.commit()
            conn.close()

            flash('Cập nhật chức vụ thành công!', 'success')
            return redirect(url_for('position.positions'))

        except PositionValidationError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f'Lỗi hệ thống: {str(e)}', 'danger')

    cursor.execute("SELECT PositionID, PositionCode, PositionName, PositionLevel, MinSalary, MaxSalary, Status, Description FROM Positions WHERE PositionID = %s", (id,))
    position_data = cursor.fetchone()
    conn.close()

    if not position_data:
        flash('Không tìm thấy chức vụ!', 'danger')
        return redirect(url_for('position.positions'))

    return render_template('position/edit_position.html', position=position_data)

# ---------------------------------------------------------------------
# 4. XÓA 1 CHỨC VỤ
# ---------------------------------------------------------------------
@position_bp.route('/delete_position/<int:id>')
def delete_position(id):
    if 'user_id' not in session or session.get('role') != 'Admin':
        flash('Chỉ Admin mới có quyền xóa chức vụ!', 'danger')
        return redirect(url_for('position.positions'))

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Kiểm tra xem có nhân viên nào đang giữ chức vụ này không (đổi ? thành %s)
        cursor.execute("SELECT COUNT(*) FROM Employees WHERE PositionID = %s AND COALESCE(IsDeleted, 0) = 0", (id,))
        if cursor.fetchone()[0] > 0:
            flash('Không thể xóa chức vụ này vì đang có nhân viên giữ chức vụ!', 'danger')
        else:
            cursor.execute("DELETE FROM Positions WHERE PositionID = %s", (id,))
            conn.commit()
            flash('Xóa chức vụ thành công!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Lỗi khi xóa: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('position.positions'))

# ---------------------------------------------------------------------
# 5. XÓA HÀNG LOẠT (BULK DELETE)
# ---------------------------------------------------------------------
@position_bp.route('/delete_selected_positions', methods=['POST'])
def delete_selected_positions():
    if 'user_id' not in session or session.get('role') != 'Admin':
        flash('Chỉ Admin mới có quyền thực hiện!', 'danger')
        return redirect(url_for('position.positions'))

    position_ids = request.form.getlist('position_ids')
    if not position_ids:
        flash('Vui lòng chọn ít nhất một chức vụ để xóa!', 'warning')
        return redirect(url_for('position.positions'))

    conn = get_connection()
    cursor = conn.cursor()

    try:
        format_strings = ','.join(['%s'] * len(position_ids))
        cursor.execute(f"DELETE FROM Positions WHERE PositionID IN ({format_strings})", tuple(position_ids))
        conn.commit()
        flash(f'Đã xóa thành công {len(position_ids)} chức vụ!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Không thể xóa các chức vụ đã chọn do ràng buộc dữ liệu!', 'danger')
    finally:
        conn.close()

    return redirect(url_for('position.positions'))

# ---------------------------------------------------------------------
# 6. XUẤT CSV DANH SÁCH CHỨC VỤ
# ---------------------------------------------------------------------
@position_bp.route('/export_positions_csv')
def export_positions_csv():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT PositionID, PositionCode, PositionName, PositionLevel, MinSalary, MaxSalary, Status, Description FROM Positions ORDER BY PositionLevel ASC")
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    output.write('\ufeff') # UTF-8 BOM cho Excel tiếng Việt
    writer = csv.writer(output)

    writer.writerow(['ID', 'Mã Chức Vụ', 'Tên Chức Vụ', 'Cấp Độ', 'Lương Tối Thiểu', 'Lương Tối Đa', 'Trạng Thái', 'Mô Tả'])

    for r in rows:
        if isinstance(r, tuple):
            writer.writerow(list(r))
        else:
            writer.writerow([r.PositionID, r.PositionCode, r.PositionName, r.PositionLevel, r.MinSalary, r.MaxSalary, r.Status, r.Description])

    output.seek(0)
    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=positions.csv'}
    )