import os
import random
from datetime import datetime, timedelta, time as dtime
import psycopg2
from werkzeug.security import generate_password_hash

# --- DỮ LIỆU CẤU HÌNH SẴN (CONSTANTS) ---
DEFAULT_USERS = [
    {"Username": "admin", "Password": "123456", "FullName": "Quản Trị Viên Hệ Thống", "Email": "admin@hrm.com", "Role": "Admin", "IsActive": True},
    {"Username": "manager", "Password": "123456", "FullName": "Quản Lý Nhân Sự", "Email": "manager@hrm.com", "Role": "Manager", "IsActive": True},
    {"Username": "employee", "Password": "123456", "FullName": "Nhân Viên Mẫu", "Email": "employee@hrm.com", "Role": "User", "IsActive": True}
]

DEPARTMENTS = ["Phòng Công Nghệ Thông Tin", "Phòng Nhân Sự", "Phòng Kế Toán", "Phòng Kinh Doanh", "Phòng Marketing", "Phòng Hành Chính", "Phòng Mua Hàng", "Phòng Kho", "Phòng Vận Hành"]
POSITIONS = ["Giám Đốc", "Trưởng Phòng", "Phó Phòng", "Quản Lý Dự Án", "Kỹ Sư Phần Mềm", "Chuyên Viên Nhân Sự", "Kế Toán Viên", "Chuyên Viên Marketing", "Nhân Viên Kinh Doanh"]

