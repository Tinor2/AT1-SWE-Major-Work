// Dark Mode Toggle
(function() {
    const themeToggle = document.getElementById('theme-toggle');
    const iconSun = document.querySelector('.theme-toggle .icon-sun');
    const iconMoon = document.querySelector('.theme-toggle .icon-moon');

    const currentTheme = localStorage.getItem('theme') || 'light';
    applyTheme(currentTheme);
    updateThemeIcons(currentTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const theme = document.documentElement.getAttribute('data-theme');
            const newTheme = theme === 'dark' ? 'light' : 'dark';

            applyTheme(newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcons(newTheme);
        });
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        document.documentElement.style.colorScheme = theme === 'dark' ? 'dark' : 'light';
    }

    function updateThemeIcons(theme) {
        const isDark = theme === 'dark';
        if (iconSun) iconSun.hidden = !isDark;
        if (iconMoon) iconMoon.hidden = isDark;
    }

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            const newTheme = e.matches ? 'dark' : 'light';
            applyTheme(newTheme);
            updateThemeIcons(newTheme);
        }
    });
})();
