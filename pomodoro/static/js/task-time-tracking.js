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
            // Get timer status
            const timerResponse = await fetch('/timer/status');
            const timerData = await timerResponse.json();
            
            // Get current task
            const taskResponse = await fetch('/timer/current-task');
            const taskData = await taskResponse.json();
            
            if (timerData.success && taskData.success) {
                // Log timer status
                const phase = timerData.current_phase || 'unknown';
                const state = timerData.timer_state || 'unknown';
                console.log(`⏰ Timer status: ${state} (${phase})`);
                
                // Check if selected task changed
                const serverSelectedTaskId = taskData.selected_task?.id;
                if (serverSelectedTaskId !== this.selectedTaskId) {
                    console.log(`🔄 Task selection changed from ${this.selectedTaskId} to ${serverSelectedTaskId}`);
                    this.selectedTaskId = serverSelectedTaskId === null ? null : serverSelectedTaskId;
                    this.updateUI();
                }
                
                // Log time tracking info if task is selected and timer is in work session
                if (this.selectedTaskId && taskData.selected_task && state === 'session') {
                    console.log(`⏱️ Task ${this.selectedTaskId} being tracked during work session`);
                    
                    // Calculate live elapsed time including current session
                    const baseTime = taskData.selected_task.total_time_seconds || 0;
                    let currentTime = 0;
                    
                    if (timerData.timer_started_at) {
                        try {
                            // Try to parse as timestamp (number or ISO string)
                            const startedAt = new Date(timerData.timer_started_at);
                            if (!isNaN(startedAt.getTime())) {
                                currentTime = Math.floor((Date.now() / 1000) - (startedAt.getTime() / 1000));
                            }
                        } catch (error) {
                            console.warn('⚠️ Could not parse timer_started_at:', timerData.timer_started_at);
                            currentTime = 0;
                        }
                    }
                    
                    const liveTotalTime = baseTime + Math.max(0, currentTime);
                    
                    console.log(`📊 Base completed time: ${baseTime}s`);
                    console.log(`⏰ Current session elapsed: ${currentTime}s`);
                    console.log(`📊 Live total time: ${liveTotalTime}s`);
                    
                    // Update task time display in UI
                    this.updateTaskTimeDisplay(liveTotalTime);
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

    updateTaskTimeDisplay(liveTotalSeconds) {
        // Update time display for selected task
        if (this.selectedTaskId) {
            const taskElement = document.querySelector(`[data-task-id="${this.selectedTaskId}"] .time-spent`);
            if (taskElement) {
                // Format the live total time
                let formattedTime;
                if (liveTotalSeconds < 60) {
                    formattedTime = '0m';
                } else if (liveTotalSeconds < 3600) {
                    const minutes = Math.floor(liveTotalSeconds / 60);
                    formattedTime = `${minutes}m`;
                } else {
                    const hours = Math.floor(liveTotalSeconds / 3600);
                    const minutes = Math.floor((liveTotalSeconds % 3600) / 60);
                    formattedTime = `${hours}h ${minutes}m`;
                }
                
                taskElement.textContent = formattedTime;
                taskElement.title = `Live total time: ${liveTotalSeconds}s`;
            }
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.taskTracker = new TaskTimeTracker();
    console.log('Task time tracking initialized');
});
