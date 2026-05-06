# Pomodoro Timer — Detailed Implementation Roadmap

> A practical, phased plan for implementing a robust Pomodoro timer into the Pomodoro + To‑Do app. Includes DB migrations, backend APIs, frontend UI + JS, sync/persistence, testing, and manual verification between phases.

---

## Reference image

(Visual reference used during design)

`/mnt/data/Screenshot 2025-11-23 at 6.57.44 pm.png`

---

# Executive summary

This roadmap provides a comprehensive, phase-by-phase implementation plan for adding a robust Pomodoro timer to the existing Flask application. Each phase includes detailed step-by-step execution strategies, success criteria, risk mitigation, testing approaches, and manual verification checkpoints.

Key architectural decisions:
- **Server is the source of truth** for timer state and remaining time
- **Hybrid approach**: client performs second-by-second UI countdown, server does authoritative time calculations and periodic syncs
- **Timer state is list-specific**: switching lists auto-pauses current timer and loads new list's state
- **Incremental enhancement**: builds on existing Flask routes, templates, and database patterns
- **Manual verification after each phase** before proceeding

Implementation highlights:
- **8 detailed phases** from preparation through final testing and polish
- **Step-by-step execution plans** with 6 detailed steps per phase
- **Comprehensive testing strategy** including unit tests, integration tests, and manual verification
- **Risk mitigation and success criteria** clearly defined for each phase
- **Architecture preservation** ensuring existing functionality remains intact
- **Accessibility and UX enhancements** including notifications, sounds, and keyboard navigation

Total estimated timeline: **10-14 days** with verification checkpoints after each phase

---

## Development Approach

- **Single branch development**: Work directly in main branch with regular commits
- **Phase-by-phase implementation**: Complete each phase fully, then stop for manual verification
- **Architecture preservation**: Extend existing patterns rather than replace them
- **Incremental testing**: Manual verification checkpoints after each phase

---

# Roadmap (milestones & deliverables)

## Phase 0 — Preparation & Setup
**Goal:** Prepare development environment and verify current state.

### Current State Analysis
- Verify existing database schema matches `schema.sql`
- Confirm Flask app runs correctly with current features
- Test existing list switching and task management functionality
- Document current active list behavior

### Setup Tasks
- Backup current database: `cp instance/pomodoro.sqlite instance/pomodoro.backup.sqlite`
- Verify all existing routes work: `/`, `/lists/`, auth flows
- Test current CSS and JavaScript functionality
- Create development checkpoint documentation

### Manual Verification Checklist
- [ ] Flask app starts without errors
- [ ] User registration/login works
- [ ] List creation and switching works
- [ ] Task creation, editing, deletion works
- [ ] All existing CSS styles load properly
- [ ] All existing JavaScript functions work

**Duration: 0.5 day**
**Stop here for manual verification before proceeding**

---

## Phase 1 — Database Schema Enhancement
**Goal:** Add timer state columns to lists table while preserving existing functionality.

### Schema Analysis
Current lists table already has basic timer settings:
- `pomo_session INTEGER DEFAULT 25`
- `pomo_short_break INTEGER DEFAULT 5` 
- `pomo_long_break INTEGER DEFAULT 15`
- `pomo_current_time INTEGER DEFAULT 0`

### Additional Timer State Columns Needed
Add these columns to `CREATE TABLE lists` in `schema.sql`:
```sql
-- Timer state management
timer_state TEXT DEFAULT 'idle' CHECK(timer_state IN ('idle', 'session', 'short_break', 'long_break', 'paused')),
timer_remaining INTEGER DEFAULT 0,
sessions_completed INTEGER DEFAULT 0,
timer_started_at TIMESTAMP NULL,
timer_last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### Migration Strategy
Since we're working incrementally:
1. **Development approach**: Drop and recreate database using `flask init-db`
2. **Migration file**: Create `migrations/002_add_timer_state.sql` for future production use

```sql
-- migrations/002_add_timer_state.sql
ALTER TABLE lists ADD COLUMN timer_state TEXT DEFAULT 'idle' CHECK(timer_state IN ('idle', 'session', 'short_break', 'long_break', 'paused'));
ALTER TABLE lists ADD COLUMN timer_remaining INTEGER DEFAULT 0;
ALTER TABLE lists ADD COLUMN sessions_completed INTEGER DEFAULT 0;
ALTER TABLE lists ADD COLUMN timer_started_at TIMESTAMP NULL;
ALTER TABLE lists ADD COLUMN timer_last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
```

### Implementation Strategy

#### Step-by-Step Execution Plan
1. **Schema File Updates**
   - Open `schema.sql` and locate the `CREATE TABLE lists` statement (around line 19)
   - Add the new timer columns after the existing `pomo_long_break` line
   - Include CHECK constraint for `timer_state` to ensure data integrity
   - Add `timer_last_updated` with DEFAULT CURRENT_TIMESTAMP for tracking

2. **Database Initialization Updates**
   - Open `pomodoro/db.py` and locate the `init_db()` function
   - Verify the function reads from `schema.sql` correctly
   - Test that the new schema will be properly initialized
   - No changes should be needed since it reads the schema file directly

3. **Migration File Creation**
   - Create new file: `migrations/002_add_timer_state.sql`
   - Write ALTER TABLE statements for each new column
   - Include the CHECK constraint in the ALTER statement
   - Test migration syntax with SQLite validation

4. **Database Testing**
   - Stop Flask application if running
   - Remove existing database: `rm instance/pomodoro.sqlite`
   - Reinitialize database: `flask init-db`
   - Verify new schema: `sqlite3 instance/pomodoro.sqlite "PRAGMA table_info(lists)"`
   - Check that all new columns exist with correct defaults

5. **Functionality Verification**
   - Start Flask application: `flask run`
   - Register a new user to test database operations
   - Create a new list and verify it works with new schema
   - Test all existing list and task functionality
   - Verify no errors in Flask logs or browser console

#### Success Criteria
- New schema file contains all timer columns with proper constraints
- Database initialization works without errors
- Migration file is ready for production deployment
- All existing functionality continues to work
- New columns have correct default values and constraints

#### Risk Mitigation
- **Schema errors**: Test with fresh database initialization
- **Migration failures**: Verify SQL syntax with SQLite validator
- **Data corruption**: Backup database before any schema changes
- **Feature regression**: Test all existing functionality thoroughly

#### Testing Strategy
- **Unit testing**: Test schema creation in isolation
- **Integration testing**: Test with full Flask application
- **Regression testing**: Verify all existing features work
- **Constraint testing**: Try to insert invalid data to verify CHECK constraints

### Edge Cases & Considerations
- **Existing lists**: New columns will have default values, no migration needed for existing data
- **CHECK constraints**: Ensure invalid timer states cannot be inserted
- **NULL handling**: `timer_started_at` should be NULL when timer is idle
- **Timezone**: All timestamps in UTC for consistency

### Manual Verification Checklist
- [ ] `flask init-db` runs without errors
- [ ] New lists table has all timer columns (use `PRAGMA table_info(lists)`)
- [ ] Existing list creation still works
- [ ] List switching functionality preserved
- [ ] Default timer values are correctly applied
- [ ] Database constraints work (try invalid timer_state)

**Duration: 1 day**
**Stop here for manual verification before proceeding**

---

## Phase 2 — Backend Timer API Implementation
**Goal:** Add timer endpoints to existing `routes/home.py` following current patterns.

### Architecture Integration
Extend the existing `home.py` pattern:
- Use existing `get_db()` helper function
- Follow existing `@login_required` pattern
- Use existing JSON response patterns from `update_tags_ajax()`
- Maintain existing error handling with `flash()` and JSON responses

### New Timer Endpoints
Add to `routes/home.py`:

```python
@bp.route('/timer/status', methods=['GET'])
@login_required
def get_timer_status():
    """Get current timer state for active list."""
    # Similar pattern to existing routes
    
