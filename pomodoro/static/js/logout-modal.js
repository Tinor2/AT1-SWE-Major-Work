// Logout Confirmation Modal
class LogoutModal {
    constructor() {
        this.modal = document.getElementById('logoutModal');
        this.logoutBtn = document.querySelector('.logout-btn');
        this.cancelBtn = this.modal ? this.modal.querySelector('.modal-cancel') : null;
        this.confirmBtn = this.modal ? this.modal.querySelector('.modal-confirm') : null;
        this.closeBtn = this.modal ? this.modal.querySelector('.modal-close') : null;
        this.backdrop = this.modal ? this.modal.querySelector('.modal-backdrop') : null;
        this.logoutForm = document.querySelector('.logout-form');
        
        this.init();
    }
    
    init() {
        if (!this.modal || !this.logoutBtn) return;
        
        // Prevent form submission and show modal instead
        this.logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.showModal();
        });
        
        // Close modal handlers
        if (this.cancelBtn) this.cancelBtn.addEventListener('click', () => this.hideModal());
        if (this.closeBtn) this.closeBtn.addEventListener('click', () => this.hideModal());
        if (this.backdrop) this.backdrop.addEventListener('click', () => this.hideModal());
        
        // Confirm logout handler
        if (this.confirmBtn) this.confirmBtn.addEventListener('click', () => this.confirmLogout());
        
        // Escape key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.classList.contains('show')) {
                this.hideModal();
            }
        });
    }
    
    showModal() {
        this.modal.classList.add('show');
        this.modal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        
        // Focus on confirm button for accessibility
        if (this.confirmBtn) {
            this.confirmBtn.focus();
        }
    }
    
    hideModal() {
        this.modal.classList.remove('show');
        this.modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        
        // Return focus to logout button
        if (this.logoutBtn) {
            this.logoutBtn.focus();
        }
    }
    
    confirmLogout() {
        // Submit the logout form
        if (this.logoutForm) {
            this.logoutForm.submit();
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new LogoutModal();
});
