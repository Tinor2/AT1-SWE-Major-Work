// Pomodoro Timer JavaScript Implementation
class PomodoroTimer {
    constructor() {
        // DOM Elements
        this.container = document.getElementById('timerContainer');
        this.display = document.getElementById('timerDisplay');
        this.phaseDisplay = document.getElementById('timerPhase');
        this.pausedStatus = document.getElementById('timerPausedStatus');
        this.progressBar = document.getElementById('progressBar');
        this.startPauseBtn = document.getElementById('startPauseBtn');
        this.resetBtn = document.getElementById('resetBtn');
        this.skipBtn = document.getElementById('skipBtn');
        this.resetSetsBtn = document.getElementById('resetSetsBtn');
        this.sessionCounter = document.getElementById('sessionCounter');
        
        // Timer State
        this.state = {
            timer_state: 'idle',
            current_phase: null,  // ADD THIS
            timer_remaining: 25 * 60,  // Show session time when idle
            sessions_completed: 0,
            pomo_session: 25,
            pomo_short_break: 5,
            pomo_long_break: 15,
            timer_started_at: null,
            timer_last_updated: null
        };
        
        // Timer Management
        this.countdownInterval = null;
        this.syncInterval = null;
        this.isRunning = false;
        this.lastSyncTime = 0;
        this.syncRetryCount = 0;
        this.isBackground = false;
        this.lastKnownTime = Date.now();
        this.sleepDetectionInterval = null;
        this.transitionsEnabled = false; // Track if transitions are enabled
        
        // Phase display names
        this.phaseNames = {
            'idle': 'Focus Session',
            'session': 'Focus Session',
            'short_break': 'Short Break',
            'long_break': 'Long Break',
            'paused': 'Paused'
        };
        
        this.init();
    }
    
    async init() {
        try {
            this.bindEvents();
            await this.loadState();
            this.updateDisplay();
            
            // Start sleep detection
            this.sleepDetectionInterval = setInterval(() => {
                this.checkForSleep();
            }, 60000); // Check every minute
        } catch (error) {
            console.error('Timer initialization failed:', error);
        }
    }
    
    bindEvents() {
        // Timer control events
        if (this.startPauseBtn) {
            this.startPauseBtn.addEventListener('click', () => this.toggleTimer());
        }
        if (this.resetBtn) {
            this.resetBtn.addEventListener('click', () => this.reset());
        }
        if (this.skipBtn) {
            this.skipBtn.addEventListener('click', () => this.skip());
        }
        if (this.resetSetsBtn) {
            this.resetSetsBtn.addEventListener('click', () => this.resetSets());
        }
        
        // Visibility change handling
        document.addEventListener('visibilitychange', () => this.handleVisibilityChange());
        
        // Page unload cleanup
        window.addEventListener('beforeunload', () => this.cleanup());
    }
    