@bp.route('/timer/start', methods=['POST']) 
@login_required
def start_timer():
    """Start or resume timer for active list."""
    # Follow existing JSON response pattern
    
@bp.route('/timer/pause', methods=['POST'])
@login_required
def pause_timer():
    """Pause current timer."""
    
@bp.route('/timer/reset', methods=['POST'])
@login_required  
def reset_timer():
    """Reset timer to idle state."""
    
@bp.route('/timer/skip', methods=['POST'])
@login_required
def skip_timer():
    """Skip to next phase."""
```

### Server-Side Timer Logic
Helper functions to add to `home.py`:

```python
def calculate_remaining_time(list_row):
    """Calculate remaining time based on server time."""
    
def get_next_phase(current_state, sessions_completed):
    """Determine next phase and session count."""
    
def update_timer_state(list_id, state, remaining=None):
    """Update timer state in database."""
```

### List Switching Integration
Modify existing `select_list()` in `routes/lists.py`:
- Auto-pause timer on current active list before switching
- Load new list's timer state
- Follow existing transaction patterns in the function

### Implementation Strategy

#### Step-by-Step Execution Plan
1. **Code Analysis and Pattern Identification**
   - Review existing `routes/home.py` structure and patterns
   - Identify existing JSON response patterns in `update_tags_ajax()`
   - Note existing error handling with `flash()` and JSON returns
   - Understand current `get_db()` usage pattern throughout the file

2. **Timer Helper Functions Implementation**
   - Add `calculate_remaining_time()` function at the bottom of `home.py`
   - Add `get_next_phase()` function for phase transitions
   - Add `update_timer_state()` function for database updates
   - Include proper error handling and logging in each helper

3. **Timer Status Endpoint Implementation**
   - Add `@bp.route('/timer/status', methods=['GET'])` before existing routes
   - Implement logic to get active list for current user
   - Handle case where no active list exists
   - Return JSON response with all timer state information
   - Follow existing JSON response patterns from `update_tags_ajax()`

4. **Timer Control Endpoints Implementation**
   - Add `@bp.route('/timer/start', methods=['POST'])` endpoint
   - Add `@bp.route('/timer/pause', methods=['POST'])` endpoint  
   - Add `@bp.route('/timer/reset', methods=['POST'])` endpoint
   - Add `@bp.route('/timer/skip', methods=['POST'])` endpoint
   - Each endpoint should follow the same pattern: validate → update → respond

5. **List Switching Integration**
   - Open `routes/lists.py` and locate the `select_list()` function
   - Add logic to pause current timer before switching lists
   - Integrate timer pause logic into existing database transaction
   - Ensure existing list switching functionality remains unchanged

6. **Testing and Validation**
   - Start Flask application and test each endpoint individually
   - Use browser dev tools or curl to test API responses
   - Test with no active list scenario
   - Test with invalid state transitions
   - Verify error handling works correctly

#### Success Criteria
- All timer endpoints return proper JSON responses
- Timer state persists correctly in database
- List switching pauses current timer appropriately
- Error handling works for all edge cases
- Existing functionality remains completely intact

#### Risk Mitigation
- **Route conflicts**: Ensure new routes don't conflict with existing ones
- **Database errors**: Use proper transactions and error handling
- **State corruption**: Validate all state transitions server-side
- **Performance**: Keep database queries efficient and minimal

#### Testing Strategy
- **Unit testing**: Test each helper function individually
- **Endpoint testing**: Test each API endpoint with various inputs
- **Integration testing**: Test timer with list switching
- **Error scenario testing**: Test all error conditions and edge cases

#### Code Integration Details
- Follow existing import patterns and code organization
- Use existing `get_db()` helper function consistently
- Match existing JSON response structure and error handling
- Maintain existing code style and documentation patterns
- Ensure all new routes have proper `@login_required` decorators

### Edge Cases & Error Handling
- **No active list**: Return appropriate error (follow existing patterns)
- **Invalid state transitions**: Validate server-side, return 400 with message
- **Database errors**: Use existing error handling patterns
- **Concurrent access**: Simple transaction-based locking
- **Timer completion**: Auto-transition to next phase

### Manual Verification Checklist
- [ ] All existing routes still work (/task/add, /task/toggle, etc.)
- [ ] New timer endpoints return valid JSON responses
- [ ] Timer state persists in database correctly
- [ ] List switching pauses current timer and loads new state
- [ ] Error handling works for invalid states
- [ ] Database transactions don't break existing functionality
- [ ] Test with browser network tools: verify API responses

**Duration: 2 days**
**Stop here for manual verification before proceeding**

---

## Phase 3 — Frontend Timer UI Implementation
**Goal:** Replace timer placeholder in existing template with functional timer interface.

### Current Template Analysis
Existing `templates/home/index.html` structure:
- Uses `.home-layout` with `.pomodoro-panel` and `.tasks-panel`
- Timer placeholder in `.pomodoro-panel` (lines 19-29)
- Already includes CSS files: `style.css`, `modal.css`, etc.
- Follows existing CSS patterns and responsive design

### Template Enhancement Strategy
Replace existing timer placeholder (lines 19-29) with:

```html
<div class="pomodoro-placeholder">
    <p class="list-name">Active List: {{ active_list['name'] }}</p>
    <div class="timer-settings">
        <p>Session: {{ active_list['pomo_session'] }} min</p>
        <p>Short Break: {{ active_list['pomo_short_break'] }} min</p>
        <p>Long Break: {{ active_list['pomo_long_break'] }} min</p>
    </div>
    
    <!-- NEW: Timer Interface -->
    <div class="timer-container" id="timerContainer">
        <div class="timer-phase" id="timerPhase">Focus Session</div>
        <div class="timer-display" id="timerDisplay">25:00</div>
        <div class="timer-progress">
            <div class="progress-bar" id="progressBar"></div>
        </div>
        <div class="timer-controls">
            <button id="startPauseBtn" class="btn btn-primary">Start</button>
            <button id="resetBtn" class="btn btn-secondary">Reset</button>
            <button id="skipBtn" class="btn btn-secondary">Skip</button>
        </div>
        <div class="timer-sessions" id="sessionCounter">0/4 sessions</div>
    </div>
</div>
```

### CSS Integration Strategy
Extend existing `static/css/style.css`:
- Use existing CSS variables (`--primary-color`, `--success-color`, etc.)
- Follow existing button patterns (`.btn`, `.btn-primary`, `.btn-secondary`)
- Maintain responsive design patterns from existing layout
- Add timer-specific classes that complement existing styles

```css
/* Add to existing style.css */
.timer-container {
    /* Follow existing panel patterns */
}

.timer-display {
    /* Large, readable font using existing typography */
}

.progress-bar {
    /* Use existing color variables */
}

