// Collapsible Tasks Functionality
class CollapsibleTasks {
    constructor() {
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }
    }
    
    initialize() {
        this.setupCollapseButtons();
    }
    
    setupCollapseButtons() {
        // Add click listeners to collapse buttons using event delegation
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('collapse-btn')) {
                e.preventDefault();
                e.stopPropagation();
                this.toggleCollapse(e.target);
                return;
            }
            
            // Also check if click is on a collapse button by role or other attributes
            if (e.target.getAttribute('aria-label') && e.target.getAttribute('aria-label').includes('subtasks')) {
                e.preventDefault();
                e.stopPropagation();
                this.toggleCollapse(e.target);
                return;
            }
        });
        
        // Direct button binding as backup
        setTimeout(() => {
            const buttons = document.querySelectorAll('.collapse-btn');
            buttons.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.toggleCollapse(btn);
                });
            });
        }, 100);
    }
    
    toggleCollapse(button) {
        const taskItem = button.closest('.task-item');
        
        if (!taskItem || !taskItem.classList.contains('parent')) {
            return;
        }
        
        const isCollapsed = taskItem.classList.contains('collapsed');
        
        if (isCollapsed) {
            // Expand
            taskItem.classList.remove('collapsed');
            button.textContent = '▼';
            button.setAttribute('aria-label', 'Collapse subtasks');
        } else {
            // Collapse
            taskItem.classList.add('collapsed');
            button.textContent = '▶';
            button.setAttribute('aria-label', 'Expand subtasks');
        }
        
        // Optional: Save state to localStorage
        this.saveCollapseState(taskItem.dataset.taskId, !isCollapsed);
    }
    
    saveCollapseState(taskId, isCollapsed) {
        try {
            const collapsedStates = JSON.parse(localStorage.getItem('collapsedTasks') || '{}');
            if (isCollapsed) {
                collapsedStates[taskId] = true;
            } else {
                delete collapsedStates[taskId];
            }
            localStorage.setItem('collapsedTasks', JSON.stringify(collapsedStates));
        } catch (e) {
            console.warn('Could not save collapse state:', e);
        }
    }
    
    restoreCollapseStates() {
        try {
            const collapsedStates = JSON.parse(localStorage.getItem('collapsedTasks') || '{}');
            Object.keys(collapsedStates).forEach(taskId => {
                const taskItem = document.querySelector(`[data-task-id="${taskId}"]`);
                if (taskItem && taskItem.classList.contains('parent')) {
                    taskItem.classList.add('collapsed');
                    const collapseBtn = taskItem.querySelector('.collapse-btn');
                    if (collapseBtn) {
                        collapseBtn.textContent = '▶';
                        collapseBtn.setAttribute('aria-label', 'Expand subtasks');
                    }
                }
            });
        } catch (e) {
            console.warn('Could not restore collapse states:', e);
        }
    }
}

// Initialize the collapsible tasks functionality
new CollapsibleTasks();
