document.addEventListener("DOMContentLoaded", function () {
    const bodyEl = document.body;

    // Đọc và parse dữ liệu được truyền ngầm từ data attributes của thẻ body
    const dashboardData = {
        departmentLabels: JSON.parse(bodyEl.dataset.departmentLabels || "[]"),
        departmentCounts: JSON.parse(bodyEl.dataset.departmentCounts || "[]"),
        salaryMonths: JSON.parse(bodyEl.dataset.salaryMonths || "[]"),
        salaryTotals: JSON.parse(bodyEl.dataset.salaryTotals || "[]"),
        attendanceData: JSON.parse(bodyEl.dataset.attendanceData || "[0, 0, 0, 0]")
    };

    // 1. Biểu đồ phòng ban (Department Chart)
    const deptEl = document.getElementById("departmentChart"); // (Hoặc ID canvas tương ứng trong dashboard của cậu)
    if (deptEl && dashboardData.departmentLabels.length > 0) {
        new Chart(deptEl, {
            type: "bar",
            data: {
                labels: dashboardData.departmentLabels,
                datasets: [{
                    label: "Số lượng nhân viên",
                    data: dashboardData.departmentCounts,
                    backgroundColor: "#2563eb",
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // 2. Biểu đồ quỹ lương theo tháng (Salary Chart)
    const salaryEl = document.getElementById("salaryChart");
    if (salaryEl && dashboardData.salaryMonths.length > 0) {
        new Chart(salaryEl, {
            type: "line",
            data: {
                labels: dashboardData.salaryMonths,
                datasets: [{
                    label: "Tổng quỹ lương",
                    data: dashboardData.salaryTotals,
                    borderColor: "#16a34a",
                    backgroundColor: "rgba(22, 163, 74, 0.1)",
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true
            }
        });
    }

    // 3. Biểu đồ chấm công (Attendance Chart)
    const attendanceEl = document.getElementById(" attendanceChart");
    if (attendanceEl) {
        new Chart(attendanceEl, {
            type: "doughnut",
            data: {
                labels: ["Đúng giờ", "Đi trễ", "Vắng mặt", "Chưa điểm danh"],
                datasets: [{
                    data: dashboardData.attendanceData,
                    backgroundColor: ["#16a34a", "#f59e0b", "#dc2626", "#9ca3af"]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: "bottom" }
                }
            }
        });
    }
});