.timer-phase.session { color: var(--primary-color); }
.timer-phase.short_break { color: var(--success-color); }
.timer-phase.long_break { color: var(--secondary-color); }
```

### Implementation Strategy

#### Step-by-Step Execution Plan
1. **Template Analysis and Preparation**
   - Open `templates/home/index.html` and locate the timer placeholder section (lines 19-29)
   - Identify the existing `.pomodoro-placeholder` div structure
   - Note the current list name display and timer settings display
   - Understand the existing CSS classes and structure patterns

2. **HTML Template Updates**
   - Replace the existing timer placeholder `<p class="timer-placeholder">Timer will go here</p>` with the new timer container
   - Preserve the existing list name and timer settings display
   - Add the new timer container with all required elements (display, progress, controls, session counter)
   - Ensure proper semantic HTML structure and accessibility attributes

3. **CSS Integration Planning**
   - Open `static/css/style.css` and review existing CSS variables and patterns
   - Identify existing button styles (`.btn`, `.btn-primary`, `.btn-secondary`)
   - Note existing color scheme and typography patterns
   - Plan timer-specific CSS that complements existing styles

4. **CSS Implementation**
   - Add timer container styles following existing panel patterns
   - Implement timer display styles with large, readable fonts
   - Add progress bar styles using existing CSS variables
   - Create phase-specific color classes using existing color scheme
   - Ensure responsive design following existing mobile-first patterns

5. **Responsive Design Testing**
   - Test timer UI on different screen sizes
   - Verify timer elements scale properly on mobile devices
   - Ensure touch targets are appropriately sized for mobile
   - Test layout doesn't break on very small screens

6. **Accessibility Implementation**
   - Add proper ARIA labels to all interactive elements
   - Ensure keyboard navigation works for all timer controls
   - Test with screen reader emulation tools
   - Verify color contrast meets accessibility standards

#### Success Criteria
- Timer UI displays correctly in the placeholder area
- All existing functionality remains intact
- Responsive design works across all device sizes
- Accessibility features work correctly
- CSS integrates seamlessly with existing styles

#### Risk Mitigation
- **Layout conflicts**: Ensure new CSS doesn't break existing components
- **Responsive issues**: Test thoroughly on mobile devices
- **Accessibility gaps**: Test with actual screen readers if possible
- **CSS specificity**: Use specific enough selectors to avoid conflicts

#### Testing Strategy
- **Visual testing**: Verify appearance matches design requirements
- **Functional testing**: Ensure all UI elements are present and clickable
- **Responsive testing**: Test on various screen sizes and devices
- **Accessibility testing**: Test keyboard navigation and screen readers
- **Cross-browser testing**: Test in Chrome, Firefox, Safari, Edge

#### Integration Details
- Use existing CSS variables for colors and spacing
- Follow existing naming conventions for CSS classes
- Maintain existing HTML structure and patterns
- Ensure timer UI doesn't interfere with existing task management UI
- Keep JavaScript dependencies minimal at this stage

### Edge Cases & Considerations
- **No active list**: Show appropriate message (existing pattern)
- **CSS conflicts**: Ensure new styles don't break existing components
- **Responsive behavior**: Test on mobile devices
- **Browser compatibility**: Test modern browsers
- **Loading states**: Handle initial page load gracefully

### Manual Verification Checklist
- [ ] Page loads without errors
- [ ] Timer UI displays correctly in placeholder area
- [ ] All existing functionality still works (tasks, lists, etc.)
- [ ] Responsive design works on mobile
- [ ] CSS styles apply correctly (colors, fonts, layout)
- [ ] No JavaScript errors (even though JS not implemented yet)
- [ ] Accessibility: keyboard can navigate to timer buttons
- [ ] Existing CSS animations and transitions still work

**Duration: 1 day**
**Stop here for manual verification before proceeding**

---

## Phase 4 — Frontend Timer JavaScript Implementation
**Goal:** Create timer functionality that integrates with existing JavaScript patterns.

### Current JavaScript Architecture Analysis
Existing JavaScript files in `static/js/`:
- `home.js` - Main page functionality, follows module pattern
- `unified-drag-controller.js` - Complex drag operations, uses event delegation
- `delete-modal.js` - Modal interactions, follows class-based pattern
- All use modern JavaScript (async/await, fetch API)
- Follow consistent error handling patterns
- Use CSRF tokens from existing patterns

### Timer JavaScript Implementation Strategy
Create `static/js/timer.js` following existing patterns:

```javascript
// Follow existing class-based pattern from delete-modal.js
class PomodoroTimer {
    constructor() {
        this.container = document.getElementById('timerContainer');
        this.display = document.getElementById('timerDisplay');
        this.phaseDisplay = document.getElementById('timerPhase');
        this.progressBar = document.getElementById('progressBar');
        this.startPauseBtn = document.getElementById('startPauseBtn');
        this.resetBtn = document.getElementById('resetBtn');
        this.skipBtn = document.getElementById('skipBtn');
        this.sessionCounter = document.getElementById('sessionCounter');
        
        this.state = {
            timer_state: 'idle',
            timer_remaining: 0,
            sessions_completed: 0,
            current_phase: 'session'
        };
        
        this.countdownInterval = null;
        this.syncInterval = null;
        this.init();
    }
    
    async init() {
        this.bindEvents();
        await this.loadState();
    }
    
    bindEvents() {
        // Follow existing event delegation patterns
        this.startPauseBtn.addEventListener('click', () => this.toggleTimer());
        this.resetBtn.addEventListener('click', () => this.reset());
        this.skipBtn.addEventListener('click', () => this.skip());
        
        // Follow existing visibility patterns
        document.addEventListener('visibilitychange', () => this.handleVisibilityChange());
    }
    
    async loadState() {
        // Use existing fetch patterns from other JS files
        try {
            const response = await fetch('/timer/status');
            const data = await response.json();
            this.updateState(data);
            this.updateDisplay();
        } catch (error) {
            console.error('Failed to load timer state:', error);
        }
    }
    
    async toggleTimer() {
        if (this.state.timer_state === 'idle' || this.state.timer_state === 'paused') {
            await this.start();
        } else {
            await this.pause();
        }
    }
    
    async start() {
        // Use existing CSRF and fetch patterns
        const formData = new FormData();
        formData.append('csrf_token', this.getCsrfToken());
        
        try {
            const response = await fetch('/timer/start', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            if (data.success) {
                this.updateState(data);
                this.startCountdown();
                this.startPeriodicSync();
            }
        } catch (error) {
            console.error('Failed to start timer:', error);
        }
    }
    
    async pause() {
        // Similar pattern to start()
    }
    
    async reset() {
        // Similar pattern to start()
    }
    
    async skip() {
        // Similar pattern to start()
    }
    
    startCountdown() {
        this.stopCountdown();
        this.countdownInterval = setInterval(() => {
            this.state.timer_remaining--;
            this.updateDisplay();
            
            if (this.state.timer_remaining <= 0) {
                this.handleCompletion();
            }
        }, 1000);
    }
    
    stopCountdown() {
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
            this.countdownInterval = null;
        }
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
            const response = await fetch('/timer/status');
            const data = await response.json();
            this.updateState(data);
            this.updateDisplay();
        } catch (error) {
            console.error('Sync failed:', error);
        }
    }
    
    handleCompletion() {
        this.stopCountdown();
        this.skip(); // Move to next phase
        this.showNotification();
    }
    
    updateState(data) {
        // Update local state from server response
        Object.assign(this.state, data);
    }
    
    updateDisplay() {
        // Update UI elements
        const minutes = Math.floor(this.state.timer_remaining / 60);
        const seconds = this.state.timer_remaining % 60;
        this.display.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        // Update phase display
        this.phaseDisplay.textContent = this.getPhaseDisplayName(this.state.timer_state);
        
        // Update progress bar
        this.updateProgressBar();
        
        // Update session counter
        this.sessionCounter.textContent = `${this.state.sessions_completed % 4}/4 sessions`;
        
        // Update button states
        this.updateButtonStates();
    }
    
    getCsrfToken() {
        // Follow existing CSRF token pattern
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }
    
    // Additional helper methods...
}

