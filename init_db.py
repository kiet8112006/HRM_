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

    print("🚀 Đang kết nối và khởi tạo cơ sở dữ liệu PostgreSQL Cloud theo đúng cấu trúc chuẩn...")
    conn = psycopg2.connect(db_url, sslmode='require')
    cursor = conn.cursor()

    try:
        # 1. TẠO CÁC BẢNG (SCHEMA) KHỚP CHÍNH XÁC VỚI CÁC ẢNH CUNG CẤP
        cursor.execute("""
            -- 1. Users Table
            CREATE TABLE IF NOT EXISTS Users (
                UserID SERIAL PRIMARY KEY,
                Username VARCHAR(50) NOT NULL,
                PasswordHash VARCHAR(255) NOT NULL,
                FullName VARCHAR(100) NOT NULL,
                Email VARCHAR(100),
                Role VARCHAR(20) NOT NULL,
                IsActive BOOLEAN,
                CreatedAt TIMESTAMP,
                LastLogin TIMESTAMP
            );

            -- 2. Positions Table
            CREATE TABLE IF NOT EXISTS Positions (
                PositionID SERIAL PRIMARY KEY,
                PositionName VARCHAR(100) NOT NULL,
                Description VARCHAR(255),
                PositionCode VARCHAR(20),
                PositionLevel INT,
                MinSalary NUMERIC(18,2),
                MaxSalary NUMERIC(18,2),
                Status VARCHAR(20),
                IsDeleted SMALLINT
            );

            -- 3. Departments Table (ManagerID FK sẽ được ALTER thêm vào sau để tránh lỗi vòng lặp phụ thuộc với Employees)
            CREATE TABLE IF NOT EXISTS Departments (
                DepartmentID SERIAL PRIMARY KEY,
                DepartmentName VARCHAR(100) NOT NULL,
                ManagerID INT,
                DepartmentCode VARCHAR(20),
                Description VARCHAR(255),
                Location VARCHAR(100),
                Status VARCHAR(20),
                IsDeleted SMALLINT
            );

            -- 4. Employees Table
            CREATE TABLE IF NOT EXISTS Employees (
                EmployeeID SERIAL PRIMARY KEY,
                FullName VARCHAR(100) NOT NULL,
                Gender VARCHAR(10),
                DOB DATE,
                Email VARCHAR(100),
                Phone VARCHAR(15),
                DepartmentID INT REFERENCES Departments(DepartmentID) ON DELETE SET NULL,
                PositionID INT REFERENCES Positions(PositionID) ON DELETE SET NULL,
                HireDate DATE,
                Status VARCHAR(20),
                EmployeeCode VARCHAR(20),
                CitizenID VARCHAR(12),
                Address VARCHAR(255),
                Nationality VARCHAR(50),
                MaritalStatus VARCHAR(30),
                EmergencyContact VARCHAR(100),
                EmergencyPhone VARCHAR(10),
                Photo VARCHAR(255),
                ManagerID INT REFERENCES Employees(EmployeeID) ON DELETE SET NULL,
                CitizenFrontPhoto VARCHAR(255),
                CitizenBackPhoto VARCHAR(255),
                IsDeleted SMALLINT
            );

            -- Thêm lại khóa ngoại ManagerID cho bảng Departments tham chiếu tới Employees
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name = 'fk_departments_manager'
                ) THEN
                    ALTER TABLE Departments 
                    ADD CONSTRAINT fk_departments_manager 
                    FOREIGN KEY (ManagerID) REFERENCES Employees(EmployeeID) ON DELETE SET NULL;
                END IF;
            END $$;

            -- 5. Attendance Table
            CREATE TABLE IF NOT EXISTS Attendance (
                AttendanceID SERIAL PRIMARY KEY,
                EmployeeID INT NOT NULL REFERENCES Employees(EmployeeID) ON DELETE CASCADE,
                Date DATE NOT NULL,
                CheckInTime TIME,
                CheckOutTime TIME,
                Status VARCHAR(50),
                ShiftID INT,
                WorkingHours NUMERIC(5,2),
                OvertimeHours NUMERIC(5,2),
                LateMinutes INT,
                EarlyLeaveMinutes INT,
                CheckInMethod VARCHAR(30),
                ApprovalStatus VARCHAR(30),
                Notes VARCHAR(255),
                IsDeleted INT
            );

            -- 6. AuditLogs Table
            CREATE TABLE IF NOT EXISTS AuditLogs (
                LogID SERIAL PRIMARY KEY,
                UserID INT NOT NULL,
                Username VARCHAR(50) NOT NULL,
                Role VARCHAR(30) NOT NULL,
                Module VARCHAR(50) NOT NULL,
                Action VARCHAR(30) NOT NULL,
                RecordID INT,
                Description VARCHAR(500) NOT NULL,
                IPAddress VARCHAR(50),
                UserAgent VARCHAR(300),
                CreatedAt TIMESTAMP NOT NULL
            );

            -- 7. Contracts Table
            CREATE TABLE IF NOT EXISTS Contracts (
                ContractID SERIAL PRIMARY KEY,
                EmployeeID INT NOT NULL REFERENCES Employees(EmployeeID) ON DELETE CASCADE,
                ContractType VARCHAR(100),
                StartDate DATE,
                EndDate DATE,
                Status VARCHAR(50),
                ContractCode VARCHAR(20),
                ContractNumber VARCHAR(50),
                BasicSalary NUMERIC(18,2),
                WorkLocation VARCHAR(200),
                DepartmentID INT REFERENCES Departments(DepartmentID) ON DELETE SET NULL,
                PositionID INT REFERENCES Positions(PositionID) ON DELETE SET NULL,
                Signer VARCHAR(100),
                SignDate DATE,
                ProbationMonths INT,
                ContractFile VARCHAR(255),
                Description VARCHAR(500),
                IsDeleted SMALLINT
            );

            -- 8. LeaveRequests Table
            CREATE TABLE IF NOT EXISTS LeaveRequests (
                RequestID SERIAL PRIMARY KEY,
                EmployeeID INT NOT NULL REFERENCES Employees(EmployeeID) ON DELETE CASCADE,
                FromDate DATE,
                ToDate DATE,
                Reason VARCHAR(500),
                Status VARCHAR(50),
                LeaveCode VARCHAR(20),
                TotalDays INT,
                Attachment VARCHAR(255),
                AppliedDate DATE,
                ApprovedBy VARCHAR(100),
                ApprovedDate DATE,
                Description VARCHAR(255),
                LeaveType VARCHAR(50),
                IsDeleted SMALLINT
            );

            -- 9. Notifications Table
            CREATE TABLE IF NOT EXISTS Notifications (
                NotificationID SERIAL PRIMARY KEY,
                Title VARCHAR(200) NOT NULL,
                Message VARCHAR(500) NOT NULL,
                Type VARCHAR(30) NOT NULL,
                ReceiverRole VARCHAR(30),
                ReceiverID INT,
                Url VARCHAR(255),
                IsRead BOOLEAN,
                CreatedAt TIMESTAMP
            );

            -- 10. Salaries Table
            CREATE TABLE IF NOT EXISTS Salaries (
                SalaryID SERIAL PRIMARY KEY,
                EmployeeID INT NOT NULL REFERENCES Employees(EmployeeID) ON DELETE CASCADE,
                BaseSalary NUMERIC(18,2),
                Bonus NUMERIC(18,2),
                Allowance NUMERIC(18,2),
                month INT,
                year INT,
                SalaryCode VARCHAR(20),
                OvertimePay NUMERIC(18,2),
                Deduction NUMERIC(18,2),
                Tax NUMERIC(18,2),
                Insurance NUMERIC(18,2),
                NetSalary NUMERIC(18,2),
                PaymentDate DATE,
                Status VARCHAR(20),
                Notes VARCHAR(255),
                IsDeleted SMALLINT
            );
        """)
        print("✅ Đã tạo toàn bộ cấu trúc các bảng chuẩn theo đúng các hình ảnh mẫu.")

        # 2. SEED USERS
        cursor.execute("SELECT COUNT(*) FROM Users;")
        if cursor.fetchone()[0] == 0:
            for u in DEFAULT_USERS:
                pass_hash = generate_password_hash(u["Password"])
                cursor.execute("""
                    INSERT INTO Users (Username, PasswordHash, FullName, Email, Role, IsActive, CreatedAt)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
                """, (u["Username"], pass_hash, u["FullName"], u["Email"], u["Role"], u["IsActive"]))
            print("-> Đã khởi tạo dữ liệu mẫu cho bảng Users.")

        # 3. SEED POSITIONS
        cursor.execute("SELECT COUNT(*) FROM Positions;")
        if cursor.fetchone()[0] == 0:
            for i, pos in enumerate(POSITIONS, 1):
                cursor.execute("""
                    INSERT INTO Positions (PositionName, PositionCode, Description, PositionLevel, MinSalary, MaxSalary, Status, IsDeleted)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 0);
                """, (pos, f"POS{i:03d}", f"Mô tả chức vụ {pos}", i, 5000000.0, 30000000.0, "Active"))
            print("-> Đã khởi tạo dữ liệu mẫu cho bảng Positions.")

        # 4. SEED DEPARTMENTS
        cursor.execute("SELECT COUNT(*) FROM Departments;")
        if cursor.fetchone()[0] == 0:
            for i, dept in enumerate(DEPARTMENTS, 1):
                cursor.execute("""
                    INSERT INTO Departments (DepartmentName, DepartmentCode, Description, Location, Status, IsDeleted)
                    VALUES (%s, %s, %s, %s, %s, 0);
                """, (dept, f"DP{i:03d}", f"Mô tả cho {dept}", "TP. Hồ Chí Minh", "Active"))
            print("-> Đã khởi tạo dữ liệu mẫu cho bảng Departments.")

        # 5. SEED EMPLOYEES
        cursor.execute("SELECT COUNT(*) FROM Employees;")
        if cursor.fetchone()[0] == 0:
            cursor.execute("SELECT DepartmentID FROM Departments;")
            dept_ids = [r[0] for r in cursor.fetchall()]
            cursor.execute("SELECT PositionID FROM Positions;")
            pos_ids = [r[0] for r in cursor.fetchall()]

            sample_employees = [
                ("Nguyễn Văn An", "Nam", "1992-05-10", "an.nguyen@hrm.com", "0901234567", dept_ids[0], pos_ids[1], "2021-01-15", "Active", "EMP001", "284729103847", "123 Lê Lợi, Q1, TP.HCM", "Việt Nam", "Độc thân", "Nguyễn Thị Hoa", "0909123456"),
                ("Trần Thị Bích", "Nữ", "1995-08-20", "bich.tran@hrm.com", "0912345678", dept_ids[1], pos_ids[5], "2021-03-20", "Active", "EMP002", "384729103848", "456 Nguyễn Huệ, Q1, TP.HCM", "Việt Nam", "Đã kết hôn", "Trần Văn Minh", "0909234567"),
                ("Lê Hoàng Nam", "Nam", "1990-12-02", "nam.le@hrm.com", "0923456789", dept_ids[0], pos_ids[4], "2020-06-01", "Active", "EMP003", "484729103849", "789 Cách Mạng Tháng 8, Q3, TP.HCM", "Việt Nam", "Độc thân", "Lê Thị Mai", "0909345678"),
                ("Phạm Minh Tuấn", "Nam", "1998-03-15", "tuan.pham@hrm.com", "0934567890", dept_ids[2], pos_ids[6], "2022-09-10", "Active", "EMP004", "584729103850", "12 Hoàng Văn Thụ, Q.Phú Nhuận, TP.HCM", "Việt Nam", "Độc thân", "Phạm Văn Hùng", "0909456789")
            ]

            for emp in sample_employees:
                cursor.execute("""
                    INSERT INTO Employees (
                        FullName, Gender, DOB, Email, Phone, DepartmentID, PositionID, 
                        HireDate, Status, EmployeeCode, CitizenID, Address, Nationality, 
                        MaritalStatus, EmergencyContact, EmergencyPhone, IsDeleted
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0);
                """, emp)
            print("-> Đã khởi tạo dữ liệu mẫu cho bảng Employees.")

        # 6. SEED SALARIES & CONTRACTS
        cursor.execute("SELECT EmployeeID FROM Employees;")
        emp_ids = [r[0] for r in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) FROM Salaries;")
        if cursor.fetchone()[0] == 0 and emp_ids:
            for eid in emp_ids:
                cursor.execute("""
                    INSERT INTO Salaries (
                        EmployeeID, BaseSalary, Bonus, Allowance, month, year, 
                        SalaryCode, NetSalary, Status, IsDeleted
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0);
                """, (eid, 15000000.0, 2000000.0, 1000000.0, 7, 2026, f"SAL-202607-{eid:04d}", 18000000.0, "Đã thanh toán"))
            print("-> Đã khởi tạo dữ liệu mẫu cho bảng Salaries.")

        cursor.execute("SELECT COUNT(*) FROM Contracts;")
        if cursor.fetchone()[0] == 0 and emp_ids:
            for i, eid in enumerate(emp_ids, 1):
                cursor.execute("""
                    INSERT INTO Contracts (
                        EmployeeID, ContractType, StartDate, EndDate, Status, 
                        ContractCode, ContractNumber, BasicSalary, IsDeleted
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0);
                """, (eid, "Không xác định thời hạn", "2022-01-01", None, "Hiệu lực", f"HD-{i:05d}", f"HDLD/2026/{i:04d}", 15000000.0))
            print("-> Đã khởi tạo dữ liệu mẫu cho bảng Contracts.")

        conn.commit()
        print("🎉 TẤT CẢ CÁC BẢNG VÀ DỮ LIỆU ĐÃ ĐƯỢC CẬP NHẬT CHÍNH XÁC THÀNH CÔNG!")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Lỗi trong quá trình khởi tạo dữ liệu: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    init_database()