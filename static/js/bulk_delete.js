document.addEventListener("DOMContentLoaded", () => {
    const selectAll = document.getElementById("check-all");
    const deleteButton = document.getElementById("delete-selected-btn");
    const form = document.getElementById("bulk-delete-form");

    if (!selectAll || !deleteButton || !form) return;

    // Lấy tên đối tượng từ data-entity trong form (Ví dụ: data-entity="nhân viên")
    // Mặc định nếu không truyền sẽ là "mục"
    const entityName = form.dataset.entity || "mục";

    // Helper: Lấy tất cả checkbox hàng trong bảng
    const getItemCheckboxes = () => document.querySelectorAll(".item-checkbox");

    // Helper: Cập nhật trạng thái nút Xóa & Indeterminate của checkbox Chọn Tất Cả
    const updateUIState = () => {
        const checkboxes = getItemCheckboxes();
        const checked = document.querySelectorAll(".item-checkbox:checked");

        deleteButton.disabled = checked.length === 0;

        if (checkboxes.length > 0) {
            selectAll.checked = checked.length === checkboxes.length;
            selectAll.indeterminate = checked.length > 0 && checked.length < checkboxes.length;
        }
    };

    // 1. Xử lý khi nhấn "Select All"
    selectAll.addEventListener("change", function () {
        getItemCheckboxes().forEach((cb) => (cb.checked = this.checked));
        this.indeterminate = false;
        updateUIState();
    });

    // 2. Xử lý khi tick từng ô (Dùng Event Delegation tối ưu bộ nhớ & dynamic elements)
    document.addEventListener("change", (e) => {
        if (e.target.classList.contains("item-checkbox")) {
            updateUIState();
        }
    });

    // 3. Xử lý khi Submit Form Xóa
    form.addEventListener("submit", function (e) {
        const checkedCount = document.querySelectorAll(".item-checkbox:checked").length;

        if (checkedCount === 0) {
            e.preventDefault();
            alert(`Vui lòng chọn ít nhất một ${entityName}!`);
            return;
        }

        if (!confirm(`Bạn có chắc muốn xóa ${checkedCount} ${entityName} đã chọn?`)) {
            e.preventDefault();
        }
    });

    // Khởi tạo trạng thái ban đầu
    updateUIState();
});