// Initialize timer when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new PomodoroTimer();
});
```

### Integration with Existing JavaScript
Add timer script to `templates/home/index.html`:
```html
<!-- Add to existing scripts block -->
<script src="{{ url_for('static', filename='js/timer.js') }}"></script>
```

### Implementation Strategy

#### Step-by-Step Execution Plan
1. **JavaScript Architecture Setup**
   - Create new file `static/js/timer.js`
   - Review existing patterns in `delete-modal.js` and `unified-drag-controller.js`
   - Establish class-based structure following existing conventions
   - Set up proper error handling and logging patterns

2. **Core Timer Class Implementation**
   - Implement `PomodoroTimer` class constructor with DOM element references
   - Add state management object with timer properties
   - Initialize event listeners for all timer controls
   - Set up initial state loading from server

3. **Server Communication Implementation**
   - Implement `loadState()` method using fetch API
   - Add `start()`, `pause()`, `reset()`, `skip()` methods
   - Follow existing CSRF token patterns from other JavaScript files
   - Implement proper JSON response handling

4. **Timer Countdown Logic**
   - Implement `startCountdown()` and `stopCountdown()` methods
   - Add precise 1-second interval handling
   - Implement completion detection and automatic phase transitions
   - Add display updates for each second

5. **Periodic Synchronization**
   - Implement `syncWithServer()` method for 30-second syncs
   - Add visibility change detection for immediate syncs
   - Implement conflict resolution preferring server state
   - Add exponential backoff for failed sync attempts

6. **UI Updates and Display Management**
   - Implement `updateDisplay()` method for all UI elements
   - Add time formatting with MM:SS display
   - Implement progress bar updates
   - Add button state management (Start/Pause text changes)

#### Success Criteria
- Timer class follows existing JavaScript patterns
- All timer controls work correctly
- Server communication is reliable and error-handled
- Countdown is accurate and synchronized
- UI updates are smooth and responsive

#### Risk Mitigation
- **Memory leaks**: Properly clean up intervals and event listeners
- **Network failures**: Implement robust error handling and retry logic
- **Timer drift**: Use server as source of truth with periodic sync
- **Performance**: Optimize DOM updates and avoid unnecessary calculations

#### Testing Strategy
- **Unit testing**: Test individual methods in isolation
- **Integration testing**: Test server communication endpoints
- **Performance testing**: Monitor memory usage and CPU over time
- **Error scenario testing**: Test network failures and server errors
- **Cross-browser testing**: Ensure compatibility across browsers

#### Integration Details
- Follow existing class-based patterns from `delete-modal.js`
- Use existing fetch API patterns with proper error handling
- Match existing CSRF token handling approach
- Maintain consistent code style and documentation
- Ensure no conflicts with existing JavaScript functionality

### Edge Cases & Error Handling
- **Network failures**: Continue countdown, retry sync with exponential backoff
- **Page visibility**: Sync when tab becomes visible
- **Multiple tabs**: Use server state as source of truth
- **Browser sleep**: Detect and resync on wake
- **Invalid server responses**: Graceful fallback

### Manual Verification Checklist
- [ ] Timer loads initial state from server
- [ ] Start/pause/reset buttons work correctly
- [ ] Timer countdown displays properly
- [ ] Progress bar animates smoothly
- [ ] Phase transitions work correctly
- [ ] Session counter updates
- [ ] Server sync works every 30 seconds
- [ ] Tab visibility change triggers sync
- [ ] Network errors handled gracefully
- [ ] No conflicts with existing JavaScript
- [ ] Console is clean (no errors)
- [ ] Memory usage stable over time

**Duration: 2 days**
**Stop here for manual verification before proceeding**

---

## Phase 5 — Enhanced Sync & Multi-tab Support
**Goal:** Refine synchronization and handle complex edge cases.

### Current Sync Implementation Analysis
From Phase 4, we have:
- Basic 30-second periodic sync
- Visibility change handling
- Network failure fallback
- Server as source of truth

### Enhanced Sync Features

#### 1. Conflict Resolution Strategy
```javascript
// Enhanced sync with conflict detection
async syncWithServer() {
    try {
        const response = await fetch('/timer/status');
        const data = await response.json();
        
        // Check for conflicts
        if (this.detectConflict(data)) {
            await this.resolveConflict(data);
        } else {
            this.updateState(data);
            this.updateDisplay();
        }
    } catch (error) {
        this.handleSyncError(error);
    }
}

detectConflict(serverData) {
    // Detect if server state is newer than local state
    return serverData.timer_last_updated > this.lastSyncTime;
}

async resolveConflict(serverData) {
    // Always prefer server state
    this.updateState(serverData);
    this.updateDisplay();
    
    // If timer was running locally, restart with server time
    if (this.countdownInterval) {
        this.stopCountdown();
        if (serverData.timer_state === 'session' || 
            serverData.timer_state === 'short_break' || 
            serverData.timer_state === 'long_break') {
            this.startCountdown();
        }
    }
}
```

#### 2. Background Tab Management
```javascript
// Handle background tab behavior
handleVisibilityChange() {
    if (document.hidden) {
        // Tab going to background
        this.stopCountdown(); // Stop local countdown to save resources
        this.syncWithServer(); // Final sync before backgrounding
    } else {
        // Tab coming to foreground
        this.syncWithServer(); // Immediate sync on visibility
        if (this.state.timer_state !== 'idle' && this.state.timer_state !== 'paused') {
            this.startCountdown(); // Resume countdown if needed
        }
    }
}
```

#### 3. Network Resilience
```javascript
// Enhanced error handling with exponential backoff
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

