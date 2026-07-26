import csv
import io
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, current_app
from werkzeug.utils import secure_filename
from database import get_connection

contract_bp = Blueprint('contract', __name__, url_prefix='/contracts')

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'png', 'jpg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@contract_bp.route('/')
def list_contracts():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    base_where = "WHERE c.IsDeleted = 0"
    params = []
    
    if search_query:
        base_where += " AND (c.ContractCode LIKE ? OR e.FullName LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
        
    if status_filter:
        base_where += " AND c.Status = ?"
        params.append(status_filter)
        
    # Query đếm tổng dòng
    count_sql = f"""
        SELECT COUNT(*) 
        FROM Contracts c 
        LEFT JOIN Employees e ON c.EmployeeID = e.EmployeeID 
        {base_where}
    """
    cursor.execute(count_sql, params)
    total_count = cursor.fetchone()[0]
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    # Query lấy dữ liệu phân trang
    data_sql = f"""
        SELECT c.ContractID, c.ContractCode, e.FullName, c.ContractType, 
               c.StartDate, c.EndDate, c.Status, c.ContractFile
        FROM Contracts c
        LEFT JOIN Employees e ON c.EmployeeID = e.EmployeeID
        {base_where}
        ORDER BY c.ContractID DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    cursor.execute(data_sql, params + [offset, per_page])
    contracts = cursor.fetchall()
    
    conn.close()
    
    return render_template(
        'contracts/list.html',
        contracts=contracts,
        page=page,
        total_pages=total_pages,
        search_query=search_query,
        status_filter=status_filter
    )


@contract_bp.route('/add', methods=['GET', 'POST'])
def add_contract():
    conn = get_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        contract_code = request.form.get('contract_code')
        contract_number = request.form.get('contract_number')
        contract_type = request.form.get('contract_type')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date') or None
        basic_salary = request.form.get('basic_salary') or 0
        work_location = request.form.get('work_location')
        department_id = request.form.get('department_id') or None
        position_id = request.form.get('position_id') or None
        signer = request.form.get('signer')
        sign_date = request.form.get('sign_date') or None
        probation_months = request.form.get('probation_months') or 0
        description = request.form.get('description')
        status = request.form.get('status', 'Hiệu lực')
        
        # Xử lý Upload File
        file = request.files.get('contract_file')
        filename = None
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            
        insert_sql = """
            INSERT INTO Contracts (
                EmployeeID, ContractCode, ContractNumber, ContractType,
                StartDate, EndDate, BasicSalary, WorkLocation, DepartmentID,
                PositionID, Signer, SignDate, ProbationMonths, ContractFile,
                Description, Status, IsDeleted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """
        cursor.execute(insert_sql, (
            employee_id, contract_code, contract_number, contract_type,
            start_date, end_date, basic_salary, work_location, department_id,
            position_id, signer, sign_date, probation_months, filename,
            description, status
        ))
        conn.commit()
        conn.close()
        flash('Thêm hợp đồng thành công!', 'success')
        return redirect(url_for('contract.list_contracts'))
        
    # Get Employees/Departments/Positions cho Form
    cursor.execute("SELECT EmployeeID, FullName FROM Employees WHERE IsDeleted = 0")
    employees = cursor.fetchall()
    
    cursor.execute("SELECT DepartmentID, DepartmentName FROM Departments")
    departments = cursor.fetchall()
    
    cursor.execute("SELECT PositionID, PositionName FROM Positions")
    positions = cursor.fetchall()
    
    conn.close()
    return render_template('contracts/add.html', employees=employees, departments=departments, positions=positions)


@contract_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_contract(id):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM Contracts WHERE ContractID = ? AND IsDeleted = 0", (id,))
    contract = cursor.fetchone()
    
    if not contract:
        conn.close()
        flash('Hợp đồng không tồn tại!', 'danger')
        return redirect(url_for('contract.list_contracts'))
        
    if request.method == 'POST':
        # Lấy file hiện tại (Index 14)
        old_file = contract[14] if isinstance(contract, (list, tuple)) else getattr(contract, 'ContractFile', None)
        
        file = request.files.get('contract_file')
        filename = old_file
        
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            
        update_sql = """
            UPDATE Contracts SET
                EmployeeID = ?, ContractCode = ?, ContractNumber = ?, ContractType = ?,
                StartDate = ?, EndDate = ?, BasicSalary = ?, WorkLocation = ?,
                DepartmentID = ?, PositionID = ?, Signer = ?, SignDate = ?,
                ProbationMonths = ?, ContractFile = ?, Description = ?, Status = ?
            WHERE ContractID = ?
        """
        cursor.execute(update_sql, (
            request.form.get('employee_id'),
            request.form.get('contract_code'),
            request.form.get('contract_number'),
            request.form.get('contract_type'),
            request.form.get('start_date'),
            request.form.get('end_date') or None,
            request.form.get('basic_salary') or 0,
            request.form.get('work_location'),
            request.form.get('department_id') or None,
            request.form.get('position_id') or None,
            request.form.get('signer'),
            request.form.get('sign_date') or None,
            request.form.get('probation_months') or 0,
            filename,
            request.form.get('description'),
            request.form.get('status'),
            id
        ))
        conn.commit()
        conn.close()
        flash('Cập nhật hợp đồng thành công!', 'success')
        return redirect(url_for('contract.list_contracts'))

    cursor.execute("SELECT EmployeeID, FullName FROM Employees WHERE IsDeleted = 0")
    employees = cursor.fetchall()
    
    cursor.execute("SELECT DepartmentID, DepartmentName FROM Departments")
    departments = cursor.fetchall()
    
    cursor.execute("SELECT PositionID, PositionName FROM Positions")
    positions = cursor.fetchall()
    
    conn.close()
    return render_template('contracts/edit.html', contract=contract, employees=employees, departments=departments, positions=positions)


@contract_bp.route('/delete/<int:id>', methods=['POST'])
def delete_contract(id):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE Contracts SET IsDeleted = 1 WHERE ContractID = ?", (id,))
    conn.commit()
    conn.close()
    
    flash('Xóa hợp đồng thành công!', 'success')
    return redirect(url_for('contract.list_contracts'))


@contract_bp.route('/export')
def export_contracts_csv():
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = """
        SELECT c.ContractCode, c.ContractNumber, e.FullName, c.ContractType,
               c.StartDate, c.EndDate, c.BasicSalary, c.WorkLocation, c.Status
        FROM Contracts c
        LEFT JOIN Employees e ON c.EmployeeID = e.EmployeeID
        WHERE c.IsDeleted = 0
        ORDER BY c.ContractID DESC
    """
    cursor.execute(sql)
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    output.write("\ufeff")  # BOM UTF-8 cho Excel
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Mã HĐ', 'Số HĐ', 'Nhân viên', 'Loại HĐ', 
        'Ngày bắt đầu', 'Ngày kết thúc', 'Lương cơ bản', 'Nơi làm việc', 'Trạng thái'
    ])
    
    for row in rows:
        writer.writerow(list(row))
        
    return Response(
        output.getvalue().encode('utf-8'),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=contracts_report.csv'}
    )