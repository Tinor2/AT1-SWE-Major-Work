// Unified Drag Controller - Single Source of Truth for Drag Operations
// Eliminates double placeholder issue by architectural design

class UnifiedDragController {
    constructor() {
        // Core state
        this.placeholder = null;
        this.draggedElement = null;
        this.dragMode = null; // 'reorder' or 'hierarchy'
        this.dropTarget = null;
        this.isReordering = false;
        
        // Animation state
        this.originalRect = null;
        
        // Debug logging state
        this.lastLoggedMode = null;
        
        // Task list reference
        this.taskList = null;
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }
    }
    
    // Single entry point for all drag operations
    initialize() {
        this.taskList = document.querySelector('.task-list');
        if (!this.taskList) {
            console.warn('Task list not found. Drag controller disabled.');
            return;
        }
        
        this.setupEventListeners();
        console.log('Unified Drag Controller initialized');
    }
    
    // Setup all event listeners in one place
    setupEventListeners() {
        // Task list events
        this.taskList.addEventListener('dragover', this.handleDragOver.bind(this));
        this.taskList.addEventListener('drop', this.handleDrop.bind(this));
        
        // Individual task events
        document.querySelectorAll('.task-item').forEach(item => {
            item.addEventListener('dragstart', this.handleDragStart.bind(this));
            item.addEventListener('dragend', this.handleDragEnd.bind(this));
        });
    }
    
    // Single drag start logic
    handleDragStart(e) {
        if (this.isReordering) return;
        
        this.draggedElement = e.target.closest('.task-item');
        if (!this.draggedElement) return;
        
        // Add visual feedback
        this.draggedElement.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', this.draggedElement.innerHTML);
        this.isReordering = true;
        
        // Store original position for animation
        this.originalRect = this.draggedElement.getBoundingClientRect();
        
        console.log('Drag started:', this.draggedElement.dataset.taskId);
    }
    
    // Single drag over logic - THE KEY FIX (WITH ENHANCED LOGGING)
    handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        
        if (!this.draggedElement) return;
        
        const targetElement = e.target.closest('.task-item');
        
        if (targetElement && targetElement !== this.draggedElement) {
            // SINGLE mode detection
            const newMode = this.detectDropMode(targetElement, e.clientX, e.clientY);
            this.dropTarget = targetElement;
            
            // Smart logging - only log when mode changes
            if (this.lastLoggedMode !== newMode) {
                console.log(`🎯 Mode changed: ${this.lastLoggedMode || 'none'} → ${newMode}`);
                this.lastLoggedMode = newMode;
            }
            
            // Update drag mode
            this.dragMode = newMode;
            
            // Add visual feedback for hierarchy mode
            this.updateVisualFeedback();
            
            // SINGLE placeholder positioning
            this.updatePlaceholderPosition(e);
        } else {
            this.dropTarget = null;
            this.dragMode = 'reorder';
            
            // Log mode change back to reorder
            if (this.lastLoggedMode !== 'reorder') {
                console.log(`🎯 Mode changed: ${this.lastLoggedMode || 'none'} → reorder`);
                this.lastLoggedMode = 'reorder';
            }
            
            // Remove visual feedback
            this.updateVisualFeedback();
            
            this.updatePlaceholderPosition(e);
        }
    }
    
    // Simplified drop logic - RED BOXES AND BLUE HIGHLIGHTS BOTH WORK
    handleDrop(e) {
        e.preventDefault();
        
        if (!this.draggedElement) return;
        
        console.log('🎯 Drop executed - Mode:', this.dragMode, 'Target:', this.dropTarget?.dataset.taskId);
        
        if (this.dragMode === 'hierarchy' && this.dropTarget) {
            console.log('🔗 Executing hierarchy creation...');
            this.createSubtaskRelationship();
        } else {
            console.log('🔄 Executing smart reordering (red boxes and blue highlights)...');
            this.performSmartReorder();
        }
    }
    
    // Single drag end logic (WITH ENHANCED CLEANUP)
    handleDragEnd(e) {
        if (!this.draggedElement) return;
        
        console.log('🏁 Drag ended');
        
        // Centralized cleanup
        this.removePlaceholder();
        this.draggedElement.classList.remove('dragging');
        this.draggedElement = null;
        this.dropTarget = null;
        this.dragMode = null;
        this.isReordering = false;
        
        // Reset debug state
        this.lastLoggedMode = null;
        
        // Remove visual feedback
        this.updateVisualFeedback();
    }
    
    // Simplified visual feedback for two modes only
    updateVisualFeedback() {
        // Remove any existing feedback classes
        document.querySelectorAll('.hierarchy-drop-target, .main-reorder-target').forEach(el => {
            el.classList.remove('hierarchy-drop-target', 'main-reorder-target');
        });
        
        // Add mode-specific visual feedback
        if (this.dropTarget) {
            switch (this.dragMode) {
                case 'main-reorder':
                    this.dropTarget.classList.add('main-reorder-target');
                    break;
                case 'hierarchy':
                    this.dropTarget.classList.add('hierarchy-drop-target');
                    break;
                default:
                    // No specific visual feedback for 'reorder' mode
                    break;
            }
        }
    }
    
    // Sliding animation for dropped elements
    animateDrop(element) {
        if (!this.originalRect) return;
        
        // Get the new position after DOM insertion
        const newRect = element.getBoundingClientRect();
        
        // Calculate slide distance
        const slideDistance = this.originalRect.top - newRect.top;
        
        // Only animate if moved significantly (avoid micro-animations)
        if (Math.abs(slideDistance) > 5) {
            // Set initial transform position
            element.style.transform = `translateY(${slideDistance}px)`;
            element.style.transition = 'none';
            
            // Force DOM update
            element.offsetHeight; // Trigger reflow
            
            // Apply transition and animate to final position
            element.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
            element.style.transform = 'translateY(0)';
            
            // Clean up after animation
            setTimeout(() => {
                element.style.transition = '';
                element.style.transform = '';
            }, 300);
        }
        
        // Reset original rect for next drag
        this.originalRect = null;
    }
    
    // Placeholder management - SINGLE SOURCE
    createPlaceholder() {
        // Remove ANY existing placeholders first (defensive programming)
        this.removePlaceholder();
        
        // Create EXACTLY ONE placeholder
        this.placeholder = document.createElement('li');
        this.placeholder.className = 'task-placeholder';
        this.placeholder.innerHTML = '<div class="placeholder-text">Drop task here</div>';
    }
    
    removePlaceholder() {
        // Remove ALL placeholders (defensive cleanup)
        document.querySelectorAll('.task-placeholder').forEach(p => p.remove());
        this.placeholder = null;
    }
    
    // Mode detection - SINGLE DECISION POINT (RIGHT HALF)
    // Enhanced drag mode detection - EDGE DETECTION FOR SUBTASK CREATION
    detectDropMode(targetElement, x, y) {
        const rect = targetElement.getBoundingClientRect();
        const edgeThreshold = rect.width * 0.425; // 42.5% from edges (85% total)
        
        // Get task hierarchy information
        const isDraggedSubtask = this.draggedElement?.classList.contains('subtask');
        const isDraggedParent = this.draggedElement?.classList.contains('parent');
        const isDraggedMain = !isDraggedSubtask && !isDraggedParent;
        const isTargetSubtask = targetElement.classList.contains('subtask');
        const isTargetParent = targetElement.classList.contains('parent');
        const isTargetMain = !isTargetSubtask && !isTargetParent;
        
        // PRIORITY 1: Hierarchy mode (creating subtasks) - EDGE DETECTION
        // Create subtasks when dragging near edges (left or right 42.5% each = 85% total)
        // BUT PREVENT PARENT TASKS FROM BECOMING SUBTASKS
        const distanceFromLeft = x - rect.left;
        const distanceFromRight = rect.right - x;
        
        if ((distanceFromLeft < edgeThreshold || distanceFromRight < edgeThreshold) && 
            this.canBecomeSubtask(targetElement) && !isDraggedParent) {
            return 'hierarchy';
        }
        
        // PRIORITY 2: Main reordering - CENTER AREA (only 15%)
        // Allow: main-main, subtask-subtask, parent-main
        // Block: main-subtask, parent-subtask
        if (isDraggedMain && isTargetMain) {
            // Main task over main task - allow reordering
            return 'main-reorder';
        } else if (isDraggedSubtask && isTargetSubtask) {
            // Subtask over subtask - allow reordering
            return 'main-reorder';
        } else if (isDraggedParent && isTargetMain) {
            // Parent over main - allow reordering
            return 'main-reorder';
        } else if (isDraggedSubtask && isTargetMain) {
            // Subtask over main - allow reordering (extraction)
            return 'main-reorder';
        }
        // All other combinations (main-subtask, parent-subtask) get no visual feedback
        
        // Default to no mode for incompatible combinations
        return 'reorder';
    }
    
    // Get the parent task ID for a subtask
    getParentTaskId(subtaskElement) {
        // Find the parent task by traversing up the DOM
        const parentContainer = subtaskElement.closest('.task-children');
        if (parentContainer) {
            const parentTask = parentContainer.previousElementSibling?.closest('.task-item');
            return parentTask?.dataset.taskId;
        }
        return null;
    }
    
    // Check if a task can become a subtask - PREVENT PARENT TASKS
    canBecomeSubtask(targetElement) {
        const targetId = targetElement.dataset.taskId;
        const draggedId = this.draggedElement.dataset.taskId;
        const isDraggedParent = this.draggedElement?.classList.contains('parent');
        
        // Prevent self-reference
        if (targetId === draggedId) {
            console.log('🚫 Cannot make task a subtask of itself');
            return false;
        }
        
        // PREVENT PARENT TASKS FROM BECOMING SUBTASKS (max 2 layers)
        if (isDraggedParent) {
            console.log('🚫 Parent tasks cannot become subtasks (max 2 layers)');
            return false;
        }
        
        // Prevent circular references
        const isDescendant = this.isDescendant(targetId, draggedId);
        if (isDescendant) {
            console.log('🚫 Cannot make task a subtask of its own descendant');
            return false;
        }
        
        // Main tasks can become subtasks, but other subtasks can't
        const canBecomeSubtask = !targetElement.classList.contains('subtask');
        
        if (canBecomeSubtask) {
            console.log('✅ Task can become subtask');
        } else {
            console.log('🚫 Target is already a subtask');
        }
        
        return canBecomeSubtask;
    }
    
    // Check if potentialDescendant is actually a descendant of potentialAncestor
    isDescendant(potentialDescendant, potentialAncestor) {
        let current = potentialDescendant;
        while (current) {
            const parentId = document.querySelector(`[data-task-id="${current}"]`)?.dataset.parentId;
            if (parentId === potentialAncestor) {
                return true;
            }
            current = parentId;
        }
        return false;
    }
    
    // Update placeholder position based on current drag state
    // Simplified placeholder positioning - MAIN TASK LIST ONLY
    updatePlaceholderPosition(e) {
        // Ensure placeholder exists
        if (!this.placeholder) {
            this.createPlaceholder();
        }
        
        // Always use main task list - simple and reliable
        const container = this.taskList;
        
        // Defensive check: ensure container exists
        if (!container || !container.appendChild) {
            console.warn('Invalid container for placeholder positioning');
            return;
        }
        
        const afterElement = this.getDragAfterElement(container, e.clientY);
        
        try {
            if (afterElement == null) {
                if (container.lastElementChild !== this.placeholder) {
                    container.appendChild(this.placeholder);
                }
            } else {
                // Defensive check: ensure afterElement is in the container
                if (container.contains(afterElement)) {
                    if (afterElement.previousElementSibling !== this.placeholder) {
                        container.insertBefore(this.placeholder, afterElement);
                    }
                }
            }
        } catch (error) {
            console.warn('Placeholder positioning error:', error.message);
            // Fallback: append to end of container
            try {
                container.appendChild(this.placeholder);
            } catch (fallbackError) {
                console.warn('Fallback positioning failed:', fallbackError.message);
            }
        }
    }
    
    // Get element after which to insert placeholder
    getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.task-item:not(.dragging)')];
        
        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }
    
    // Execute hierarchy creation (WITH COMPREHENSIVE LOGGING)
    // Create subtask relationship using the reliable update_hierarchy endpoint
    createSubtaskRelationship() {
        console.log('🔗 Creating subtask relationship...');
        
        const draggedId = this.draggedElement.dataset.taskId;
        const targetId = this.dropTarget.dataset.taskId;
        
        console.log(`📝 Making task ${draggedId} a subtask of ${targetId}`);
        
        // Show loading state
        document.querySelectorAll('.task-item').forEach(el => el.style.opacity = '0.7');
        
        // Use our reliable update_hierarchy endpoint
        this.updateTaskHierarchy(draggedId, targetId, targetId);
        
        console.log('✅ Subtask relationship creation initiated');
    }
    
    // Smart reordering that handles hierarchy updates for both red boxes and blue highlights
    performSmartReorder() {
        const placeholder = document.querySelector('.task-placeholder');
        if (!placeholder || !placeholder.parentNode) return;
        
        console.log('🔄 Performing smart reordering...');
        
        const draggedId = this.draggedElement.dataset.taskId;
        const isDraggedSubtask = this.draggedElement.classList.contains('subtask');
        const isDraggedParent = this.draggedElement.classList.contains('parent');
        
        // Determine where we're dropping
        const dropTarget = this.dropTarget;
        const isTargetSubtask = dropTarget?.classList.contains('subtask');
        const isTargetParent = dropTarget?.classList.contains('parent');
        
        // Determine the container and context for hierarchy decisions
        const container = placeholder.parentNode;
        const isInMainList = container.classList.contains('task-list');
        const isInSubtaskList = container.classList.contains('task-children');
        
        console.log(`📊 Moving ${isDraggedSubtask ? 'subtask' : isDraggedParent ? 'parent' : 'main'} ${draggedId} to ${isInMainList ? 'main' : 'subtask'} level`);
        
        // Move the element in the DOM first
        placeholder.parentNode.insertBefore(this.draggedElement, placeholder);
        placeholder.remove();
        
        // Determine new hierarchy based on container and target
        let newParentId = null;
        
        if (isDraggedSubtask && isInMainList) {
            // Subtask moving to main list -> extract
            console.log('📤 Extracting subtask to main level');
            newParentId = null;
            this.draggedElement.classList.remove('subtask');
        } else if (!isDraggedSubtask && isInSubtaskList) {
            // Main task moving to subtask list -> make subtask
            console.log('🔗 Converting main task to subtask');
            // Find the parent task for this subtask container
            const parentTask = container.closest('.task-item');
            newParentId = parentTask?.dataset.taskId;
            this.draggedElement.classList.add('subtask');
        } else if (isDraggedSubtask && isInSubtaskList) {
            // Subtask moving within subtask lists
            const draggedParentId = this.getParentTaskId(this.draggedElement);
            const containerParentTask = container.closest('.task-item');
            const containerParentId = containerParentTask?.dataset.taskId;
            
            if (draggedParentId !== containerParentId) {
                console.log('🔄 Moving subtask to new parent');
                newParentId = containerParentId;
            } else {
                console.log('↔️ Reordering within same parent');
                newParentId = draggedParentId; // Keep same parent
            }
        }
        // Main-to-main and parent-to-main keep parent_id = null
        
        // Find the task we're dropping after for position
        const positionAfterId = this.findPositionAfterId(this.draggedElement);
        
        // Update hierarchy in backend
        this.updateTaskHierarchy(draggedId, newParentId, positionAfterId);
        
        // Add sliding animation
        this.animateDrop(this.draggedElement);
        
        console.log('✅ Smart reordering completed');
    }
    
    // Helper to find the task we're dropping after
    findPositionAfterId(droppedElement) {
        // Get the previous sibling task item
        const prevSibling = droppedElement.previousElementSibling;
        if (prevSibling && prevSibling.classList.contains('task-item')) {
            return prevSibling.dataset.taskId;
        }
        return null;
    }
    
    // Update task hierarchy in backend
    updateTaskHierarchy(taskId, newParentId, positionAfterId = null) {
        const listId = this.taskList.dataset.listId;
        
        fetch('/task/update_hierarchy', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({
                task_id: taskId,
                parent_id: newParentId,
                position_after_id: positionAfterId,
                list_id: listId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                console.error('Failed to update task hierarchy:', data.error);
                this.showError('Failed to update task hierarchy');
                setTimeout(() => location.reload(), 2000);
            } else {
                console.log('✅ Task hierarchy updated successfully');
                // Reload to reflect changes
                setTimeout(() => location.reload(), 500);
            }
        })
        .catch(error => {
            console.error('Error updating task hierarchy:', error);
            this.showError('Error updating task hierarchy');
            setTimeout(() => location.reload(), 2000);
        });
    }
    
    // Utility: Get CSRF token
    getCsrfToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }
    
    // Utility: Show error message
    showError(message) {
        const flashDiv = document.createElement('div');
        flashDiv.className = 'flash flash-error';
        flashDiv.textContent = message;
        flashDiv.style.position = 'fixed';
        flashDiv.style.top = '20px';
        flashDiv.style.right = '20px';
        flashDiv.style.zIndex = '9999';
        
        document.body.appendChild(flashDiv);
        setTimeout(() => flashDiv.remove(), 3000);
    }
}

// Initialize the unified controller when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if no other drag system is active
    if (typeof TaskReordering === 'undefined' && typeof HierarchicalTaskReordering === 'undefined') {
        new UnifiedDragController();
    } else {
        console.warn('Other drag systems detected. Unified controller disabled to prevent conflicts.');
    }
});
