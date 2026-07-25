"""
DANH SÁCH HẰNG SỐ PHỤ VỤ CHO SEEDER NOTIFICATIONS
"""

NOTIFICATION_TYPES = ["Info", "Warning", "Success", "System"]

SAMPLE_NOTIFICATIONS = [
    {
        "Title": "Đơn nghỉ phép mới chờ duyệt",
        "Message": "Nhân viên Nguyễn Văn A đã gửi đơn xin nghỉ phép năm. Vui lòng kiểm tra và phê duyệt.",
        "Type": "Info",
        "ReceiverRole": "Admin",
        "Url": "/leave_requests"
    },
    {
        "Title": "Hợp đồng sắp hết hạn",
        "Message": "Có 3 hợp đồng lao động sẽ hết hạn trong vòng 30 ngày tới. Hãy tiến hành gia hạn.",
        "Type": "Warning",
        "ReceiverRole": "Manager",
        "Url": "/contracts"
    },
    {
        "Title": "Thanh toán lương thành công",
        "Message": "Bảng lương tháng hiện tại đã được kế toán phê duyệt và gửi thông báo tới nhân viên.",
        "Type": "Success",
        "ReceiverRole": None,  # Gửi cho toàn bộ mọi người
        "Url": "/salaries"
    },
    {
        "Title": "Bảo trì hệ thống định kỳ",
        "Message": "Hệ thống HRM sẽ tiến hành bảo trì server vào lúc 23:00 cuối tuần này.",
        "Type": "System",
        "ReceiverRole": None,
        "Url": "/notifications"
    }
]