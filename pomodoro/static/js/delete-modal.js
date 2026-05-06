// Delete Confirmation Modal
class DeleteModal {
    constructor() {
        this.modal = document.getElementById('deleteModal');
        this.taskContent = document.getElementById('taskContent');
        this.confirmBtn = this.modal.querySelector('.modal-confirm');
        this.cancelBtn = this.modal.querySelector('.modal-cancel');
        this.closeBtn = this.modal.querySelector('.modal-close');
        this.backdrop = this.modal.querySelector('.modal-backdrop');
        
        this.currentTaskId = null;
        
        this.init();
    }
    
    init() {
        // Add click listeners to all delete buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.delete-btn')) {
                const btn = e.target.closest('.delete-btn');
                this.showModal(btn.dataset.taskId, btn.dataset.taskContent);
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
    
    showModal(taskId, taskContent) {
        this.currentTaskId = taskId;
        this.taskContent.textContent = taskContent;
        
        // Reset title for task deletion
        const modalTitle = document.getElementById('modalTitle');
        modalTitle.textContent = 'Confirm Delete';
        
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
        this.currentTaskId = null;
        
        // Restore body scroll
        document.body.style.overflow = '';
    }
    
    confirmDelete() {
        if (this.currentTaskId) {
            // Create and submit a form
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/task/${this.currentTaskId}/delete`;
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
    new DeleteModal();
});
