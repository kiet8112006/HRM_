document.addEventListener("DOMContentLoaded", function () {
    const body = document.body;

    // Parse JSON an toàn
    const safeJSONParse = (attrName) => {
        const value = body.getAttribute(attrName);
        if (!value) return [];
        try {
            // Trường hợp Jinja đã format thành JSON String chuẩn
            const parsed = typeof value === 'string' ? JSON.parse(value) : value;
            // Nếu sau khi parse vẫn ra chuỗi (do escape 2 lần), parse thêm lần nữa
            if (typeof parsed === 'string') {
                return JSON.parse(parsed);
            }
            return Array.isArray(parsed) ? parsed : [];
        } catch (e) {
            console.error(`Lỗi parse JSON ở attribute [${attrName}]:`, e, value);
            return [];
        }
    };

    // Format tiền tệ gọn nhẹ (10M, 500K,...)
    const formatCurrencyCompact = (value) => {
        if (value >= 1_000_000_000) return (value / 1_000_000_000).toFixed(1) + "B";
        if (value >= 1_000_000) return (value / 1_000_000).toFixed(1) + "M";
        if (value >= 1_000) return (value / 1_000).toFixed(0) + "K";
        return value;
    };

    // Palette màu tự động lặp lại
    const BASE_COLORS = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16'];
    const generateColors = (count) => Array.from({ length: count }, (_, i) => BASE_COLORS[i % BASE_COLORS.length]);

    // Tránh trùng lặp instance làm vỡ Canvas
    const chartInstances = {};
    const renderChart = (canvasId, config) => {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        if (chartInstances[canvasId]) {
            chartInstances[canvasId].destroy();
        }

        chartInstances[canvasId] = new Chart(canvas, config);
    };

    /* 1. LẤY DỮ LIỆU TỪ ATTRIBUTE CỦA BODY */
    const salaryNames = safeJSONParse("data-salary-names");
    const salaryValues = safeJSONParse("data-salary-values");
    const leaveStatus = safeJSONParse("data-leave-status");
    const leaveCounts = safeJSONParse("data-leave-counts");
    const departmentNames = safeJSONParse("data-department-names");
    const departmentCounts = safeJSONParse("data-department-counts");

    /* 2. RENDER CÁC BIỂU ĐỒ */

    // 1. BIỂU ĐỒ PHÒNG BAN (Bar Chart)
    if (departmentNames.length > 0) {
        renderChart('departmentChart', {
            type: 'bar',
            data: {
                labels: departmentNames,
                datasets: [{
                    label: 'Số lượng nhân sự',
                    data: departmentCounts,
                    backgroundColor: generateColors(departmentNames.length),
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { 
                    y: { 
                        beginAtZero: true, 
                        ticks: { stepSize: 1, precision: 0 } 
                    } 
                }
            }
        });
    }

    // 2. BIỂU ĐỒ TOP 5 LƯƠNG (Bar Chart)
    if (salaryNames.length > 0) {
        renderChart('salaryChart', {
            type: 'bar',
            data: {
                labels: salaryNames,
                datasets: [{
                    label: 'Tổng thu nhập',
                    data: salaryValues,
                    backgroundColor: '#10b981',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `Thu nhập: ${ctx.raw.toLocaleString('vi-VN')} VNĐ`
                        }
                    }
                },
                scales: { 
                    y: { 
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => formatCurrencyCompact(value)
                        }
                    } 
                }
            }
        });
    }

    // 3. BIỂU ĐỒ TÌNH TRẠNG NGHỈ PHÉP (Doughnut Chart)
    if (leaveStatus.length > 0) {
        renderChart('leaveChart', {
            type: 'doughnut',
            data: {
                labels: leaveStatus,
                datasets: [{
                    data: leaveCounts,
                    backgroundColor: ['#f59e0b', '#10b981', '#ef4444', '#8b5cf6'].slice(0, leaveStatus.length),
                    borderWidth: 2,
                    borderColor: 'var(--bg-card, #ffffff)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                    legend: { position: 'bottom' } 
                }
            }
        });
    }
});