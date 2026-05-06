/**
 * Task Name Editing with Advanced Mobile Touch Support
 * Phase 3: Enhanced mobile experience with haptic feedback and gestures
 */

class TaskEditor {
    constructor() {
        this.taps = new Map(); // Track tap times for each task
        this.tapTimeout = new Map(); // Clear tap timeouts
        this.longPressTimeout = new Map(); // Long press timeouts
        this.editingTask = null; // Currently editing task
        this.originalContent = ''; // Original task content
        this.tapThreshold = 300; // milliseconds between taps
        this.longPressThreshold = 500; // milliseconds for long press
        this.isEditing = false;
        this.isTouchDevice = this.detectTouchDevice();
        this.touchStartPos = new Map(); // Track touch start positions
        this.hasMoved = new Map(); // Track if touch moved
        this.keyboardHeight = 0; // Track virtual keyboard height
        this.originalScrollPos = 0; // Original scroll position
        this.mobilePaddingAdded = false; // Track if we added padding for mobile
        
        this.init();
    }
    
    detectTouchDevice() {
        return (
            'ontouchstart' in window ||
            navigator.maxTouchPoints > 0 ||
            navigator.msMaxTouchPoints > 0
        );
    }
    
    init() {
        console.log('Task Editor initialized - Phase 3 Advanced Mobile');
        this.attachEventListeners();
        this.setupKeyboardHandling();
        this.setupHapticFeedback();
    }
    
