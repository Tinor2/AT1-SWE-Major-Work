/**
 * Task Time Tracking Frontend
 * Handles task selection and time tracking UI integration
 */

class TaskTimeTracker {
    constructor() {
        this.selectedTaskId = null;
        this.initEventListeners();
        this.loadCurrentSession();
    }

    initEventListeners() {
        // Task selection checkboxes
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('task-selector')) {
                this.handleTaskSelection(e.target);
            }
        });

        // Timer state changes
        this.observeTimerState();
    }

    handleTaskSelection(checkbox) {
        const taskId = parseInt(checkbox.dataset.taskId);
        const taskItem = checkbox.closest('.task-item');
        
        // Only allow selection of parent tasks (not subtasks)
        if (taskItem.classList.contains('subtask')) {
            checkbox.checked = false;
            console.log('Subtasks cannot be selected for time tracking');
            return;
        }
        
        // Uncheck all other task selectors
        document.querySelectorAll('.task-selector').forEach(cb => {
            if (cb !== checkbox) cb.checked = false;
        });

        if (checkbox.checked) {
            this.selectTask(taskId);
        } else {
            this.deselectTask();
        }
    }

    async selectTask(taskId) {
        try {
            console.log(`🎯 SELECTING task ${taskId} for time tracking`);
            const response = await fetch('/timer/select-task', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({task_id: taskId})
            });
            
            if (response.ok) {
                this.selectedTaskId = taskId;
                this.updateUI();
                console.log(`✅ Task ${taskId} selected successfully`);
            } else {
                console.error('❌ Failed to select task');
                // Revert checkbox on failure
                const checkbox = document.querySelector(`[data-task-id="${taskId}"].task-selector`);
                if (checkbox) checkbox.checked = false;
            }
        } catch (error) {
            console.error('❌ Error selecting task:', error);
            // Revert checkbox on error
            const checkbox = document.querySelector(`[data-task-id="${taskId}"].task-selector`);
            if (checkbox) checkbox.checked = false;
        }
    }

    async deselectTask() {
        try {
            console.log('🔴 DESELECTING task');
            await fetch('/timer/deselect-task', {method: 'POST'});
            this.selectedTaskId = null;
            this.updateUI();
            console.log('✅ Task deselected successfully');
        } catch (error) {
            console.error('❌ Error deselecting task:', error);
        }
    }

    observeTimerState() {
        // Poll timer status every 5 seconds
        setInterval(() => this.updateTimerStatus(), 5000);
        
        // Listen for timer control button clicks
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-timer-action]')) {
                // Update timer status after button clicks
                setTimeout(() => this.updateTimerStatus(), 500);
            }
        });
    }

    async updateTimerStatus() {
        try {
            const response = await fetch('/timer/status');
            const data = await response.json();
            
            if (data.success) {
                // Log timer status
                const phase = data.current_phase || 'unknown';
                const state = data.timer_state || 'unknown';
                console.log(`⏰ Timer status: ${state} (${phase})`);
                
                // Check if selected task changed
                const serverSelectedTaskId = data.selected_task?.id;
                if (serverSelectedTaskId !== this.selectedTaskId) {
                    console.log(`🔄 Task selection changed from ${this.selectedTaskId} to ${serverSelectedTaskId}`);
                    this.selectedTaskId = serverSelectedTaskId === null ? null : serverSelectedTaskId;
                    this.updateUI();
                }
                
                // Log time tracking info if task is selected
                if (this.selectedTaskId && data.selected_task) {
                    const startTime = data.selected_task.started_at;
                    if (startTime) {
                        const elapsed = Math.floor(Date.now() / 1000 - startTime);
                        console.log(`⏱️ Task ${this.selectedTaskId} tracking: ${elapsed}s elapsed`);
                    }
                }
            }
        } catch (error) {
            console.error('❌ Failed to update timer status:', error);
        }
    }

    updateUI() {
        // Update task selection checkboxes
        document.querySelectorAll('.task-selector').forEach(cb => {
            const taskId = parseInt(cb.dataset.taskId);
            const shouldBeChecked = taskId === this.selectedTaskId;
            
            // Only update if state actually changed to prevent flickering
            if (cb.checked !== shouldBeChecked) {
                cb.checked = shouldBeChecked;
            }
        });

        // Update task item highlighting
        document.querySelectorAll('.task-item').forEach(item => {
            const taskId = parseInt(item.dataset.taskId);
            const shouldBeSelected = taskId === this.selectedTaskId;
            const currentlySelected = item.hasAttribute('data-selected');
            
            // Only update if state actually changed to prevent flickering
            if (shouldBeSelected !== currentlySelected) {
                if (shouldBeSelected) {
                    item.setAttribute('data-selected', 'true');
                } else {
                    item.removeAttribute('data-selected');
                }
            }
        });
    }

    async loadCurrentSession() {
        try {
            await this.updateTimerStatus();
            this.updateUI();
        } catch (error) {
            console.error('Failed to load current session:', error);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.taskTracker = new TaskTimeTracker();
    console.log('Task time tracking initialized');
});
