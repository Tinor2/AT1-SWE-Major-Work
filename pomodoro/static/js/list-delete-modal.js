// List Delete Confirmation Modal
class ListDeleteModal {
    constructor() {
        this.modal = document.getElementById('listDeleteModal');
        this.listName = document.getElementById('listName');
        this.confirmBtn = this.modal.querySelector('.modal-confirm');
        this.cancelBtn = this.modal.querySelector('.modal-cancel');
        this.closeBtn = this.modal.querySelector('.modal-close');
        this.backdrop = this.modal.querySelector('.modal-backdrop');
        
        this.currentListId = null;
        
        this.init();
    }
    
    init() {
        // Add click listeners to all delete buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.delete-list-btn')) {
                const btn = e.target.closest('.delete-list-btn');
                this.showModal(btn.dataset.listId, btn.dataset.listName);
            }
        });
        
        // Close modal handlers
        this.cancelBtn.addEventListener('click', () => this.hideModal());
        this.closeBtn.addEventListener('click', () => this.hideModal());
        this.backdrop.addEventListener('click', () => this.hideModal());
        
        // Confirm delete handler
        this.confirmBtn.addEventListener('click', () => this.confirmDelete());
        
        // Escape key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.classList.contains('show')) {
                this.hideModal();
            }
        });
    }
    
    showModal(listId, listName) {
        this.currentListId = listId;
        this.listName.textContent = listName;
        this.modal.classList.add('show');
        this.modal.setAttribute('aria-hidden', 'false');
        
        // Focus on confirm button for accessibility
        this.confirmBtn.focus();
        
        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    }
    
    hideModal() {
        this.modal.classList.remove('show');
        this.modal.setAttribute('aria-hidden', 'true');
        this.currentListId = null;
        
        // Restore body scroll
        document.body.style.overflow = '';
    }
    
    confirmDelete() {
        if (this.currentListId) {
            // Create and submit a form
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/lists/${this.currentListId}/delete`;
            form.style.display = 'none';
            
            // Add CSRF token if exists (for Flask-WTF)
            const csrfToken = document.querySelector('meta[name="csrf-token"]');
            if (csrfToken) {
                const csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrf_token';
                csrfInput.value = csrfToken.getAttribute('content');
                form.appendChild(csrfInput);
            }
            
            document.body.appendChild(form);
            form.submit();
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ListDeleteModal();
});
