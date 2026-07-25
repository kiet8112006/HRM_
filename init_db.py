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
        # 1. TẠO CÁC BẢNG (SCHEMA)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                UserID SERIAL PRIMARY KEY,
                Username VARCHAR(50) UNIQUE NOT NULL,
                PasswordHash VARCHAR(255) NOT NULL,
                FullName VARCHAR(100),
                Email VARCHAR(100),
                Role VARCHAR(20) DEFAULT 'User',
                IsActive BOOLEAN DEFAULT TRUE,
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                LastLogin TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS Departments (
                DepartmentID SERIAL PRIMARY KEY,
                DepartmentCode VARCHAR(20),
                DepartmentName VARCHAR(100) NOT NULL,
                Description TEXT,
                Location VARCHAR(100),
                ManagerID INT REFERENCES Employees(EmployeeID) ON DELETE SET NULL,
                Status VARCHAR(20) DEFAULT 'Active',
                IsDeleted INT DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Positions (
                PositionID SERIAL PRIMARY KEY,
                PositionCode VARCHAR(20),
                PositionName VARCHAR(100) NOT NULL,
                Description TEXT,
                Status VARCHAR(20) DEFAULT 'Active',
                IsDeleted INT DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Employees (
                EmployeeID SERIAL PRIMARY KEY,
                FullName VARCHAR(100) NOT NULL,
                Gender VARCHAR(10),
                DOB DATE,
                HireDate DATE,
                Email VARCHAR(100) UNIQUE,
                Phone VARCHAR(20),
                DepartmentID INT REFERENCES Departments(DepartmentID) ON DELETE SET NULL,
                PositionID INT REFERENCES Positions(PositionID) ON DELETE SET NULL,
                ManagerID INT,
                Status VARCHAR(20) DEFAULT 'Active',
                CitizenID VARCHAR(20),
                Address TEXT,
                Nationality VARCHAR(50) DEFAULT 'Việt Nam',
                MaritalStatus VARCHAR(20),
                EmergencyContact VARCHAR(100),
                EmergencyPhone VARCHAR(20),
                Photo VARCHAR(255),
                CitizenFrontPhoto VARCHAR(255),
                CitizenBackPhoto VARCHAR(255),
                IsDeleted INT DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Salaries (
                SalaryID SERIAL PRIMARY KEY,
                EmployeeID INT REFERENCES Employees(EmployeeID) ON DELETE CASCADE,
                BaseSalary DECIMAL(12, 2) DEFAULT 0,
                Bonus DECIMAL(12, 2) DEFAULT 0,
                Allowance DECIMAL(12, 2) DEFAULT 0,
                month INT,
                year INT,
                SalaryCode VARCHAR(50),
                OvertimePay DECIMAL(12, 2) DEFAULT 0,
                Deduction DECIMAL(12, 2) DEFAULT 0,
                Tax DECIMAL(12, 2) DEFAULT 0,
                Insurance DECIMAL(12, 2) DEFAULT 0,
                NetSalary DECIMAL(12, 2) DEFAULT 0,
                PaymentDate DATE,
                Status VARCHAR(30) DEFAULT 'Chưa thanh toán',
                Notes TEXT,
                IsDeleted INT DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Contracts (
                ContractID SERIAL PRIMARY KEY,
                EmployeeID INT REFERENCES Employees(EmployeeID) ON DELETE CASCADE,
                ContractType VARCHAR(50),
                StartDate DATE,
                EndDate DATE,
                Status VARCHAR(30),
                ContractCode VARCHAR(50),
                ContractNumber VARCHAR(50),
                BasicSalary DECIMAL(12, 2),
                WorkLocation TEXT,
                DepartmentID INT,
                PositionID INT,
                Signer VARCHAR(100),
                SignDate DATE,
                ProbationMonths INT DEFAULT 0,
                ContractFile VARCHAR(255),
                Description TEXT,
                IsDeleted INT DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS LeaveRequests (
                LeaveID SERIAL PRIMARY KEY,
                EmployeeID INT REFERENCES Employees(EmployeeID) ON DELETE CASCADE,
                FromDate DATE,
                ToDate DATE,
                Reason TEXT,
                Status VARCHAR(30) DEFAULT 'Chờ duyệt',
                LeaveCode VARCHAR(50),
                TotalDays INT,
                Attachment VARCHAR(255),
                AppliedDate DATE,
                ApprovedBy VARCHAR(100),
                ApprovedDate DATE,
                Description TEXT,
                LeaveType VARCHAR(50),
                IsDeleted INT DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Attendance (
                AttendanceID SERIAL PRIMARY KEY,
                EmployeeID INT REFERENCES Employees(EmployeeID) ON DELETE CASCADE,
                Date DATE,
                CheckInTime TIME,
                CheckOutTime TIME,
                Status VARCHAR(30),
                ShiftID INT DEFAULT 1,
                WorkingHours DECIMAL(4, 2) DEFAULT 0,
                OvertimeHours DECIMAL(4, 2) DEFAULT 0,
                LateMinutes INT DEFAULT 0,
                EarlyLeaveMinutes INT DEFAULT 0,
                CheckInMethod VARCHAR(30),
                ApprovalStatus VARCHAR(30),
                Notes TEXT,
                IsDeleted INT DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Notifications (
                NotificationID SERIAL PRIMARY KEY,
                Title VARCHAR(200) NOT NULL,
                Message TEXT NOT NULL,
                Type VARCHAR(30) DEFAULT 'Info',
                ReceiverRole VARCHAR(20),
                ReceiverID INT,
                Url VARCHAR(255),
                IsRead INT DEFAULT 0,
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS AuditLogs (
                LogID SERIAL PRIMARY KEY,
                UserID INT,
                Username VARCHAR(50),
                Role VARCHAR(20),
                Module VARCHAR(50),
                Action VARCHAR(30),
                RecordID INT,
                Description TEXT,
                IPAddress VARCHAR(50),
                UserAgent TEXT,
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("✅ Đã tạo cấu trúc các bảng thành công.")

        # 2. SEED USERS
        cursor.execute("SELECT COUNT(*) FROM Users;")
        if cursor.fetchone()[0] == 0:
            for u in DEFAULT_USERS:
                pass_hash = generate_password_hash(u["Password"])
                cursor.execute("""
                    INSERT INTO Users (Username, PasswordHash, FullName, Email, Role, IsActive)
                    VALUES (%s, %s, %s, %s, %s, %s);
                """, (u["Username"], pass_hash, u["FullName"], u["Email"], u["Role"], u["IsActive"]))
            print("-> Đã khởi tạo danh sách Users mẫu.")

        # 3. SEED DEPARTMENTS
        cursor.execute("SELECT COUNT(*) FROM Departments;")
        if cursor.fetchone()[0] == 0:
            for i, dept in enumerate(DEPARTMENTS, 1):
                cursor.execute("""
                    INSERT INTO Departments (DepartmentName, DepartmentCode, Description, Location, Status)
                    VALUES (%s, %s, %s, %s, %s);
                """, (dept, f"DP{i:03d}", f"Mô tả cho {dept}", "TP. Hồ Chí Minh", "Active"))
            print("-> Đã khởi tạo Phòng ban mẫu.")

        # 4. SEED POSITIONS
        cursor.execute("SELECT COUNT(*) FROM Positions;")
        if cursor.fetchone()[0] == 0:
            for i, pos in enumerate(POSITIONS, 1):
                cursor.execute("""
                    INSERT INTO Positions (PositionName, PositionCode, Description, Status)
                    VALUES (%s, %s, %s, %s);
                """, (pos, f"POS{i:03d}", f"Mô tả chức vụ {pos}", "Hoạt động"))
            print("-> Đã khởi tạo Chức vụ mẫu.")

        # 5. SEED EMPLOYEES
        cursor.execute("SELECT COUNT(*) FROM Employees;")
        if cursor.fetchone()[0] == 0:
            cursor.execute("SELECT DepartmentID FROM Departments;")
            dept_ids = [r[0] for r in cursor.fetchall()]
            cursor.execute("SELECT PositionID FROM Positions;")
            pos_ids = [r[0] for r in cursor.fetchall()]

            sample_employees = [
                ("Nguyễn Văn An", "Nam", "1992-05-10", "2021-01-15", "an.nguyen@hrm.com", "0901234567", dept_ids[0], pos_ids[1], "284729103847", "123 Lê Lợi, Q1, TP.HCM"),
                ("Trần Thị Bích", "Nữ", "1995-08-20", "2021-03-20", "bich.tran@hrm.com", "0912345678", dept_ids[1], pos_ids[5], "384729103848", "456 Nguyễn Huệ, Q1, TP.HCM"),
                ("Lê Hoàng Nam", "Nam", "1990-12-02", "2020-06-01", "nam.le@hrm.com", "0923456789", dept_ids[0], pos_ids[4], "484729103849", "789 Cách Mạng Tháng 8, Q3, TP.HCM"),
                ("Phạm Minh Tuấn", "Nam", "1998-03-15", "2022-09-10", "tuan.pham@hrm.com", "0934567890", dept_ids[2], pos_ids[6], "584729103850", "12 Hoàng Văn Thụ, Q.Phú Nhuận, TP.HCM")
            ]

            for emp in sample_employees:
                cursor.execute("""
                    INSERT INTO Employees (FullName, Gender, DOB, HireDate, Email, Phone, DepartmentID, PositionID, CitizenID, Address)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, emp)
            print("-> Đã khởi tạo Danh sách Nhân viên mẫu.")

        # 6. SEED SALARIES & CONTRACTS & LEAVE & ATTENDANCE
        cursor.execute("SELECT EmployeeID FROM Employees;")
        emp_ids = [r[0] for r in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) FROM Salaries;")
        if cursor.fetchone()[0] == 0 and emp_ids:
            for eid in emp_ids:
                cursor.execute("""
                    INSERT INTO Salaries (EmployeeID, BaseSalary, Bonus, Allowance, month, year, SalaryCode, NetSalary, Status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (eid, 15000000.0, 2000000.0, 1000000.0, 7, 2026, f"SAL-202607-{eid:04d}", 16500000.0, "Đã thanh toán"))
            print("-> Đã khởi tạo Bảng lương mẫu.")

        cursor.execute("SELECT COUNT(*) FROM Contracts;")
        if cursor.fetchone()[0] == 0 and emp_ids:
            for i, eid in enumerate(emp_ids, 1):
                cursor.execute("""
                    INSERT INTO Contracts (EmployeeID, ContractType, StartDate, Status, ContractCode, ContractNumber, BasicSalary)
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