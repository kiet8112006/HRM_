document.addEventListener("DOMContentLoaded", () => {
    // 1. Cấu hình kiểm tra file chung
    const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
    const MAX_SIZE_MB = 2;
    const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
    const DEFAULT_AVATAR = "/static/avatars/default.png";

    // Helper: Hàm xử lý Preview ảnh dùng URL.createObjectURL (Tối ưu RAM & Tái sử dụng)
    function setupImagePreview(inputId, previewId, options = {}) {
        const input = document.getElementById(inputId);
        const preview = document.getElementById(previewId);

        if (!input || !preview) return;

        input.addEventListener("change", function () {
            const file = this.files[0];

            // Nếu người dùng nhấn Cancel (không chọn file)
            if (!file) return;

            // Kiểm tra Validate (nếu chọn flag validate)
            if (options.validate) {
                if (!ALLOWED_TYPES.includes(file.type)) {
                    alert('Định dạng ảnh không hợp lệ (chỉ chấp nhận JPG, PNG, WEBP).');
                    resetInput(this, preview);
                    return;
                }

                if (file.size > MAX_SIZE_BYTES) {
                    alert(`Ảnh không được lớn hơn ${MAX_SIZE_MB}MB.`);
                    resetInput(this, preview);
                    return;
                }
            }

            // Giải phóng bộ nhớ Blob cũ nếu có (Tránh memory leak)
            if (preview.dataset.objectUrl) {
                URL.revokeObjectURL(preview.dataset.objectUrl);
            }

            // Tạo Object URL mới
            const objectUrl = URL.createObjectURL(file);
            preview.src = objectUrl;
            preview.dataset.objectUrl = objectUrl; // Lưu vết để revoke sau này
            preview.style.display = 'block';
        });
    }

    // Helper: Reset input về mặc định
    function resetInput(input, preview) {
        input.value = "";
        preview.src = DEFAULT_AVATAR;
        if (preview.dataset.objectUrl) {
            URL.revokeObjectURL(preview.dataset.objectUrl);
            delete preview.dataset.objectUrl;
        }
    }

    // 2. Đăng ký Upload & Preview cho các Input
    setupImagePreview("photo", "preview-image", { validate: true });
    setupImagePreview("citizen-front", "preview-citizen-front", { validate: true });
    setupImagePreview("citizen-back", "preview-citizen-back", { validate: true });

    // 3. Quản lý Modal Lightbox (Tối ưu bằng Event Delegation)
    const modal = document.getElementById("image-modal");
    const modalImage = document.getElementById("modal-image");
    const closeModalBtn = document.getElementById("close-modal");

    if (modal && modalImage) {
        // Event Delegation: Lắng nghe click toàn trang cho các phần tử có class .preview-click
        document.addEventListener("click", (e) => {
            if (e.target.classList.contains("preview-click")) {
                modal.style.display = "flex";
                modalImage.src = e.target.src;
            }
        });

        // Đóng Modal khi bấm nút Close hoặc Bấm ra ngoài vùng Modal
        const hideModal = () => { modal.style.display = "none"; };

        if (closeModalBtn) closeModalBtn.addEventListener("click", hideModal);
        
        modal.addEventListener("click", (e) => {
            if (e.target === modal) hideModal();
        });
    }
});