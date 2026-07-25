document.addEventListener("DOMContentLoaded", () => {
    const themeToggle = document.getElementById("theme-toggle");
    const html = document.documentElement;

    // --- BỔ SUNG ĐOẠN NÀY ĐỂ ĐỌC LẠI THEME KHI LOAD TRANG ---
    const savedTheme = localStorage.getItem("theme") || "light";
    html.dataset.theme = savedTheme;

    if (!themeToggle) return;

    const icon = themeToggle.querySelector("i");
    const text = themeToggle.querySelector("span");

    // 1. Hàm cập nhật UI của Button
    const updateThemeButton = (theme) => {
        const isDark = theme === "dark";
        if (icon) icon.textContent = isDark ? "☀️" : "🌙";
        if (text) text.textContent = isDark ? "Light Mode" : "Dark Mode";
    };

    // 2. Hàm set theme chuẩn hoá
    const setTheme = (newTheme, saveToStorage = true) => {
        html.dataset.theme = newTheme;
        if (saveToStorage) {
            localStorage.setItem("theme", newTheme);
        }
        updateThemeButton(newTheme);
    };

    // Sync lại trạng thái nút khi trang load xong
    updateThemeButton(html.dataset.theme);

    // 3. Sự kiện Toggle
    themeToggle.addEventListener("click", () => {
        const currentTheme = html.dataset.theme;
        const nextTheme = currentTheme === "dark" ? "light" : "dark";
        setTheme(nextTheme);
    });

    // 4. Đồng bộ Theme khi người dùng đổi ở Tab khác
    window.addEventListener("storage", (e) => {
        if (e.key === "theme" && e.newValue) {
            setTheme(e.newValue, false);
        }
    });

    // 5. Đồng bộ khi người dùng thay đổi Theme Hệ thống
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
        if (!localStorage.getItem("theme")) {
            setTheme(e.matches ? "dark" : "light", false);
        }
    });
});