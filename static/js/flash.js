document.addEventListener("DOMContentLoaded", () => {
    const flashMessages = document.querySelectorAll(".flash-message");
    if (flashMessages.length === 0) return;

    // Helper: Hàm đóng thông báo có hiệu ứng fade-out
    const dismissFlash = (flashItem) => {
        if (!flashItem || flashItem.classList.contains("flash-hide")) return;
        
        flashItem.classList.add("flash-hide");
        setTimeout(() => {
            flashItem.remove();
        }, 300); // 300ms trùng với transition CSS
    };

    // 1. Đăng ký tự động ẩn sau 5 giây
    flashMessages.forEach((item) => {
        const timer = setTimeout(() => {
            dismissFlash(item);
        }, 5000);

        // Lưu timer ID vào element để xóa nếu cần
        item.dataset.timerId = timer;
    });

    // 2. Bắt sự kiện nhấn nút đóng (X) bằng Event Delegation
    document.addEventListener("click", (e) => {
        const closeBtn = e.target.closest(".flash-close");
        if (closeBtn) {
            const flashItem = closeBtn.closest(".flash-message");
            if (flashItem) {
                // Xóa bộ đếm tự động ẩn nếu người dùng bấm nút đóng
                if (flashItem.dataset.timerId) {
                    clearTimeout(Number(flashItem.dataset.timerId));
                }
                dismissFlash(flashItem);
            }
        }
    });
});