// Reset retry count on successful sync
updateState(data) {
    Object.assign(this.state, data);
    this.lastSyncTime = data.timer_last_updated || Date.now();
    this.syncRetryCount = 0; // Reset retry count
}
```

#### 4. Browser Sleep Detection
```javascript
// Detect browser sleep/wake using time stamps
constructor() {
    // ... existing constructor code
    this.lastKnownTime = Date.now();
    this.sleepDetectionInterval = setInterval(() => {
        this.checkForSleep();
    }, 60000); // Check every minute
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
```

### List Switching Enhancement
Enhance the existing list switching logic in `routes/lists.py`:

```python
@bp.route('/<int:id>/select', methods=('POST',))
@login_required
def select_list(id):
    db = get_db()
    
    # PAUSE current timer before switching
    current_active = db.execute(
        'SELECT id FROM lists WHERE is_active = 1 AND user_id = ?',
        (current_user.id,)
    ).fetchone()
    
    if current_active and current_active['id'] != id:
        # Pause timer on current list
        db.execute(
            'UPDATE lists SET timer_state = ?, timer_last_updated = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?',
            ('paused', current_active['id'], current_user.id)
        )
    
    # ... existing list switching logic ...
```

### Implementation Strategy

#### Step-by-Step Execution Plan
1. **Conflict Detection Implementation**
   - Add `detectConflict()` method to compare server and local timestamps
   - Implement `resolveConflict()` method preferring server state
   - Add `lastSyncTime` tracking to detect state changes
   - Test conflict resolution with simulated server changes

2. **Background Tab Optimization**
   - Enhance `handleVisibilityChange()` method for tab visibility events
   - Implement countdown stopping when tab goes to background
   - Add immediate sync when tab becomes visible
   - Test resource usage in background tabs

3. **Network Resilience Enhancement**
   - Implement `handleSyncError()` with exponential backoff logic
   - Add retry counter and maximum retry limits
   - Implement graceful degradation during network failures
   - Test with simulated network failures

4. **Browser Sleep Detection**
   - Add `checkForSleep()` method using timestamp comparison
   - Implement periodic time difference checking
   - Add forced sync on sleep detection
   - Test with browser sleep simulation

5. **List Switching Integration**
   - Modify `routes/lists.py` `select_list()` function
   - Add timer pause logic before list switching
   - Integrate with existing database transaction patterns
   - Test timer behavior during list switches

6. **Multi-tab Testing and Optimization**
   - Test with multiple browser tabs simultaneously
   - Verify sync behavior across tabs
   - Optimize sync frequency to prevent server overload
   - Test rapid tab switching scenarios

#### Success Criteria
- Multi-tab synchronization works reliably
- Background tabs don't waste system resources
- Network failures are handled gracefully with automatic retry
- Browser sleep/wake cycles are detected and handled
- List switching properly pauses current timer
- No sync storms or excessive server requests

#### Risk Mitigation
- **Sync storms**: Implement debouncing and rate limiting
- **Memory leaks**: Properly clean up intervals and event listeners
- **Performance degradation**: Monitor CPU and memory usage
- **State corruption**: Always prefer server state as source of truth
- **Network overload**: Implement exponential backoff and retry limits

#### Testing Strategy
- **Multi-tab testing**: Open multiple tabs and verify synchronization
- **Network simulation**: Use browser dev tools to simulate network failures
- **Sleep testing**: Test browser sleep/wake cycles
- **Performance monitoring**: Monitor resource usage during extended operation
- **Stress testing**: Test with rapid tab switching and network interruptions

#### Integration Details
- Extend existing `timer.js` class with new methods
- Maintain existing API endpoints and response patterns
- Follow existing error handling and logging patterns
- Ensure backward compatibility with existing functionality
- Use existing database transaction patterns in list switching

### Edge Cases & Advanced Scenarios
- **Clock skew**: Handle server/client time differences
- **Rapid tab switching**: Prevent sync storms
- **Long network outages**: Graceful degradation
- **System sleep**: Detect and handle system sleep/wake
- **Multiple rapid clicks**: Debounce user actions

### Manual Verification Checklist
- [ ] Multiple tabs stay synchronized
- [ ] Background tabs don't waste resources
- [ ] Network failures trigger retry with backoff
- [ ] Browser sleep/wake is handled correctly
- [ ] List switching pauses current timer
- [ ] Rapid tab switching doesn't cause errors
- [ ] Clock skew is handled gracefully
- [ ] Long network outages don't break timer
- [ ] Memory usage remains stable
- [ ] CPU usage is reasonable in background tabs

**Duration: 1-2 days**
**Stop here for manual verification before proceeding**

---

## Phase 6 — User Experience Enhancements & Accessibility
**Goal:** Add notifications, sounds, and accessibility features while maintaining existing patterns.

### Current UX Patterns Analysis
Existing application UX patterns:
- Uses `flash()` messages for user feedback
- Follows semantic HTML patterns
- Uses ARIA attributes in existing modals
- Has responsive design patterns
- Uses CSS transitions for interactions

### Notification System Implementation

#### 1. Browser Notifications
```javascript
// Add to timer.js class
async requestNotificationPermission() {
    if ('Notification' in window) {
        if (Notification.permission === 'default') {
            const permission = await Notification.requestPermission();
            return permission === 'granted';
        }
        return Notification.permission === 'granted';
    }
    return false;
}

showNotification(message, options = {}) {
    if (this.notificationsEnabled && 'Notification' in window) {
        const notification = new Notification('Pomodoro Timer', {
            body: message,
            icon: '/static/assets/timer-icon.png',
            ...options
        });
        
        // Auto-close after 5 seconds
        setTimeout(() => notification.close(), 5000);
    }
    
    // Fallback: use existing flash message pattern
    this.showFlashMessage(message);
}

showFlashMessage(message) {
    // Follow existing flash message pattern
    const flashContainer = document.querySelector('.flash-messages') || this.createFlashContainer();
    const flashElement = document.createElement('div');
    flashElement.className = 'flash flash-info';
    flashElement.textContent = message;
    flashContainer.appendChild(flashElement);
    
    // Auto-remove after 3 seconds
    setTimeout(() => flashElement.remove(), 3000);
}
```

#### 2. Sound System
```javascript
// Sound notification system
playSound(type = 'complete') {
    if (!this.soundEnabled) return;
    
    const audio = new Audio(`/static/sounds/timer-${type}.mp3`);
    audio.volume = 0.5; // Respect user preferences
    audio.play().catch(error => {
        console.log('Sound play failed:', error);
    });
}

// Add sound toggle to UI
addSoundToggle() {
    const soundToggle = document.createElement('button');
    soundToggle.className = 'sound-toggle';
    soundToggle.innerHTML = '🔊';
    soundToggle.addEventListener('click', () => {
        this.soundEnabled = !this.soundEnabled;
        soundToggle.innerHTML = this.soundEnabled ? '🔊' : '🔇';
    });
    
    this.container.appendChild(soundToggle);
}
```

#### 3. Browser Title Updates
```javascript
// Update browser tab title
updateTitle() {
    const timeStr = this.formatTime(this.state.timer_remaining);
    const phaseName = this.getPhaseDisplayName(this.state.timer_state);
    
    if (this.state.timer_state === 'idle') {
        document.title = 'Pomodoro + To-Do';
    } else {
        document.title = `${timeStr} - ${phaseName} - Pomodoro + To-Do`;
    }
}

// Call this in updateDisplay()
updateDisplay() {
    // ... existing updateDisplay code ...
    this.updateTitle();
}
```

### Accessibility Enhancements

#### 1. ARIA Live Regions
```html
<!-- Add to timer template -->
<div class="timer-container" id="timerContainer">
    <!-- existing timer elements -->
    
    <!-- ARIA live region for screen readers -->
    <div class="sr-only" aria-live="polite" aria-atomic="true" id="timerAnnouncements">
        Timer announcements will appear here
    </div>
</div>
```

```javascript
// Screen reader announcements
announceToScreenReader(message) {
    const announcement = document.getElementById('timerAnnouncements');
    if (announcement) {
        announcement.textContent = message;
        
        // Clear after announcement
        setTimeout(() => {
            announcement.textContent = '';
        }, 1000);
    }
}

// Call on important events
handleCompletion() {
    this.stopCountdown();
    this.announceToScreenReader(`Timer completed. Moving to ${this.getNextPhaseName()}`);
    this.showNotification(`${this.getPhaseDisplayName(this.state.timer_state)} completed!`);
    this.playSound();
    this.skip();
}
```

#### 2. Keyboard Navigation
```javascript
// Enhanced keyboard support
bindEvents() {
    // ... existing event bindings ...
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return; // Don't interfere with form inputs
        }
        
        switch(e.code) {
            case 'Space':
                e.preventDefault();
                this.toggleTimer();
                break;
            case 'KeyR':
                e.preventDefault();
                this.reset();
                break;
            case 'KeyS':
                e.preventDefault();
                this.skip();
                break;
        }
    });
}
```

#### 3. Enhanced Button Accessibility
```javascript
updateButtonStates() {
    // Update button states and accessibility
    const isRunning = this.state.timer_state === 'session' || 
                     this.state.timer_state === 'short_break' || 
                     this.state.timer_state === 'long_break';
    
    this.startPauseBtn.textContent = isRunning ? 'Pause' : 'Start';
    this.startPauseBtn.setAttribute('aria-label', isRunning ? 'Pause timer' : 'Start timer');
    
    this.resetBtn.setAttribute('aria-label', 'Reset timer');
    this.skipBtn.setAttribute('aria-label', 'Skip to next phase');
    
    // Add appropriate ARIA attributes
    this.display.setAttribute('aria-label', `Timer displaying ${this.formatTime(this.state.timer_remaining)} remaining`);
}
```

### Visual Feedback Enhancements

#### 1. Progress Bar Animation
```css
/* Add to style.css */
.progress-bar {
    transition: width 1s linear;
    background: linear-gradient(90deg, var(--primary-color) 0%, var(--primary-light) 100%);
}

