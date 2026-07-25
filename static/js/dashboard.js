/* ==========================================================
   1. Helper & Data Parsing
========================================================== */

// Hàm parse JSON an toàn
function parseJSON(value) {
    if (!value || typeof value !== "string") return [];
    try {
        const parsed = JSON.parse(value.trim());
        return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
        console.error("JSON Parse Error:", error, value);
        return [];
    }
}

// Format số tiền (VD: 15.5M VNĐ hoặc chuẩn locale)
const formatCurrencyM = (value) => {
    return new Intl.NumberFormat('vi-VN', { 
        maximumFractionDigits: 1 
    }).format(value / 1_000_000) + "M";
};

// Lưu trữ instance của các chart để destroy() khi render lại (tránh leak)
const chartInstances = {};

// Hàm helper để render chart an toàn
function createChart(canvasId, config) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    // Destroy chart cũ nếu đã tồn tại trên canvas này
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    // Đăng ký Plugin DataLabels nếu có
    if (typeof ChartDataLabels !== "undefined" && !config.plugins) {
        config.plugins = [ChartDataLabels];
    }

    chartInstances[canvasId] = new Chart(canvas, config);
    return chartInstances[canvasId];
}

/* ==========================================================
   2. Render Functions
========================================================== */

function renderDepartmentChart(data) {
    if (!data.departmentLabels.length || !data.departmentCounts.length) return;

    createChart("departmentChart", {
        type: "doughnut",
        data: {
            labels: data.departmentLabels,
            datasets: [{
                data: data.departmentCounts,
                backgroundColor: [
                    "#2563eb", "#22c55e", "#f59e0b", "#ef4444",
                    "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16"
                ],
                borderWidth: 2,
                borderColor: "var(--bg-card, #ffffff)" // Tự động đổi viền theo Theme CSS
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "60%",
            plugins: {
                legend: { position: "right" },
                datalabels: {
                    color: "#ffffff",
                    font: { weight: "bold", size: 13 },
                    formatter: (value) => (value > 0 ? value : "")
                }
            }
        }
    });
}

function renderSalaryChart(data) {
    if (!data.salaryTotals.length) return;

    const values = data.salaryTotals;
    const maxSalary = Math.max(...values);

    // Highlight tháng có lương cao nhất
    const pointColors = values.map(val => val === maxSalary ? "#ef4444" : "#2563eb");

    createChart("salaryChart", {
        type: "line",
        data: {
            labels: data.salaryMonths,
            datasets: [{
                label: "Tổng lương",
                data: values,
                borderColor: "#2563eb",
                backgroundColor: "rgba(37, 99, 235, 0.12)",
                fill: true,
                tension: 0.35,
                pointRadius: 5,
                pointHoverRadius: 8,
                pointBackgroundColor: pointColors
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                datalabels: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `Tổng lương: ${ctx.raw.toLocaleString('vi-VN')} VNĐ`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: (value) => formatCurrencyM(value)
                    }
                }
            }
        }
    });
}

function renderAttendanceChart(data) {
    if (!data.attendanceData.length) return;

    createChart("attendanceChart", {
        type: "doughnut",
        data: {
            labels: ["Đi làm", "Đi trễ", "Nghỉ", "Chưa chấm công"],
            datasets: [{
                data: data.attendanceData,
                backgroundColor: ["#22c55e", "#f59e0b", "#ef4444", "#94a3b8"],
                borderWidth: 2,
                borderColor: "var(--bg-card, #ffffff)"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "65%",
            plugins: {
                legend: { position: "right" },
                datalabels: {
                    color: "#ffffff",
                    font: { weight: "bold", size: 13 },
                    formatter: (value) => (value > 0 ? value : "")
                }
            }
        }
    });
}

/* ==========================================================
   3. Main Initialization
========================================================== */

document.addEventListener("DOMContentLoaded", () => {
    const body = document.body;

    // Load Data
    const dashboardData = {
        departmentLabels: parseJSON(body.dataset.departmentLabels),
        departmentCounts: parseJSON(body.dataset.departmentCounts),
        salaryMonths: parseJSON(body.dataset.salaryMonths),
        salaryTotals: parseJSON(body.dataset.salaryTotals),
        attendanceData: parseJSON(body.dataset.attendanceData)
    };

    // Render All Charts
    renderDepartmentChart(dashboardData);
    renderSalaryChart(dashboardData);
    renderAttendanceChart(dashboardData);
});