    attachEventListeners() {
        // Use event delegation for dynamic content
        document.addEventListener('click', this.handleClick.bind(this));
        document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
        document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: true });
        document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });
        document.addEventListener('keydown', this.handleKeydown.bind(this));
        
        // Close editing when clicking outside
        document.addEventListener('click', this.handleOutsideClick.bind(this));
        
        // Handle virtual keyboard
        if (this.isTouchDevice) {
            window.addEventListener('resize', this.handleKeyboardToggle.bind(this));
            window.addEventListener('orientationchange', this.handleOrientationChange.bind(this));
        }
    }
    
    setupKeyboardHandling() {
        // Listen for keyboard show/hide on mobile
        if (this.isTouchDevice) {
            // Visual viewport API for better keyboard handling
            if (window.visualViewport) {
                window.visualViewport.addEventListener('resize', this.handleVisualViewportResize.bind(this));
            }
        }
    }
    
    setupHapticFeedback() {
        // Check if haptic feedback is available
        this.hapticSupported = 'vibrate' in navigator;
    }
    
    triggerHaptic(type = 'light') {
        if (!this.hapticSupported) return;
        
        try {
            switch (type) {
                case 'light':
                    navigator.vibrate(10);
                    break;
                case 'medium':
                    navigator.vibrate(25);
                    break;
                case 'heavy':
                    navigator.vibrate(50);
                    break;
                case 'success':
                    navigator.vibrate([10, 50, 10]);
                    break;
                case 'error':
                    navigator.vibrate([100, 50, 100]);
                    break;
                case 'doubleTap':
                    navigator.vibrate(15);
                    break;
                case 'longPress':
                    navigator.vibrate(30);
                    break;
            }
        } catch (error) {
            console.log('Haptic feedback not available:', error);
        }
    }
    
    handleClick(event) {
        const taskContent = event.target.closest('.task-content');
        if (!taskContent || this.isEditing) return;
        
        const taskId = taskContent.dataset.taskId || this.getTaskIdFromElement(taskContent);
        if (!taskId) return;
        
        // On touch devices, let touch events handle clicks
        if (this.isTouchDevice) {
            return;
        }
        
        this.handleTap(taskId, taskContent, 'click');
    }
    
    handleTouchStart(event) {
        const taskContent = event.target.closest('.task-content');
        if (!taskContent || this.isEditing) return;
        
        const taskId = taskContent.dataset.taskId || this.getTaskIdFromElement(taskContent);
        if (!taskId) return;
        
        // Prevent default to avoid double-tap zoom and text selection
        event.preventDefault();
        
        const touch = event.touches[0];
        const touchId = event.changedTouches[0].identifier;
        
        // Store touch start position and time
        this.touchStartPos.set(taskId, {
            x: touch.clientX,
            y: touch.clientY,
            time: Date.now(),
            touchId: touchId
        });
        
        this.hasMoved.set(taskId, false);
        
        // Setup long press detection
        this.setupLongPress(taskId, taskContent);
        
        // Setup double tap detection
        this.handleTap(taskId, taskContent, 'touch');
    }
    
    handleTouchMove(event) {
        const taskContent = event.target.closest('.task-content');
        if (!taskContent) return;
        
        const taskId = taskContent.dataset.taskId || this.getTaskIdFromElement(taskContent);
        if (!taskId) return;
        
        const touch = event.touches[0];
        const startPos = this.touchStartPos.get(taskId);
        
        if (startPos) {
            const deltaX = Math.abs(touch.clientX - startPos.x);
            const deltaY = Math.abs(touch.clientY - startPos.y);
            const moveThreshold = 10; // pixels
            
            if (deltaX > moveThreshold || deltaY > moveThreshold) {
                this.hasMoved.set(taskId, true);
                this.clearLongPress(taskId);
            }
        }
    }
    
    handleTouchEnd(event) {
        const taskContent = event.target.closest('.task-content');
        if (!taskContent) return;
        
        const taskId = taskContent.dataset.taskId || this.getTaskIdFromElement(taskContent);
        if (!taskId) return;
        
        // Clear long press timeout
        this.clearLongPress(taskId);
        
        // Clean up touch tracking
        this.touchStartPos.delete(taskId);
        this.hasMoved.delete(taskId);
        
        // Prevent default if this was a potential edit gesture
        if (!this.isEditing) {
            event.preventDefault();
        }
    }
    
    setupLongPress(taskId, taskContent) {
        // Clear any existing long press timeout
        this.clearLongPress(taskId);
        
        // Set new long press timeout
        const timeout = setTimeout(() => {
            if (!this.hasMoved.get(taskId) && !this.isEditing) {
                this.triggerHaptic('longPress');
                this.startEditing(taskId, taskContent, 'longPress');
            }
        }, this.longPressThreshold);
        
        this.longPressTimeout.set(taskId, timeout);
    }
    
    clearLongPress(taskId) {
        if (this.longPressTimeout.has(taskId)) {
            clearTimeout(this.longPressTimeout.get(taskId));
            this.longPressTimeout.delete(taskId);
        }
    }
    
    handleTap(taskId, taskContent, eventType) {
        // Single tap - immediately start editing
        this.triggerHaptic('light');
        this.startEditing(taskId, taskContent, 'singleTap');
    }
    
    getTaskIdFromElement(element) {
        const taskItem = element.closest('.task-item');
        return taskItem ? taskItem.dataset.taskId : null;
    }
    
    startEditing(taskId, taskContent, trigger = 'singleTap') {
        if (this.isEditing) return;
        
        this.isEditing = true;
        this.editingTask = taskId;
        this.originalContent = taskContent.textContent.trim();
        
        // Store original scroll position for mobile
        if (this.isTouchDevice) {
            this.originalScrollPos = window.pageYOffset;
        }
        
        // Create input element
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'task-edit-input';
        input.value = this.originalContent;
        input.setAttribute('aria-label', 'Edit task name');
        input.setAttribute('data-task-id', taskId);
        input.setAttribute('data-trigger', trigger);
        
        // Mobile-specific attributes
        if (this.isTouchDevice) {
            input.setAttribute('autocapitalize', 'off');
            input.setAttribute('autocorrect', 'off');
            input.setAttribute('spellcheck', 'false');
            input.setAttribute('autocomplete', 'off');
            input.setAttribute('inputmode', 'text'); // Better mobile keyboard
        }
        
        // Replace content with input
        taskContent.innerHTML = '';
        taskContent.appendChild(input);
        
        // Add visual feedback
        taskContent.classList.add('editing');
        const taskItem = taskContent.closest('.task-item');
        if (taskItem) {
            taskItem.classList.add('task-editing');
            
            // Mobile-specific: Add spacing around editing task
            if (this.isTouchDevice) {
                this.addMobileEditingSpacing(taskItem);
            }
        }
        
        // Focus and select text
        input.focus();
        input.select();
        
        // Mobile-specific: Ensure input stays visible and comfortable
        if (this.isTouchDevice) {
            this.ensureInputVisible(input);
            this.optimizeMobileInput(input);
        }
        
        console.log(`Started editing task ${taskId} via ${trigger}: "${this.originalContent}"`);
    }
    
    addMobileEditingSpacing(taskItem) {
        // Add spacing to make editing more comfortable on mobile
        const nextSibling = taskItem.nextElementSibling;
        if (nextSibling) {
            nextSibling.style.marginTop = '1rem';
        }
        
        // Add some breathing room at the bottom if needed
        const parent = taskItem.parentElement;
        if (parent) {
            const rect = taskItem.getBoundingClientRect();
            const viewportHeight = window.innerHeight;
            
            if (rect.bottom > viewportHeight * 0.8) {
                // Add temporary padding to ensure input is visible
                parent.style.paddingBottom = '100px';
                this.mobilePaddingAdded = true;
            }
        }
    }
    
    optimizeMobileInput(input) {
        // Additional mobile optimizations
        setTimeout(() => {
            // Ensure cursor is at the end for better UX
            const len = input.value.length;
            input.setSelectionRange(len, len);
            
            // Add a slight delay before re-selecting all text
            setTimeout(() => {
                input.select();
            }, 100);
        }, 50);
    }
    
    ensureInputVisible(input) {
        // Small delay to allow keyboard to appear
        setTimeout(() => {
            const rect = input.getBoundingClientRect();
            const viewportHeight = window.innerHeight;
            
            // Check if input might be hidden by keyboard
            if (rect.bottom > viewportHeight * 0.7) {
                // Scroll to keep input visible
                input.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }, 300);
    }
    
    handleKeyboardToggle() {
        if (!this.isTouchDevice || !this.isEditing) return;
        
        const currentHeight = window.innerHeight;
        const heightChange = Math.abs(this.keyboardHeight - currentHeight);
        
        if (heightChange > 150) { // Significant height change = keyboard
            if (currentHeight < this.keyboardHeight) {
                // Keyboard appeared
                this.handleKeyboardShow();
            } else {
                // Keyboard disappeared
                this.handleKeyboardHide();
            }
            this.keyboardHeight = currentHeight;
        } else if (this.keyboardHeight === 0) {
            // Initialize keyboard height
            this.keyboardHeight = currentHeight;
        }
    }
    
    handleVisualViewportResize() {
        if (!this.isEditing) return;
        
        const viewport = window.visualViewport;
        const input = document.querySelector('.task-edit-input');
        
        if (input && viewport) {
            // Adjust input position based on visual viewport
            const inputRect = input.getBoundingClientRect();
            const viewportTop = viewport.offsetTop;
            
            if (inputRect.bottom > viewportTop + viewport.height * 0.8) {
                input.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    }
    
    handleKeyboardShow() {
        // Adjust layout for keyboard
        const input = document.querySelector('.task-edit-input');
        if (input) {
            setTimeout(() => {
                input.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 100);
        }
    }
    
    handleKeyboardHide() {
        // Restore original scroll position if no changes were made
        const input = document.querySelector('.task-edit-input');
        if (input && input.value === this.originalContent) {
            setTimeout(() => {
                window.scrollTo(0, this.originalScrollPos);
            }, 100);
        }
    }
    
    handleOrientationChange() {
        // Re-center input on orientation change
        setTimeout(() => {
            const input = document.querySelector('.task-edit-input');
            if (input) {
                input.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }, 500); // Allow orientation to complete
    }
    
    async saveTask(taskId, newContent) {
        const trimmedContent = newContent.trim();
        
        if (trimmedContent === this.originalContent) {
            // No change, just cancel
            this.cancelEditing();
            return;
        }
        
        if (!trimmedContent) {
            // Empty content, show error
            this.triggerHaptic('error');
            this.showError('Task content cannot be empty');
            return;
        }
        
        try {
            // Show loading state
            this.showLoading(taskId);
            
            // Make API call
            const response = await fetch(`/task/${taskId}/update`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ content: trimmedContent })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Success - update UI
                this.triggerHaptic('success');
                this.updateTaskContent(taskId, trimmedContent);
                this.showSuccess('Task updated successfully');
                console.log(`Task ${taskId} updated to: "${trimmedContent}"`);
            } else {
                // Error from server
                this.triggerHaptic('error');
                this.showError(data.error || 'Failed to update task');
            }
        } catch (error) {
            console.error('Error updating task:', error);
            this.triggerHaptic('error');
            this.showError('Network error. Please try again.');
        } finally {
            this.hideLoading(taskId);
        }
    }
    
    cancelEditing() {
        if (!this.isEditing) return;
        
        const taskId = this.editingTask;
        const taskContent = document.querySelector(`.task-content[data-task-id="${taskId}"]`) ||
                           document.querySelector(`.task-item[data-task-id="${taskId}"] .task-content`);
        
        if (taskContent) {
            // Restore original content
            taskContent.innerHTML = this.originalContent;
            taskContent.classList.remove('editing');
            
            const taskItem = taskContent.closest('.task-item');
            if (taskItem) {
                taskItem.classList.remove('task-editing');
                
                // Clean up mobile spacing
                if (this.isTouchDevice) {
                    this.removeMobileEditingSpacing(taskItem);
                }
            }
        }
        
        // Restore scroll position on mobile
        if (this.isTouchDevice) {
            setTimeout(() => {
                window.scrollTo(0, this.originalScrollPos);
            }, 100);
        }
        
        this.resetEditingState();
    }
    
    removeMobileEditingSpacing(taskItem) {
        // Remove spacing that was added for mobile editing
        const nextSibling = taskItem.nextElementSibling;
        if (nextSibling) {
            nextSibling.style.marginTop = '';
        }
        
        // Remove temporary padding
        const parent = taskItem.parentElement;
        if (parent && this.mobilePaddingAdded) {
            parent.style.paddingBottom = '';
            this.mobilePaddingAdded = false;
        }
    }
    
    updateTaskContent(taskId, newContent) {
        const taskContent = document.querySelector(`.task-content[data-task-id="${taskId}"]`) ||
                           document.querySelector(`.task-item[data-task-id="${taskId}"] .task-content`);
        
        if (taskContent) {
            taskContent.innerHTML = newContent;
            taskContent.classList.remove('editing');
            
            const taskItem = taskContent.closest('.task-item');
            if (taskItem) {
                taskItem.classList.remove('task-editing');
                
                // Clean up mobile spacing after save
                if (this.isTouchDevice) {
                    this.removeMobileEditingSpacing(taskItem);
                }
            }
        }
        
        this.resetEditingState();
    }
    
    resetEditingState() {
        this.isEditing = false;
        this.editingTask = null;
        this.originalContent = '';
        this.keyboardHeight = 0;
        this.originalScrollPos = 0;
    }
    
    handleKeydown(event) {
        if (!this.isEditing) return;
        
        const input = event.target.closest('.task-edit-input');
        if (!input) return;
        
        switch (event.key) {
            case 'Enter':
                event.preventDefault();
                const taskId = input.dataset.taskId;
                this.triggerHaptic('light');
                this.saveTask(taskId, input.value);
                break;
            case 'Escape':
                event.preventDefault();
                this.triggerHaptic('light');
                this.cancelEditing();
                break;
        }
    }
    
    handleOutsideClick(event) {
        if (!this.isEditing) return;
        
        const input = event.target.closest('.task-edit-input');
        if (input) return; // Clicking inside the input
        
        const taskContent = event.target.closest('.task-content');
        if (taskContent && taskContent.classList.contains('editing')) return; // Clicking on the editing task
        
        // Clicking outside - cancel editing
        this.cancelEditing();
    }
    
    showLoading(taskId) {
        const taskItem = document.querySelector(`.task-item[data-task-id="${taskId}"]`);
        if (taskItem) {
            taskItem.classList.add('task-saving');
        }
    }
    
    hideLoading(taskId) {
        const taskItem = document.querySelector(`.task-item[data-task-id="${taskId}"]`);
        if (taskItem) {
            taskItem.classList.remove('task-saving');
        }
    }
    
    showError(message) {
        // Create or update error toast
        this.showToast(message, 'error');
    }
    
    showSuccess(message) {
        // Create or update success toast
        this.showToast(message, 'success');
    }
    
    showToast(message, type = 'info') {
        // Remove existing toast if any
        const existingToast = document.querySelector('.task-edit-toast');
        if (existingToast) {
            existingToast.remove();
        }
        
        // Create new toast
        const toast = document.createElement('div');
        toast.className = `task-edit-toast task-edit-toast--${type}`;
        toast.textContent = message;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');
        
        // Add to page
        document.body.appendChild(toast);
        
        // Trigger animation
        requestAnimationFrame(() => {
            toast.classList.add('task-edit-toast--show');
        });
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            toast.classList.remove('task-edit-toast--show');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.remove();
                }
            }, 300);
        }, 3000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.taskEditor = new TaskEditor();
});

// Export for potential use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TaskEditor;
}
