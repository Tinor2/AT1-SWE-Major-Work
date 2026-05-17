# Task Time Tracking Feature Roadmap

## Overview
Add the ability to select specific todo list items and track the amount of Pomodoro session time spent on each task. Break times should not count towards task time.

## Phase 1: Database Design & Migration

### 1.1 Design Database Schema
Create a new table to track time sessions per task:

```sql
CREATE TABLE task_time_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    session_start_at TEXT NOT NULL,  -- ISO datetime
    session_end_at TEXT,              -- ISO datetime (null for active sessions)
    duration_seconds INTEGER NOT NULL DEFAULT 0,  -- Calculated duration
    is_active BOOLEAN NOT NULL DEFAULT 0,  -- Whether this is the current active session
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
```

### 1.2 Add Task Time Summary Column
Add a column to the `tasks` table for quick access to total time:

```sql
ALTER TABLE tasks ADD COLUMN total_time_seconds INTEGER DEFAULT 0;
```

### 1.3 Create Migration File
Create `migrations/006_add_task_time_tracking.sql`:

```sql
-- Create task time sessions table
CREATE TABLE task_time_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    session_start_at TEXT NOT NULL,
    session_end_at TEXT,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Add total time column to tasks table
ALTER TABLE tasks ADD COLUMN total_time_seconds INTEGER DEFAULT 0;

-- Create index for performance
CREATE INDEX idx_task_time_sessions_task_user ON task_time_sessions (task_id, user_id);
CREATE INDEX idx_task_time_sessions_active ON task_time_sessions (is_active, user_id);
```

## Phase 2: Model Layer Updates

### 2.1 Create Time Tracking Model
Create `pomodoro/models/time_tracking.py`:

```python
from ..db import get_db
from datetime import datetime, timezone

def start_task_session(task_id, user_id):
    """Start a new time tracking session for a task."""
    db = get_db()
    
    # End any existing active sessions for this user
    db.execute(
        'UPDATE task_time_sessions SET is_active = 0, session_end_at = ?, duration_seconds = ? WHERE is_active = 1 AND user_id = ?',
        (datetime.now(timezone.utc).isoformat(), 0, user_id)
    )
    
    # Start new session
    db.execute(
        'INSERT INTO task_time_sessions (task_id, user_id, session_start_at, is_active) VALUES (?, ?, ?, 1)',
        (task_id, user_id, datetime.now(timezone.utc).isoformat())
    )
    db.commit()

def end_current_session(user_id):
    """End the current active time tracking session."""
    db = get_db()
    
    # Get current active session
    session = db.execute(
        'SELECT * FROM task_time_sessions WHERE is_active = 1 AND user_id = ?',
        (user_id,)
    ).fetchone()
    
    if session:
        end_time = datetime.now(timezone.utc)
        start_time = datetime.fromisoformat(session['session_start_at'].replace('Z', '+00:00'))
        duration = int((end_time - start_time).total_seconds())
        
        # Update session
        db.execute(
            'UPDATE task_time_sessions SET is_active = 0, session_end_at = ?, duration_seconds = ? WHERE id = ?',
            (end_time.isoformat(), duration, session['id'])
        )
        
        # Update task total time
        db.execute(
            'UPDATE tasks SET total_time_seconds = total_time_seconds + ? WHERE id = ?',
            (duration, session['task_id'])
        )
        db.commit()

def get_active_session(user_id):
    """Get the current active time tracking session."""
    db = get_db()
    return db.execute(
        'SELECT tts.*, t.content as task_content FROM task_time_sessions tts JOIN tasks t ON tts.task_id = t.id WHERE tts.is_active = 1 AND tts.user_id = ?',
        (user_id,)
    ).fetchone()

def get_task_time_summary(task_id, user_id):
    """Get total time spent on a task."""
    db = get_db()
    result = db.execute(
        'SELECT COALESCE(SUM(duration_seconds), 0) as total_seconds FROM task_time_sessions WHERE task_id = ? AND user_id = ?',
        (task_id, user_id)
    ).fetchone()
    return result['total_seconds'] if result else 0

def get_task_sessions(task_id, user_id, limit=10):
    """Get recent time sessions for a task."""
    db = get_db()
    return db.execute(
        'SELECT * FROM task_time_sessions WHERE task_id = ? AND user_id = ? ORDER BY created_at DESC LIMIT ?',
        (task_id, user_id, limit)
    ).fetchall()
```

### 2.2 Update Task Model
Add time tracking functions to `pomodoro/models/task.py`:

