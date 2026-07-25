"""
DANH SÁCH HẰNG SỐ PHỤ VỤ CHO SEEDER AUDIT LOGS
"""

MODULES = [
    "Employees",
    "Departments",
    "Positions",
    "Salaries",
    "Contracts",
    "LeaveRequests",
    "Attendance",
    "Users",
    "Auth"
]

ACTIONS = ["CREATE", "UPDATE", "DELETE", "LOGIN", "LOGOUT", "EXPORT"]

IP_ADDRESSES = [
    "127.0.0.1",
    "192.168.1.15",
    "192.168.1.102",
    "10.0.0.5"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
]