def init_database():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("[ERROR] Không tìm thấy biến môi trường DATABASE_URL!")
        return

    print("🚀 Đang kết nối và khởi tạo cơ sở dữ liệu PostgreSQL Cloud...")
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    try:
        # 1. TẠO CÁC BẢNG (SCHEMA) VỚI TÊN CỘT CHỮ THƯỜNG HOÀN TOÀN
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                userid SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                passwordhash VARCHAR(255) NOT NULL,
                fullname VARCHAR(100),
                email VARCHAR(100),
                role VARCHAR(20) DEFAULT 'User',
                isactive BOOLEAN DEFAULT TRUE,
                createdat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                lastlogin TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS Departments (
                departmentid SERIAL PRIMARY KEY,
                departmentcode VARCHAR(20),
                departmentname VARCHAR(100) NOT NULL,
                description TEXT,
                location VARCHAR(100),
                managerid INT,
                status VARCHAR(20) DEFAULT 'Active',
                isdeleted INT DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Positions (
                positionid SERIAL PRIMARY KEY,
                positioncode VARCHAR(20),
                positionname VARCHAR(100) NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'Active',
                isdeleted INT DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Employees (
                employeeid SERIAL PRIMARY KEY,
                fullname VARCHAR(100) NOT NULL,
                gender VARCHAR(10),
                dob DATE,
                hiredate DATE,
                email VARCHAR(100) UNIQUE,
                phone VARCHAR(20),
                departmentid INT REFERENCES Departments(departmentid) ON DELETE SET NULL,
                positionid INT REFERENCES Positions(positionid) ON DELETE SET NULL,
                managerid INT,
                status VARCHAR(20) DEFAULT 'Active',
                citizenid VARCHAR(20),
                address TEXT,
                nationality VARCHAR(50) DEFAULT 'Việt Nam',
                maritalstatus VARCHAR(20),
                emergencycontact VARCHAR(100),
                emergencyphone VARCHAR(20),
                photo VARCHAR(255),
                citizenfrontphoto VARCHAR(255),
                citizenbackphoto VARCHAR(255),
                isdeleted INT DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Salaries (
                salaryid SERIAL PRIMARY KEY,
                employeeid INT REFERENCES Employees(employeeid) ON DELETE CASCADE,
                basesalary DECIMAL(12, 2) DEFAULT 0,
                bonus DECIMAL(12, 2) DEFAULT 0,
                allowance DECIMAL(12, 2) DEFAULT 0,
                month INT,
                year INT,
                salarycode VARCHAR(50),
                overtimepay DECIMAL(12, 2) DEFAULT 0,
                deduction DECIMAL(12, 2) DEFAULT 0,
                tax DECIMAL(12, 2) DEFAULT 0,
                insurance DECIMAL(12, 2) DEFAULT 0,
                netsalary DECIMAL(12, 2) DEFAULT 0,
                paymentdate DATE,
                status VARCHAR(30) DEFAULT 'Chưa thanh toán',
                notes TEXT,
                isdeleted INT DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Contracts (
                contractid SERIAL PRIMARY KEY,
                employeeid INT REFERENCES Employees(employeeid) ON DELETE CASCADE,
                contracttype VARCHAR(50),
                startdate DATE,
                enddate DATE,
                status VARCHAR(30),
                contractcode VARCHAR(50),
                contractnumber VARCHAR(50),
                basicsalary DECIMAL(12, 2),
                worklocation TEXT,
                departmentid INT,
                positionid INT,
                signer VARCHAR(100),
                signdate DATE,
                probationmonths INT DEFAULT 0,
                contractfile VARCHAR(255),
                description TEXT,
                isdeleted INT DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS LeaveRequests (
                leaveid SERIAL PRIMARY KEY,
                employeeid INT REFERENCES Employees(employeeid) ON DELETE CASCADE,
                fromdate DATE,
                todate DATE,
                reason TEXT,
                status VARCHAR(30) DEFAULT 'Chờ duyệt',
                leavecode VARCHAR(50),
                totaldays INT,
                attachment VARCHAR(255),
                applieddate DATE,
                approvedby VARCHAR(100),
                approveddate DATE,
                description TEXT,
                leavetype VARCHAR(50),
                isdeleted INT DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Attendance (
                attendanceid SERIAL PRIMARY KEY,
                employeeid INT REFERENCES Employees(employeeid) ON DELETE CASCADE,
                date DATE,
                checkintime TIME,
                checkouttime TIME,
                status VARCHAR(30),
                shiftid INT DEFAULT 1,
                workinghours DECIMAL(4, 2) DEFAULT 0,
                overtimehours DECIMAL(4, 2) DEFAULT 0,
                lateminutes INT DEFAULT 0,
                earlyleaveminutes INT DEFAULT 0,
                checkinmethod VARCHAR(30),
                approvalstatus VARCHAR(30),
                notes TEXT,
                isdeleted INT DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Notifications (
                notificationid SERIAL PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                message TEXT NOT NULL,
                type VARCHAR(30) DEFAULT 'Info',
                receiverrole VARCHAR(20),
                receiverid INT,
                url VARCHAR(255),
                isread INT DEFAULT 0,
                createdat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS AuditLogs (
                logid SERIAL PRIMARY KEY,
                userid INT,
                username VARCHAR(50),
                role VARCHAR(20),
                module VARCHAR(50),
                action VARCHAR(30),
                recordid INT,
                description TEXT,
                ipaddress VARCHAR(50),
                useragent TEXT,
                createdat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("✅ Đã tạo cấu trúc các bảng thành công với tên cột chuẩn chữ thường.")

        # 2. SEED USERS
        cursor.execute("SELECT COUNT(*) FROM Users;")
        if cursor.fetchone()[0] == 0:
            for u in DEFAULT_USERS:
                pass_hash = generate_password_hash(u["Password"])
                cursor.execute("""
                    INSERT INTO Users (username, passwordhash, fullname, email, role, isactive)
                    VALUES (%s, %s, %s, %s, %s, %s);
                """, (u["Username"], pass_hash, u["FullName"], u["Email"], u["Role"], u["IsActive"]))
            print("-> Đã khởi tạo danh sách Users mẫu.")

        # 3. SEED DEPARTMENTS
        cursor.execute("SELECT COUNT(*) FROM Departments;")
        if cursor.fetchone()[0] == 0:
            for i, dept in enumerate(DEPARTMENTS, 1):
                cursor.execute("""
                    INSERT INTO Departments (departmentname, departmentcode, description, location, status)
                    VALUES (%s, %s, %s, %s, %s);
                """, (dept, f"DP{i:03d}", f"Mô tả cho {dept}", "TP. Hồ Chí Minh", "Active"))
            print("-> Đã khởi tạo Phòng ban mẫu.")

        # 4. SEED POSITIONS
        cursor.execute("SELECT COUNT(*) FROM Positions;")
        if cursor.fetchone()[0] == 0:
            for i, pos in enumerate(POSITIONS, 1):
                cursor.execute("""
                    INSERT INTO Positions (positionname, positioncode, description, status)
                    VALUES (%s, %s, %s, %s);
                """, (pos, f"POS{i:03d}", f"Mô tả chức vụ {pos}", "Hoạt động"))
            print("-> Đã khởi tạo Chức vụ mẫu.")

        # 5. SEED EMPLOYEES
        cursor.execute("SELECT COUNT(*) FROM Employees;")
        if cursor.fetchone()[0] == 0:
            cursor.execute("SELECT departmentid FROM Departments;")
            dept_ids = [r[0] for r in cursor.fetchall()]
            cursor.execute("SELECT positionid FROM Positions;")
            pos_ids = [r[0] for r in cursor.fetchall()]

            sample_employees = [
                ("Nguyễn Văn An", "Nam", "1992-05-10", "2021-01-15", "an.nguyen@hrm.com", "0901234567", dept_ids[0], pos_ids[1], "284729103847", "123 Lê Lợi, Q1, TP.HCM"),
                ("Trần Thị Bích", "Nữ", "1995-08-20", "2021-03-20", "bich.tran@hrm.com", "0912345678", dept_ids[1], pos_ids[5], "384729103848", "456 Nguyễn Huệ, Q1, TP.HCM"),
                ("Lê Hoàng Nam", "Nam", "1990-12-02", "2020-06-01", "nam.le@hrm.com", "0923456789", dept_ids[0], pos_ids[4], "484729103849", "789 Cách Mạng Tháng 8, Q3, TP.HCM"),
                ("Phạm Minh Tuấn", "Nam", "1998-03-15", "2022-09-10", "tuan.pham@hrm.com", "0934567890", dept_ids[2], pos_ids[6], "584729103850", "12 Hoàng Văn Thụ, Q.Phú Nhuận, TP.HCM")
            ]

            for emp in sample_employees:
                cursor.execute("""
                    INSERT INTO Employees (fullname, gender, dob, hiredate, email, phone, departmentid, positionid, citizenid, address)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, emp)
            print("-> Đã khởi tạo Danh sách Nhân viên mẫu.")

        # 6. SEED SALARIES & CONTRACTS
        cursor.execute("SELECT employeeid FROM Employees;")
        emp_ids = [r[0] for r in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) FROM Salaries;")
        if cursor.fetchone()[0] == 0 and emp_ids:
            for eid in emp_ids:
                cursor.execute("""
                    INSERT INTO Salaries (employeeid, basesalary, bonus, allowance, month, year, salarycode, netsalary, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (eid, 15000000.0, 2000000.0, 1000000.0, 7, 2026, f"SAL-202607-{eid:04d}", 16500000.0, "Đã thanh toán"))
            print("-> Đã khởi tạo Bảng lương mẫu.")

        cursor.execute("SELECT COUNT(*) FROM Contracts;")
        if cursor.fetchone()[0] == 0 and emp_ids:
            for i, eid in enumerate(emp_ids, 1):
                cursor.execute("""
                    INSERT INTO Contracts (employeeid, contracttype, startdate, status, contractcode, contractnumber, basicsalary)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """, (eid, "Không xác định thời hạn", "2022-01-01", "Hiệu lực", f"HD-{i:05d}", f"HDLD/2026/{i:04d}", 15000000.0))
            print("-> Đã khởi tạo Hợp đồng lao động mẫu.")

        conn.commit()
        print("🎉 TẤT CẢ DỮ LIỆU ĐÃ ĐƯỢC SEED THÀNH CÔNG VÀO POSTGRESQL CLOUD!")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Lỗi trong quá trình khởi tạo dữ liệu: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    init_database()