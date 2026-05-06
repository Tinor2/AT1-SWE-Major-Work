document.addEventListener('DOMContentLoaded', function() {
    console.log('Lists page loaded');
    
    // List Edit Modal functionality
    const editModal = document.getElementById('listEditModal');
    const editForm = document.getElementById('listEditForm');
    const listNameInput = document.getElementById('listNameInput');
    const listDescriptionInput = document.getElementById('listDescriptionInput');
    let currentEditingListId = null;
    
    // Open edit modal when edit button is clicked
    document.addEventListener('click', function(e) {
        if (e.target.closest('.edit-list-btn')) {
            const btn = e.target.closest('.edit-list-btn');
            currentEditingListId = btn.dataset.listId;
            const listName = btn.dataset.listName;
            const listDescription = btn.dataset.listDescription;
            
            // Populate form fields
            listNameInput.value = listName;
            listDescriptionInput.value = listDescription;
            
            // Set form action
            editForm.action = `/lists/${currentEditingListId}/edit`;
            
            // Show modal
            editModal.classList.add('show');
        }
    });
    
    // Close modal handlers
    function closeEditModal() {
        editModal.classList.remove('show');
        currentEditingListId = null;
        editForm.reset();
    }
    
    // Close modal on cancel button click
    editModal.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal-cancel') || e.target.classList.contains('modal-close')) {
            closeEditModal();
        }
    });
    
    // Close modal on backdrop click
    editModal.addEventListener('click', function(e) {
        if (e.target === editModal || e.target.classList.contains('modal-backdrop')) {
            closeEditModal();
        }
    });
    
    // Handle form submission
    editForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(editForm);
        const submitBtn = editForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        
        // Show loading state
        submitBtn.textContent = 'Saving...';
        submitBtn.disabled = true;
        
        fetch(editForm.action, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.ok) {
                // Success - reload page to show updated list
                window.location.reload();
            } else {
                throw new Error('Failed to update list');
            }
        })
        .catch(error => {
            console.error('Error updating list:', error);
            // Show error message
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-error';
            errorDiv.textContent = 'Failed to update list. Please try again.';
            editForm.querySelector('.modal-body').prepend(errorDiv);
            
            // Reset button
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
            
            // Remove error message after 3 seconds
            setTimeout(() => {
                if (errorDiv.parentNode) {
                    errorDiv.parentNode.removeChild(errorDiv);
                }
            }, 3000);
        });
    });
    
    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && editModal.classList.contains('show')) {
            closeEditModal();
        }
    });
});