.timer-phase.session { color: var(--primary-color); }
.timer-phase.short_break { color: var(--success-color); }
.timer-phase.long_break { color: var(--secondary-color); }

/* Pulse animation for running timer */
.timer-container.running .timer-display {
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.8; }
}
```

#### 2. Completion Animation
```javascript
// Visual feedback on completion
showCompletionAnimation() {
    this.container.classList.add('completed');
    
    // Remove class after animation
    setTimeout(() => {
        this.container.classList.remove('completed');
    }, 2000);
}
```

### Implementation Strategy

#### Step-by-Step Execution Plan
1. **Notification System Implementation**
   - Add `requestNotificationPermission()` method for browser permissions
   - Implement `showNotification()` method with browser API and flash fallback
   - Add `showFlashMessage()` method following existing flash patterns
   - Test notification behavior with permission granted/denied scenarios

2. **Sound System Implementation**
   - Add `playSound()` method with error handling
   - Implement `addSoundToggle()` method for user control
   - Create sound files in `static/sounds/` directory
   - Test sound playback across different browsers and mobile devices

3. **Browser Title Updates**
   - Add `updateTitle()` method to modify document.title
   - Integrate title updates into existing `updateDisplay()` method
   - Test title updates during different timer phases
   - Ensure title resets appropriately when timer is idle

4. **Accessibility Enhancements**
   - Add ARIA live region to HTML template for screen readers
   - Implement `announceToScreenReader()` method for important events
   - Add keyboard shortcuts (Space, R, S) with proper event handling
   - Enhance button accessibility with dynamic ARIA labels

5. **Visual Feedback Implementation**
   - Add CSS animations for progress bar and timer display
   - Implement `showCompletionAnimation()` method for phase transitions
   - Add pulse animation for running timer state
   - Test animations don't impact timer performance

6. **Cross-Platform Testing**
   - Test notifications on desktop browsers (Chrome, Firefox, Safari, Edge)
   - Test sound playback on mobile devices
   - Verify accessibility features with screen readers
   - Test keyboard shortcuts don't conflict with existing functionality

#### Success Criteria
- Browser notifications work with proper permission handling
- Sound system works with user controls and fallback behavior
- Browser title updates provide clear timer status
- Accessibility features work with screen readers and keyboard navigation
- Visual feedback enhances user experience without impacting performance
- All features work across desktop and mobile platforms

#### Risk Mitigation
- **Notification permissions**: Handle denied permissions gracefully with fallback
- **Sound autoplay**: Address browser autoplay policies with user interaction requirements
- **Accessibility gaps**: Test with actual screen readers and keyboard-only navigation
- **Performance impact**: Ensure animations don't affect timer accuracy
- **Mobile compatibility**: Test and optimize for mobile browser limitations

#### Testing Strategy
- **Permission testing**: Test notification behavior with granted/denied permissions
- **Sound testing**: Test audio playback across browsers and devices
- **Accessibility testing**: Use screen reader emulators and keyboard-only navigation
- **Performance testing**: Monitor timer accuracy during animations
- **Cross-browser testing**: Verify all features work across target browsers

#### Integration Details
- Extend existing `timer.js` class with new UX methods
- Follow existing flash message patterns for notification fallbacks
- Use existing CSS variables and animation patterns
- Maintain existing keyboard shortcuts and event handling patterns
- Ensure all new features are optional and don't break existing functionality

### Edge Cases & Considerations
- **Notification permissions**: Handle denied permissions gracefully
- **Sound autoplay**: Browser policies may block autoplay
- **Screen reader compatibility**: Test with actual screen readers
- **Mobile limitations**: Some features may not work on mobile
- **Performance**: Animations shouldn't impact timer accuracy

### Manual Verification Checklist
- [ ] Browser notifications work (permission granted/denied)
- [ ] Sound plays correctly and can be toggled
- [ ] Browser title updates with remaining time
- [ ] Screen reader announces timer events
- [ ] Keyboard shortcuts work (Space, R, S)
- [ ] Progress bar animates smoothly
- [ ] Completion animations trigger correctly
- [ ] All accessibility attributes are present
- [ ] Mobile compatibility is maintained
- [ ] Performance impact is minimal
- [ ] Existing functionality remains intact

**Duration: 1-2 days**
**Stop here for manual verification before proceeding**

---

## Phase 7 — Complete List Integration & Edge Cases
**Goal:** Ensure timer behavior works seamlessly with existing list management system.

### Current List System Analysis
Existing list functionality in `routes/lists.py`:
- `select_list()` handles switching active lists
- `create_list()` creates new lists with default timer settings
- `delete_list()` handles list deletion with cascade
- Lists already have timer duration columns (`pomo_session`, etc.)

### Timer State Preservation Strategy
**Decision**: When switching lists, **pause current timer** and preserve its state.

#### Enhanced List Switching Logic
Update `routes/lists.py` `select_list()` function:

```python
@bp.route('/<int:id>/select', methods=('POST',))
@login_required
def select_list(id):
    db = get_db()
    
    # Get current active list
    current_active = db.execute(
        'SELECT * FROM lists WHERE is_active = 1 AND user_id = ?',
        (current_user.id,)
    ).fetchone()
    
    # PAUSE timer on current list if it exists and is different
    if current_active and current_active['id'] != id:
        current_timer_state = current_active['timer_state']
        if current_timer_state in ('session', 'short_break', 'long_break'):
            # Pause the running timer
            db.execute(
                '''UPDATE lists SET 
                    timer_state = ?, 
                    timer_last_updated = CURRENT_TIMESTAMP 
                   WHERE id = ? AND user_id = ?''',
                ('paused', current_active['id'], current_user.id)
            )
    
    # ... existing list switching logic remains the same ...
```

#### List Creation Enhancement
Update `routes/lists.py` `create()` function to initialize timer state properly (already works with defaults).

#### List Deletion Enhancement
Update `routes/lists.py` `delete_list()` function to handle active list deletion (already handles fallback).

### Frontend List Integration

#### Timer State Loading on List Switch
Add to `timer.js`:

```javascript
// Handle list switching by reloading state
async handleListSwitch() {
    this.stopCountdown();
    this.stopPeriodicSync();
    await this.loadState();
    this.updateDisplay();
}

