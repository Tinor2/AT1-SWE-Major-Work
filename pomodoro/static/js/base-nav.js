(function () {
    const toggle = document.querySelector('.nav-toggle');
    const menu = document.getElementById('nav-menu');

    if (!toggle || !menu) return;

    toggle.addEventListener('click', () => {
        const open = toggle.getAttribute('aria-expanded') === 'true';
        toggle.setAttribute('aria-expanded', String(!open));
        menu.classList.toggle('is-open', !open);
    });

    menu.querySelectorAll('.nav-link, .logout-btn').forEach((el) => {
        el.addEventListener('click', () => {
            toggle.setAttribute('aria-expanded', 'false');
            menu.classList.remove('is-open');
        });
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && menu.classList.contains('is-open')) {
            toggle.setAttribute('aria-expanded', 'false');
            menu.classList.remove('is-open');
            toggle.focus();
        }
    });
})();

(function () {
    document.querySelectorAll('.flash-dismiss').forEach((btn) => {
        btn.addEventListener('click', () => {
            const flash = btn.closest('.flash');
            if (flash) {
                flash.style.animation = 'none';
                flash.style.opacity = '0';
                flash.style.transform = 'translateY(-6px)';
                flash.style.transition = 'opacity 0.2s, transform 0.2s';
                setTimeout(() => flash.remove(), 200);
            }
        });
    });
})();