```python
def update_task_total_time(task_id, user_id):
    """Recalculate and update total time for a task."""
    db = get_db()
    total_time = get_task_time_summary(task_id, user_id)
    db.execute(
        'UPDATE tasks SET total_time_seconds = ? WHERE id = ? AND user_id = ?',
        (total_time, task_id, user_id)
    )
    db.commit()

def get_tasks_with_time(list_id, user_id):
    """Get tasks with their total time included."""
    db = get_db()
    return db.execute(
        '''SELECT t.*, COALESCE(tts.total_time, 0) as total_time_seconds
           FROM tasks t 
           LEFT JOIN (
               SELECT task_id, SUM(duration_seconds) as total_time 
               FROM task_time_sessions 
               WHERE user_id = ? 
               GROUP BY task_id
           ) tts ON t.id = tts.task_id
           WHERE t.list_id = ? AND t.user_id = ?
           ORDER BY t.level ASC, t.position ASC''',
        (user_id, list_id, user_id)
    ).fetchall()
```

## Phase 3: Timer Logic Updates

### 3.1 Update Timer State Management
Modify `pomodoro/routes/timer.py`:

```python
def update_timer_state(list_id, state, remaining=None, sessions_completed=None, current_phase=None, selected_task_id=None):
    """Update timer state with task tracking."""
    from .. import db
    from ..models.time_tracking import start_task_session, end_current_session
    
    db = db.get_db()
    
    # Handle task session management
    if state == 'running' and selected_task_id and current_phase == 'session':
        # Start tracking time for selected task during work session
        start_task_session(selected_task_id, current_user.id)
    elif state in ('paused', 'idle', 'short_break', 'long_break'):
        # End time tracking when not in work session
        end_current_session(current_user.id)
    
    # Update existing timer state logic...
    # (rest of the function remains the same)
```

### 3.2 Add Selected Task to Timer Status
Update timer status endpoint to include selected task:

```python
@bp.route('/status', methods=['GET'])
@login_required
def get_timer_status():
    """Get current timer state including selected task."""
    from ..models.list import get_active_list
    from ..models.time_tracking import get_active_session
    
    active_list = get_active_list(current_user.id)
    active_session = get_active_session(current_user.id)
    
    # ... existing timer logic ...
    
    return jsonify({
        'timer_state': timer_state,
        'remaining': remaining,
        'selected_task': {
            'id': active_session['task_id'] if active_session else None,
            'content': active_session['task_content'] if active_session else None
        },
        'sessions_completed': sessions_completed,
        'current_phase': current_phase
    })
```

## Phase 4: Task Selection UI

### 4.1 Add Task Selection to Template
Update `pomodoro/templates/home/partials/task_item.html`:

```html
<div class="task-header">
    <!-- Add task selection checkbox -->
    <input type="checkbox" 
           class="task-selector" 
           data-task-id="{{ task.id }}"
           {% if active_session and active_session.task_id == task.id %}checked{% endif %}>
    
    <!-- Existing task content -->
    <div class="drag-handle">⋮⋮</div>
    <!-- ... rest of existing content ... -->
    
    <!-- Add time display -->
    <div class="task-time-display">
        {% if task.total_time_seconds > 0 %}
            <span class="time-spent" title="Total time spent">
                {{ format_duration(task.total_time_seconds) }}
            </span>
        {% endif %}
    </div>
</div>
```

### 4.2 Create Time Display Helper
Add to `pomodoro/templates/base.html`:

```html
<script>
// Time formatting helper
function formatDuration(seconds) {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
}
</script>
```

## Phase 5: Frontend Integration

### 5.1 Task Selection JavaScript
Create `pomodoro/static/js/task-time-tracking.js`:

```javascript
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
            const response = await fetch('/timer/select-task', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({task_id: taskId})
            });
            
            if (response.ok) {
                this.selectedTaskId = taskId;
                this.updateUI();
            }
        } catch (error) {
            console.error('Failed to select task:', error);
        }
    }

    async deselectTask() {
        try {
            await fetch('/timer/deselect-task', {method: 'POST'});
            this.selectedTaskId = null;
            this.updateUI();
        } catch (error) {
            console.error('Failed to deselect task:', error);
        }
    }

    observeTimerState() {
        // Poll timer status every 5 seconds
        setInterval(() => this.updateTimerStatus(), 5000);
    }

    async updateTimerStatus() {
        try {
            const response = await fetch('/timer/status');
            const data = await response.json();
            
            if (data.selected_task?.id !== this.selectedTaskId) {
                this.selectedTaskId = data.selected_task?.id;
                this.updateUI();
            }
        } catch (error) {
            console.error('Failed to update timer status:', error);
        }
    }

    updateUI() {
        // Update task selection checkboxes
        document.querySelectorAll('.task-selector').forEach(cb => {
            cb.checked = parseInt(cb.dataset.taskId) === this.selectedTaskId;
        });

        // Update selected task display
        const selectedDisplay = document.getElementById('selected-task-display');
        if (selectedDisplay && this.selectedTaskId) {
            const taskElement = document.querySelector(`[data-task-id="${this.selectedTaskId}"] .task-content`);
            if (taskElement) {
                selectedDisplay.textContent = `Working on: ${taskElement.textContent}`;
                selectedDisplay.style.display = 'block';
            }
        } else if (selectedDisplay) {
            selectedDisplay.style.display = 'none';
        }
    }

    async loadCurrentSession() {
        await this.updateTimerStatus();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new TaskTimeTracker();
});
```