// Call this when page loads with new active list
// (List switching already causes page reload, so this works automatically)
```

### Edge Cases & Advanced Scenarios

#### 1. Timer Settings Update
```python
# Add endpoint to update timer settings
@bp.route('/timer/settings', methods=['POST'])
@login_required
def update_timer_settings():
    db = get_db()
    
    active_list = db.execute(
        'SELECT id, timer_state FROM lists WHERE is_active = 1 AND user_id = ?',
        (current_user.id,)
    ).fetchone()
    
    if not active_list:
        return jsonify({'success': False, 'error': 'No active list'})
    
    # Only allow settings changes when timer is idle
    if active_list['timer_state'] != 'idle':
        return jsonify({'success': False, 'error': 'Cannot change settings while timer is running'})
    
    # Update settings
    session_length = int(request.form.get('session_length', 25))
    short_break = int(request.form.get('short_break', 5))
    long_break = int(request.form.get('long_break', 15))
    
    db.execute(
        '''UPDATE lists SET 
            pomo_session = ?, 
            pomo_short_break = ?, 
            pomo_long_break = ?
           WHERE id = ?''',
        (session_length, short_break, long_break, active_list['id'])
    )
    db.commit()
    
    return jsonify({'success': True})
```

#### 2. Timer State Validation
```python
# Add helper function to validate timer state
def validate_timer_state(list_row):
    """Ensure timer state is consistent."""
    state = list_row['timer_state']
    remaining = list_row['timer_remaining']
    started_at = list_row['timer_started_at']
    
    # Basic validation rules
    if state in ('session', 'short_break', 'long_break') and not started_at:
        return False, 'Timer running but no start time'
    
    if state == 'paused' and started_at:
        return False, 'Paused timer should not have start time'
    
    return True, 'State is valid'
```

### Implementation Strategy

#### Step-by-Step Execution Plan
1. **List Switching Enhancement**
   - Open `routes/lists.py` and locate the `select_list()` function
   - Add logic to query current active list before switching
   - Implement timer pausing logic for running timers
   - Integrate timer pause into existing database transaction
   - Test list switching with various timer states

2. **Timer Settings Endpoint Implementation**
   - Add new `/timer/settings` endpoint to `routes/home.py`
   - Implement validation to only allow settings changes when timer is idle
   - Add form handling for session, short break, and long break durations
   - Test settings update with both idle and running timer states

3. **State Validation Helper Implementation**
   - Add `validate_timer_state()` function to `routes/home.py`
   - Implement logic to check timer state consistency
   - Add validation for running timers with missing start times
   - Test validation with various timer state scenarios

4. **Frontend List Integration**
   - Add `handleListSwitch()` method to `timer.js` class
   - Implement timer cleanup on list switches (stop countdown, sync)
   - Add automatic state loading on page reload after list switch
   - Test timer behavior during rapid list switching

5. **Edge Case Handling**
   - Test timer behavior when deleting the active list
   - Verify timer state persistence during list operations
   - Test with single list scenarios (no other lists to switch to)
   - Handle cases where no active list exists

6. **Comprehensive Testing**
   - Test all list operations (create, switch, delete) with timer states
   - Verify timer state persistence across list operations
   - Test concurrent timer and list operations
   - Validate all edge cases and error scenarios

#### Success Criteria
- List switching properly pauses current timer and preserves state
- Timer settings can be updated when timer is idle
- Timer settings updates are rejected when timer is running
- Timer state validation catches and prevents inconsistencies
- All existing list functionality continues to work
- Timer state persists correctly across all list operations

#### Risk Mitigation
- **State corruption**: Implement proper validation and error handling
- **Transaction conflicts**: Ensure database operations are atomic
- **User confusion**: Provide clear feedback for settings update restrictions
- **Performance**: Keep list operations efficient despite timer integration

#### Testing Strategy
- **Unit testing**: Test each helper function and endpoint individually
- **Integration testing**: Test timer behavior with list operations
- **Edge case testing**: Test all error scenarios and boundary conditions
- **Regression testing**: Ensure existing list functionality remains intact
- **Performance testing**: Verify list operations remain responsive

#### Integration Details
- Extend existing `routes/lists.py` with timer-aware logic
- Add new endpoint to `routes/home.py` following existing patterns
- Enhance `timer.js` with list switching handling
- Use existing database transaction patterns
- Maintain existing error handling and response patterns

### Manual Verification Checklist
- [ ] List switching pauses current timer correctly
- [ ] New lists start with correct default timer state
- [ ] List deletion preserves timer state appropriately
- [ ] Active list switching loads correct timer state
- [ ] Timer settings update works when idle
- [ ] Timer settings update rejected when running
- [ ] Timer state validation catches inconsistencies
- [ ] All existing list functionality still works
- [ ] Timer state persists across list operations
- [ ] Edge cases (no lists, single list) handled correctly

**Duration: 1-2 days**
**Stop here for manual verification before proceeding**

---

## Phase 8 — Final Testing & Polish
**Goal:** Comprehensive testing and performance optimization while maintaining existing architecture.

### Testing Strategy Following Existing Patterns

#### 1. Backend Unit Tests
Create `test_timer_backend.py` following existing test patterns from `test_hierarchy.py`:

```python
import pytest
from pomodoro.routes.home import calculate_remaining_time, get_next_phase
from datetime import datetime, timedelta

class TestTimerLogic:
    def test_calculate_remaining_time_idle(self):
        # Test idle state returns stored remaining time
        list_row = {
            'timer_state': 'idle',
            'timer_remaining': 1500,
            'timer_started_at': None
        }
        assert calculate_remaining_time(list_row) == 1500
    
    def test_calculate_remaining_time_running(self):
        # Test running timer calculates elapsed time
        started_time = datetime.utcnow() - timedelta(minutes=5)
        list_row = {
            'timer_state': 'session',
            'timer_remaining': 1500,  # 25 minutes
            'timer_started_at': started_time.isoformat()
        }
        remaining = calculate_remaining_time(list_row)
        assert 1200 <= remaining <= 1202  # ~20 minutes remaining (allowing for test timing)
    
    def test_get_next_phase_session_to_break(self):
        # Test session transitions to break
        next_phase, sessions = get_next_phase('session', 3)
        assert next_phase == 'short_break'
        assert sessions == 4
    
    def test_get_next_phase_session_to_long_break(self):
        # Test every 4th session goes to long break
        next_phase, sessions = get_next_phase('session', 4)
        assert next_phase == 'long_break'
        assert sessions == 5
```

#### 2. API Integration Tests
Create `test_timer_api.py`:

```python
class TestTimerAPI:
    def test_timer_status_endpoint(self, client, auth):
        # Test getting timer status
        auth.login()
        response = client.get('/timer/status')
        assert response.status_code == 200
        data = response.get_json()
        assert 'timer_state' in data
        assert 'timer_remaining' in data
    
    def test_timer_start_endpoint(self, client, auth):
        # Test starting timer
        auth.login()
        response = client.post('/timer/start')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['timer_state'] == 'session'
    
    def test_timer_pause_endpoint(self, client, auth):
        # Test pausing timer
        auth.login()
        # Start first
        client.post('/timer/start')
        # Then pause
        response = client.post('/timer/pause')
        assert response.status_code == 200
        data = response.get_json()
        assert data['timer_state'] == 'paused'
