document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const appMain = document.querySelector('.app-main');

    function toggleSidebar() {
        if (window.innerWidth > 992) {
            // Trên Desktop: Trượt thu gọn / mở ra như rèm cửa
            sidebar.classList.toggle('collapsed');
            if (appMain) {
                appMain.style.marginLeft = sidebar.classList.contains('collapsed') ? '0' : '260px';
                appMain.style.transition = 'margin-left 0.35s cubic-bezier(0.4, 0, 0.2, 1)';
            }
        } else {
            // Trên Mobile: Trượt ra/vào kèm overlay
            sidebar.classList.toggle('show');
            if (sidebarOverlay) {
                sidebarOverlay.classList.toggle('show');
            }
        }
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function () {
            sidebar.classList.remove('show');
            sidebarOverlay.classList.remove('show');
        });
    }
});