    async loadState() {
        try {
            const response = await fetch('/timer/status', {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            if (data.success) {
                this.updateState(data);
                this.updateDisplay();
                
                // Start countdown if timer is running
                if (data.timer_state === 'session' || data.timer_state === 'short_break' || data.timer_state === 'long_break') {
                    this.startCountdown();
                    this.startPeriodicSync();
                }
            } else {
                console.error('Server error loading timer state:', data.error);
            }
        } catch (error) {
            console.error('Failed to load timer state:', error);
            // Set default state
            this.state.timer_state = 'idle';
            this.state.timer_remaining = 0;
            this.updateDisplay();
        }
    }
    
    async toggleTimer() {
        if (this.state.timer_state === 'idle' || this.state.timer_state === 'paused') {
            await this.start();
        } else if (this.state.timer_state === 'session' || this.state.timer_state === 'short_break' || this.state.timer_state === 'long_break') {
            await this.pause();
        }
    }
    
    async start() {
        try {
            const formData = new FormData();
            formData.append('csrf_token', this.getCsrfToken());
            
            const response = await fetch('/timer/start', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            if (data.success) {
                this.updateState(data);
                this.startCountdown();
                this.startPeriodicSync();
                this.updateDisplay();
                console.log('Timer started successfully');
            } else {
                console.error('Server error starting timer:', data.error);
                this.showError('Failed to start timer');
            }
        } catch (error) {
            console.error('Failed to start timer:', error);
            this.showError('Network error starting timer');
        }
    }
    
    async pause() {
        try {
            const formData = new FormData();
            formData.append('csrf_token', this.getCsrfToken());
            
            const response = await fetch('/timer/pause', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            if (data.success) {
                this.updateState(data);
                this.stopCountdown();
                this.stopPeriodicSync();
                this.updateDisplay();
                console.log('Timer paused successfully');
            } else {
                console.error('Server error pausing timer:', data.error);
                this.showError('Failed to pause timer');
            }
        } catch (error) {
            console.error('Failed to pause timer:', error);
            this.showError('Network error pausing timer');
        }
    }
    
    async reset() {
        try {
            const formData = new FormData();
            formData.append('csrf_token', this.getCsrfToken());
            
            const response = await fetch('/timer/reset', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            if (data.success) {
                this.updateState(data);
                this.stopCountdown();
                this.stopPeriodicSync();
                this.updateDisplay();
                console.log('Timer reset successfully');
            } else {
                console.error('Server error resetting timer:', data.error);
                this.showError('Failed to reset timer');
            }
        } catch (error) {
            console.error('Failed to reset timer:', error);
            this.showError('Network error resetting timer');
        }
    }
    
    async skip() {
        try {
            const formData = new FormData();
            formData.append('csrf_token', this.getCsrfToken());
            
            const response = await fetch('/timer/skip', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            if (data.success) {
                this.updateState(data);
                this.updateDisplay();
                
                // Start countdown if new state is a running state
                if (data.timer_state === 'session' || data.timer_state === 'short_break' || data.timer_state === 'long_break') {
                    this.startCountdown();
                    this.startPeriodicSync();
                } else {
                    this.stopCountdown();
                    this.stopPeriodicSync();
                }
                
                console.log('Timer skipped successfully');
            } else {
                console.error('Skip failed:', data.error);
            }
        } catch (error) {
            console.error('Skip error:', error);
        }
    }
    
    async resetSets() {
        // Show confirmation modal
        let modal = document.getElementById('resetSetsModal');
        
        // If modal not found, try to wait a bit and find it again
        if (!modal) {
            // Wait for DOM to be ready
            await new Promise(resolve => setTimeout(resolve, 100));
            modal = document.getElementById('resetSetsModal');
        }
        
        if (!modal) {
            console.error('Reset sets modal not found. Make sure you are logged in and on the home page.');
            // Fallback: show browser confirm dialog
            const confirmed = confirm('Are you sure you want to reset your sets?\n\nThis will:\n• Reset set counter to 1\n• Return to first focus session\n• Reset timer to 25:00\n\nYour current progress will be lost.');
            if (!confirmed) return;
            
            // Direct reset without modal
            await this.performResetSets();
            return;
        }
        
        // Show modal
        modal.classList.add('show');
        
        // Handle modal interactions
        const confirmBtn = modal.querySelector('.modal-confirm');
        const cancelBtn = modal.querySelector('.modal-cancel');
        const closeBtn = modal.querySelector('.modal-close');
        
        const closeModal = () => {
            modal.classList.remove('show');
        };
        
        const confirmReset = async () => {
            closeModal();
            await this.performResetSets();
        };
        
        // Add event listeners
        confirmBtn.onclick = confirmReset;
        cancelBtn.onclick = closeModal;
        closeBtn.onclick = closeModal;
        
        // Close on backdrop click
        modal.querySelector('.modal-backdrop').onclick = closeModal;
        
        // Close on escape key
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                closeModal();
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);
    }
    
    async performResetSets() {
        try {
            const formData = new FormData();
            formData.append('csrf_token', this.getCsrfToken());
            
            const response = await fetch('/timer/reset-sets', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            if (data.success) {
                this.updateState(data);
                this.updateDisplay();
                
                // Stop any running countdown since we're resetting to paused state
                this.stopCountdown();
                this.stopPeriodicSync();
                
                // Visual feedback - briefly highlight the session counter
                if (this.sessionCounter) {
                    this.sessionCounter.style.background = 'rgba(var(--success-color-rgb), 0.2)';
                    this.sessionCounter.style.transform = 'scale(1.05)';
                    setTimeout(() => {
                        this.sessionCounter.style.background = '';
                        this.sessionCounter.style.transform = '';
                    }, 300);
                }
            } else {
                console.error('Reset sets failed:', data.error);
            }
        } catch (error) {
            console.error('Reset sets error:', error);
        }
    }
    
    startCountdown() {
        this.stopCountdown();
        this.isRunning = true;
        
        this.countdownInterval = setInterval(() => {
            if (this.state.timer_remaining > 0) {
                this.state.timer_remaining--;
                this.updateDisplay();
            } else {
                this.handleCompletion();
            }
        }, 1000);
    }
    
    stopCountdown() {
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
            this.countdownInterval = null;
        }
        this.isRunning = false;
    }
    
    startPeriodicSync() {
        this.stopPeriodicSync();
        this.syncInterval = setInterval(() => {
            this.syncWithServer();
        }, 30000); // 30 seconds
    }
    
    stopPeriodicSync() {
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
            this.syncInterval = null;
        }
    }
    
    async syncWithServer() {
        try {
            const now = Date.now();
            // Rate limit syncs to avoid overwhelming the server
            if (now - this.lastSyncTime < 5000 && !this.isBackground) {
                return;
            }
            
            const response = await fetch('/timer/status', {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Check for conflicts
                    if (this.detectConflict(data)) {
                        await this.resolveConflict(data);
                    } else {
                        this.updateState(data);
                        this.updateDisplay();
                    }
                }
            }
        } catch (error) {
            this.handleSyncError(error);
        }
    }
    
    detectConflict(serverData) {
        // Detect if server state is newer than local state
        const serverUpdateTime = new Date(serverData.timer_last_updated).getTime();
        return serverUpdateTime > this.lastSyncTime;
    }
    
    async resolveConflict(serverData) {
        console.log('Timer conflict detected, resolving with server state');
        
        // Always prefer server state
        const wasRunning = this.isRunning;
        this.updateState(serverData);
        this.updateDisplay();
        
        // If timer was running locally, restart with server time
        if (wasRunning) {
            this.stopCountdown();
            if (serverData.timer_state === 'session' || 
                serverData.timer_state === 'short_break' || 
                serverData.timer_state === 'long_break') {
                this.startCountdown();
            }
        }
    }
    
    handleSyncError(error) {
        console.error('Sync error:', error);
        
        if (!this.syncRetryCount) {
            this.syncRetryCount = 0;
        }
        
        // Exponential backoff: 1s, 2s, 4s, 8s, 16s max
        const delay = Math.min(1000 * Math.pow(2, this.syncRetryCount), 16000);
        
        setTimeout(() => {
            this.syncRetryCount++;
            this.syncWithServer();
        }, delay);
    }
    
    handleVisibilityChange() {
        if (document.hidden) {
            // Tab going to background
            this.isBackground = true;
            this.stopCountdown(); // Stop local countdown to save resources
            this.syncWithServer(); // Final sync before backgrounding
            this.stopPeriodicSync(); // Stop periodic sync in background
        } else {
            // Tab coming to foreground
            this.isBackground = false;
            this.syncWithServer(); // Immediate sync on visibility
            if (this.state.timer_state !== 'idle' && this.state.timer_state !== 'paused') {
                this.startCountdown(); // Resume countdown if needed
                this.startPeriodicSync(); // Resume periodic sync
            }
        }
    }
    
    handleCompletion() {
        this.stopCountdown();
        this.showCompletionNotification();
        
        // Auto-advance to next phase after a short delay
        setTimeout(() => {
            this.skip();
        }, 1000);
    }
    
    updateState(data) {
        // Update local state from server response
        Object.assign(this.state, data);
        this.lastSyncTime = data.timer_last_updated ? new Date(data.timer_last_updated).getTime() : Date.now();
        this.syncRetryCount = 0; // Reset retry count
    }
    
    checkForSleep() {
        const now = Date.now();
        const timeDiff = now - this.lastKnownTime;
        
        // If more than 2 minutes have passed, assume browser was asleep
        if (timeDiff > 120000) {
            console.log('Browser sleep detected, forcing sync');
            this.syncWithServer();
        }
        
        this.lastKnownTime = now;
    }
    
    updateDisplay() {
        if (!this.display) return;
        
        // Update timer display
        let displayTime = this.state.timer_remaining;
        
        // If idle, show the session time instead of 0
        if (this.state.timer_state === 'idle') {
            displayTime = this.state.pomo_session * 60;
        }
        
        const minutes = Math.floor(displayTime / 60);
        const seconds = displayTime % 60;
        this.display.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        // Update phase display - use current_phase when paused, timer_state when running
        if (this.phaseDisplay) {
            let phaseText;
            if (this.state.timer_state === 'paused') {
                // When paused, use stored current_phase
                phaseText = this.phaseNames[this.state.current_phase] || 'Focus Session';
            } else {
                // When running or idle, use timer_state
                phaseText = this.phaseNames[this.state.timer_state] || 'Focus Session';
            }
            this.phaseDisplay.textContent = phaseText;
        }
        
        // Update paused status visibility
        if (this.pausedStatus) {
            if (this.state.timer_state === 'paused') {
                this.pausedStatus.style.display = 'block';
            } else {
                this.pausedStatus.style.display = 'none';
            }
        }
        
        // Update progress bar
        this.updateProgressBar();
        
        // Update session counter
        if (this.sessionCounter) {
            const currentInSet = this.state.sessions_completed % 4;
            const totalSets = Math.floor(this.state.sessions_completed / 4);
            
            if (this.state.timer_state === 'idle') {
                this.sessionCounter.textContent = `Ready to start • Set ${totalSets + 1}`;
            } else if (currentInSet === 0 && this.state.timer_state === 'session') {
                this.sessionCounter.textContent = `Session 1 of 4 • Set ${totalSets + 1}`;
            } else if (currentInSet === 1 && (this.state.timer_state === 'short_break' || this.state.timer_state === 'long_break')) {
                this.sessionCounter.textContent = `Break after Session 1 • Set ${totalSets + 1}`;
            } else if (currentInSet === 1 && this.state.timer_state === 'session') {
                this.sessionCounter.textContent = `Session 2 of 4 • Set ${totalSets + 1}`;
            } else if (currentInSet === 2 && (this.state.timer_state === 'short_break' || this.state.timer_state === 'long_break')) {
                this.sessionCounter.textContent = `Break after Session 2 • Set ${totalSets + 1}`;
            } else if (currentInSet === 2 && this.state.timer_state === 'session') {
                this.sessionCounter.textContent = `Session 3 of 4 • Set ${totalSets + 1}`;
            } else if (currentInSet === 3 && (this.state.timer_state === 'short_break' || this.state.timer_state === 'long_break')) {
                this.sessionCounter.textContent = `Break after Session 3 • Set ${totalSets + 1}`;
            } else if (currentInSet === 3 && this.state.timer_state === 'session') {
                this.sessionCounter.textContent = `Session 4 of 4 • Set ${totalSets + 1}`;
            } else {
                // Fallback for paused states
                this.sessionCounter.textContent = `${currentInSet + 1}/4 sessions • Set ${totalSets + 1}`;
            }
        }
        
        // Update button states
        this.updateButtonStates();
        
        // Update container classes for styling
        this.updateContainerClasses();
    }
    
    updateContainerClasses() {
        if (!this.container) return;
        
        // Remove all phase classes
        this.container.classList.remove('session', 'short-break', 'long-break', 'paused', 'idle');
        
        // Add appropriate class based on state
        if (this.state.timer_state === 'paused') {
            this.container.classList.add('paused');
            // Also add the underlying phase class for styling
            if (this.state.current_phase) {
                this.container.classList.add(this.state.current_phase.replace('_', '-'));
            }
        } else {
            this.container.classList.add(this.state.timer_state.replace('_', '-'));
        }
    }
    
    updateProgressBar() {
        if (!this.progressBar) return;
        
        let totalTime, elapsed;
        
        // Use current_phase when paused, timer_state when running
        const phase = this.state.timer_state === 'paused' ? this.state.current_phase : this.state.timer_state;
        
        switch (phase) {
            case 'session':
                totalTime = this.state.pomo_session * 60;
                break;
            case 'short_break':
                totalTime = this.state.pomo_short_break * 60;
                break;
            case 'long_break':
                totalTime = this.state.pomo_long_break * 60;
                break;
            case 'idle':
                totalTime = this.state.pomo_session * 60;
                elapsed = 0;
                this.progressBar.style.width = '0%';
                return;
            default:
                // Fallback for any other state
                totalTime = this.state.pomo_session * 60;
        }
        
        elapsed = totalTime - this.state.timer_remaining;
        const progress = Math.max(0, Math.min(100, (elapsed / totalTime) * 100));
        
        // Enable transitions after first update (prevents page load animation)
        if (!this.transitionsEnabled) {
            this.progressBar.classList.add('transitions-enabled');
            this.transitionsEnabled = true;
        }
        
        this.progressBar.style.width = `${progress}%`;
    }
    
    updateButtonStates() {
        if (!this.startPauseBtn) return;
        
        const isRunning = this.state.timer_state === 'session' || this.state.timer_state === 'short_break' || this.state.timer_state === 'long_break';
        const isPaused = this.state.timer_state === 'paused';
        
        if (isRunning) {
            this.startPauseBtn.textContent = 'Pause';
            this.startPauseBtn.className = 'btn btn-warning';
        } else {
            this.startPauseBtn.textContent = 'Start';
            this.startPauseBtn.className = 'btn btn-primary';
        }
    }
    
    updateContainerClasses() {
        if (!this.container) return;
        
        // Remove all state classes
        this.container.classList.remove('session', 'short-break', 'long-break', 'paused', 'completed');
        
        // Add current state class
        if (this.state.timer_state !== 'idle') {
            this.container.classList.add(this.state.timer_state.replace('_', '-'));
        }
    }
    
    getCsrfToken() {
        // Follow existing CSRF token pattern
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }
        
        // Fallback to form input
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        if (csrfInput) {
            return csrfInput.value;
        }
        
        return '';
    }
    
    showCompletionNotification() {
        // Add completion animation
        if (this.container) {
            this.container.classList.add('completed');
            setTimeout(() => {
                this.container.classList.remove('completed');
            }, 3000);
        }
        
        // Show browser notification if permitted
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('Pomodoro Timer', {
                body: `${this.phaseNames[this.state.timer_state]} completed!`,
                icon: '/static/assets/favicon.ico'
            });
        }
    }
    
    showError(message) {
        // Simple error display - could be enhanced with toast notifications
        console.error(message);
        // Optionally show user feedback
        if (this.container) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'timer-error';
            errorDiv.textContent = message;
            errorDiv.style.cssText = 'color: var(--error-color); font-size: 0.875rem; margin-top: 0.5rem;';
            this.container.appendChild(errorDiv);
            setTimeout(() => errorDiv.remove(), 3000);
        }
    }
    
    cleanup() {
        this.stopCountdown();
        this.stopPeriodicSync();
        
        // Clean up sleep detection
        if (this.sleepDetectionInterval) {
            clearInterval(this.sleepDetectionInterval);
            this.sleepDetectionInterval = null;
        }
    }
}

// Initialize timer when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if timer container exists
    if (document.getElementById('timerContainer')) {
        new PomodoroTimer();
    }
});

// Request notification permission on first user interaction
document.addEventListener('click', () => {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}, { once: true });