```

#### 3. Frontend JavaScript Tests
Create `test_timer_frontend.js` using existing patterns:

```javascript
// Simple test suite for timer functionality
describe('PomodoroTimer', () => {
    let timer;
    
    beforeEach(() => {
        // Setup mock DOM
        document.body.innerHTML = `
            <div id="timerContainer">
                <div id="timerDisplay">25:00</div>
                <div id="timerPhase">Focus Session</div>
                <button id="startPauseBtn">Start</button>
            </div>
        `;
        timer = new PomodoroTimer();
    });
    
    test('initializes with correct state', () => {
        expect(timer.state.timer_state).toBe('idle');
        expect(timer.state.timer_remaining).toBe(0);
    });
    
    test('formats time correctly', () => {
        timer.state.timer_remaining = 125; // 2:05
        timer.updateDisplay();
        expect(timer.display.textContent).toBe('02:05');
    });
});
```

#### 4. Manual Testing Checklist

##### Basic Functionality
- [ ] Timer starts from idle state
- [ ] Timer pauses correctly
- [ ] Timer resets to idle
- [ ] Timer skips to next phase
- [ ] Phase transitions work (session → break → session)
- [ ] Session counter increments correctly
- [ ] Long break triggers after 4 sessions

##### List Integration
- [ ] List switching pauses current timer
- [ ] New lists have correct default timer settings
- [ ] Timer state persists across list operations
- [ ] Deleting active list handles timer correctly

##### Sync & Multi-tab
- [ ] Multiple tabs stay synchronized
- [ ] Background tabs don't waste resources
- [ ] Visibility change triggers sync
- [ ] Network failures handled gracefully

##### User Experience
- [ ] Browser notifications work
- [ ] Sound plays and can be toggled
- [ ] Browser title updates
- [ ] Keyboard shortcuts work
- [ ] Accessibility features work

##### Performance
- [ ] Memory usage stable over long periods
- [ ] CPU usage reasonable
- [ ] No memory leaks on repeated operations
- [ ] Timer accuracy maintained

##### Edge Cases
- [ ] Browser sleep/wake handled
- [ ] Network interruption recovery
- [ ] Invalid server responses handled
- [ ] Rapid user actions debounced

#### 5. Cross-browser Testing
Test on:
- [ ] Chrome (desktop & mobile)
- [ ] Firefox (desktop & mobile)
- [ ] Safari (desktop & mobile)
- [ ] Edge (desktop)

#### 6. Mobile-Specific Testing
- [ ] Responsive design works on small screens
- [ ] Touch interactions work correctly
- [ ] Performance acceptable on mobile devices
- [ ] Background tab behavior correct

### Performance Optimization

#### 1. JavaScript Optimization
```javascript
// Debounce rapid timer operations
debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Debounce rapid clicks
this.startPauseBtn.addEventListener('click', 
    this.debounce(() => this.toggleTimer(), 100)
);
```

#### 2. CSS Optimization
```css
/* Use CSS transforms for animations (better performance) */
.timer-display {
    will-change: transform;
    transform: translateZ(0); /* Force GPU acceleration */
}

/* Reduce repaints with optimized animations */
.progress-bar {
    transform: translateZ(0);
    will-change: width;
}
```

### Final Polish Tasks

#### 1. Code Cleanup
- Remove console.log statements for production
- Add proper JSDoc comments
- Ensure consistent code formatting
- Remove unused CSS/JS

#### 2. Error Handling Enhancement
- Add user-friendly error messages
- Implement proper error logging
- Add fallback behavior for edge cases

#### 3. Documentation Updates
- Update README.md with timer features
- Add user guide for timer functionality
- Document API endpoints

### Implementation Strategy

#### Step-by-Step Execution Plan
1. **Backend Unit Test Development**
   - Create `test_timer_backend.py` following existing patterns from `test_hierarchy.py`
   - Implement tests for `calculate_remaining_time()` with various scenarios
   - Add tests for `get_next_phase()` phase transition logic
   - Test edge cases like negative times, invalid states
   - Run tests with `pytest test_timer_backend.py`

2. **API Integration Test Development**
   - Create `test_timer_api.py` with comprehensive endpoint testing
   - Test all timer endpoints (`/timer/status`, `/timer/start`, `/timer/pause`, etc.)
   - Test error scenarios (no active list, invalid states)
   - Test authentication requirements for all endpoints
   - Verify JSON response structures and error handling

3. **Frontend JavaScript Test Development**
   - Create `test_timer_frontend.js` using existing JavaScript test patterns
   - Test timer class initialization and state management
   - Test UI updates and display formatting
   - Test event handling and user interactions
   - Verify error handling and network failure scenarios

4. **Manual Testing Execution**
   - Execute comprehensive manual testing checklist
   - Test basic timer functionality (start/pause/reset/skip)
   - Test list integration and switching behavior
   - Test multi-tab synchronization and background behavior
   - Test UX features (notifications, sounds, accessibility)
   - Test performance under extended operation

5. **Cross-Browser and Device Testing**
   - Test timer functionality on Chrome, Firefox, Safari, Edge
   - Test mobile responsiveness and touch interactions
   - Verify notifications and sound across platforms
   - Test accessibility features with screen readers
   - Document any browser-specific issues or workarounds

6. **Performance Optimization Implementation**
   - Add debounce logic for rapid user interactions
   - Optimize CSS animations with GPU acceleration
   - Implement memory leak prevention and cleanup
   - Monitor and optimize CPU usage during extended operation
   - Profile and optimize network request patterns

#### Success Criteria
- All automated tests pass consistently
- Manual testing checklist fully completed
- Cross-browser compatibility verified
- Performance benchmarks meet requirements
- Accessibility features work correctly
- Code is clean, documented, and maintainable

#### Risk Mitigation
- **Test coverage gaps**: Ensure all code paths and edge cases are tested
- **Browser compatibility**: Test thoroughly across target browsers and devices
- **Performance issues**: Monitor and optimize resource usage
- **Accessibility gaps**: Test with actual assistive technologies
- **Documentation drift**: Keep documentation updated with code changes

#### Testing Strategy
- **Automated testing**: Comprehensive unit and integration tests
- **Manual testing**: Detailed checklist-based testing
- **Performance testing**: Monitor resource usage and responsiveness
- **Accessibility testing**: Screen reader and keyboard navigation testing
- **Cross-browser testing**: Verify functionality across browsers
- **Device testing**: Test on mobile and desktop platforms

#### Integration Details
- Follow existing test patterns and naming conventions
- Use existing testing frameworks and tools
- Maintain existing code style and documentation standards
- Ensure all tests are repeatable and reliable
- Document any browser-specific limitations or requirements

### Manual Verification Checklist
- [ ] All automated tests pass
- [ ] Manual testing checklist completed
- [ ] Cross-browser compatibility verified
- [ ] Mobile testing completed
- [ ] Performance benchmarks meet requirements
- [ ] Accessibility testing passed
- [ ] Error scenarios handled gracefully
- [ ] Documentation is complete and accurate
- [ ] Code is clean and maintainable
- [ ] User experience is polished

**Duration: 2-3 days**
**Final implementation complete**

---

# Implementation Summary

This roadmap provides a complete, phase-by-phase approach to implementing a robust Pomodoro timer that:

- **Builds incrementally** on existing Flask architecture
- **Maintains current patterns** and code style
- **Provides manual verification** after each phase
- **Handles all edge cases** and complex scenarios
- **Ensures accessibility** and cross-browser compatibility
- **Includes comprehensive testing** and performance optimization

Each phase builds upon the previous one, with clear stopping points for manual verification before proceeding to ensure quality and maintainability.