### 5.2 Update Home Template
Add to `pomodoro/templates/home/index.html`:

```html
<!-- Add selected task display -->
<div id="selected-task-display" class="selected-task-display" style="display: none;">
    Working on: <span id="selected-task-name"></span>
</div>

<!-- Include time tracking script -->
<script src="{{ url_for('static', filename='js/task-time-tracking.js') }}"></script>
```

## Phase 6: API Endpoints

### 6.1 Task Selection Endpoints
Add to `pomodoro/routes/timer.py`:

```python
@bp.route('/select-task', methods=['POST'])
@login_required
def select_task():
    """Select a task for time tracking."""
    if not request.is_json:
        return jsonify({'error': 'Invalid request format'}), 400
    
    data = request.get_json()
    task_id = data.get('task_id')
    
    if not task_id:
        return jsonify({'error': 'Task ID required'}), 400
    
    from ..models.task import get_task_by_id
    task = get_task_by_id(task_id, current_user.id)
    
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    # Store selected task in session or database
    session['selected_task_id'] = task_id
    
    # If timer is currently running in session mode, start tracking
    # (This will be handled by timer state updates)
    
    return jsonify({'success': True, 'task_id': task_id})

@bp.route('/deselect-task', methods=['POST'])
@login_required
def deselect_task():
    """Deselect current task."""
    session.pop('selected_task_id', None)
    
    # End any active time tracking session
    from ..models.time_tracking import end_current_session
    end_current_session(current_user.id)
    
    return jsonify({'success': True})
```

### 6.2 Time Summary Endpoint
Add to `pomodoro/routes/tasks.py`:

```python
@bp.route('/task/<int:id>/time-summary', methods=['GET'])
@login_required
def task_time_summary(id):
    """Get time tracking summary for a task."""
    from ..models.time_tracking import get_task_sessions, get_task_time_summary
    
    task = get_task_by_id(id, current_user.id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    sessions = get_task_sessions(id, current_user.id)
    total_seconds = get_task_time_summary(id, current_user.id)
    
    return jsonify({
        'task_id': id,
        'total_seconds': total_seconds,
        'sessions': [dict(session) for session in sessions]
    })
```

## Phase 7: CSS Styling

### 7.1 Add Time Tracking Styles
Create `pomodoro/static/css/time-tracking.css`:

```css
/* Task selection styling */
.task-selector {
    margin-right: 8px;
    cursor: pointer;
}

.task-selector:checked + .task-content {
    font-weight: bold;
    color: #2196F3;
}

/* Time display styling */
.task-time-display {
    margin-left: auto;
    font-size: 0.8em;
    color: #666;
}

.time-spent {
    background: #f0f0f0;
    padding: 2px 6px;
    border-radius: 12px;
    font-weight: 500;
}

/* Selected task display */
.selected-task-display {
    background: #e3f2fd;
    border: 1px solid #2196F3;
    border-radius: 4px;
    padding: 8px 12px;
    margin-bottom: 16px;
    font-weight: 500;
    color: #1976D2;
}

/* Task item highlight when selected */
.task-item[data-selected="true"] {
    background: #f5f5f5;
    border-left: 4px solid #2196F3;
}
```

## Phase 8: Testing & Verification

### 8.1 Unit Tests
Create test cases for:
- Time session creation and ending
- Task total time calculations
- Timer state integration
- API endpoint responses

### 8.2 Integration Tests
Test complete workflows:
1. Select task → Start timer → Verify time tracking
2. Pause timer → Verify time tracking stops
3. Switch tasks → Verify correct task tracking
4. Complete session → Verify total time updates

### 8.3 Edge Cases
- Timer starts without task selected
- Task deleted during active session
- Multiple browser tabs with same user
- Session timeout handling

## Implementation Order

1. **Phase 1-2**: Database and Model Layer (Foundation)
2. **Phase 3**: Timer Logic Updates (Core functionality)
3. **Phase 4-5**: UI Components (User interface)
4. **Phase 6**: API Endpoints (Backend integration)
5. **Phase 7**: Styling (Visual polish)
6. **Phase 8**: Testing (Quality assurance)

## Success Criteria

- ✅ Users can select a task via checkbox
- ✅ Timer only tracks time during work sessions
- ✅ Break times do not count toward task time
- ✅ Total time displays per task
- ✅ Time persists across sessions
- ✅ Multiple tasks can be tracked over time
- ✅ Clean UI showing current selected task
- ✅ No performance impact on existing features

## Technical Considerations

- **Performance**: Use database indexes for time queries
- **Accuracy**: Handle timezone conversions properly
- **Concurrency**: Prevent multiple active sessions per user
- **Data Integrity**: Ensure time calculations are consistent
- **User Experience**: Clear visual feedback for task selection
